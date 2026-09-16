# Contributing

Changes must preserve these invariants:

- Leader owns intent alignment, key decisions, risk classification, worker routing, synthesis, and acceptance. It has `vscode/askQuestions`, bounded `vscode/memory`, `agent`, `read`, `search`, and one read-only `web` tool, but no `todo`. Memory is limited to user-requested stable preferences and reusable project facts; it never stores task state or triggers work. Leader uses source and web access only for narrow decisive facts; it never edits, executes, logs in, writes externally, sends workspace content or credentials, or takes over Worker operations.
- Implementer has edit and execute capability within a Leader-declared scope; deletion requires a confirmed high-risk literal deletion plan and Hook confirmation.
- Workers are hidden and cannot invoke subagents.
- Leader owns the configured Worker model and explicitly specifies it on each initial invocation; VS Code Worker manifests stay model-neutral; Codex and ZCode pin their models in native definitions. Analyzer handles focused read-only facts; Implementer handles the smallest sufficient change and direct self-verification. Clear changes may go directly to Implementer without a redundant Analyzer stage.
- Every Worker receives a proportional brief with one concrete observable `GOAL`, explicit scope and non-goals in `BOUNDARIES`, itemized acceptance criteria and evidence in `DONE`, and escalation conditions in `STOP_AND_REPORT`. `GOAL` is plain text, not a command or persistent task; Leader must not simulate a Worker lifecycle, polling loop, or automatic reinvocation through other tools or prose. The Worker stops at sufficient evidence, does not pursue incidental findings, and returns `NEEDS_LEADER` before expanding product choices, boundaries, risk, or validation depth.
- A changed public TypeScript export/type/signature declares `PUBLIC_TYPESCRIPT_API` in `DONE` and supplies isolated compiler plus positive/negative consumer evidence. A changed observable empty/missing/nullish/zero/edge/no-data branch declares `BEHAVIOR_BOUNDARY` with source-supported expected rows. A triggered item cannot be accepted as `NOT_VERIFIED` or broadened into an unrelated suite.
- Parallelize necessary dependency-ready packages with non-overlapping file ownership, contracts, generated artifacts, and command side effects. Serialize only for a named dependency or conflict; Tester and Reviewer may overlap only when their commands do not contend for caches, generated artifacts, data, or environment state.
- Worker reports stay concise and evidence-based: exact source or command result, actual boundary, gaps, and one concrete decision request when needed. Do not reintroduce routine evidence ledgers, consensus stages, or an isolated arbitration agent.
- Native Worker invocations are stateless. Follow-up work starts a new invocation from the concise brief, reported checkpoint, and current filesystem state; never claim an in-place resume.
- Maintain direct-execution gates, failure routing, and cost discipline in `src/protocols/poor-mode.md`, then run `python3 scripts/sync_poor_mode.py --write`. Deterministic rejection skips identical retries; uncertain writer termination blocks replacement. VS Code permits one disclosed fallback; Codex does so only in explicit `parent-worker` mode; ZCode 0.8.0 stops.
- Do not add implementation capability to Leader. Add it to the least-privileged suitable Worker with matching guard coverage, or document that the request must leave this mode.
- Test and review are independent mandatory gates for high-risk work and discretionary, evidence-based gates for routine work.
- GitHub writes and unknown GitHub actions require Hook confirmation; named read-only GitHub actions remain available.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests -v` before submitting changes.
