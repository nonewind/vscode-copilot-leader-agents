#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any


START_MARKER = "<!-- leader-worker-agents:start -->"
END_MARKER = "<!-- leader-worker-agents:end -->"
LEGACY_HEADER = "# Leader/Worker mode for ZCode"
MODE_PATTERN = re.compile(r"(?m)^leader-worker-execution-mode:\s*(strict|adaptive)\s*$")
LEADER_EDIT_TOOLS = {"edit", "write", "applypatch", "notebookedit"}
LEADER_COMMAND_TOOL = "bash"


def emit(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))


def path_text(value: Any) -> str:
    """Return structured path-like fields without scanning edit bodies."""
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


def hit(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def mode_from_text(text: str) -> str | None:
    start_count = text.count(START_MARKER)
    end_count = text.count(END_MARKER)
    if start_count or end_count:
        if start_count != 1 or end_count != 1:
            return "strict"
        start = text.index(START_MARKER) + len(START_MARKER)
        end = text.index(END_MARKER, start)
        matches = MODE_PATTERN.findall(text[start:end])
        return matches[0] if len(matches) == 1 else "strict"
    if LEGACY_HEADER in text:
        return "strict"
    return None


def leader_mode(data: dict[str, Any]) -> str | None:
    explicit_root = (
        data.get("project_root")
        or data.get("projectRoot")
        or os.environ.get("ZCODE_PROJECT_DIR")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or ""
    )
    if explicit_root:
        candidates = (Path(str(explicit_root)),)
    else:
        cwd = data.get("cwd") or ""
        if not cwd:
            return None
        directory = Path(str(cwd))
        candidates = (directory, *directory.parents)
    for candidate in candidates:
        try:
            text = (candidate / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        mode = mode_from_text(text)
        if mode is not None:
            return mode
    return None


def leader_boundary_reason(kind: str) -> str:
    if kind == "command":
        return (
            "Leader/Worker mode is active: the primary Agent plans, adjudicates, and accepts, and does not "
            "run workspace commands itself. Restate the work as one bounded package and dispatch it: "
            "implementation and setup commands to leader-implementer, targeted validation commands to "
            "leader-tester, and read-only fact questions to leader-analyzer. To leave the mode, remove the "
            "Leader/Worker block from AGENTS.md instead of working around the guard."
        )
    if kind == "edit":
        return (
            "Leader/Worker mode is active: the primary Agent plans, adjudicates, and accepts, and does not "
            "edit files itself. Restate the change as one bounded package with GOAL, BOUNDARIES, DONE, and "
            "STOP_AND_REPORT, and dispatch it to leader-implementer. To leave the mode, remove the "
            "Leader/Worker block from AGENTS.md instead of working around the guard."
        )
    return (
        "Leader/Worker mode is active: primary-Agent MCP tools sit outside the Leader boundary. Delegate the "
        "task to a Worker whose tools cover it, or report the limitation to the user, instead of bypassing "
        "the guard."
    )


def delete_decision(command: str) -> str | None:
    if not hit([r"\b(?:rm|unlink|del|erase|Remove-Item|rmdir|rd)\b", r"\bfind\b[^\n]*\s-delete\b", r"\bgit\s+rm\b"], command):
        return None
    if hit([r"(?:&&|[;&|><])", r"\bfind\b[^\n]*\s-delete\b", r"\bgit\s+rm\b"], command):
        return "deny"
    try:
        tokens = shlex.split(command)
    except ValueError:
        return "deny"
    ignored = {"--", "-f", "--force", "-r", "-R", "--recursive", "-rf", "-fr", "/f", "/q", "/s"}
    targets = [token for token in tokens[1:] if token not in ignored]
    unsafe = set("*?$`[]{}~!^%&|<>()#=")
    return "ask" if targets and all(not any(char in target for char in unsafe) for target in targets) else "deny"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return 0
    tool_name = str(data.get("tool_name", ""))
    tool_input = data.get("tool_input", {})
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""
    paths = path_text(tool_input)

    normalized = tool_name.strip().lower()
    mode = leader_mode(data)

    if command and hit([
        r"\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b",
        r"\bgit\s+branch\s+(-d|-D|-m|-M|--delete|--move)\b",
    ], command):
        emit("deny", "Git-writing operations are blocked by the Leader/Worker policy.")
        return 0
    deletion = delete_decision(command)
    if deletion == "deny":
        emit("deny", "Deletion requires one standalone command with literal targets and explicit confirmation.")
        return 0

    if mode == "strict":
        if normalized.startswith("mcp__"):
            emit("deny", leader_boundary_reason("mcp"))
            return 0
        if normalized == LEADER_COMMAND_TOOL:
            emit("deny", leader_boundary_reason("command"))
            return 0
        if normalized in LEADER_EDIT_TOOLS:
            emit("deny", leader_boundary_reason("edit"))
            return 0

    if mode == "adaptive" and normalized.startswith("mcp__"):
        emit("deny", leader_boundary_reason("mcp"))
        return 0

    if deletion == "ask":
        emit("ask", "Deletion requires one standalone command with literal targets and explicit confirmation.")
        return 0

    if command and hit([
        r"\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update|upgrade)\b",
        r"\b(pip|pip3|poetry|uv|conda)\s+(install|add|remove|sync|update)\b",
        r"\b(cargo\s+add|go\s+get|dotnet\s+add\s+package)\b",
        r"\b(apt|apt-get|yum|dnf|pacman|brew|choco|winget)\s+(install|remove|upgrade|update)\b",
        r"\b(alembic\s+upgrade|flask\s+db\s+upgrade|manage\.py\s+migrate|prisma\s+migrate)\b",
        r"\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete|patch|replace)|helm\s+(install|upgrade|uninstall)|docker\s+(push|rm|rmi))\b",
    ], command):
        emit("ask", "Dependency, environment, migration, deployment, or external mutation requires explicit confirmation.")
        return 0

    if normalized in LEADER_EDIT_TOOLS and hit([
        r"(^|[\\/])\.env(?:\.|$)",
        r"(^|[\\/])(?:credentials|secrets?)(?:\.|[\\/]|$)",
        r"(^|[\\/])(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock)$",
        r"(^|[\\/])(?:Dockerfile|docker-compose[^\\/]*\.ya?ml)$",
        r"(^|[\\/])(?:\.github[\\/]workflows|k8s|kubernetes|terraform|migrations?)([\\/]|$)",
    ], paths):
        emit("ask", "Sensitive configuration, lockfile, infrastructure, migration, or credential-related edit requires explicit confirmation.")
        return 0

    if mode == "adaptive":
        if normalized == LEADER_COMMAND_TOOL:
            emit("ask", "Adaptive Leader mode requires explicit approval for this direct command.")
            return 0
        if normalized in LEADER_EDIT_TOOLS:
            emit("ask", "Adaptive Leader mode requires explicit approval for this direct edit.")
            return 0

    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
