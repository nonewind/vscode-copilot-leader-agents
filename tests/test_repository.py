import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_repository_validation(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def run_guard(self, payload):
        result = subprocess.run(
            [sys.executable, str(ROOT / "src/hooks/guard.py")],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_guard_denies_git_write(self):
        output = self.run_guard({
            "tool_name": "runTerminalCommand",
            "tool_input": {"command": "git commit -am test"},
        })
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_asks_for_dependency_install(self):
        output = self.run_guard({
            "tool_name": "runTerminalCommand",
            "tool_input": {"command": "pnpm install"},
        })
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_guard_allows_read_only_git(self):
        output = self.run_guard({
            "tool_name": "runTerminalCommand",
            "tool_input": {"command": "git diff --stat"},
        })
        self.assertTrue(output["continue"])


if __name__ == "__main__":
    unittest.main()
