#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "zcode"
DEFAULT_MARKETPLACE_DIR = Path.home() / ".zcode" / "leader-worker-agents"
START_MARKER = "<!-- leader-worker-agents:start -->"
END_MARKER = "<!-- leader-worker-agents:end -->"


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


def managed_policy() -> str:
    policy = (SOURCE_ROOT / "AGENTS.md").read_text(encoding="utf-8").strip()
    return f"{START_MARKER}\n{policy}\n{END_MARKER}"


def merge_project_policy(project: Path, dry_run: bool) -> None:
    if not project.exists() or not project.is_dir():
        raise RuntimeError(f"Project directory does not exist: {project}")
    target = project.resolve() / "AGENTS.md"
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
    print(f"Install project policy: {target}")
    if not dry_run:
        target.write_text(merged, encoding="utf-8")


def main() -> int:
    args = parse_args()
    destination = args.marketplace_dir.expanduser().resolve()
    stage_marketplace(destination, args.dry_run)
    if args.project:
        merge_project_policy(args.project.expanduser(), args.dry_run)
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
