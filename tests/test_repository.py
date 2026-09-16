import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_zcode_plugin_has_bounded_workers_and_leader_protocol(self):
        zcode = ROOT / "zcode"
        plugin = zcode / "plugins/leader-worker"
        manifest = json.loads((plugin / ".zcode-plugin/plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads((zcode / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "leader-worker")
        self.assertEqual(manifest["version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())
        self.assertEqual(marketplace["plugins"][0]["source"], "./plugins/leader-worker")

        expected_tools = {
            "analyzer": {"Read", "Grep", "Glob", "WebFetch", "WebSearch"},
            "implementer": {"Read", "Grep", "Glob", "Bash", "Edit", "Write"},
            "tester": {"Read", "Grep", "Glob", "Bash"},
            "reviewer": {"Read", "Grep", "Glob", "Bash"},
        }
        for name, tools in expected_tools.items():
            text = (plugin / f"agents/leader-{name}.md").read_text(encoding="utf-8")
            frontmatter = text.split("---", 2)[1]
            for tool in tools:
                self.assertIn(tool, frontmatter)
            for token in ["GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER", "stateless invocation", "never invoke another subagent"]:
                self.assertIn(token, text)

        leader = (zcode / "AGENTS.md").read_text(encoding="utf-8")
        for token in ["primary ZCode Agent is the Leader", "task-topology gate", "Goal Mode", "routing instruction", "strict", "adaptive"]:
            self.assertIn(token, leader)

        skill = (plugin / "skills/leader-worker-mode/SKILL.md").read_text(encoding="utf-8")
        for token in ["every repository task", "strict mode", "adaptive mode"]:
            self.assertIn(token, skill)

    def run_zcode_guard(self, payload):
        guard = ROOT / "zcode/plugins/leader-worker/hooks/guard.py"
        result = subprocess.run(
            [sys.executable, str(guard)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def mark_zcode_mode(self, project, mode):
        (project / "AGENTS.md").write_text(
            "<!-- leader-worker-agents:start -->\n"
            "# Leader/Worker mode for ZCode\n"
            f"leader-worker-execution-mode: {mode}\n"
            "<!-- leader-worker-agents:end -->\n",
            encoding="utf-8",
        )

    def test_zcode_guard_denies_primary_agent_execution_when_mode_is_marked(self):
        with tempfile.TemporaryDirectory() as temp:
            marked = Path(temp)
            self.mark_zcode_mode(marked, "strict")
            for tool_name, tool_input in [
                ("Bash", {"command": "git status"}),
                ("Edit", {"file_path": "a.py", "old_string": "x", "new_string": "y"}),
                ("Write", {"file_path": "a.py", "content": "x"}),
                ("mcp__node_repl__js", {"code": "1"}),
            ]:
                with self.subTest(tool=tool_name):
                    output = self.run_zcode_guard({
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "cwd": str(marked),
                    })
                    self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_zcode_guard_detects_mode_from_manual_agents_md_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            marked = Path(temp)
            (marked / "AGENTS.md").write_text("# Leader/Worker mode for ZCode\n", encoding="utf-8")
            nested = marked / "nested" / "deeper"
            nested.mkdir(parents=True)
            output = self.run_zcode_guard({
                "tool_name": "Bash",
                "tool_input": {"command": "echo hi"},
                "cwd": str(nested),
            })
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_zcode_guard_adaptive_asks_for_direct_actions_but_keeps_hard_denies(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            self.mark_zcode_mode(project, "adaptive")
            cases = [
                ("Edit", {"file_path": "a.py", "new_string": "x"}, "ask"),
                ("Bash", {"command": "python -m unittest"}, "ask"),
                ("mcp__node_repl__js", {"code": "1"}, "deny"),
                ("Bash", {"command": "git commit -am test"}, "deny"),
                ("Bash", {"command": "rm -- $FILES"}, "deny"),
                ("Bash", {"command": "pnpm install"}, "ask"),
            ]
            for tool_name, tool_input, decision in cases:
                with self.subTest(tool=tool_name, input=tool_input):
                    output = self.run_zcode_guard({
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "cwd": str(project),
                    })
                    self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], decision)

    def test_zcode_guard_mode_parse_fails_closed_and_walks_to_filesystem_root(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            deep = project.joinpath(*[f"level-{index}" for index in range(7)])
            deep.mkdir(parents=True)
            for declaration in [
                "leader-worker-execution-mode: invalid",
                "leader-worker-execution-mode: adaptive\nleader-worker-execution-mode: strict",
                "",
            ]:
                (project / "AGENTS.md").write_text(
                    "<!-- leader-worker-agents:start -->\n"
                    f"{declaration}\n"
                    "<!-- leader-worker-agents:end -->\n",
                    encoding="utf-8",
                )
                with self.subTest(declaration=declaration):
                    output = self.run_zcode_guard({
                        "tool_name": "Bash",
                        "tool_input": {"command": "echo hi"},
                        "cwd": str(deep),
                    })
                    self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_zcode_guard_keeps_previous_behavior_without_mode_marker(self):
        git_write = "git " + "commit -am test"
        dep_install = "pnpm " + "install"
        with tempfile.TemporaryDirectory() as temp:
            for command, decision in [(git_write, "deny"), (dep_install, "ask")]:
                with self.subTest(command=command):
                    output = self.run_zcode_guard({
                        "tool_name": "Bash",
                        "tool_input": {"command": command},
                        "cwd": temp,
                    })
                    self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], decision)
            for tool_name, tool_input in [
                ("Bash", {"command": "git status"}),
                ("Edit", {"file_path": "a.py", "old_string": "x", "new_string": "y"}),
            ]:
                with self.subTest(tool=tool_name):
                    output = self.run_zcode_guard({
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "cwd": temp,
                    })
                    self.assertTrue(output["continue"], json.dumps(output))

            sensitive = self.run_zcode_guard({
                "tool_name": "Edit",
                "tool_input": {"file_path": "package-lock.json", "new_string": "x"},
                "cwd": temp,
            })
            self.assertEqual(sensitive["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_zcode_guard_scopes_rules_to_command_and_path_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            for body in ["mention git commit here", "example pnpm install", "package-lock.json"]:
                with self.subTest(body=body):
                    output = self.run_zcode_guard({
                        "tool_name": "Edit",
                        "tool_input": {"file_path": "docs/notes.md", "new_string": body},
                        "cwd": temp,
                    })
                    self.assertTrue(output["continue"], json.dumps(output))

            nested = self.run_zcode_guard({
                "tool_name": "Edit",
                "tool_input": {"edits": [{"file_path": ".github/workflows/ci.yml", "new_string": "safe body"}]},
                "cwd": temp,
            })
            self.assertEqual(nested["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_zcode_guard_blocks_git_write_and_prompts_for_install(self):
        guard = ROOT / "zcode/plugins/leader-worker/hooks/guard.py"
        for command, decision in [("git commit -am test", "deny"), ("pnpm install", "ask")]:
            result = subprocess.run(
                [sys.executable, str(guard)],
                input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"], decision)

    def test_zcode_installer_stages_portable_marketplace_and_merges_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            marketplace = temp_root / "marketplace"
            project = temp_root / "project"
            project.mkdir()
            agents = project / "AGENTS.md"
            agents.write_text("# Existing project rules\n", encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "scripts/install_zcode.py"),
                "--marketplace-dir", str(marketplace),
                "--project", str(project),
            ]
            first = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            staged = json.loads((marketplace / "marketplace.json").read_text(encoding="utf-8"))
            self.assertEqual(staged["plugins"][0]["source"], "./plugins/leader-worker")
            text = agents.read_text(encoding="utf-8")
            self.assertIn("# Existing project rules", text)
            self.assertEqual(text.count("<!-- leader-worker-agents:start -->"), 1)
            self.assertTrue((marketplace / "plugins/leader-worker/.zcode-plugin/plugin.json").exists())

            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual(agents.read_text(encoding="utf-8").count("<!-- leader-worker-agents:start -->"), 1)

            adaptive = subprocess.run(command + ["--mode", "adaptive"], text=True, capture_output=True)
            self.assertEqual(adaptive.returncode, 0, adaptive.stdout + adaptive.stderr)
            self.assertIn("leader-worker-execution-mode: adaptive", agents.read_text(encoding="utf-8"))

            preserved = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(preserved.returncode, 0, preserved.stdout + preserved.stderr)
            self.assertIn("leader-worker-execution-mode: adaptive", agents.read_text(encoding="utf-8"))

    def test_zcode_installer_fails_closed_on_malformed_mode_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / "project"
            project.mkdir()
            agents = project / "AGENTS.md"
            agents.write_text(
                "leader-worker-execution-mode: adaptive\n"
                "<!-- leader-worker-agents:start -->\n"
                "leader-worker-execution-mode: invalid\n"
                "<!-- leader-worker-agents:end -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/install_zcode.py"),
                    "--marketplace-dir",
                    str(root / "marketplace"),
                    "--project",
                    str(project),
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("malformed execution mode", result.stdout)
            managed = agents.read_text(encoding="utf-8").split("<!-- leader-worker-agents:start -->", 1)[1]
            self.assertIn("leader-worker-execution-mode: strict", managed)

    def test_zcode_sources_do_not_contain_machine_local_paths(self):
        paths = [ROOT / "marketplace.json", *(ROOT / "zcode").rglob("*")]
        patterns = [r"/Users/[^/]+/", r"[A-Za-z]:\\Users\\[^\\]+\\", r"\.zcode/cli/plugins/cache", r"sess_[0-9a-f-]{8,}"]
        for path in paths:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text, re.IGNORECASE), str(path))

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

        adaptive = ROOT / "src/agents/leader-adaptive.agent.md"
        adaptive_text = adaptive.read_text(encoding="utf-8")
        adaptive_frontmatter = adaptive_text.split("---", 2)[1]
        self.assertIn("'edit'", adaptive_frontmatter)
        self.assertIn("'execute'", adaptive_frontmatter)
        self.assertIn("leader-worker-execution-mode: adaptive", adaptive_text)
        for token in ["`DIRECT:`", "共享 adaptive 条件", "移交 Implementer"]:
            self.assertIn(token, adaptive_text)
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
                for token in ["确定且可观察", "逐项验收标准", "两个及以上可独立验收", "要求 Leader 拆", "不得创建、更新或等待任何 goal/持续任务", "不得自行"]:
                    self.assertIn(token, text)
                self.assertNotIn("ARBITRATION_REQUIRED", text)
                self.assertNotIn("Evidence ledger", text)

    def run_codex_installer(self, project, *args):
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/install_codex.py"),
                "--project",
                str(project),
                *args,
            ],
            text=True,
            capture_output=True,
        )

    def test_codex_source_has_static_defaults_removed_and_paired_fallback_roles(self):
        config = (ROOT / "codex/config.toml").read_text(encoding="utf-8")
        self.assertIn("enabled = true", config)
        self.assertIn("max_concurrent_threads_per_session = 4", config)
        self.assertNotIn("default_subagent_model", config)
        self.assertNotIn("default_subagent_reasoning_effort", config)

        for name in ["analyzer", "implementer", "tester", "reviewer"]:
            base = (ROOT / f"codex/agents/leader-{name}.toml").read_text(encoding="utf-8")
            fallback = (ROOT / f"codex/agents/leader-{name}-fallback.toml").read_text(encoding="utf-8")
            self.assertIn('model = "gpt-5.6-luna"', base)
            self.assertIn("model_reasoning_effort", base)
            self.assertNotRegex(fallback, r"(?m)^\s*(?:model|model_reasoning_effort)\s*=")
            self.assertIn(f'name = "leader_{name}_fallback"', fallback)
            for token in ["sandbox_mode", "developer_instructions", "GOAL", "STOP_AND_REPORT"]:
                self.assertIn(token, fallback)

    def test_codex_installer_fresh_modes_and_idempotence(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            first = self.run_codex_installer(project)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            policy = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("leader-worker-execution-mode: strict", policy)
            self.assertIn("leader-worker-fallback-mode: stop", policy)
            self.assertFalse(any((project / ".codex/agents").glob("*-fallback.toml")))

            second = self.run_codex_installer(project, "--mode", "adaptive", "--fallback", "parent-worker")
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            policy = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("leader-worker-execution-mode: adaptive", policy)
            self.assertIn("leader-worker-fallback-mode: parent-worker", policy)
            self.assertEqual(len(list((project / ".codex/agents").glob("*-fallback.toml"))), 4)

            third = self.run_codex_installer(project)
            self.assertEqual(third.returncode, 0, third.stdout + third.stderr)
            self.assertIn("already current", third.stdout)
            self.assertIn("leader-worker-fallback-mode: parent-worker", (project / "AGENTS.md").read_text(encoding="utf-8"))

            stop = self.run_codex_installer(project, "--fallback", "stop")
            self.assertEqual(stop.returncode, 0, stop.stdout + stop.stderr)
            self.assertFalse(any((project / ".codex/agents").glob("*-fallback.toml")))

    def test_codex_installer_fails_closed_on_malformed_mode_state(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            (project / "AGENTS.md").write_text(
                "leader-worker-execution-mode: adaptive\n"
                "<!-- leader-worker-codex:start -->\n"
                "leader-worker-execution-mode: invalid\n"
                "leader-worker-fallback-mode: invalid\n"
                "<!-- leader-worker-codex:end -->\n",
                encoding="utf-8",
            )
            result = self.run_codex_installer(project)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("malformed execution mode", result.stdout)
            self.assertIn("malformed fallback mode", result.stdout)
            managed = (project / "AGENTS.md").read_text(encoding="utf-8").split("<!-- leader-worker-codex:start -->", 1)[1]
            self.assertIn("leader-worker-execution-mode: strict", managed)
            self.assertIn("leader-worker-fallback-mode: stop", managed)

    def test_codex_installer_legacy_default_migration_is_exact_and_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            config = project / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                "[agents]\n"
                "enabled = true\n"
                "max_concurrent_threads_per_session = 4\n"
                'default_subagent_model = "gpt-5.6-luna"\n'
                'default_subagent_reasoning_effort = "high"\n',
                encoding="utf-8",
            )
            refused = self.run_codex_installer(project)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("--migrate-agent-defaults", refused.stdout + refused.stderr)

            migrated = self.run_codex_installer(project, "--migrate-agent-defaults")
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
            text = config.read_text(encoding="utf-8")
            self.assertNotIn("default_subagent_model", text)
            self.assertNotIn("default_subagent_reasoning_effort", text)
            self.assertTrue(list(config.parent.glob("config.toml.backup-*")))

            parent = self.run_codex_installer(project, "--fallback", "parent-worker")
            self.assertEqual(parent.returncode, 0, parent.stdout + parent.stderr)
            self.assertEqual(len(list((project / ".codex/agents").glob("*-fallback.toml"))), 4)

    def test_codex_installer_preserves_custom_defaults_but_blocks_parent_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            config = project / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                "[agents]\n"
                'default_subagent_model = "custom-model"\n'
                'default_subagent_reasoning_effort = "low"\n',
                encoding="utf-8",
            )
            stop = self.run_codex_installer(project)
            self.assertEqual(stop.returncode, 0, stop.stdout + stop.stderr)
            text = config.read_text(encoding="utf-8")
            self.assertIn('default_subagent_model = "custom-model"', text)
            self.assertIn('default_subagent_reasoning_effort = "low"', text)

            parent = self.run_codex_installer(project, "--fallback", "parent-worker")
            self.assertNotEqual(parent.returncode, 0)
            self.assertIn("custom project defaults remain", parent.stdout + parent.stderr)

    def test_codex_installer_mixed_legacy_and_custom_defaults_remain_safe(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            config = project / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text(
                "[agents]\n"
                'default_subagent_model = "gpt-5.6-luna"\n'
                'default_subagent_reasoning_effort = "custom-effort"\n',
                encoding="utf-8",
            )
            migrated = self.run_codex_installer(project, "--migrate-agent-defaults")
            self.assertEqual(migrated.returncode, 0, migrated.stdout + migrated.stderr)
            text = config.read_text(encoding="utf-8")
            self.assertNotIn('default_subagent_model = "gpt-5.6-luna"', text)
            self.assertIn('default_subagent_reasoning_effort = "custom-effort"', text)

            parent = self.run_codex_installer(project, "--fallback", "parent-worker")
            self.assertNotEqual(parent.returncode, 0)
            self.assertIn("custom project defaults remain", parent.stdout + parent.stderr)

    def test_codex_installer_does_not_remove_modified_or_unowned_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            parent = self.run_codex_installer(project, "--fallback", "parent-worker")
            self.assertEqual(parent.returncode, 0, parent.stdout + parent.stderr)
            fallback = project / ".codex/agents/leader-analyzer-fallback.toml"
            fallback.write_text(fallback.read_text(encoding="utf-8") + "# user edit\n", encoding="utf-8")
            stop = self.run_codex_installer(project, "--fallback", "stop")
            self.assertNotEqual(stop.returncode, 0)
            self.assertIn("Refusing to remove unowned or modified fallback", stop.stdout + stop.stderr)
            self.assertTrue(fallback.exists())

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            target = project / ".codex/agents/leader-analyzer-fallback.toml"
            target.parent.mkdir(parents=True)
            target.write_text(
                (ROOT / "codex/agents/leader-analyzer-fallback.toml").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            parent = self.run_codex_installer(project, "--fallback", "parent-worker")
            self.assertNotEqual(parent.returncode, 0)
            self.assertIn("Refusing to overwrite unowned or modified fallback", parent.stdout + parent.stderr)

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
        for token in ["重试一次", "确定性拒绝", "不指定 Worker 模型", "不得自动发现第三方模型"]:
            self.assertIn(token, leader)
        for token in ["低成本执行模型", "机械执行的任务包", "不得声称已设置 `max`", "不得向调用中编造 `reasoningEffort` 字段", "相关文件", "合理处理", "视情况而定", "全面检查"]:
            self.assertIn(token, leader)

        installer = (ROOT / "scripts/install.py").read_text(encoding="utf-8")
        self.assertIn(f'DEFAULT_WORKER_MODEL = "{expected_model}"', installer)
        self.assertIn(f'DEFAULT_WORKER_MODEL_SELECTOR_ID = "{expected_selector_id}"', installer)
        self.assertIn("--update-extension", installer)
        self.assertNotIn("def discover_model", installer)
        self.assertIn("model = args.model or DEFAULT_WORKER_MODEL", installer)
        powershell_installer = (ROOT / "install.ps1").read_text(encoding="utf-8")
        self.assertIn('[ValidateSet("strict", "adaptive")]', powershell_installer)
        self.assertIn('@("--leader", $Leader)', powershell_installer)

    def test_compound_task_uses_dependency_waves_and_parallel_packages(self):
        leader = (ROOT / "src/agents/leader.agent.md").read_text(encoding="utf-8")
        for token in [
            "### 任务拓扑门",
            "单 Worker 快速通道",
            "两个及以上可独立验收",
            "阶段波次",
            "禁止把它们合并给同一个 Worker",
            "默认采用最大安全并行度",
            "多个 Implementer",
            "不需要用户额外提出并行要求",
            "预先声明",
            "禁止重复扫描",
            "Tester 与 Reviewer",
        ]:
            self.assertIn(token, leader)
        self.assertNotIn("修改默认串行", leader)

        orchestration = (ROOT / "src/skills/leader-orchestration/SKILL.md").read_text(encoding="utf-8")
        for token in [
            "task-topology gate",
            "dependency-ordered stage waves",
            "must not merge them into one large Worker assignment",
            "parallel wave",
            'generic phrase "shared workspace" is not a reason to serialize',
            "Multiple Implementers may run concurrently",
            "predeclared next-wave package",
        ]:
            self.assertIn(token, orchestration)
        self.assertNotIn("Keep shared-workspace modification serial", orchestration)

        cost_control = (ROOT / "src/skills/cost-control/SKILL.md").read_text(encoding="utf-8")
        for token in [
            "task-topology gate",
            "launch all dependency-ready packages",
            "Never merge two independently acceptable packages",
            "Multiple Implementers should run concurrently",
        ]:
            self.assertIn(token, cost_control)

        architecture = (ROOT / "docs/ARCHITECTURE.md").read_text(encoding="utf-8")
        for token in ["TASK_TOPOLOGY_GATE", "DEPENDENCY_ORDERED_WAVES", "dependency-wave graph"]:
            self.assertIn(token, architecture)
        self.assertNotIn("parallel-read, serial-write funnel", architecture)

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

    def test_guard_scopes_command_and_sensitive_path_rules_to_structured_fields(self):
        for body in ["mention git commit here", "example pnpm install", "package-lock.json"]:
            with self.subTest(body=body):
                output = self.run_guard({
                    "tool_name": "editFile",
                    "tool_input": {"file_path": "docs/notes.md", "new_string": body},
                })
                self.assertTrue(output["continue"], json.dumps(output))

        sensitive = self.run_guard({
            "tool_name": "editFile",
            "tool_input": {"file_path": "package-lock.json", "new_string": "safe body"},
        })
        self.assertEqual(sensitive["hookSpecificOutput"]["permissionDecision"], "ask")

        nested_sensitive = self.run_guard({
            "tool_name": "editFile",
            "tool_input": {"edits": [{"file_path": ".github/workflows/ci.yml", "new_string": "safe body"}]},
        })
        self.assertEqual(nested_sensitive["hookSpecificOutput"]["permissionDecision"], "ask")

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
