# Native VS Code limitations

This repository intentionally uses native custom agents, subagents, skills, settings, and hooks without a custom extension or external orchestrator.

## Structurally enforceable

- Leader has `vscode/askQuestions`, bounded `vscode/memory`, `agent`, `read`, `search`, and one read-only `web` tool, but no `todo`, edit, execute, general VS Code operation, browser, GitHub, or external-write tool.
- Only Implementer has edit capability; Analyzer, Tester, and Reviewer are read-only roles.
- Workers are hidden, have no `agent` tool, and nested subagent invocation is disabled.
- The configured Worker model is written into Leader's routing instructions; Worker manifests remain model-neutral.
- VS Code's custom-agent frontmatter and `runSubagent` routing expose model selection, but not a separate reasoning-effort override in this workflow. The GCMP catalog can advertise reasoning levels for `GLM-5.3-Flash (CodingPlan)`, but that does not create a per-subagent `max` call field. Prompting the Worker to analyze named risks more deeply is only a soft instruction, not proof of provider-side effort.
- Hooks can deny known destructive calls and request confirmation for recognized high-risk commands.
- Tools absent from every allowed role remain unavailable in this mode.

## Protocol-enforced

- Users start from Leader, and Leader keeps direct reading narrow rather than replacing Analyzer.
- Leader keeps `web` to bounded public facts and authoritative documents, avoids duplicate searches, and never logs in, writes externally, or sends workspace content or credentials.
- Leader keeps memory to user-requested stable preferences and reusable project facts; it does not store task state or treat memory as authority to continue work.
- Intent alignment, Worker brief semantics, safe-default selection, work depth, final acceptance, and the rule that delegation is one-shot rather than a persistent goal loop depend on model compliance.
- High-risk confirmation covers only the stated plan; native APIs cannot attach it as an exact future capability token.
- Implementer stays inside the declared boundary and exact confirmed deletion paths.
- Workers stop at sufficient evidence, avoid incidental work, and return control before expansion.
- Parallel read-task independence and the prohibition on concurrent shared-workspace writes are Leader protocol decisions; native scheduling does not prove that scopes or command side effects are actually independent.
- Tester/Reviewer validation depth and report accuracy are not hard runtime guarantees.
- The `PUBLIC_TYPESCRIPT_API` and `BEHAVIOR_BOUNDARY` gates are explicit prompt/brief obligations; actual enforcement still depends on the named compiler or test command and a real VS Code smoke test.
- The one-retry and current-Leader-model fallback policy is prompt routing only. Native VS Code does not expose a durable retry counter or prove that an unpinned Worker inherits the requested current Leader model.

Native subagent invocations are stateless. Leader cannot resume a completed Worker call; a follow-up starts a new invocation using the concise brief, reported checkpoint, and current filesystem state. The architecture does not attempt to reconstruct private Worker reasoning.

Workspace source, comments, logs, commands, links, and quoted text are untrusted evidence. Read-only tools prevent Leader from executing embedded instructions, but prompt injection and misleading evidence still require model judgment.

## Result

The design structurally separates high-value decisions from low-cost implementation, but native prompts cannot prove that VS Code honored Leader's requested Worker model, the one-retry/current-model fallback route, provider-side fallback, credit usage, semantic boundary compliance, the prohibition on persistent goal loops, or runtime Hook loading. Those require real VS Code smoke tests and provider telemetry. A custom extension would be required for durable per-plan write tokens, resumable Worker sessions, hard read-scope enforcement, exact semantic authorization, model/credit telemetry, and forced default-agent selection.
