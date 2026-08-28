from __future__ import annotations

import importlib.util
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    path = ROOT / "tools" / "benchmark.py"
    spec = importlib.util.spec_from_file_location("poor_mode_benchmark", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_rubric_has_exact_score_buckets():
    rubric = json.loads((ROOT / "evaluator" / "rubric.json").read_text(encoding="utf-8"))
    cases = rubric["correctness_cases"]
    assert sum(case["points"] for case in cases) == 70
    assert sum(case["points"] for case in cases if case["runner"] == "backend") == 35
    assert sum(case["points"] for case in cases if case["runner"] == "frontend") == 30
    assert sum(case["points"] for case in cases if case["runner"] == "static") == 5
    assert len({case["id"] for case in cases}) == len(cases)
    assert all(case["match"] for case in cases)


def test_candidate_pack_does_not_contain_evaluator_material():
    candidate = ROOT / "candidate"
    relative_files = {
        path.relative_to(candidate).as_posix()
        for path in candidate.rglob("*")
        if path.is_file() and "node_modules" not in path.parts
    }
    assert not any("hidden" in name.lower() for name in relative_files)
    assert not any(name.startswith("evaluator/") for name in relative_files)
    assert "TASK.md" in relative_files
    assert "CONTRACT.md" in relative_files


def test_protected_manifest_detects_changes(tmp_path):
    runner = load_runner()
    source = ROOT / "candidate"
    target = tmp_path / "candidate"
    import shutil

    shutil.copytree(source, target)
    config = json.loads((ROOT / "benchmark.json").read_text(encoding="utf-8"))
    before = runner.protected_manifest(target, config["protected_globs"])
    assert "backend/tests/test_smoke.py" in before
    assert "frontend/tests/smoke.spec.ts" in before
    (target / "TASK.md").write_text("tampered", encoding="utf-8")
    after = runner.protected_manifest(target, config["protected_globs"])
    assert before["TASK.md"] != after["TASK.md"]


def test_case_scoring_requires_every_parameterized_row():
    runner = load_runner()
    rubric = {
        "correctness_cases": [
            {"id": "matrix", "runner": "backend", "match": "case", "points": 3, "hard": True}
        ]
    }
    earned, hard_earned, hard_total, _ = runner.score_cases(
        rubric,
        {"backend": [
            {"nodeid": "case[a]", "status": "passed"},
            {"nodeid": "case[b]", "status": "failed"},
        ]},
    )
    assert earned == 0
    assert hard_earned == 0
    assert hard_total == 3


def test_linear_efficiency_does_not_reward_missing_metrics():
    runner = load_runner()
    assert runner.linear_score(None, 18, 55, 3) == 0
    assert runner.linear_score(18, 18, 55, 3) == 3
    assert runner.linear_score(55, 18, 55, 3) == 0


def test_cases_roll_up_to_stable_capability_categories():
    runner = load_runner()
    assert runner.case_category("backend.auth_patch") == "backend.auth"
    assert runner.case_category("backend.page_invalid") == "backend.query"
    assert runner.case_category("frontend.race") == "frontend.async"
    assert runner.case_category("integration.stable_key") == "integration.contract"


def test_scoreboard_schema_matches_runner():
    runner = load_runner()
    with (ROOT / "scoreboard" / "runs.csv").open(newline="", encoding="utf-8") as stream:
        header = next(csv.reader(stream))
    assert header == runner.SCOREBOARD_FIELDS
