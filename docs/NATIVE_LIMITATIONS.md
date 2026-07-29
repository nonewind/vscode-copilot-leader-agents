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
- High-risk user confirmation applies only to the stated plan; native APIs cannot bind it to an exact capability token.
- Leader's task-risk classification and decision to execute directly or delegate are instruction-enforced.
- Implementer stays within the Leader-declared file scope.
- Implementer deletes only exact file paths listed in the confirmed high-risk scope.
- Leader's direct local investigation, implementation and validation for low-risk or routine work are instruction-enforced.
- Worker agents communicate only through structured reports.
- GitHub write and unknown GitHub actions can be routed through Hook confirmation; other tool APIs may still require instruction-level controls because VS Code does not expose a semantic authorization API.
- A stale high-risk confirmation is not reused for a later task.

VS Code does not currently expose a supported native API that turns a chat confirmation into a durable, scoped capability token attached to later file edits. Hooks can inspect tool calls and block patterns, but cannot reliably understand the full semantic high-risk boundary or prove that a deletion path appeared in the confirmed scope.

## Result

This is the strongest practical design available under the native-only constraint. A custom extension would be required for deterministic per-plan write tokens, session state, exact path authorization, and forced default-agent selection.
