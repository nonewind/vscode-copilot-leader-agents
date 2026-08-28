#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "benchmark.json"
RUBRIC_PATH = ROOT / "evaluator" / "rubric.json"
RUNS_DIR = ROOT / "runs"
SCOREBOARD_PATH = ROOT / "scoreboard" / "runs.csv"
SCOREBOARD_FIELDS = [
    "run_id", "benchmark_version", "model", "provider", "price_note", "context_window", "input_tokens",
    "output_tokens", "cost_amount", "cost_currency", "score_per_cost_unit", "started_at", "finished_at",
    "duration_minutes", "worker_calls", "tool_actions", "rework_rounds", "fallback_used", "correctness",
    "engineering", "efficiency", "integrity", "total", "grade", "reasoning_index", "diligence_index",
    "slacking_index", "status", "metrics_complete", "protected_changed", "review_note",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_manifest(root: Path, globs: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for pattern in globs:
        if pattern.endswith("/**"):
            paths = (root / pattern[:-3]).rglob("*")
        else:
            paths = root.glob(pattern)
        for path in sorted(paths):
            if path.is_file():
                result[path.relative_to(root).as_posix()] = sha256(path)
    return result


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return normalized[:28] or "model"


def load_run(run_id: str) -> tuple[Path, dict[str, Any]]:
    run_dir = RUNS_DIR / run_id
    metadata_path = run_dir / "run.json"
    if not metadata_path.is_file():
        raise SystemExit(f"Unknown run_id: {run_id}")
    return run_dir, read_json(metadata_path)


def prepare(args: argparse.Namespace) -> None:
    config = read_json(CONFIG_PATH)
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{slug(args.model)}-{uuid.uuid4().hex[:6]}"
    run_dir = RUNS_DIR / run_id
    workspace = run_dir / "workspace"
    shutil.copytree(
        ROOT / config["candidate_root"],
        workspace,
        ignore=shutil.ignore_patterns("node_modules", "dist", "__pycache__", ".pytest_cache", "*.db"),
    )
    manifest = protected_manifest(workspace, config["protected_globs"])
    metadata = {
        "run_id": run_id,
        "benchmark_id": config["id"],
        "benchmark_version": config["version"],
        "model": args.model,
        "provider": args.provider,
        "price_note": args.price_note,
        "leader_model": args.leader_model,
        "context_window": args.context_window,
        "prepared_at": utc_now(),
        "started_at": None,
        "finished_at": None,
        "worker_calls": None,
        "tool_actions": None,
        "rework_rounds": None,
        "input_tokens": None,
        "output_tokens": None,
        "cost_amount": None,
        "cost_currency": "",
        "fallback_used": False,
        "claims": [],
        "engineering_review_score": None,
        "engineering_review_note": "",
        "invalid_reason": "",
        "protected_manifest": manifest,
    }
    write_json(run_dir / "run.json", metadata)
    print(json.dumps({"run_id": run_id, "workspace": str(workspace)}, ensure_ascii=False, indent=2))


def start(args: argparse.Namespace) -> None:
    run_dir, metadata = load_run(args.run_id)
    if metadata.get("started_at") and not args.restart:
        raise SystemExit("Run already started; pass --restart only when intentionally discarding the old timing")
    metadata["started_at"] = utc_now()
    metadata["finished_at"] = None
    write_json(run_dir / "run.json", metadata)
    print(f"Started {args.run_id} at {metadata['started_at']}")


def record(args: argparse.Namespace) -> None:
    run_dir, metadata = load_run(args.run_id)
    for key in ("worker_calls", "tool_actions", "rework_rounds", "input_tokens", "output_tokens"):
        value = getattr(args, key)
        if value is not None:
            if value < 0:
                raise SystemExit(f"{key} cannot be negative")
            metadata[key] = value
    if args.cost_amount is not None:
        if args.cost_amount < 0:
            raise SystemExit("cost-amount cannot be negative")
        if not args.cost_currency:
            raise SystemExit("cost-currency is required with cost-amount")
        metadata["cost_amount"] = args.cost_amount
        metadata["cost_currency"] = args.cost_currency.upper()
    if args.fallback_used:
        metadata["fallback_used"] = True
    if args.claim:
        metadata["claims"] = sorted(set(metadata.get("claims", []) + args.claim))
    if args.engineering_score is not None:
        if not 0 <= args.engineering_score <= 7:
            raise SystemExit("engineering-score must be between 0 and 7")
        if not args.engineering_note:
            raise SystemExit("engineering-note is required with engineering-score")
        metadata["engineering_review_score"] = args.engineering_score
        metadata["engineering_review_note"] = args.engineering_note
    if args.invalid_reason:
        metadata["invalid_reason"] = args.invalid_reason
    write_json(run_dir / "run.json", metadata)
    print(f"Recorded metrics for {args.run_id}")


def run_command(
    command: list[str], cwd: Path, output_path: Path, env: dict[str, str] | None = None
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
            check=False,
        )
        output = completed.stdout
        returncode = completed.returncode
        status = "passed" if returncode == 0 else "failed"
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        output = str(error)
        returncode = None
        status = "not_run"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    return {
        "status": status,
        "returncode": returncode,
        "seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3),
        "output": str(output_path),
    }


def parse_backend_results(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    return read_json(path).get("tests", [])


def parse_frontend_results(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    try:
        payload = read_json(path)
    except (json.JSONDecodeError, OSError):
        return []
    results: list[dict[str, str]] = []
    for suite in payload.get("testResults", []):
        for assertion in suite.get("assertionResults", []):
            name = assertion.get("fullName") or " ".join(
                [*assertion.get("ancestorTitles", []), assertion.get("title", "")]
            )
            results.append(
                {
                    "nodeid": name,
                    "status": "passed" if assertion.get("status") == "passed" else "failed",
                    "detail": "",
                }
            )
    return results


def static_results(workspace: Path) -> list[dict[str, str]]:
    app_path = workspace / "frontend" / "src" / "App.vue"
    source = app_path.read_text(encoding="utf-8") if app_path.is_file() else ""
    checks = {
        "text_rendering": "v-html" not in source
        and bool(re.search(r"task-title[^>]*>\s*\{\{\s*task\.title\s*\}\}", source)),
        "stable_key": bool(re.search(r":key\s*=\s*[\"']task\.id[\"']", source)),
        "create_disabled": bool(
            re.search(r"<button[^>]+:disabled\s*=\s*[\"'][^\"']*(creating|isCreating)", source)
        ),
        "update_disabled": bool(
            re.search(r"<select[^>]+:disabled\s*=\s*[\"'][^\"']*(pending|updating)", source)
        ),
    }
    return [
        {"nodeid": key, "status": "passed" if passed else "failed", "detail": ""}
        for key, passed in checks.items()
    ]


def score_cases(rubric: dict[str, Any], results: dict[str, list[dict[str, str]]]):
    earned = 0.0
    hard_earned = 0.0
    hard_total = 0.0
    details = []
    for case in rubric["correctness_cases"]:
        matches = [item for item in results.get(case["runner"], []) if case["match"] in item["nodeid"]]
        passed = bool(matches) and all(item["status"] == "passed" for item in matches)
        points = float(case["points"])
        if passed:
            earned += points
        if case.get("hard"):
            hard_total += points
            if passed:
                hard_earned += points
        details.append({**case, "passed": passed, "earned": points if passed else 0.0})
    return round(earned, 2), hard_earned, hard_total, details


def linear_score(value: float | None, excellent: float, limit: float, points: float) -> float:
    if value is None:
        return 0.0
    if value <= excellent:
        return points
    if value >= limit:
        return 0.0
    return points * (limit - value) / (limit - excellent)


def inspect_integrity(workspace: Path, metadata: dict[str, Any], config: dict[str, Any]):
    current = protected_manifest(workspace, config["protected_globs"])
    original = metadata.get("protected_manifest", {})
    protected_changed = sorted(
        key for key in original if original.get(key) != current.get(key)
    )
    forbidden_patterns = [r"\.skip\s*\(", r"\.only\s*\(", r"pytest\.mark\.skip", r"pytest\.skip\s*\("]
    forbidden_hits = []
    for path in workspace.rglob("*"):
        if not path.is_file() or any(part in {"node_modules", ".git", "dist"} for part in path.parts):
            continue
        if any(part in {"evaluator", "hidden_tests"} for part in path.relative_to(workspace).parts):
            forbidden_hits.append(path.relative_to(workspace).as_posix())
            continue
        if path.suffix not in {".py", ".ts", ".vue"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(re.search(pattern, text) for pattern in forbidden_patterns):
            forbidden_hits.append(path.relative_to(workspace).as_posix())
    return protected_changed, sorted(forbidden_hits)


def grade(total: float, correctness: float, protected_changed: list[str]) -> str:
    if protected_changed:
        return "D"
    result = "S" if total >= 90 else "A" if total >= 80 else "B" if total >= 70 else "C" if total >= 60 else "D"
    if correctness < 42 and result in {"S", "A", "B"}:
        return "C"
    return result


def case_category(case_id: str) -> str:
    if case_id.startswith("backend.auth_"):
        return "backend.auth"
    if case_id.startswith("backend.page_") or case_id == "backend.search":
        return "backend.query"
    if "validation" in case_id:
        return "backend.validation"
    if case_id.startswith("backend.idempotency"):
        return "backend.idempotency"
    if case_id.startswith("backend.concurrency"):
        return "backend.concurrency"
    if case_id in {"backend.transaction", "backend.utc"}:
        return case_id
    if case_id in {"frontend.pagination", "frontend.boundaries", "frontend.timezone"}:
        return "frontend.boundaries"
    if case_id in {"frontend.race", "frontend.loading", "frontend.preserve"}:
        return "frontend.async"
    if case_id in {"frontend.rollback", "frontend.duplicate_update"}:
        return "frontend.update"
    if case_id in {"frontend.duplicate_create", "frontend.idempotency"}:
        return "frontend.create"
    if case_id == "frontend.errors":
        return "frontend.errors"
    if case_id.startswith("integration."):
        return "integration.contract"
    return case_id


def update_scoreboard(score: dict[str, Any], metadata: dict[str, Any]) -> None:
    rows = []
    if SCOREBOARD_PATH.is_file():
        with SCOREBOARD_PATH.open(newline="", encoding="utf-8") as stream:
            rows = [row for row in csv.DictReader(stream) if row.get("run_id") != metadata["run_id"]]
    row = {
        "run_id": metadata["run_id"],
        "benchmark_version": metadata["benchmark_version"],
        "model": metadata["model"],
        "provider": metadata["provider"],
        "price_note": metadata.get("price_note", ""),
        "context_window": metadata.get("context_window"),
        "input_tokens": metadata.get("input_tokens"),
        "output_tokens": metadata.get("output_tokens"),
        "cost_amount": metadata.get("cost_amount"),
        "cost_currency": metadata.get("cost_currency", ""),
        "score_per_cost_unit": (
            round(score["total"] / metadata["cost_amount"], 2)
            if metadata.get("cost_amount") not in (None, 0) else None
        ),
        "started_at": metadata["started_at"],
        "finished_at": metadata["finished_at"],
        "duration_minutes": score["duration_minutes"],
        "worker_calls": metadata.get("worker_calls"),
        "tool_actions": metadata.get("tool_actions"),
        "rework_rounds": metadata.get("rework_rounds"),
        "fallback_used": metadata.get("fallback_used", False),
        "correctness": score["correctness"],
        "engineering": score["engineering"],
        "efficiency": score["efficiency"],
        "integrity": score["integrity"],
        "total": score["total"],
        "grade": score["grade"],
        "reasoning_index": score["reasoning_index"],
        "diligence_index": score["diligence_index"],
        "slacking_index": score["slacking_index"],
        "status": score["status"],
        "metrics_complete": score["metrics_complete"],
        "protected_changed": ";".join(score["protected_changed"]),
        "review_note": metadata.get("engineering_review_note", ""),
    }
    rows.append({key: "" if value is None else value for key, value in row.items()})
    SCOREBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCOREBOARD_PATH.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=SCOREBOARD_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def evaluate(args: argparse.Namespace) -> None:
    config = read_json(CONFIG_PATH)
    rubric = read_json(RUBRIC_PATH)
    run_dir, metadata = load_run(args.run_id)
    if not metadata.get("started_at"):
        raise SystemExit(f"Run {args.run_id} has not started; run the start command after environment setup")
    workspace = run_dir / "workspace"
    results_dir = run_dir / "results"
    results_dir.mkdir(exist_ok=True)
    base_env = os.environ.copy()

    public_backend = run_command(
        [sys.executable, "-m", "pytest", "-q"],
        workspace / "backend",
        results_dir / "backend-public.log",
        {**base_env, "PYTHONPATH": str(workspace / "backend")},
    )
    backend_json = results_dir / "backend-hidden.json"
    hidden_backend = run_command(
        [
            sys.executable,
            "-m",
            "pytest",
            str(ROOT / "evaluator" / "backend"),
            "-q",
            "--score-output",
            str(backend_json),
        ],
        workspace / "backend",
        results_dir / "backend-hidden.log",
        {**base_env, "PYTHONPATH": str(workspace / "backend")},
    )

    frontend = workspace / "frontend"
    public_frontend = run_command(
        ["npm", "test", "--", "--run"],
        frontend,
        results_dir / "frontend-public.log",
        {**base_env, "TZ": "Asia/Shanghai", "LANG": "zh_CN.UTF-8"},
    )
    frontend_json = results_dir / "frontend-hidden.json"
    hidden_frontend = run_command(
        [
            "npm", "test", "--", "--run",
            "--config", str(ROOT / "evaluator" / "frontend" / "vitest.config.mjs"),
            "--reporter=json", "--outputFile", str(frontend_json),
        ],
        frontend,
        results_dir / "frontend-hidden.log",
        {
            **base_env,
            "TZ": "Asia/Shanghai",
            "LANG": "zh_CN.UTF-8",
            "CANDIDATE_FRONTEND": str(frontend),
        },
    )
    typecheck = run_command(
        ["npm", "run", "typecheck"],
        frontend,
        results_dir / "frontend-typecheck.log",
        {**base_env, "TZ": "Asia/Shanghai", "LANG": "zh_CN.UTF-8"},
    )

    frontend_case_results = parse_frontend_results(frontend_json)
    hidden_frontend["status"] = (
        "passed"
        if frontend_case_results and all(item["status"] == "passed" for item in frontend_case_results)
        else "failed"
    )
    runner_results = {
        "backend": parse_backend_results(backend_json),
        "frontend": frontend_case_results,
        "static": static_results(workspace),
    }
    correctness, hard_earned, hard_total, case_details = score_cases(rubric, runner_results)

    review_score = metadata.get("engineering_review_score")
    engineering = (3 if typecheck["status"] == "passed" else 0) + (review_score or 0)

    finished = datetime.now(timezone.utc)
    started = datetime.fromisoformat(metadata["started_at"].replace("Z", "+00:00"))
    duration_minutes = round((finished - started).total_seconds() / 60, 2)
    targets = config["efficiency_targets"]
    efficiency = linear_score(duration_minutes, targets["excellent_minutes"], targets["limit_minutes"], 4)
    efficiency += linear_score(metadata.get("tool_actions"), targets["excellent_tool_actions"], targets["limit_tool_actions"], 3)
    worker_calls = metadata.get("worker_calls")
    reworks = metadata.get("rework_rounds")
    if worker_calls == 1 and reworks == 0:
        efficiency += 3
    elif worker_calls is not None and reworks is not None and worker_calls <= 2 and reworks <= 1:
        efficiency += 1.5
    efficiency = round(efficiency, 2)

    protected_changed, forbidden_hits = inspect_integrity(workspace, metadata, config)
    integrity = 0.0 if protected_changed else 5.0
    if not forbidden_hits:
        integrity += 2.0
    command_statuses = {
        "backend": public_backend["status"],
        "frontend": public_frontend["status"],
        "typecheck": typecheck["status"],
    }
    claims = metadata.get("claims", [])
    truthful_count = sum(
        1 for name, status in command_statuses.items()
        if status == "passed" and any(claim.startswith(f"{name}:") for claim in claims)
    )
    integrity += truthful_count
    integrity = round(min(integrity, 10), 2)

    total = round(correctness + engineering + efficiency + integrity, 2)
    if protected_changed:
        total = min(total, rubric["integrity"]["score_cap_on_protected_change"])

    metrics_complete = all(metadata.get(key) is not None for key in ("worker_calls", "tool_actions", "rework_rounds"))
    if metadata.get("invalid_reason"):
        status = "invalid"
    elif protected_changed:
        status = "integrity_violation"
    elif metadata.get("fallback_used"):
        status = "fallback_contaminated"
    elif review_score is None:
        status = "provisional"
    elif not metrics_complete:
        status = "metrics_incomplete"
    else:
        status = "valid"

    if metadata.get("tool_actions") is None:
        reasoning_index = None
    else:
        step_efficiency = min(1.0, targets["excellent_tool_actions"] / max(1, metadata["tool_actions"]))
        reasoning_index = round((hard_earned / hard_total if hard_total else 0) * step_efficiency * 100, 1)

    categories: dict[str, list[dict[str, Any]]] = {}
    for case in case_details:
        categories.setdefault(case_category(case["id"]), []).append(case)
    covered = sum(
        1 for cases in categories.values()
        if sum(item["earned"] for item in cases) >= sum(float(item["points"]) for item in cases) * 0.5
    )
    coverage = covered / len(categories) if categories else 0
    evidence_rate = truthful_count / 3
    integrity_rate = integrity / 10
    report_path = workspace / "FINAL_REPORT.md"
    report_text = report_path.read_text(encoding="utf-8", errors="ignore") if report_path.is_file() else ""
    report_complete = bool(report_text and ("未验证" in report_text or "剩余风险" in report_text))
    diligence = round(coverage * 50 + evidence_rate * 25 + integrity_rate * 15 + (10 if report_complete else 0), 1)

    metadata["finished_at"] = finished.isoformat().replace("+00:00", "Z")
    write_json(run_dir / "run.json", metadata)
    score = {
        "run_id": args.run_id,
        "status": status,
        "correctness": correctness,
        "engineering": round(engineering, 2),
        "efficiency": efficiency,
        "integrity": integrity,
        "total": total,
        "grade": grade(total, correctness, protected_changed),
        "duration_minutes": duration_minutes,
        "reasoning_index": reasoning_index,
        "diligence_index": diligence,
        "slacking_index": round(100 - diligence, 1),
        "metrics_complete": metrics_complete,
        "protected_changed": protected_changed,
        "forbidden_hits": forbidden_hits,
        "commands": {
            "backend_public": public_backend,
            "backend_hidden": hidden_backend,
            "frontend_public": public_frontend,
            "frontend_hidden": hidden_frontend,
            "frontend_typecheck": typecheck,
        },
        "cases": case_details,
    }
    write_json(results_dir / "score.json", score)
    update_scoreboard(score, metadata)
    print(json.dumps({key: score[key] for key in (
        "run_id", "status", "correctness", "engineering", "efficiency", "integrity", "total", "grade",
        "reasoning_index", "diligence_index", "slacking_index", "metrics_complete", "protected_changed",
    )}, ensure_ascii=False, indent=2))


def leaderboard(_args: argparse.Namespace) -> None:
    if not SCOREBOARD_PATH.is_file():
        raise SystemExit("No runs recorded")
    with SCOREBOARD_PATH.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if row.get("status") != "valid" or row.get("metrics_complete", "").lower() != "true":
            continue
        key = (row["benchmark_version"], row["model"], row["provider"])
        groups.setdefault(key, []).append(row)
    output = ROOT / "scoreboard" / "generated" / "leaderboard.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["benchmark_version", "model", "provider", "runs", "median", "min", "max", "completion_rate"]
    generated = []
    for key, items in sorted(groups.items()):
        scores = [float(item["total"]) for item in items]
        completed = sum(float(item["correctness"]) >= 42 for item in items)
        generated.append(
            dict(
                zip(fields[:3], key),
                runs=len(items),
                median=round(statistics.median(scores), 2),
                min=round(min(scores), 2),
                max=round(max(scores), 2),
                completion_rate=round(completed / len(items), 3),
            )
        )
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(generated)
    print(f"Wrote {len(generated)} leaderboard rows to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Poor-mode full-stack benchmark runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="create an isolated candidate workspace")
    prepare_parser.add_argument("--model", required=True)
    prepare_parser.add_argument("--provider", required=True)
    prepare_parser.add_argument("--price-note", default="")
    prepare_parser.add_argument("--leader-model", default="")
    prepare_parser.add_argument("--context-window", type=int)
    prepare_parser.set_defaults(func=prepare)

    record_parser = subparsers.add_parser("record", help="record externally observed process metrics")
    record_parser.add_argument("run_id")
    record_parser.add_argument("--worker-calls", type=int)
    record_parser.add_argument("--tool-actions", type=int)
    record_parser.add_argument("--rework-rounds", type=int)
    record_parser.add_argument("--input-tokens", type=int)
    record_parser.add_argument("--output-tokens", type=int)
    record_parser.add_argument("--cost-amount", type=float)
    record_parser.add_argument("--cost-currency")
    record_parser.add_argument("--fallback-used", action="store_true")
    record_parser.add_argument("--claim", action="append")
    record_parser.add_argument("--engineering-score", type=float)
    record_parser.add_argument("--engineering-note")
    record_parser.add_argument("--invalid-reason")
    record_parser.set_defaults(func=record)

    start_parser = subparsers.add_parser("start", help="start wall-clock timing after environment setup")
    start_parser.add_argument("run_id")
    start_parser.add_argument("--restart", action="store_true")
    start_parser.set_defaults(func=start)

    evaluate_parser = subparsers.add_parser("evaluate", help="run hidden checks and calculate a score")
    evaluate_parser.add_argument("run_id")
    evaluate_parser.set_defaults(func=evaluate)

    leaderboard_parser = subparsers.add_parser("leaderboard", help="rebuild the aggregate leaderboard")
    leaderboard_parser.set_defaults(func=leaderboard)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
