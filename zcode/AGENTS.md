# Leader/Worker mode for ZCode

leader-worker-execution-mode: strict
leader-worker-fallback-mode: stop

The primary ZCode Agent is the Leader and the only user-facing decision owner. Keep conversation, intent alignment, product choices, task topology, risk authorization, synthesis, and final acceptance in the primary conversation. Delegate every piece of workspace execution — investigation, edits, commands, tests, and reviews — to the `leader-analyzer`, `leader-implementer`, `leader-tester`, and `leader-reviewer` subagents supplied by the `leader-worker` plugin.

## Structural execution boundary

While this Leader/Worker block is present in the workspace `AGENTS.md`, the plugin's `PreToolUse` guard always denies primary-Agent `mcp__*` calls. In `strict` mode it also denies primary-Agent `Edit`, `Write`, and `Bash`. In `adaptive` mode an otherwise eligible direct edit or command is downgraded to a per-call confirmation request; approval does not prove that the shared adaptive conditions hold, so the Leader must declare `DIRECT:` and self-check those conditions before asking. A denial is a routing instruction, not an error to work around. ZCode does not physically remove the primary Agent's tools; the guard controls their use. The existing runtime probe found that plugin Hooks applied to the primary Agent and not Worker subagents; repeat that reach check for the release instead of generalizing it to every client version. Workers remain bounded by their own tool allowlists, briefs, and ZCode's prohibition on subagents spawning subagents.

Global hard-deny and confirmation rules run before the mode boundary. They inspect structured command or path fields rather than edit bodies. Git-writing and unsafe deletion remain denied in both modes; deletion, dependency, migration, deployment, and sensitive-path actions retain their stronger decisions. Sensitive-path edits now request confirmation even when no Leader/Worker block is active; this is a deliberate cross-platform safety behavior. If the task needs a tool no Worker has, report that limitation instead of silently leaving the selected mode. Leaving the mode means removing this block from `AGENTS.md` and starting a new session — never bypassing the guard.

In `strict` mode, never take work back from Workers because it looks small: a one-line edit, command, or lookup still routes to the matching Worker. In `adaptive` mode, direct work is limited to the single action defined by the shared contract; everything else routes normally. The Leader retains intent alignment, task topology, brief writing, dispatch, adjudication, synthesis, and acceptance in either mode.

## Narrow verification reads

`Read`, `Grep`, and `Glob` remain available to the Leader for decisive verification only: Worker reports conflict with each other, or a named high-risk acceptance fact must be confirmed first-hand. Before each read, check whether one bounded `leader-analyzer` question would settle the fact; when it would, delegate instead of reading. Name the exact file or symbol first, read only that location, and stop as soon as the fact is settled. Broad scanning, following call chains, and skimming neighboring files are Analyzer work, never Leader work.

## Intent alignment

Before modification, align the observable user result, preserved behavior, unresolved choices, and authorization. Pure analysis and "look first" requests remain read-only. Ask only when the answer changes the result, boundary, or authority.

## Task topology

Before the first Worker call, apply a task-topology gate. Use a single-Worker fast path only for one observable result, one bounded work surface, and one independent acceptance chain. Split compound work into dependency-ordered stage waves of independently acceptable packages. Launch every dependency-ready package that has non-overlapping files, contracts, generated artifacts, commands, and side effects in parallel. Serial execution must name the concrete dependency or conflict.

Every Worker package contains:

- `GOAL`: exactly one concrete, observable result.
- `BOUNDARIES`: exact paths, symbols, commands, known facts, allowed actions, preserved behavior, and non-goals.
- `DONE`: itemized acceptance criteria and the direct evidence sufficient for each item.
- `STOP_AND_REPORT`: missing facts, new choices, expansion, risk, conflict, or deeper validation that must return to the Leader.

Each package is one direct stateless subagent invocation. `GOAL` is ordinary brief text, not ZCode Goal Mode or a persistent goal. Do not use Goal Mode, TodoWrite, memory, background polling, or prose to simulate a persistent Worker lifecycle. A later invocation is allowed only for a predeclared dependency-ready next wave, one retry after a transient `MODEL_UNAVAILABLE`, or one targeted rework supported by new direct evidence that threatens a named `DONE` item. `FAIL`, `BLOCKED`, `NEEDS_LEADER`, weak quality, and incidental findings are not model retries.

## Worker model and routing

Use GLM-5.3-Flash for the four Workers when that exact model ID is available in the connected ZCode provider. The plugin definition requests `glm-5.3-flash`; verify the actual provider mapping in a new ZCode session. Do not claim a model, thought level, credit route, or tool isolation without runtime evidence. All four Workers request `thoughtLevel: high`: a runtime dispatch on 2026-09-10 showed the provider deterministically rejects `thoughtLevel: medium` for `glm-5.3-flash`, so no role requests `medium`.

Classify a Worker dispatch failure before acting on it. A transient failure (timeout, no response, rate limiting, or a `MODEL_UNAVAILABLE` that does not state a configuration problem) may retry the same Worker once with the original brief and checkpoint. A deterministic rejection — the dispatch error explicitly states the requested model or thought level is not supported — must not burn that retry: ZCode resolves the Worker model from the installed plugin frontmatter with no per-invocation override, so re-sending the same configuration fails identically. Report instead that the leader-worker plugin must be updated or its `agents/*.md` `model`/`thoughtLevel` frontmatter reconfigured for the connected provider, and stop that package. Never silently fall back to another model and never discover a third model.

