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
LEADER_TOOLS = {"agent", "todo"}


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
    return (
        base / "agents",
        base / "skills",
        base / "hooks",
        base / "vscode-copilot-leader-agents",
    )


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


def validate(installed: bool) -> list[str]:
    errors: list[str] = []
    worker_model: str | None = None
    if installed:
        agents, skills, hooks, runtime = installed_paths()
        state_path = runtime / "install-state.json"
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            value = state.get("worker_model")
            if not isinstance(value, str) or not value:
                raise ValueError("worker_model is missing")
            worker_model = value
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid install state {state_path}: {exc}")
        agent_files = {
            "leader": agents / "leader.agent.md",
            "analyzer": agents / "leader-analyzer.agent.md",
            "implementer": agents / "leader-implementer.agent.md",
            "tester": agents / "leader-tester.agent.md",
            "reviewer": agents / "leader-reviewer.agent.md",
        }
    else:
        agent_files = {name: REPO_ROOT / "src/agents" / f"{name}.agent.md" for name in ["leader", *WORKERS]}
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
        if name == "leader":
            if tools != LEADER_TOOLS:
                errors.append("Leader tool set is incorrect")
            expected = {"Leader Analyzer", "Leader Implementer", "Leader Tester", "Leader Reviewer"}
            if set(fm.get("agents", [])) != expected:
                errors.append("Leader subagent allowlist is incorrect")
            if fm.get("user-invocable") is not True:
                errors.append("Leader must be user-invocable")
            text = path.read_text(encoding="utf-8")
            for required in ["默认委派 Analyzer", "默认委派 Implementer", "不得由 Leader 静默接管"]:
                if required not in text:
                    errors.append(f"Leader delegation policy is missing: {required}")
        else:
            if fm.get("user-invocable") is not False:
                errors.append(f"{name} must be hidden")
            if "agent" in tools:
                errors.append(f"{name} must not have agent tool")
            if name == "implementer" and not {"vscode", "execute", "edit"}.issubset(tools):
                errors.append("Implementer must have vscode, execute, and edit tools")
            if name in {"tester", "reviewer"} and "execute" not in tools:
                errors.append(f"{name} must have execute tool")
            if name != "implementer" and "edit" in tools:
                errors.append(f"{name} must be read-only")
            text = path.read_text(encoding="utf-8")
            if installed and "{{WORKER_MODEL}}" in text:
                errors.append(f"Unrendered model placeholder: {path}")

        if installed and worker_model:
            source = REPO_ROOT / "src/agents" / f"{name}.agent.md"
            expected = source.read_text(encoding="utf-8").replace("{{WORKER_MODEL}}", worker_model)
            if path.read_text(encoding="utf-8") != expected:
                errors.append(f"Installed agent differs from template: {path}")

    for skill_name in ["leader-orchestration", "structured-handoff", "cost-control", "scope-arbitration", "quality-gates"]:
        path = skills / skill_name / "SKILL.md"
        if not path.exists():
            errors.append(f"Missing skill: {path}")
        elif installed:
            source = REPO_ROOT / "src/skills" / skill_name / "SKILL.md"
            if path.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
                errors.append(f"Installed skill differs from template: {path}")

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
        for name in ["guard.py", "guard.ps1"]:
            path = runtime / "hooks" / name
            source = REPO_ROOT / "src/hooks" / name
            if not path.exists():
                errors.append(f"Missing installed hook runtime: {path}")
            elif path.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
                errors.append(f"Installed hook runtime differs from template: {path}")

    if installed:
        for path in settings_files():
            if not path.exists():
                errors.append(f"Missing profile settings: {path}")
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in [
                '"chat.subagents.allowInvocationsFromSubagents": false',
                '"chat.useCustomAgentHooks": true',
                '"chat.utilitySmallModel"',
            ]:
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
