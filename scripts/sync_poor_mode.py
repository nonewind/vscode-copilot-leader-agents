#!/usr/bin/env python3
"""Check or refresh the shared contract embedded in installable Leader policies."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "src/protocols/poor-mode.md"
TARGETS = (
    "src/agents/leader.agent.md",
    "src/agents/leader-adaptive.agent.md",
    "codex/AGENTS.md",
    "zcode/AGENTS.md",
)
START = "<!-- poor-mode:start -->"
END = "<!-- poor-mode:end -->"


def expected_files(root: Path) -> dict[Path, str]:
    contract = (root / SOURCE).read_text(encoding="utf-8").strip()
    block = f"{START}\n<!-- Generated from {SOURCE}; run scripts/sync_poor_mode.py --write. -->\n{contract}\n{END}"
    result = {}
    for name in TARGETS:
        path = root / name
        current = path.read_text(encoding="utf-8")
        if START in current or END in current:
            if current.count(START) != 1 or current.count(END) != 1:
                raise ValueError(f"Malformed poor-mode markers: {name}")
            start, end = current.index(START), current.index(END)
            if end < start:
                raise ValueError(f"Reversed poor-mode markers: {name}")
            expected = current[:start] + block + current[end + len(END):]
        else:
            expected = current.rstrip() + "\n\n" + block + "\n"
        result[path] = expected
    return result


def check(root: Path = ROOT) -> list[str]:
    return [f"Shared poor-mode contract differs: {path.relative_to(root)}"
            for path, expected in expected_files(root).items()
            if path.read_text(encoding="utf-8") != expected]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Refresh embedded blocks; default is read-only")
    args = parser.parse_args()
    # Compute every output before writing, so malformed markers cannot cause a partial update.
    expected = expected_files(ROOT)
    stale = [path for path, content in expected.items() if path.read_text(encoding="utf-8") != content]
    for path in stale:
        print(f"{'Sync' if args.write else 'Stale'}: {path.relative_to(ROOT)}")
        if args.write:
            path.write_text(expected[path], encoding="utf-8")
    if not stale:
        print("Poor-mode contracts are synchronized.")
    return 0 if args.write or not stale else 1


if __name__ == "__main__":
    raise SystemExit(main())
