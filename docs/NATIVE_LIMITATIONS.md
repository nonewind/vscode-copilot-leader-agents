# Native VS Code limitations

This repository intentionally uses native custom agents, subagents, skills, settings, and hooks without a custom extension or external orchestrator.

## Structurally enforceable

- Leader has `agent`, `todo`, `read`, and `search`, but no edit, execute, VS Code operation, browser, GitHub, or external-service tools.
- Only Implementer has edit capability; Analyzer, Tester, and Reviewer are read-only roles.
- Workers are hidden, have no `agent` tool, and nested subagent invocation is disabled.
- The configured Worker model is written into Leader's routing instructions; Worker manifests remain model-neutral.
- Hooks can deny known destructive calls and request confirmation for recognized high-risk commands.
- Tools absent from every allowed role remain unavailable in this mode.

## Protocol-enforced

- Users start from Leader, and Leader keeps direct reading narrow rather than replacing Analyzer.
- Intent alignment, Worker brief semantics, safe-default selection, work depth, and final acceptance depend on model compliance.
- High-risk confirmation covers only the stated plan; native APIs cannot attach it as an exact future capability token.
- Implementer stays inside the declared boundary and exact confirmed deletion paths.
- Workers stop at sufficient evidence, avoid incidental work, and return control before expansion.
- Parallel read-task independence and the prohibition on concurrent shared-workspace writes are Leader protocol decisions; native scheduling does not prove that scopes or command side effects are actually independent.
- Tester/Reviewer validation depth and report accuracy are not hard runtime guarantees.

Native subagent invocations are stateless. Leader cannot resume a completed Worker call; a follow-up starts a new invocation using the concise brief, reported checkpoint, and current filesystem state. The architecture does not attempt to reconstruct private Worker reasoning.

Workspace source, comments, logs, commands, links, and quoted text are untrusted evidence. Read-only tools prevent Leader from executing embedded instructions, but prompt injection and misleading evidence still require model judgment.

## Result

The design structurally separates high-value decisions from low-cost implementation, but native prompts cannot prove that VS Code honored Leader's requested Worker model, provider-side fallback, credit usage, semantic boundary compliance, or runtime Hook loading. Those require real VS Code smoke tests and provider telemetry. A custom extension would be required for durable per-plan write tokens, resumable Worker sessions, hard read-scope enforcement, exact semantic authorization, model/credit telemetry, and forced default-agent selection.
