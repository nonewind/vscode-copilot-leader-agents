#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "zcode"
DEFAULT_MARKETPLACE_DIR = Path.home() / ".zcode" / "leader-worker-agents"
START_MARKER = "<!-- leader-worker-agents:start -->"
END_MARKER = "<!-- leader-worker-agents:end -->"
MODE_PATTERN = re.compile(r"(?m)^leader-worker-execution-mode:\s*(strict|adaptive)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage a portable Leader/Worker marketplace and optionally merge its ZCode policy into a project"
    )
    parser.add_argument(
        "--marketplace-dir",
        type=Path,
        default=DEFAULT_MARKETPLACE_DIR,
        help="Portable marketplace destination (default: ~/.zcode/leader-worker-agents)",
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Target project whose root AGENTS.md should receive the managed Leader/Worker policy",
    )
    parser.add_argument("--mode", choices=("strict", "adaptive"), help="Leader execution mode; preserves an existing valid mode when omitted")
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


def stage_marketplace(destination: Path, dry_run: bool) -> None:
    source_files = [SOURCE_ROOT / "marketplace.json"]
    source_files.extend(sorted((SOURCE_ROOT / "plugins/leader-worker").rglob("*")))
    backup(destination, dry_run)
    print(f"Stage portable marketplace: {destination}")
    if dry_run:
        return
    if destination.exists():
        shutil.rmtree(destination)
    for source in source_files:
        if source.is_dir():
            continue
        target = destination / source.relative_to(SOURCE_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def existing_mode(existing: str) -> str | None:
    if START_MARKER not in existing and END_MARKER not in existing:
        return None
    if existing.count(START_MARKER) != 1 or existing.count(END_MARKER) != 1:
        raise RuntimeError("Cannot safely read malformed managed Leader/Worker markers")
    start = existing.index(START_MARKER) + len(START_MARKER)
    end = existing.index(END_MARKER, start)
    matches = MODE_PATTERN.findall(existing[start:end])
    return matches[0] if len(matches) == 1 else None


def managed_policy(mode: str) -> str:
    policy = (SOURCE_ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
    matches = re.findall(r"(?m)^leader-worker-execution-mode:\s*strict\s*$", policy)
    if len(matches) != 1:
        raise RuntimeError("ZCode source policy must contain one strict execution-mode declaration")
    policy = re.sub(
        r"(?m)^leader-worker-execution-mode:\s*strict\s*$",
        f"leader-worker-execution-mode: {mode}",
        policy,
        count=1,
    )
    return f"{START_MARKER}\n{policy}\n{END_MARKER}"


def merge_project_policy(project: Path, requested_mode: str | None, dry_run: bool) -> str:
    if not project.exists() or not project.is_dir():
        raise RuntimeError(f"Project directory does not exist: {project}")
    target = project.resolve() / "AGENTS.md"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    detected_mode = existing_mode(existing)
    if (START_MARKER in existing or END_MARKER in existing) and detected_mode is None:
        print("WARNING: missing, duplicate, or malformed execution mode; defaulting to strict unless explicitly requested.")
    mode = requested_mode or detected_mode or "strict"
    print(f"ZCode execution mode: detected={detected_mode or 'none'} requested={requested_mode or 'none'} final={mode}")
    block = managed_policy(mode)
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
        return mode
    backup(target, dry_run)
    print(f"Install project policy: {target}")
    if not dry_run:
        target.write_text(merged, encoding="utf-8")
    return mode


def main() -> int:
    args = parse_args()
    destination = args.marketplace_dir.expanduser().resolve()
    stage_marketplace(destination, args.dry_run)
    if args.project:
        merge_project_policy(args.project.expanduser(), args.mode, args.dry_run)
    elif args.mode:
        raise RuntimeError("--mode requires --project because execution mode is stored in the managed AGENTS.md block")
    print("\nZCode client activation is still required:")
    print("1. Open Settings -> Plugins -> Create -> Add marketplace.")
    print(f"2. Select: {destination}")
    print("3. Install/enable leader-worker and start a new session.")
    if not args.project:
        print("4. Rerun with --project /path/to/project to merge the Leader policy safely.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
