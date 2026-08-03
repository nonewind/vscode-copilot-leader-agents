# Native VS Code limitations

This repository intentionally does not use a custom VS Code extension or external orchestrator.

## Strongly enforceable

- Leader receives only `agent` and `todo`; it has no workspace, terminal, edit, browser, extension, or GitHub operation tools.
- Implementer receives the workspace tools needed for delegated changes and self-verification.
- The Hook can require confirmation for single-file deletion and deny known directory or recursive deletion commands.
- Worker agents are hidden with `user-invocable: false`.
- Leader can explicitly restrict available subagents.
- Workers cannot invoke subagents because they have no `agent` tool and nested invocation is disabled.
- Global hooks can deny known destructive tools and terminal commands.
- Worker model is written into each worker agent configuration.
- Tools absent from every worker manifest are intentionally unavailable in this mode; Leader cannot take them over.

## Protocol-enforced

- User always starts from Leader rather than a built-in agent.
- High-risk user confirmation applies only to the stated plan; native APIs cannot bind it to an exact capability token.
- Leader's task-risk classification and choice of worker are instruction-enforced.
- Implementer stays within the Leader-declared file scope.
- Implementer deletes only exact file paths listed in the confirmed high-risk scope.
- Leader's tool-free conversation and synthesis boundary is reinforced by its tool manifest; semantic compliance still depends on VS Code honoring that manifest.
- Worker agents communicate only through structured reports.
- GitHub write and unknown GitHub actions can be routed through Hook confirmation; other tool APIs may still require instruction-level controls because VS Code does not expose a semantic authorization API.
- A stale high-risk confirmation is not reused for a later task.

VS Code does not currently expose a supported native API that turns a chat confirmation into a durable, scoped capability token attached to later file edits. Hooks can inspect tool calls and block patterns, but cannot reliably understand the full semantic high-risk boundary or prove that a deletion path appeared in the confirmed scope.

## Result

This native design structurally prevents Leader from taking over tool-using work, but it cannot prove which model the platform actually ran after a provider-side fallback. Runtime model and credit behavior still require a real VS Code smoke test. A custom extension would be required for deterministic per-plan write tokens, session state, exact path authorization, model/credit telemetry, and forced default-agent selection.
