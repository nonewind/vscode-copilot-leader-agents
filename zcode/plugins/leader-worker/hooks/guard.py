#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any


LEADER_BOUNDARY_MARKERS = (
    "<!-- leader-worker-agents:start -->",
    "# Leader/Worker mode for ZCode",
)
LEADER_EDIT_TOOLS = {"edit", "write", "applypatch", "notebookedit"}
LEADER_COMMAND_TOOL = "bash"


def emit(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason,
    }}))


def flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {flatten(item)}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(flatten(item) for item in value)
    return str(value)


def hit(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def leader_boundary_active(data: dict[str, Any]) -> bool:
    cwd = data.get("cwd") or os.environ.get("ZCODE_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR") or ""
    if not cwd:
        return False
    directory = Path(cwd)
    for candidate in (directory, *directory.parents[:3]):
        try:
            text = (candidate / "AGENTS.md").read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in text for marker in LEADER_BOUNDARY_MARKERS):
            return True
    return False


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
    combined = f"{tool_name} {flatten(tool_input)}"
    command = str(tool_input.get("command", "")) if isinstance(tool_input, dict) else ""

    normalized = tool_name.strip().lower()
    if leader_boundary_active(data):
        if normalized.startswith("mcp__"):
            emit("deny", leader_boundary_reason("mcp"))
            return 0
        if normalized == LEADER_COMMAND_TOOL:
            emit("deny", leader_boundary_reason("command"))
            return 0
        if normalized in LEADER_EDIT_TOOLS:
            emit("deny", leader_boundary_reason("edit"))
            return 0

    if hit([r"\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b"], combined):
        emit("deny", "Git-writing operations are blocked by the Leader/Worker policy.")
        return 0
    deletion = delete_decision(command)
    if deletion:
        emit(deletion, "Deletion requires one standalone command with literal targets and explicit confirmation.")
        return 0
    if hit([
        r"\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update|upgrade)\b",
        r"\b(pip|pip3|poetry|uv|conda)\s+(install|add|remove|sync|update)\b",
        r"\b(alembic\s+upgrade|flask\s+db\s+upgrade|manage\.py\s+migrate|prisma\s+migrate)\b",
        r"\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete)|helm\s+(install|upgrade|uninstall)|docker\s+push)\b",
    ], combined):
        emit("ask", "Dependency, environment, migration, deployment, or external mutation requires explicit confirmation.")
        return 0
    print(json.dumps({"continue": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
