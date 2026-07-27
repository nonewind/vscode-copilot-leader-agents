# Native VS Code limitations

This repository intentionally does not use a custom VS Code extension or external orchestrator.

## Strongly enforceable

- Leader and Implementer receive the tools needed for their configured workflows.
- The Hook can require confirmation for single-file deletion and deny known directory or recursive deletion commands.
- Worker agents are hidden with `user-invocable: false`.
- Leader can explicitly restrict available subagents.
- Workers cannot invoke subagents because they have no `agent` tool and nested invocation is disabled.
- Global hooks can deny known destructive tools and terminal commands.
- Worker model is written into each worker agent configuration.

## Protocol-enforced

- User always starts from Leader rather than a built-in agent.
- `批准执行` applies only to the latest plan.
- Leader writes only when the user explicitly assigns direct work in the current task.
- Implementer stays within the Leader-declared file scope.
- Implementer deletes only exact file paths listed in the latest approved plan.
- Leader uses direct read/command tools only for exceptional verification.
- Worker agents communicate only through structured reports.
- A stale approval is not reused for a later task.

VS Code does not currently expose a supported native API that turns a chat phrase into a durable, scoped capability token attached to later file edits. Hooks can inspect tool calls and block patterns, but cannot reliably understand the full semantic plan boundary or prove that a deletion path appeared in the latest approved plan.

## Result

This is the strongest practical design available under the native-only constraint. A custom extension would be required for deterministic per-plan write tokens, session state, exact path authorization, and forced default-agent selection.
