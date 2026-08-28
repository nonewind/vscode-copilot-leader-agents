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
        self.assertIn("tools: ['vscode/askQuestions', 'vscode/memory', 'agent', 'read', 'search', 'web']", frontmatter)
        self.assertNotIn("Leader Arbiter", frontmatter)
        for worker in ["Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"]:
            self.assertIn(worker, frontmatter)
        for forbidden in ["execute", "edit", "browser", "github/*", "vscode", "todo"]:
            self.assertNotIn(f"'{forbidden}'", frontmatter)
        for token in ["意图对齐", "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "NEEDS_LEADER"]:
            self.assertIn(token, text)
        for token in ["一次直接、无状态的 Worker 调用", "`GOAL` 只是简报中的普通文本字段", "不是 `goal` 命令", "没有 `todo` 工具", "`vscode/memory` 只在用户明确要求记住时", "禁止保存当前任务的 goal", "记忆不能触发调用", "`web` 只用于", "禁止登录、提交、外部写入"]:
            self.assertIn(token, text)

    def test_all_workers_use_compact_execution_brief(self):
        for name in ["analyzer", "implementer", "tester", "reviewer"]:
            with self.subTest(name=name):
                text = (ROOT / f"src/agents/{name}.agent.md").read_text(encoding="utf-8")
                frontmatter = text.split("---", 2)[1]
                self.assertNotIn("\nmodel:", frontmatter)
                for token in ["GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER"]:
                    self.assertIn(token, text)
                for token in ["确定且可观察", "逐项验收标准", "不得创建、更新或等待任何 goal/持续任务", "不得自行"]:
                    self.assertIn(token, text)
                self.assertNotIn("ARBITRATION_REQUIRED", text)
                self.assertNotIn("Evidence ledger", text)

    def test_implementer_allows_only_confirmed_high_risk_plans(self):
        text = (ROOT / "src/agents/implementer.agent.md").read_text(encoding="utf-8")
        for token in [
            "只有在 `BOUNDARIES` 明确写明用户已确认的精确计划时才可执行",
            "完整的字面量删除计划",
            "文件或目录",
            "是否递归",
            "通配符、变量、动态计算路径",
        ]:
            self.assertIn(token, text)
        self.assertNotIn("禁止删除目录", text)

    def test_leader_has_bounded_worker_model_retry_and_fallback(self):
        expected_model = "GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)"
        expected_selector_id = "gcmp.zhipu:::glm-5.3-flash"
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        self.assertIn(expected_model, leader)
        self.assertIn("显式指定该模型", leader)
        for token in ["重试一次", "两次子模型调用均因模型错误失败", "不指定 Worker 模型", "不得自动发现第三方模型"]:
            self.assertIn(token, leader)
        for token in ["低成本执行模型", "机械执行的任务包", "不得声称已设置 `max`", "不得向调用中编造 `reasoningEffort` 字段", "相关文件", "合理处理", "视情况而定", "全面检查"]:
            self.assertIn(token, leader)

        installer = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
        self.assertIn(f'DEFAULT_WORKER_MODEL = "{expected_model}"', installer)
        self.assertIn(f'DEFAULT_WORKER_MODEL_SELECTOR_ID = "{expected_selector_id}"', installer)
        self.assertIn("--update-extension", installer)
        self.assertNotIn("def discover_model", installer)
        self.assertIn("model = args.model or DEFAULT_WORKER_MODEL", installer)

    def test_parallelism_is_read_fanout_and_serial_write(self):
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        for token in ["## 并发调度", "互不依赖", "禁止重复扫描", "修改默认串行", "Tester 与 Reviewer"]:
            self.assertIn(token, leader)

        orchestration = (ROOT / "src/skills/leader-orchestration/SKILL.md").read_text(encoding="utf-8")
        for token in ["Parallelize only independent work", "Keep shared-workspace modification serial", "Tester and Reviewer may run in parallel"]:
            self.assertIn(token, orchestration)

    def test_leader_validation_has_evidence_trigger_and_hard_stop(self):
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        for token in [
            "## 验证刹车",
            "继续验证必须说明",
            "`NOT_VERIFIED`",
            "最多进行一轮针对性返工",
            "只允许一次针对该问题的直接复核",
            "必须结束当前控制循环",
        ]:
            self.assertIn(token, leader)

        quality_gates = (ROOT / "src/skills/quality-gates/SKILL.md").read_text(encoding="utf-8")
        for token in [
            "Leader owns the decision to stop",
            "directly threatens a named `DONE` item",
            "at most one targeted rework round",
            "one direct recheck",
            "without opening another validation chain",
        ]:
            self.assertIn(token, quality_gates)

    def test_contract_trigger_gates_require_narrow_direct_evidence(self):
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        for token in [
            "## 契约触发式验收",
            "PUBLIC_TYPESCRIPT_API",
            "BEHAVIOR_BOUNDARY",
            "@ts-expect-error",
            "触发项的",
        ]:
            self.assertIn(token, leader)

        tester = (ROOT / "src/agents/tester.agent.md").read_text(encoding="utf-8")
        reviewer = (ROOT / "src/agents/reviewer.agent.md").read_text(encoding="utf-8")
        for text, token in [
            (tester, "Contract-trigger checks"),
            (tester, "视为"),
            (reviewer, "Contract-trigger review"),
            (reviewer, "公共导出"),
        ]:
            self.assertIn(token, text)

        quality_gates = (ROOT / "src/skills/quality-gates/SKILL.md").read_text(encoding="utf-8")
        for token in ["## Triggered contract gates", "not a theoretical risk", "Do not invent business inputs"]:
            self.assertIn(token, quality_gates)

        validator = (ROOT / "scripts/validate.py").read_text(encoding="utf-8")
        for token in ["Implementer contract-trigger policy", "Tester contract-trigger policy", "Reviewer contract-trigger policy"]:
            self.assertIn(token, validator)

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

    def test_guard_does_not_parse_sql_keywords(self):
        commands = [
            "psql -c 'insert into audit_log values (1)'",
            "psql -c 'update audit_log set status = 1'",
            "psql -c 'delete from audit_log'",
            "psql -c 'alter table audit_log add column source text'",
            "psql -c 'drop table audit_log'",
        ]
        for command in commands:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertTrue(output["continue"])

        for path in [ROOT / "src/hooks/guard.py", ROOT / "src/hooks/guard.ps1"]:
            text = path.read_text(encoding="utf-8").lower()
            for token in ["insert\\s+into", "update\\s+[^\\n]+\\s+set", "delete\\s+from", "alter\\s+table", "drop|truncate"]:
                self.assertNotIn(token, text)

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

    def test_guard_asks_for_literal_batch_and_recursive_deletion(self):
        commands = [
            "rm -r old-report",
            "rm -R old-report",
            "rm --recursive old-report",
            "rmdir old-report",
            "rd /s old-report",
            "del /s old-report.txt",
            "cmd /d /c del /f /q /s old-report.txt",
            "del old-report.vue",
            "rm -- a.vue b.vue",
        ]
        for command in commands:
            with self.subTest(command=command):
                output = self.run_guard({
                    "tool_name": "runTerminalCommand",
                    "tool_input": {"command": command},
                })
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_guard_denies_ambiguous_or_unsupported_deletion(self):
        commands = [
            "rm -d emptydir",
            "Remove-Item emptydir",
            "Remove-Item -LiteralPath old-report.vue",
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
        for token in ["permissionDecision", "remove-item", "rmdir", "unlink", "/[fqs]", "%!^&", "`$\\[\\]{}~#=", "github", "readonlyprefixes", '"ask"', '"deny"']:
            self.assertIn(token.lower(), text.lower())


if __name__ == "__main__":
    unittest.main()
