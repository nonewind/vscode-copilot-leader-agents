#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "codex"
START_MARKER = "<!-- leader-worker-codex:start -->"
END_MARKER = "<!-- leader-worker-codex:end -->"
MANAGED_AGENT_KEYS = {
    "enabled": "true",
    "default_subagent_model": '"gpt-5.6-luna"',
    "default_subagent_reasoning_effort": '"high"',
    "max_concurrent_threads_per_session": "4",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install project-scoped Codex Leader/Worker agents, skill, and policy"
    )
    parser.add_argument("--project", type=Path, required=True, help="Target project root")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def backup(path: Path, dry_run: bool) -> Path | None:
    if not path.exists():
        return None
    target = path.with_name(f"{path.name}.backup-{timestamp()}")
    print(f"Backup: {path} -> {target}")
    if not dry_run:
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)
    return target


def write_file(source: Path, target: Path, dry_run: bool) -> None:
    content = source.read_text(encoding="utf-8")
    if target.exists() and target.read_text(encoding="utf-8") == content:
        print(f"Already current: {target}")
        return
    backup(target, dry_run)
    print(f"Install: {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def managed_policy() -> str:
    policy = (SOURCE_ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
    return f"{START_MARKER}\n{policy}\n{END_MARKER}"


def merge_project_policy(project: Path, dry_run: bool) -> None:
    target = project / "AGENTS.md"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    block = managed_policy()
    if START_MARKER in existing or END_MARKER in existing:
        if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
            raise RuntimeError(f"Cannot safely update malformed managed markers in {target}")
        start = existing.index(START_MARKER)
        end = existing.index(END_MARKER, start) + len(END_MARKER)
        merged = existing[:start] + block + existing[end:]
    else:
        separator = "\n\n" if existing.strip() else ""
        merged = existing.rstrip() + separator + block + "\n"
    if merged == existing:
        print(f"Project policy already current: {target}")
        return
    backup(target, dry_run)
    print(f"Merge Leader policy: {target}")
    if not dry_run:
        target.write_text(merged, encoding="utf-8")


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


def merge_config(project: Path, dry_run: bool) -> None:
    target = project / ".codex" / "config.toml"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    lines = existing.splitlines()
    bounds = section_bounds(lines, "agents")
    if bounds is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[agents]")
        insert_at = len(lines)
    else:
        _, insert_at = bounds
    present: set[str] = set()
    conflicts: list[str] = []
    if bounds is not None:
        start, end = bounds
        for line in lines[start + 1:end]:
            match = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*(?:#.*)?$", line)
            if match:
                key, value = match.groups()
                present.add(key)
                if key in MANAGED_AGENT_KEYS and value != MANAGED_AGENT_KEYS[key]:
                    conflicts.append(f"agents.{key}={value} (required {MANAGED_AGENT_KEYS[key]})")
    if conflicts:
        raise RuntimeError("Refusing to overwrite existing Codex settings: " + ", ".join(conflicts))
    additions = [f"{key} = {value}" for key, value in MANAGED_AGENT_KEYS.items() if key not in present]
    if not additions:
        print(f"Codex config already current: {target}")
        return
    lines[insert_at:insert_at] = additions
    merged = "\n".join(lines) + "\n"
    backup(target, dry_run)
    print(f"Merge Codex config: {target}")
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(merged, encoding="utf-8")


def install(project: Path, dry_run: bool) -> None:
    project = project.expanduser().resolve()
    if not project.exists() or not project.is_dir():
        raise RuntimeError(f"Project directory does not exist: {project}")
    merge_config(project, dry_run)
    for source in sorted((SOURCE_ROOT / "agents").glob("*.toml")):
        write_file(source, project / ".codex" / "agents" / source.name, dry_run)
    write_file(
        SOURCE_ROOT / "skills" / "leader-worker-mode" / "SKILL.md",
        project / ".agents" / "skills" / "leader-worker-mode" / "SKILL.md",
        dry_run,
    )
    merge_project_policy(project, dry_run)
    print("\nStart a new Codex session in the target project, then run the smoke test in docs/CODEX.md.")


def main() -> int:
    args = parse_args()
    install(args.project, args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