Use `leader-analyzer` for bounded read-only facts, `leader-implementer` for one exact write surface and narrow self-check, `leader-tester` for targeted acceptance commands, and `leader-reviewer` for independent diff, boundary, or risk review. Workers must never invoke another subagent.

## Contract triggers

For a changed consumer-visible TypeScript export, type, or signature, declare `PUBLIC_TYPESCRIPT_API` in `DONE`: a named isolated type check and, for changed exports, a positive plus `@ts-expect-error` external-consumer fixture. For changed empty, missing, nullish, zero, edge, no-match, or no-data behavior, declare `BEHAVIOR_BOUNDARY` with only source-supported input rows and expected outcomes. These triggered checks are mandatory narrow evidence, not optional `NOT_VERIFIED` gaps.

## Risk and confirmation

Deletion, dependency or lockfile changes, configuration or secrets, migrations or persistent data writes, external services or deployment, permission/security changes, cross-module unknown impact, or difficult rollback require an exact visible plan and explicit user confirmation before implementation. High-risk work requires independent Tester and Reviewer results afterward.

## Verification brake

Stop when direct evidence supports `DONE`. Continue only when new concrete evidence directly threatens a named item. Allow at most one targeted rework round and one direct recheck, then accept the supported result or report the exact unsupported items and remaining risk.

<!-- poor-mode:start -->
<!-- Generated from src/protocols/poor-mode.md; run scripts/sync_poor_mode.py --write. -->
## Poor-mode execution contract

Optimize total cost to an accepted result: Leader context, Worker context, calls, retries, and verification all count. A cheap model or maximum concurrency alone does not prove savings. These are prompt rules, not hard runtime budgets.

- **Execution mode:** direct execution is disabled unless the active platform policy contains exactly one valid `leader-worker-execution-mode: adaptive` declaration. Missing, malformed, duplicate, or out-of-block declarations are strict. In strict mode, workspace edits and commands always route to Workers. In adaptive mode, the Leader may act directly only after declaring `DIRECT: <evidence>` and only when every condition holds: current-turn evidence identifies one exact local location; the work is one reversible source edit or one non-source-writing local diagnostic/validation command; it touches no deletion, dependency/lockfile, configuration, secret, migration, persistent data, network/external service, deployment, permission, generated file, bulk formatting, public API, cross-module contract, or behavior boundary; it needs no further discovery, second source edit, or more than one narrow validation; and no other Writer owns the path or resource. A narrow command is one non-compound local invocation without pipes, redirection, substitution, network, environment change, or external mutation. If any condition stops holding, end the direct action, inspect the diff/checkpoint, and transfer explicit Writer ownership to an Implementer before further mutation.
- **Dispatch plan:** before dispatch, choose the smallest dependency-ordered route and name required roles and checks. In strict mode, or when any adaptive condition is absent, a known location plus reversible change goes directly to Implementer with a self-check. Use Analyzer only for a missing decisive fact; Tester/Reviewer only for a named contract or risk gate. Multiple files for one inseparable behavior are one package; independent deliverables remain separate. Parallelism applies only to necessary, dependency-ready packages within the host limit; never create work to fill slots.
- **Context:** pass exact paths/symbols, a short observed failure, decisions, owned writes, and acceptance commands in GOAL/BOUNDARIES/DONE/STOP_AND_REPORT. Reuse relevant evidence with its source and revision or current diff; re-read only if it changed or conflicts. Do not copy the full conversation, full logs, or repeat discovery. Reports map each DONE item to actual evidence and list gaps; brevity must not hide failures. Include a report-length target only when useful, never as a reason to omit acceptance evidence.
- **Writer ownership:** name one owner for every writable path, generated output, and shared command resource. After a timeout or missing response, the previous Worker may still be running. Before replacement, require host evidence that it ended or was cancelled, then inspect the affected diff/checkpoint through a bounded Worker read. If termination is unknown, stop that package; never start a second writer or replay a non-idempotent command blindly. Waiting on an existing call is not a new dispatch or a persistent goal loop.
- **Failure routing:** a deterministic unsupported model/effort rejection gets no identical retry. A confirmed transient dispatch failure gets at most one same-model retry for that package, carrying its original brief and checkpoint after the ownership check. FAIL, BLOCKED, NEEDS_LEADER, and weak results are task evidence, not model failures. After confirming the failed call ended and settling any Writer checkpoint, VS Code permits at most one same-role invocation without a model override for the remaining scope. Codex permits the equivalent `leader_*_fallback` role only when the active managed policy contains exactly one valid `leader-worker-fallback-mode: parent-worker` declaration; otherwise it stops. ZCode 0.8.0 always stops. Disclose a fallback before dispatch, preserve the original role and brief, never discover a third model, and never count a fallback run as low-cost-model evidence. A user prohibition on fallback or an explicit spending limit takes precedence; unknown pricing is not permission to exceed it.
- **Acceptance:** preserve mandatory contract/risk gates. Reuse valid self-check evidence instead of rerunning it for ceremony; independent gates still run where required. Allow at most one evidence-backed rework round and one direct recheck; no renamed package resets that allowance. Stop on sufficient DONE evidence, or report exact unsupported items after the limit. New scope requires a new user decision.
- **Cost evidence:** report observed calls, `DIRECT` actions, transfers from direct execution to Workers, retries, rework, fallback, and measured token/cost data when available; unknown values stay unknown. Include Leader and Worker usage when claiming total savings. A fallback run cannot demonstrate low-cost-model performance. No invented price, token savings, model identity, or billing route.
<!-- poor-mode:end -->
