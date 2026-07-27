#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shlex
import sys
from typing import Any


def emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{k} {flatten(v)}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value)


def matches(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            return pattern
    return None


def terminal_delete_decision(command: str) -> str | None:
    if not matches([
        r"\b(?:rm|unlink|del|erase|Remove-Item)\b",
        r"\bfind\b[^\n]*\s-delete\b",
        r"\bgit\s+rm\b",
    ], command):
        return None

    if matches([r"(?:&&|[;&|><])"], command):
        return "deny"

    if matches([
        r"\bfind\b[^\n]*\s-delete\b",
        r"\bgit\s+rm\b",
        r"\b(?:rmdir|rd)\b",
    ], command):
        return "deny"

    try:
        tokens = shlex.split(command)
    except ValueError:
        return "deny"
    if not tokens:
        return None

    program = tokens[0].lower()
    args = tokens[1:]
    target: str | None = None

    if program == "rm":
        targets: list[str] = []
        for arg in args:
            if arg in {"--", "-f", "--force"}:
                continue
            if arg.startswith("-"):
                return "deny"
            targets.append(arg)
        if len(targets) == 1:
            target = targets[0]
    elif program == "unlink":
        targets = [arg for arg in args if arg != "--"]
        if len(targets) == 1 and not targets[0].startswith("-"):
            target = targets[0]

    shell_expansion_chars = set("*?$`[]{}~!^%&|<>()#")
    if target and not target.startswith("=") and not any(char in target for char in shell_expansion_chars):
        return "ask"
    return "deny"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return 0

    tool_name = str(data.get("tool_name", "")).lower()
    tool_input = data.get("tool_input", {})
    text = flatten(tool_input)
    combined = f"{tool_name} {text}"

    hard_deny = [
        r"\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b",
        r"\bgit\s+branch\s+(-d|-D|-m|-M|--delete|--move)\b",
        r"\brm\b[^\n]*(?:\s-[^\s]*[rR][^\s]*|\s--recursive)\b",
        r"\b(?:rmdir|rd)\b",
        r"\bdel\b[^\n]*\s/[^\s]*[sS][^\s]*",
        r"\bRemove-Item\b[^\n]*-Recurse\b",
        r"\b(drop|truncate)\s+(table|database|schema)\b",
        r"\bdelete\s+from\b",
        r"\bupdate\s+[^\n]+\s+set\b",
        r"\binsert\s+into\b",
        r"\balter\s+table\b",
    ]
    hit = matches(hard_deny, combined)
    if hit:
        emit("deny", "Destructive or Git-writing operation blocked by the Leader security policy.")
        return 0

    delete_tools = ["deletefile", "delete_file", "removefile", "remove_file"]
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    delete_decision = terminal_delete_decision(command)
    if delete_decision == "deny":
        emit("deny", "Only a standalone, non-recursive deletion command with one literal target is allowed.")
        return 0
    if any(name in tool_name for name in delete_tools) or delete_decision == "ask":
        emit("ask", "Exact single-file deletion requires explicit user confirmation; directory and recursive deletion are prohibited.")
        return 0

    approval_required = [
        r"\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update|upgrade)\b",
        r"\b(pip|pip3|poetry|uv|conda)\s+(install|add|remove|sync|update)\b",
        r"\b(cargo\s+add|go\s+get|dotnet\s+add\s+package)\b",
        r"\b(apt|apt-get|yum|dnf|pacman|brew|choco|winget)\s+(install|remove|upgrade|update)\b",
        r"\b(alembic\s+upgrade|flask\s+db\s+upgrade|manage\.py\s+migrate|prisma\s+migrate|sequelize[^\n]*db:migrate|knex[^\n]*migrate|rails\s+db:migrate)\b",
        r"\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete|patch|replace)|helm\s+(install|upgrade|uninstall)|docker\s+(push|rm|rmi)|aws\s+[^\n]*(deploy|update|delete)|gcloud\s+[^\n]*(deploy|delete)|az\s+[^\n]*(create|update|delete))\b",
    ]
    hit = matches(approval_required, combined)
    if hit:
        emit("ask", "Environment, dependency, migration, deployment, or external mutation requires explicit user confirmation.")
        return 0

    sensitive_path = matches([
        r"(^|[\\/])\.env(?:\.|$)",
        r"(^|[\\/])(?:credentials|secrets?)(?:\.|[\\/]|$)",
        r"(^|[\\/])(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock)$",
        r"(^|[\\/])(?:Dockerfile|docker-compose[^\\/]*\.ya?ml)$",
        r"(^|[\\/])(?:\.github[\\/]workflows|k8s|kubernetes|terraform|migrations?)([\\/]|$)",
    ], combined)
    edit_like = any(x in tool_name for x in ["edit", "replace", "create_file", "write"])
    if sensitive_path and edit_like:
        emit("ask", "Sensitive configuration, lockfile, infrastructure, migration, or credential-related edit requires explicit confirmation.")
        return 0

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
