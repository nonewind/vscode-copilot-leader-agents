import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_leader_is_dispatch_only(self):
        leader = ROOT / "src/agents/leader.agent.md"
        frontmatter = leader.read_text(encoding="utf-8").split("---", 2)[1]
        self.assertIn("tools: ['agent', 'todo']", frontmatter)
        for forbidden in ["execute", "read", "edit", "search", "web", "browser", "github/*", "vscode"]:
            self.assertNotIn(f"'{forbidden}'", frontmatter)

    def test_decision_escalation_is_one_shot_and_isolated(self):
        leader_text = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        leader_frontmatter = leader_text.split("---", 2)[1]
        self.assertIn("'Leader Arbiter'", leader_frontmatter)
        self.assertIn("每个用户任务最多自动调用一次 Arbiter", leader_text)
        self.assertIn("不得指定 worker 模型", leader_text)
        self.assertIn("原生子代理调用无状态", leader_text)

        arbiter_text = (ROOT / "src/agents/arbiter.agent.md").read_text(encoding="utf-8")
        arbiter_frontmatter = arbiter_text.split("---", 2)[1]
        self.assertIn("tools: ['read', 'search']", arbiter_frontmatter)
        self.assertIn("agents: []", arbiter_frontmatter)
        self.assertNotIn("\nmodel:", arbiter_frontmatter)
        self.assertNotIn("execute", arbiter_frontmatter)
        self.assertNotIn("edit", arbiter_frontmatter)
        self.assertIn("最多三个决定性", arbiter_text)
        self.assertIn("First-hand verification", arbiter_text)
        for token in ["SELECT_OPTION", "MORE_EVIDENCE_REQUIRED", "USER_DECISION_REQUIRED", "STOP"]:
            self.assertIn(token, arbiter_text)

    def test_all_workers_expose_narrow_arbitration_fuse(self):
        for name in ["analyzer", "implementer", "tester", "reviewer"]:
            with self.subTest(name=name):
                text = (ROOT / f"src/agents/{name}.agent.md").read_text(encoding="utf-8")
                self.assertIn("ARBITRATION_REQUIRED", text)
                self.assertIn("反证检查", text)
                self.assertIn("Why no safe local default", text)
                self.assertIn("Evidence ledger", text)
                self.assertIn("VERIFIED | PARTIAL | INFERRED", text)

        skill = (ROOT / "src/skills/decision-escalation/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("critical-decision fuse, not a default review stage", skill)
        self.assertIn("at most one automatic Arbiter invocation", skill)
        self.assertIn("A subagent invocation cannot be resumed", skill)

    def test_evidence_handoff_prefers_low_cost_checks(self):
        leader_text = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        self.assertIn("## 二手事实控制", leader_text)
        self.assertIn("通常不超过五条", leader_text)
        self.assertIn("仅核对点名的 `CLAIM_ID`", leader_text)
        self.assertIn("最多三个决定性 `CLAIM_ID`", leader_text)

        skill = (ROOT / "src/skills/evidence-handoff/SKILL.md").read_text(encoding="utf-8")
        for token in ["CLAIM_ID", "VERIFIED", "PARTIAL", "INFERRED", "EVIDENCE_CHECK", "at most three decisive claim IDs"]:
            self.assertIn(token, skill)

        for name in ["analyzer", "reviewer"]:
            text = (ROOT / f"src/agents/{name}.agent.md").read_text(encoding="utf-8")
            self.assertIn("EVIDENCE_CHECK: CONFIRMED | CONTRADICTED | INSUFFICIENT_EVIDENCE", text)

        quality_gates = (ROOT / "src/skills/quality-gates/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("A high-risk PASS cannot rely on an unresolved `PARTIAL` or `INFERRED` claim", quality_gates)

    def test_installer_includes_arbiter(self):
        text = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
        self.assertIn('"arbiter.agent.md": "leader-arbiter.agent.md"', text)

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
