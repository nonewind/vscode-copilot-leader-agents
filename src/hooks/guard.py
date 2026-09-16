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


def path_text(value: Any) -> str:
    """Return only structured path-like fields; never inspect edit bodies."""
    if not isinstance(value, dict):
        return ""
    parts: list[str] = []
    for key, item in value.items():
        normalized = str(key).lower()
        if normalized in {"path", "file", "file_path", "target", "target_path", "uri", "notebook_path"} or normalized.endswith("_path"):
            if isinstance(item, list):
                parts.extend(str(entry) for entry in item)
            else:
                parts.append(str(item))
        elif isinstance(item, dict):
            nested = path_text(item)
            if nested:
                parts.append(nested)
        elif isinstance(item, list):
            for entry in item:
                nested = path_text(entry)
                if nested:
                    parts.append(nested)
    return " ".join(parts)


def matches(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            return pattern
    return None


def terminal_delete_decision(command: str) -> str | None:
    """Return `ask` for one parseable deletion plan, otherwise `deny`.

    A Hook approval belongs to one tool invocation.  Consequently a literal
    `rm` command may name several files or a recursive directory and still
    receives one confirmation prompt; the Hook never attempts to retain that
    approval for a later, different command.
    """
    if not matches([
        r"\b(?:rm|unlink|del|erase|Remove-Item)\b",
        r"\b(?:rmdir|rd)\b",
        r"\bfind\b[^\n]*\s-delete\b",
        r"\bgit\s+rm\b",
    ], command):
        return None

    if matches([r"(?:&&|[;&|><])"], command):
        return "deny"

    if matches([
        r"\bfind\b[^\n]*\s-delete\b",
        r"\bgit\s+rm\b",
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
    if program in {"cmd", "cmd.exe"}:
        if args and args[0].lower() == "/d":
            args.pop(0)
        if not args or args.pop(0).lower() != "/c" or not args:
            return "deny"
        program = args.pop(0).lower()
    targets: list[str] = []

    if program == "rm":
        for arg in args:
            if arg in {"--", "-f", "--force", "-r", "-R", "--recursive", "-rf", "-fr", "-rR", "-Rf"}:
                continue
            if arg.startswith("-"):
                return "deny"
            targets.append(arg)
    elif program == "unlink":
        targets = [arg for arg in args if arg != "--"]
        if any(target.startswith("-") for target in targets):
            return "deny"
    elif program == "del":
        for arg in args:
            if arg.lower() in {"/f", "/q", "/s"}:
                continue
            if arg.startswith(("/", "-")):
                return "deny"
            targets.append(arg)
    elif program in {"rmdir", "rd"}:
        targets = [arg for arg in args if arg not in {"--", "/s", "/q"}]
        if any(target.startswith("-") for target in targets):
            return "deny"

    shell_expansion_chars = set("*?$`[]{}~!^%&|<>()#")
    if targets and all(
        not target.startswith("=") and not any(char in target for char in shell_expansion_chars)
        for target in targets
    ):
        return "ask"
    return "deny"


def github_decision(tool_name: str) -> str | None:
    """Allow named read-only GitHub tools and require confirmation for every other GitHub action."""
    if not re.search(r"(?:^|[./:_-])github(?:[./:_-]|$)", tool_name, flags=re.IGNORECASE):
        return None

    read_only = (
        "get", "list", "search", "read", "view", "fetch", "compare", "diff", "status", "download",
    )
    action = re.split(r"(?i)github[./:_-]+", tool_name, maxsplit=1)[-1].lower()
    return None if any(action.startswith(prefix) for prefix in read_only) else "ask"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return 0

    tool_name = str(data.get("tool_name", "")).lower()
    tool_input = data.get("tool_input", {})
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    paths = path_text(tool_input)

    if github_decision(tool_name) == "ask":
        emit("ask", "GitHub write or unknown action requires explicit user confirmation.")
        return 0

    hard_deny = [
        r"\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b",
        r"\bgit\s+branch\s+(-d|-D|-m|-M|--delete|--move)\b",
    ]
    hit = matches(hard_deny, command)
    if hit:
        emit("deny", "Destructive or Git-writing operation blocked by the Leader security policy.")
        return 0

    delete_tools = ["deletefile", "delete_file", "removefile", "remove_file"]
    delete_decision = terminal_delete_decision(command)
    if delete_decision == "deny":
        emit("deny", "Deletion is allowed only as one standalone command with literal, non-expanded targets.")
        return 0
    if any(name in tool_name for name in delete_tools) or delete_decision == "ask":
        emit("ask", "This deletion plan requires one explicit confirmation for the current command; approval does not carry to later commands.")
        return 0

    approval_required = [
        r"\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update|upgrade)\b",
        r"\b(pip|pip3|poetry|uv|conda)\s+(install|add|remove|sync|update)\b",
        r"\b(cargo\s+add|go\s+get|dotnet\s+add\s+package)\b",
        r"\b(apt|apt-get|yum|dnf|pacman|brew|choco|winget)\s+(install|remove|upgrade|update)\b",
        r"\b(alembic\s+upgrade|flask\s+db\s+upgrade|manage\.py\s+migrate|prisma\s+migrate|sequelize[^\n]*db:migrate|knex[^\n]*migrate|rails\s+db:migrate)\b",
        r"\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete|patch|replace)|helm\s+(install|upgrade|uninstall)|docker\s+(push|rm|rmi)|aws\s+[^\n]*(deploy|update|delete)|gcloud\s+[^\n]*(deploy|delete)|az\s+[^\n]*(create|update|delete))\b",
    ]
    hit = matches(approval_required, command)
    if hit:
        emit("ask", "Environment, dependency, migration, deployment, or external mutation requires explicit user confirmation.")
        return 0

    sensitive_path = matches([
        r"(^|[\\/])\.env(?:\.|$)",
        r"(^|[\\/])(?:credentials|secrets?)(?:\.|[\\/]|$)",
        r"(^|[\\/])(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock)$",
        r"(^|[\\/])(?:Dockerfile|docker-compose[^\\/]*\.ya?ml)$",
        r"(^|[\\/])(?:\.github[\\/]workflows|k8s|kubernetes|terraform|migrations?)([\\/]|$)",
    ], paths)
    edit_like = any(x in tool_name for x in ["edit", "replace", "create_file", "write"])
    if sensitive_path and edit_like:
        emit("ask", "Sensitive configuration, lockfile, infrastructure, migration, or credential-related edit requires explicit confirmation.")
        return 0

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
