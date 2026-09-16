#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path

from sync_poor_mode import check as check_poor_mode

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKERS = ["analyzer", "implementer", "tester", "reviewer"]
DEFAULT_WORKER_MODEL = "GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)"
DEFAULT_WORKER_MODEL_SELECTOR_ID = "gcmp.zhipu:::glm-5.3-flash"
SKILLS = ["leader-orchestration", "cost-control", "quality-gates"]
LEADER_TOOLS = {"vscode/askQuestions", "vscode/memory", "agent", "read", "search", "web"}
LEADER_ADAPTIVE_TOOLS = LEADER_TOOLS | {"edit", "execute"}
WORKER_TOOLS = {
    "analyzer": {"read", "search"},
    "implementer": {"vscode", "execute", "read", "search", "edit"},
    "tester": {"read", "search", "execute"},
    "reviewer": {"read", "search", "execute"},
}
OBSOLETE_ITEMS = [
    "leader-arbiter.agent.md",
    "decision-escalation",
    "evidence-handoff",
    "scope-arbitration",
    "structured-handoff",
]
ZCODE_WORKER_TOOLS = {
    "analyzer": {"Read", "Grep", "Glob", "WebFetch", "WebSearch"},
    "implementer": {"Read", "Grep", "Glob", "Bash", "Edit", "Write"},
    "tester": {"Read", "Grep", "Glob", "Bash"},
    "reviewer": {"Read", "Grep", "Glob", "Bash"},
}
ZCODE_WORKER_EFFORT = {
    "analyzer": "high",
    "implementer": "high",
    "tester": "high",
    "reviewer": "high",
}

CODEX_WORKERS = {
    "analyzer": "read-only",
    "implementer": "workspace-write",
    "tester": "workspace-write",
    "reviewer": "read-only",
}
CODEX_WORKER_EFFORT = {
    "analyzer": "medium",
    "implementer": "high",
    "tester": "medium",
    "reviewer": "high",
}
CODEX_LEGACY_DEFAULT_KEYS = {
    "default_subagent_model",
    "default_subagent_reasoning_effort",
}


def frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing frontmatter: {path}")
    block = text.split("---", 2)[1]
    result: dict[str, object] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value in {"true", "false"}:
            result[key] = value == "true"
        elif value.startswith("["):
            result[key] = re.findall(r"['\"]([^'\"]+)['\"]", value)
        else:
            result[key] = value.strip('"\'')
    return result


def installed_paths() -> tuple[Path, Path, Path, Path]:
    base = Path.home() / ".copilot"
    return base / "agents", base / "skills", base / "hooks", base / "vscode-copilot-leader-agents"


def settings_files() -> list[Path]:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        root = home / "Library/Application Support/Code/User"
    elif system == "Windows":
        root = Path(os.environ.get("APPDATA", "")) / "Code/User"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "Code/User"
    result = [root / "settings.json"]
    if (root / "profiles").exists():
        result.extend(sorted((root / "profiles").glob("*/settings.json")))
    return result


def require_tokens(errors: list[str], label: str, text: str, tokens: list[str]) -> None:
    for token in tokens:
        if token not in text:
            errors.append(f"{label} is missing: {token}")


def inline_list(text: str, key: str) -> set[str]:
    match = re.search(rf"(?m)^{re.escape(key)}:\s*\[([^\]]*)\]\s*$", text)
    if not match:
        return set()
    return {item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()}


