#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.9/3.10: retain the conservative line parser below.
    tomllib = None


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "codex"
START_MARKER = "<!-- leader-worker-codex:start -->"
END_MARKER = "<!-- leader-worker-codex:end -->"
STATE_NAME = "leader-worker-install-state.json"
EXECUTION_PATTERN = re.compile(r"(?m)^leader-worker-execution-mode:\s*(strict|adaptive)\s*$")
FALLBACK_PATTERN = re.compile(r"(?m)^leader-worker-fallback-mode:\s*(stop|parent-worker)\s*$")
MANAGED_AGENT_KEYS = {
    "enabled": "true",
    "max_concurrent_threads_per_session": "4",
}
LEGACY_AGENT_DEFAULTS = {
    "default_subagent_model": '"gpt-5.6-luna"',
    "default_subagent_reasoning_effort": '"high"',
}
BASE_AGENT_FILES = tuple(f"leader-{name}.toml" for name in ("analyzer", "implementer", "tester", "reviewer"))
FALLBACK_AGENT_FILES = tuple(
    f"leader-{name}-fallback.toml" for name in ("analyzer", "implementer", "tester", "reviewer")
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install project-scoped Codex Leader/Worker agents, skill, and policy"
    )
    parser.add_argument("--project", type=Path, required=True, help="Target project root")
    parser.add_argument("--mode", choices=("strict", "adaptive"), help="Leader execution mode; preserves a valid installed mode when omitted")
    parser.add_argument("--fallback", choices=("stop", "parent-worker"), help="Model fallback mode; preserves a valid installed mode when omitted")
    parser.add_argument(
        "--migrate-agent-defaults",
        action="store_true",
        help="Remove only exact legacy Leader/Worker model and effort defaults after a backup",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def backup(path: Path, stamp: str, dry_run: bool) -> Path | None:
    if not path.exists():
        return None
    target = path.with_name(f"{path.name}.backup-{stamp}")
    print(f"Backup: {path} -> {target}")
    if not dry_run:
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
    return target


def atomic_write(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.tmp-",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot safely read managed Codex install state {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"Managed Codex install state is not an object: {path}")
    return value


def managed_block(existing: str, target: Path) -> str | None:
    if START_MARKER not in existing and END_MARKER not in existing:
        return None
    if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
        raise RuntimeError(f"Cannot safely update malformed managed markers in {target}")
    start = existing.index(START_MARKER) + len(START_MARKER)
    end = existing.index(END_MARKER, start)
    return existing[start:end]


def detected_mode(block: str | None, pattern: re.Pattern[str]) -> str | None:
    if block is None:
        return None
    matches = pattern.findall(block)
    return matches[0] if len(matches) == 1 else None


def render_policy(execution_mode: str, fallback_mode: str) -> str:
    policy = (SOURCE_ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
    execution_matches = re.findall(r"(?m)^leader-worker-execution-mode:\s*strict\s*$", policy)
    fallback_matches = re.findall(r"(?m)^leader-worker-fallback-mode:\s*stop\s*$", policy)
    if len(execution_matches) != 1:
        raise RuntimeError("Codex source policy must contain one strict execution-mode declaration")
    if len(fallback_matches) != 1:
        raise RuntimeError("Codex source policy must contain one stop fallback-mode declaration")
    policy = re.sub(
        r"(?m)^leader-worker-execution-mode:\s*strict\s*$",
        f"leader-worker-execution-mode: {execution_mode}",
        policy,
        count=1,
    )
    policy = re.sub(
        r"(?m)^leader-worker-fallback-mode:\s*stop\s*$",
        f"leader-worker-fallback-mode: {fallback_mode}",
        policy,
        count=1,
    )
    return policy


def merged_policy_text(existing: str, target: Path, execution_mode: str, fallback_mode: str) -> str:
    block = f"{START_MARKER}\n{render_policy(execution_mode, fallback_mode)}\n{END_MARKER}"
    current_block = managed_block(existing, target)
    if current_block is not None:
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        return existing[:start] + block + existing[end:]
    separator = "\n\n" if existing.strip() else ""
    return existing.rstrip() + separator + block + "\n"


def section_bounds(lines: list[str], section: str) -> tuple[int, int] | None:
    header = f"[{section}]"
    if sum(line.strip() == header for line in lines) > 1:
        raise RuntimeError(f"Duplicate TOML section is not safe to merge: {header}")
    for index, line in enumerate(lines):
        if line.strip() != header:
            continue
        end = len(lines)
        for cursor in range(index + 1, len(lines)):
            if re.match(r"^\s*\[", lines[cursor]):
                end = cursor
                break
        return index, end
    return None


def scan_unmanaged_agents(project: Path) -> list[str]:
    agents = project / ".codex" / "agents"
    managed = set(BASE_AGENT_FILES) | set(FALLBACK_AGENT_FILES)
    impacted: list[str] = []
    if not agents.exists():
        return impacted
    for path in sorted(agents.glob("*.toml")):
        if path.name in managed:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing = [
            key
            for key in ("model", "model_reasoning_effort")
            if not re.search(rf"(?m)^\s*{re.escape(key)}\s*=", text)
        ]
        if missing:
            impacted.append(f"{path.name} (missing {', '.join(missing)})")
    return impacted


def merged_config_text(
    project: Path,
    existing: str,
    fallback_mode: str,
    migrate_agent_defaults: bool,
) -> tuple[str, list[str]]:
    if existing.strip() and tomllib is not None:
        try:
            tomllib.loads(existing)
        except Exception as exc:
            raise RuntimeError(f"Cannot safely parse existing Codex config: {exc}") from exc

    lines = existing.splitlines()
    bounds = section_bounds(lines, "agents")
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[agents]")
        bounds = (len(lines) - 1, len(lines))

    start, end = bounds
    entries: dict[str, tuple[str, int]] = {}
    for index in range(start + 1, end):
        line = lines[index]
        match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*(?:#.*)?$", line)
        if not match:
            continue
        key, value = match.groups()
        if key in entries:
            raise RuntimeError(f"Duplicate TOML key is not safe to merge: agents.{key}")
        entries[key] = (value, index)

    conflicts = [
        f"agents.{key}={entries[key][0]} (required {required})"
        for key, required in MANAGED_AGENT_KEYS.items()
        if key in entries and entries[key][0] != required
    ]
    if conflicts:
        raise RuntimeError("Refusing to overwrite existing Codex settings: " + ", ".join(conflicts))

    legacy_lines: list[int] = []
    custom_defaults: list[str] = []
    for key, old_value in LEGACY_AGENT_DEFAULTS.items():
        if key not in entries:
            continue
        value, index = entries[key]
        if value == old_value:
            legacy_lines.append(index)
        else:
            custom_defaults.append(f"agents.{key}={value}")

    if legacy_lines and not migrate_agent_defaults:
        raise RuntimeError(
            "Legacy Codex subagent defaults require explicit migration. "
            "Review their project-wide impact, then rerun with --migrate-agent-defaults."
        )
    if fallback_mode == "parent-worker" and custom_defaults:
        raise RuntimeError(
            "Parent-model fallback cannot inherit while custom project defaults remain: "
            + ", ".join(custom_defaults)
        )

    removed = [lines[index].strip() for index in legacy_lines]
    if legacy_lines:
        for index in sorted(legacy_lines, reverse=True):
            del lines[index]
        bounds = section_bounds(lines, "agents")
        if bounds is None:
            raise RuntimeError("Internal error: [agents] section disappeared during migration")
        start, end = bounds

    current_keys: set[str] = set()
    for line in lines[start + 1:end]:
        match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=", line)
        if match:
            current_keys.add(match.group(1))
    additions = [
        f"{key} = {value}"
        for key, value in MANAGED_AGENT_KEYS.items()
        if key not in current_keys
    ]
    lines[end:end] = additions
    merged = "\n".join(lines) + "\n"
    if removed:
        impacted = scan_unmanaged_agents(project)
        print("Migrate exact legacy [agents] defaults: " + ", ".join(removed))
        print(
            "WARNING: removing project-wide defaults can change model or effort inheritance "
            "for built-in and unmanaged custom subagents."
        )
        if impacted:
            print("Unmanaged agent files that may inherit differently:")
            for item in impacted:
                print(f"  - {item}")
    return merged, removed


def preflight_fallback_files(
    project: Path,
    fallback_mode: str,
    state: dict[str, object],
) -> tuple[dict[Path, str], list[Path], dict[str, str]]:
    target_root = project / ".codex" / "agents"
    recorded = state.get("fallback_files", {})
    recorded_hashes = recorded if isinstance(recorded, dict) else {}
    writes: dict[Path, str] = {}
    removals: list[Path] = []
    next_hashes: dict[str, str] = {}

    for filename in FALLBACK_AGENT_FILES:
        source = SOURCE_ROOT / "agents" / filename
        target = target_root / filename
        content = source.read_text(encoding="utf-8")
        if fallback_mode == "parent-worker":
            if target.exists():
                expected = recorded_hashes.get(filename)
                if not isinstance(expected, str) or file_hash(target) != expected:
                    raise RuntimeError(f"Refusing to overwrite unowned or modified fallback agent: {target}")
            writes[target] = content
            next_hashes[filename] = text_hash(content)
            continue

        if not target.exists():
            continue
        expected = recorded_hashes.get(filename)
        if not isinstance(expected, str) or file_hash(target) != expected:
            raise RuntimeError(f"Refusing to remove unowned or modified fallback agent: {target}")
        removals.append(target)

    return writes, removals, next_hashes


def install(project: Path, requested_mode: str | None, requested_fallback: str | None, migrate: bool, dry_run: bool) -> None:
    project = project.expanduser().resolve()
    if not project.exists() or not project.is_dir():
        raise RuntimeError(f"Project directory does not exist: {project}")

    policy_target = project / "AGENTS.md"
    policy_existing = policy_target.read_text(encoding="utf-8") if policy_target.exists() else ""
    block = managed_block(policy_existing, policy_target)
    old_mode = detected_mode(block, EXECUTION_PATTERN)
    old_fallback = detected_mode(block, FALLBACK_PATTERN)
    if block is not None and old_mode is None:
        print("WARNING: missing, duplicate, or malformed execution mode; defaulting to strict unless explicitly requested.")
    if block is not None and old_fallback is None:
        print("WARNING: missing, duplicate, or malformed fallback mode; defaulting to stop unless explicitly requested.")
    execution_mode = requested_mode or old_mode or "strict"
    fallback_mode = requested_fallback or old_fallback or "stop"
    print(
        "Codex modes: "
        f"execution detected={old_mode or 'none'} requested={requested_mode or 'none'} final={execution_mode}; "
        f"fallback detected={old_fallback or 'none'} requested={requested_fallback or 'none'} final={fallback_mode}"
    )

    state_path = project / ".codex" / STATE_NAME
    state = read_state(state_path)

    config_target = project / ".codex" / "config.toml"
    config_existing = config_target.read_text(encoding="utf-8") if config_target.exists() else ""
    config_content, _ = merged_config_text(project, config_existing, fallback_mode, migrate)

    writes: dict[Path, str] = {}
    writes[config_target] = config_content
    for filename in BASE_AGENT_FILES:
        source = SOURCE_ROOT / "agents" / filename
        writes[project / ".codex" / "agents" / filename] = source.read_text(encoding="utf-8")

    fallback_writes, removals, fallback_hashes = preflight_fallback_files(project, fallback_mode, state)
    writes.update(fallback_writes)

    skill_source = SOURCE_ROOT / "skills" / "leader-worker-mode" / "SKILL.md"
    skill_target = project / ".agents" / "skills" / "leader-worker-mode" / "SKILL.md"
    writes[skill_target] = skill_source.read_text(encoding="utf-8")
    writes[policy_target] = merged_policy_text(policy_existing, policy_target, execution_mode, fallback_mode)

    next_state = {
        "version": (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "execution_mode": execution_mode,
        "fallback_mode": fallback_mode,
        "fallback_files": fallback_hashes,
    }
    writes[state_path] = json.dumps(next_state, ensure_ascii=False, indent=2) + "\n"

    changed_writes = {
        path: content
        for path, content in writes.items()
        if not path.exists() or path.read_text(encoding="utf-8") != content
    }
    changed_paths = [*changed_writes, *removals]
    stamp = timestamp()
    for path in changed_paths:
        backup(path, stamp, dry_run)

    for path, content in changed_writes.items():
        print(f"Install: {path}")
        atomic_write(path, content, dry_run)
    for path in removals:
        print(f"Remove managed fallback agent: {path}")
        if not dry_run:
            path.unlink()

    if not changed_paths:
        print("Codex Leader/Worker installation already current.")
    print("\nStart a new Codex session in the target project, then run the smoke test in docs/CODEX.md.")


def main() -> int:
    args = parse_args()
    install(
        args.project,
        args.mode,
        args.fallback,
        args.migrate_agent_defaults,
        args.dry_run,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
