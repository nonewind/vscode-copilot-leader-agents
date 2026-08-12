#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKERS = ["analyzer", "implementer", "tester", "reviewer"]
DEFAULT_WORKER_MODEL = "DeepSeek-V4-Flash (Go) (gcmp.opencode)"
SKILLS = ["leader-orchestration", "cost-control", "quality-gates"]
LEADER_TOOLS = {"agent", "todo", "read", "search"}
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


def validate(installed: bool) -> list[str]:
    errors: list[str] = []
    worker_model: str | None = None
    source_version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    if installed:
        agents, skills, hooks, runtime = installed_paths()
        state_path = runtime / "install-state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            value = state.get("worker_model")
            if not isinstance(value, str) or not value:
                raise ValueError("worker_model is missing")
            worker_model = value
            if state.get("version") != source_version:
                errors.append(f"Installed version {state.get('version')} differs from source {source_version}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid install state {state_path}: {exc}")
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
            if tools != LEADER_TOOLS:
                errors.append("Leader tool set is incorrect")
            expected_agents = {"Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"}
            if set(fm.get("agents", [])) != expected_agents:
                errors.append("Leader subagent allowlist is incorrect")
            if fm.get("user-invocable") is not True:
                errors.append("Leader must be user-invocable")
            require_tokens(errors, "Leader control policy", text, ["意图对齐", "`GOAL`", "`BOUNDARIES`", "`DONE`", "`STOP_AND_REPORT`", "NEEDS_LEADER", "不得代替 Analyzer 广泛扫描", worker_model or DEFAULT_WORKER_MODEL, "显式指定该模型", "不得自动发现、静默回退"])
        else:
            if fm.get("user-invocable") is not False:
                errors.append(f"{name} must be hidden")
            if fm.get("agents") != []:
                errors.append(f"{name} must not invoke subagents")
            if tools != WORKER_TOOLS[name]:
                errors.append(f"{name} tool set is incorrect")
            if "model" in fm:
                errors.append(f"{name} must not fix its own model")
            require_tokens(errors, f"{name} execution contract", text, ["GOAL", "BOUNDARIES", "DONE", "STOP_AND_REPORT", "NEEDS_LEADER"])

        if installed and worker_model:
            source = REPO_ROOT / "src/agents" / f"{name}.agent.md"
            expected = source.read_text(encoding="utf-8").replace(DEFAULT_WORKER_MODEL, worker_model)
            if text != expected:
                errors.append(f"Installed agent differs from template: {path}")
        elif name != "leader" and "{{WORKER_MODEL}}" in text:
            errors.append(f"Worker must not contain a model placeholder: {path}")

    for skill_name in SKILLS:
        path = skills / skill_name / "SKILL.md"
        if not path.exists():
            errors.append(f"Missing skill: {path}")
        elif installed:
            source = REPO_ROOT / "src/skills" / skill_name / "SKILL.md"
            if path.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
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