def normalized_codex_agent(text: str) -> str:
    """Compare base and fallback role bodies while ignoring routing metadata."""
    ignored = {"name", "description", "model", "model_reasoning_effort"}
    lines = []
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_]+)\s*=", line)
        if match and match.group(1) in ignored:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def validate_zcode(errors: list[str], source_version: str) -> None:
    root = REPO_ROOT / "zcode"
    plugin = root / "plugins/leader-worker"
    manifest_path = plugin / ".zcode-plugin/plugin.json"
    marketplace_path = root / "marketplace.json"
    repository_marketplace_path = REPO_ROOT / "marketplace.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        repository_marketplace = json.loads(repository_marketplace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid ZCode manifest: {exc}")
        return
    if manifest.get("name") != "leader-worker" or manifest.get("version") != source_version:
        errors.append("ZCode plugin name or version differs from repository VERSION")
    entries = marketplace.get("plugins", [])
    if not isinstance(entries, list) or not entries or entries[0].get("source") != "./plugins/leader-worker":
        errors.append("ZCode marketplace does not publish the leader-worker plugin")
    elif entries[0].get("version") != source_version:
        errors.append("ZCode marketplace version differs from repository VERSION")
    repository_entries = repository_marketplace.get("plugins", [])
    if not isinstance(repository_entries, list) or not repository_entries or repository_entries[0].get("source") != "./zcode/plugins/leader-worker":
        errors.append("Repository marketplace does not publish the portable ZCode plugin path")
    elif repository_entries[0].get("version") != source_version:
        errors.append("Repository marketplace version differs from repository VERSION")

    portable_files = [repository_marketplace_path, marketplace_path]
    portable_files.extend(path for path in root.rglob("*") if path.is_file())
    forbidden = [r"/Users/[^/]+/", r"[A-Za-z]:\\Users\\[^\\]+\\", r"\.zcode/cli/plugins/cache", r"sess_[0-9a-f-]{8,}"]
    for path in portable_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in forbidden):
            errors.append(f"ZCode portable source contains machine-local data: {path}")

    agents_dir = plugin / "agents"
    for name, expected_tools in ZCODE_WORKER_TOOLS.items():
        path = agents_dir / f"leader-{name}.md"
        if not path.exists():
            errors.append(f"Missing ZCode subagent: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if inline_list(text, "tools") != expected_tools:
            errors.append(f"ZCode {name} tool set is incorrect")
        require_tokens(errors, f"ZCode {name} contract", text, [
            "GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER",
            "stateless invocation", "never invoke another subagent",
        ])
        if "model: glm-5.3-flash" not in text or f"thoughtLevel: {ZCODE_WORKER_EFFORT[name]}" not in text:
            errors.append(f"ZCode {name} model or thought level is incorrect")

    agents_md = (root / "AGENTS.md").read_text(encoding="utf-8")
    require_tokens(errors, "ZCode Leader protocol", agents_md, [
        "primary ZCode Agent is the Leader", "task-topology gate", "dependency-ordered stage waves",
        "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "Goal Mode",
        "PUBLIC_TYPESCRIPT_API", "BEHAVIOR_BOUNDARY", "at most one targeted rework round",
        "leader-worker-execution-mode: strict", "In `strict` mode", "In `adaptive` mode",
        "routing instruction", "Sensitive-path edits", "deterministic rejection",
    ])
    skill_path = plugin / "skills/leader-worker-mode/SKILL.md"
    if not skill_path.exists():
        errors.append(f"Missing ZCode skill: {skill_path}")
    else:
        require_tokens(errors, "ZCode leader-worker skill", skill_path.read_text(encoding="utf-8"), [
            "every repository task", "strict mode", "adaptive mode", "one `GOAL`",
        ])
    hook_path = plugin / "hooks/hooks.json"
    guard_path = plugin / "hooks/guard.py"
    try:
        hook = json.loads(hook_path.read_text(encoding="utf-8"))
        pre_tool = hook["hooks"]["PreToolUse"][0]
        matcher = pre_tool.get("matcher", "")
        if any(token not in matcher for token in ["Bash", "Edit", "Write", "mcp"]) or pre_tool["hooks"][0].get("type") != "process":
            errors.append("ZCode PreToolUse hook is incorrectly configured")
    except (OSError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid ZCode hook config: {exc}")
    if not guard_path.exists():
        errors.append(f"Missing ZCode guard: {guard_path}")
    else:
        require_tokens(errors, "ZCode guard leader boundary", guard_path.read_text(encoding="utf-8"), [
            "leader-worker-agents:start", "leader-worker-agents:end", "MODE_PATTERN",
            "leader-implementer", "leader-tester", "leader-analyzer", "path_text",
        ])


def validate_codex(errors: list[str]) -> None:
    root = REPO_ROOT / "codex"
    try:
        config_text = (root / "config.toml").read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"Invalid Codex config: {exc}")
        return
    for line in ["[agents]", "enabled = true", "max_concurrent_threads_per_session = 4"]:
        if line not in config_text:
            errors.append(f"Codex [agents] managed setting is missing: {line}")
    for key in CODEX_LEGACY_DEFAULT_KEYS:
        if re.search(rf"(?m)^\s*{re.escape(key)}\s*=", config_text):
            errors.append(f"Codex source config must not set project-wide {key}")

    for name, sandbox in CODEX_WORKERS.items():
        path = root / "agents" / f"leader-{name}.toml"
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Invalid Codex {name} agent: {exc}")
            continue
        if f'name = "leader_{name}"' not in text:
            errors.append(f"Codex {name} name is incorrect")
        if 'model = "gpt-5.6-luna"' not in text or f'model_reasoning_effort = "{CODEX_WORKER_EFFORT[name]}"' not in text:
            errors.append(f"Codex {name} model configuration is incorrect")
        if f'sandbox_mode = "{sandbox}"' not in text:
            errors.append(f"Codex {name} sandbox is incorrect")
        require_tokens(errors, f"Codex {name} contract", text, [
            "GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER",
            "stateless invocation", "never spawn another subagent",
        ])

        fallback = root / "agents" / f"leader-{name}-fallback.toml"
        try:
            fallback_text = fallback.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Invalid Codex {name} fallback agent: {exc}")
            continue
        if f'name = "leader_{name}_fallback"' not in fallback_text:
            errors.append(f"Codex {name} fallback name is incorrect")
        if re.search(r"(?m)^\s*(?:model|model_reasoning_effort)\s*=", fallback_text):
            errors.append(f"Codex {name} fallback must omit model and effort")
        if f'sandbox_mode = "{sandbox}"' not in fallback_text:
            errors.append(f"Codex {name} fallback sandbox is incorrect")
        if normalized_codex_agent(text) != normalized_codex_agent(fallback_text):
            errors.append(f"Codex {name} base and fallback role contracts differ")

    leader = (root / "AGENTS.md").read_text(encoding="utf-8")
    require_tokens(errors, "Codex Leader protocol", leader, [
        "primary Codex agent is the Leader", "task-topology gate", "dependency-ordered stage waves",
        "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "gpt-5.6-luna",
        "leader-worker-execution-mode: strict", "protocol-enforced, not structurally enforced",
        "parent turn's live sandbox and approval overrides", "leader_analyzer_fallback",
        "at most one targeted rework round", "deterministic rejection",
    ])
    skill = (root / "skills/leader-worker-mode/SKILL.md").read_text(encoding="utf-8")
    require_tokens(errors, "Codex leader-worker skill", skill, [
        "every repository task", "leader_analyzer", "leader_implementer", "gpt-5.6-luna",
        "protocol-enforced", "`strict` mode", "`adaptive` mode", "live sandbox", "leader_*_fallback",
    ])
    installer = REPO_ROOT / "scripts/install_codex.py"
    require_tokens(errors, "Codex installer", installer.read_text(encoding="utf-8"), [
        "leader-worker-codex:start", "--migrate-agent-defaults", "Parent-model fallback cannot inherit",
        "atomic_write", "fallback_files", ".agents", "leader-worker-mode",
    ])


def validate(installed: bool) -> list[str]:
    errors: list[str] = []
    worker_model: str | None = None
    source_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    if not installed:
        validate_zcode(errors, source_version)
        validate_codex(errors)
        try:
            errors.extend(check_poor_mode(REPO_ROOT))
        except (OSError, ValueError) as exc:
            errors.append(f"Invalid shared poor-mode contract: {exc}")

    if installed:
        agents, skills, hooks, runtime = installed_paths()
        state_path = runtime / "install-state.json"
        state: dict[str, object] = {}
        try:
            loaded_state = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(loaded_state, dict):
                raise ValueError("install state is not an object")
            state = loaded_state
            value = state.get("worker_model")
            if not isinstance(value, str) or not value:
                raise ValueError("worker_model is missing")
            worker_model = value
            if state.get("version") != source_version:
                errors.append(f"Installed version {state.get('version')} differs from source {source_version}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid install state {state_path}: {exc}")
        leader_mode = state.get("leader_mode")
        if leader_mode not in {"strict", "adaptive"}:
            errors.append(f"Invalid installed Leader mode: {leader_mode}")
            leader_mode = "strict"
        agent_files = {
            "leader": agents / "leader.agent.md",
            **{name: agents / f"leader-{name}.agent.md" for name in WORKERS},
        }
    else:
        agent_files = {
            "leader": REPO_ROOT / "src/agents/leader.agent.md",
            **{name: REPO_ROOT / f"src/agents/{name}.agent.md" for name in WORKERS},
        }
        skills = REPO_ROOT / "src/skills"
        hooks = REPO_ROOT / "src/hooks"

        adaptive_path = REPO_ROOT / "src/agents/leader-adaptive.agent.md"
        try:
            adaptive_fm = frontmatter(adaptive_path)
            adaptive_text = adaptive_path.read_text(encoding="utf-8")
        except Exception as exc:
            errors.append(f"Invalid adaptive Leader: {exc}")
        else:
            if set(adaptive_fm.get("tools", [])) != LEADER_ADAPTIVE_TOOLS:
                errors.append("Adaptive Leader tool set is incorrect")
            if set(adaptive_fm.get("agents", [])) != {"Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"}:
                errors.append("Adaptive Leader subagent allowlist is incorrect")
            require_tokens(errors, "Adaptive Leader policy", adaptive_text, [
                "leader-worker-execution-mode: adaptive", "`DIRECT:`", "共享 adaptive 条件",
                "移交 Implementer", "一次局部源文件修改", "一条窄诊断/验证命令",
            ])

    for name, path in agent_files.items():
        if not path.exists():
            errors.append(f"Missing agent: {path}")
            continue
        try:
            fm = frontmatter(path)
        except Exception as exc:
            errors.append(str(exc))
            continue

        tools = set(fm.get("tools", []))
        text = path.read_text(encoding="utf-8")
        if name == "leader":
            expected_tools = LEADER_ADAPTIVE_TOOLS if installed and leader_mode == "adaptive" else LEADER_TOOLS
            if tools != expected_tools:
                errors.append("Leader tool set is incorrect")
            expected_agents = {"Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"}
            if set(fm.get("agents", [])) != expected_agents:
                errors.append("Leader subagent allowlist is incorrect")
            if fm.get("user-invocable") is not True:
                errors.append("Leader must be user-invocable")
            require_tokens(errors, "Leader control policy", text, ["意图对齐", "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "NEEDS_LEADER", "一次直接、无状态的 Worker 调用", "不是 `goal` 命令", "没有 `todo` 工具", "`vscode/memory` 只在用户明确要求记住时", "禁止保存当前任务的 goal", "记忆不能触发调用", "`web` 只用于", "禁止登录、提交、外部写入", "不得代替 Analyzer 广泛扫描", worker_model or DEFAULT_WORKER_MODEL, "显式指定该模型", "低成本执行模型", "机械执行的任务包", "不得声称已设置 `max`", "不得向调用中编造 `reasoningEffort` 字段", "相关文件", "合理处理", "视情况而定", "全面检查", "PUBLIC_TYPESCRIPT_API", "BEHAVIOR_BOUNDARY", "触发项的 `NOT_VERIFIED` 是未满足的 `DONE`", "重试一次", "确定性拒绝", "不得自动发现第三方模型", "### 任务拓扑门", "单 Worker 快速通道", "两个及以上可独立验收", "阶段波次", "禁止把它们合并给同一个 Worker", "默认采用最大安全并行度", "多个 Implementer", "不需要用户额外提出并行要求", "预先声明"])
            if "修改默认串行" in text:
                errors.append("Leader control policy still defaults implementation to serial")
        else:
            if fm.get("user-invocable") is not False:
                errors.append(f"{name} must be hidden")
            if fm.get("agents") != []:
                errors.append(f"{name} must not invoke subagents")
            if tools != WORKER_TOOLS[name]:
                errors.append(f"{name} tool set is incorrect")
            if "model" in fm:
                errors.append(f"{name} must not fix its own model")
            require_tokens(errors, f"{name} execution contract", text, ["GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER", "确定且可观察", "逐项验收标准", "两个及以上可独立验收", "要求 Leader 拆", "不得创建、更新或等待任何 goal/持续任务", "不得自行"])
            if name == "implementer":
                require_tokens(errors, "Implementer contract-trigger policy", text, ["PUBLIC_TYPESCRIPT_API", "BEHAVIOR_BOUNDARY", "@ts-ignore"])
            if name == "tester":
                require_tokens(errors, "Tester contract-trigger policy", text, ["PUBLIC_TYPESCRIPT_API", "BEHAVIOR_BOUNDARY", "@ts-expect-error", "触发项的 `NOT_VERIFIED` 视为 `FAIL`", "Contract-trigger checks"])
            if name == "reviewer":
                require_tokens(errors, "Reviewer contract-trigger policy", text, ["PUBLIC_TYPESCRIPT_API", "BEHAVIOR_BOUNDARY", "@ts-expect-error", "Contract-trigger review"])

        if installed and worker_model:
            source_name = "leader-adaptive.agent.md" if name == "leader" and leader_mode == "adaptive" else f"{name}.agent.md"
            source = REPO_ROOT / "src/agents" / source_name
            expected = source.read_text(encoding="utf-8").replace(DEFAULT_WORKER_MODEL, worker_model)
            if text != expected:
                errors.append(f"Installed agent differs from template: {path}")
        elif name != "leader" and "{{WORKER_MODEL}}" in text:
            errors.append(f"Worker must not contain a model placeholder: {path}")

    for skill_name in SKILLS:
        path = skills / skill_name / "SKILL.md"
        if not path.exists():
            errors.append(f"Missing skill: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if skill_name == "leader-orchestration":
            require_tokens(errors, "Leader orchestration topology policy", text, ["task-topology gate", "dependency-ordered stage waves", "must not merge them into one large Worker assignment", "parallel wave", "Multiple Implementers may run concurrently", "predeclared next-wave package"])
            if "Keep shared-workspace modification serial" in text:
                errors.append("Leader orchestration still defaults shared-workspace modification to serial")
        elif skill_name == "cost-control":
            require_tokens(errors, "Cost-control topology policy", text, ["task-topology gate", "launch all dependency-ready packages", "Never merge two independently acceptable packages", "Multiple Implementers should run concurrently"])
        if installed:
            source = REPO_ROOT / "src/skills" / skill_name / "SKILL.md"
            if text != source.read_text(encoding="utf-8"):
                errors.append(f"Installed skill differs from template: {path}")

    if installed:
        agents, skills, _, runtime = installed_paths()
        obsolete_paths = [agents / OBSOLETE_ITEMS[0], *[skills / name for name in OBSOLETE_ITEMS[1:]]]
        for path in obsolete_paths:
            if path.exists():
                errors.append(f"Obsolete managed item remains installed: {path}")

    hook_file = hooks / "vscode-copilot-leader-guard.json"
    if not hook_file.exists():
        errors.append(f"Missing hook: {hook_file}")
    else:
        try:
            json.loads(hook_file.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"Invalid hook JSON: {exc}")
        if installed and hook_file.read_text(encoding="utf-8") != (REPO_ROOT / "src/hooks/vscode-copilot-leader-guard.json").read_text(encoding="utf-8"):
            errors.append(f"Installed hook config differs from template: {hook_file}")

    if installed:
        _, _, _, runtime = installed_paths()
        for name in ["guard.py", "guard.ps1"]:
            path = runtime / "hooks" / name
            source = REPO_ROOT / "src/hooks" / name
            if not path.exists():
                errors.append(f"Missing installed hook runtime: {path}")
            elif path.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
                errors.append(f"Installed hook runtime differs from template: {path}")

        for path in settings_files():
            if not path.exists():
                errors.append(f"Missing profile settings: {path}")
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in ['"chat.subagents.allowInvocationsFromSubagents": false', '"chat.useCustomAgentHooks": true', '"chat.utilitySmallModel"']:
                if token not in text:
                    errors.append(f"Profile setting missing in {path}: {token}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--installed", action="store_true")
    args = parser.parse_args()
    errors = validate(args.installed)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
