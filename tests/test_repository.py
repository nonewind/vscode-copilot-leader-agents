import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_leader_is_decision_only(self):
        leader = ROOT / "src/agents/leader.agent.md"
        text = leader.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertIn("tools: ['agent', 'todo', 'read', 'search']", frontmatter)
        self.assertNotIn("Leader Arbiter", frontmatter)
        for worker in ["Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"]:
            self.assertIn(worker, frontmatter)
        for forbidden in ["execute", "edit", "web", "browser", "github/*", "vscode"]:
            self.assertNotIn(f"'{forbidden}'", frontmatter)
        for token in ["意图对齐", "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "NEEDS_LEADER"]:
            self.assertIn(token, text)

    def test_all_workers_use_compact_execution_brief(self):
        for name in ["analyzer", "implementer", "tester", "reviewer"]:
            with self.subTest(name=name):
                text = (ROOT / f"src/agents/{name}.agent.md").read_text(encoding="utf-8")
                frontmatter = text.split("---", 2)[1]
                self.assertNotIn("\nmodel:", frontmatter)
                for token in ["GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER"]:
                    self.assertIn(token, text)
                self.assertNotIn("ARBITRATION_REQUIRED", text)
                self.assertNotIn("Evidence ledger", text)

    def test_leader_owns_explicit_worker_model(self):
        expected_model = "DeepSeek-V4-Flash (Go) (gcmp.opencode)"
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        self.assertIn(expected_model, leader)
        self.assertIn("显式指定该模型", leader)
        self.assertIn("不得自动发现、静默回退", leader)

        installer = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
        self.assertIn(f'DEFAULT_WORKER_MODEL = "{expected_model}"', installer)
        self.assertNotIn("def discover_model", installer)
        self.assertIn("model = args.model or DEFAULT_WORKER_MODEL", installer)

    def test_parallelism_is_read_fanout_and_serial_write(self):
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        for token in ["## 并发调度", "互不依赖", "禁止重复扫描", "修改默认串行", "Tester 与 Reviewer"]:
            self.assertIn(token, leader)

        orchestration = (ROOT / "src/skills/leader-orchestration/SKILL.md").read_text(encoding="utf-8")
        for token in ["Parallelize only independent work", "Keep shared-workspace modification serial", "Tester and Reviewer may run in parallel"]:
            self.assertIn(token, orchestration)

    def test_retired_workflow_files_are_removed(self):
        self.assertFalse((ROOT / "src/agents/arbiter.agent.md").exists())
        for name in ["decision-escalation", "evidence-handoff", "scope-arbitration", "structured-handoff"]:
            self.assertFalse((ROOT / f"src/skills/{name}/SKILL.md").exists())

        text = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
        self.assertNotIn('"arbiter.agent.md": "leader-arbiter.agent.md"', text)
        self.assertIn('remove_obsolete_item(agent_dir / "leader-arbiter.agent.md"', text)
        for name in ["decision-escalation", "evidence-handoff", "scope-arbitration", "structured-handoff"]:
            self.assertIn(f'"{name}"', text)

    def test_only_three_core_skills_remain(self):
        skill_files = sorted(path.parent.name for path in (ROOT / "src/skills").glob("*/SKILL.md"))
        self.assertEqual(skill_files, ["cost-control", "leader-orchestration", "quality-gates"])

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

    def test_guard_asks_for_github_write_or_unknown_action(self):
        for tool_name in ["github/push", "github/create_pull_request", "github/unknown_operation"]:
            with self.subTest(tool_name=tool_name):
                output = self.run_guard({
                    "tool_name": tool_name,
                    "tool_input": {"repository": "owner/repository"},
                })
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_guard_allows_named_read_only_github_action(self):
        output = self.run_guard({
            "tool_name": "github/get_pull_request",
            "tool_input": {"repository": "owner/repository", "number": 1},
        })
        self.assertTrue(output["continue"])

    def test_guard_asks_for_single_file_deletion(self):
        commands = [
            "rm -- old-report.vue",
            "unlink old-report.vue",
        ]
        for command in commands:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_guard_denies_directory_or_recursive_deletion(self):
        commands = [
            "rm -r old-report",
            "rm -R old-report",
            "rm --recursive old-report",
            "Remove-Item -Recurse old-report",
            "rmdir old-report",
            "rd /s old-report",
            "del /s old-report",
            "rm -- a.vue b.vue",
            "rm -d emptydir",
            "Remove-Item emptydir",
            "Remove-Item -LiteralPath old-report.vue",
            "del old-report.vue",
            "del -Recurse old-report",
            "erase /s old-report",
            "find old-report -type f -delete",
            "rm -- $FILES",
            "rm -- [ab].vue",
            "rm -- {a,b}.vue",
            "rm -- ~/old-report.vue",
            "rm -- =ls",
            "rm -- old#report.vue",
        ]
        for command in commands:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_denies_compound_deletion(self):
        commands = [
            "rm -- old-report.vue && touch replacement.vue",
            "unlink old-report.vue; pnpm build",
            "Remove-Item old-report.vue | Out-Null",
            "del old-report.vue > deletion.log",
        ]
        for command in commands:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_guard_asks_for_delete_file_tool(self):
        output = self.run_guard({
            "tool_name": "deleteFile",
            "tool_input": {"path": "old-report.vue"},
        })
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_guard_allows_build_and_test(self):
        for command in ["pnpm build", "python -m unittest"]:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertTrue(output["continue"])

    def test_guard_allows_read_only_git(self):
        output = self.run_guard({
            "tool_name": "runTerminalCommand",
            "tool_input": {"command": "git diff --stat"},
        })
        self.assertTrue(output["continue"])

    def test_powershell_guard_has_matching_delete_policy(self):
        text = (ROOT / "src/hooks/guard.ps1").read_text(encoding="utf-8")
        for token in ["permissionDecision", "remove-item", "rmdir", "unlink", "%!^&", "`$\\[\\]{}~#=", "github", "readonlyprefixes", '"ask"', '"deny"']:
            self.assertIn(token.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
