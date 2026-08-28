# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | `vscode/askQuestions`, `vscode/memory`, `agent`, `read`, `search`, `web` | Intent, key decisions, bounded memory/source/web checks, routing, synthesis, acceptance |
| Analyzer | Worker model | No | `read`, `search` | Focused read-only facts |
| Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Minimum sufficient scoped changes and direct self-checks |
| Tester | Worker model | No | `read`, `search`, `execute` | Targeted acceptance validation |
| Reviewer | Worker model | No | `read`, `search`, `execute` | Independent diff, boundary, correctness, and risk review |

Leader cannot edit, execute commands, perform general VS Code operations, use a browser, call GitHub, or write to external services. Its read-only tools are reserved for a small fact that materially changes a decision and cannot be trusted from current Worker evidence. `web` is the only network tool and is restricted to a bounded public fact or authoritative document unavailable from the workspace; it never logs in, writes externally, or sends workspace content or credentials. Memory retains only stable preferences or reusable project facts the user explicitly asks to remember; task goals, plans, todos, Worker progress, checkpoints, open items, and continuation instructions are forbidden. Routine repository exploration stays on the low-cost model.

The installed Leader configuration owns model routing. Its default Worker model is `GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)`, backed by GCMP catalog ID `glm-5.3-flash` and selector route `gcmp.zhipu:::glm-5.3-flash`. Worker manifests are model-neutral. The current VS Code subagent interface has no independent per-subagent reasoning-effort call field, so the design neither sends a fabricated `reasoningEffort` field nor claims a `max` setting even if a model catalog exposes reasoning levels. An invocation error or `MODEL_UNAVAILABLE` receives one stateless retry with the same brief and checkpoint. If both attempts fail for that model reason, Leader invokes the same Worker role without a Worker-model override so it inherits the current Leader model for the remaining in-scope task. `FAIL`, `BLOCKED`, `NEEDS_LEADER`, and inadequate task results do not trigger a model retry; no third model is discovered.

Workers are hidden, have no `agent` tool, and cannot create nested subagents. Implementer is the only role with edit capability. Hooks remain defense in depth for known dangerous operations.

## Control loop

```text
REQUEST
  -> LEADER_INTENT_ALIGNMENT
      -> RESULT_CHANGING_AMBIGUITY -> USER_QUESTION -> INTENT_ALIGNMENT
      -> CLEAR_ANALYSIS -> DEPENDENCY_CHECK
          -> INDEPENDENT_READS -> ANALYZER_A || ANALYZER_B || ANALYZER_C -> LEADER_DECISION
          -> DEPENDENT_READS -> SERIAL_ANALYZER -> LEADER_DECISION
          -> CLEAR_CHANGE -> WORKER_BRIEF
          -> WORKER_MODEL_ERROR -> SAME_WORKER_RETRY_ONCE -> MAIN_MODEL_SAME_WORKER_ROLE
          -> ROUTINE -> IMPLEMENTER -> NARROW_SELF_CHECK -> LEADER_ACCEPTANCE
          -> HIGH_RISK -> USER_CONFIRMATION -> IMPLEMENTER -> TESTER || REVIEWER -> LEADER_ACCEPTANCE
          -> NEEDS_LEADER
              -> DIRECT_THREAT_TO_DONE -> ONE_TARGETED_REWORK -> ONE_DIRECT_RECHECK -> LEADER_ACCEPTANCE_OR_REPORT
              -> GAP_ONLY -> LEADER_ACCEPTANCE_OR_REPORT
              -> NEW_BOUNDARY_OR_AUTHORITY -> USER_DECISION
```

Every Worker brief states:

- `GOAL`: one concrete observable result;
- `BOUNDARIES`: explicit allowed scope, preserved behavior, and non-goals;
- `DONE`: itemized acceptance criteria and sufficient direct evidence for each;
- `STOP_AND_REPORT`: conditions that return control to Leader.

The brief is semantic and proportional, not a fixed field budget. GLM-5.3-Flash is treated as a low-cost executor: Leader resolves intent, decomposes work, and makes key choices before delegation. A change brief includes direct problem evidence, required behavior, exact allowed files or symbols, preserved behavior, non-goals, itemized evidence for every `DONE` item, and dependency order when one exists. For a changed consumer-visible TypeScript export/type/signature, Leader declares `PUBLIC_TYPESCRIPT_API` in `DONE` with named compiler evidence and a positive/negative external-consumer fixture. For a changed observable data or branch boundary, it declares `BEHAVIOR_BOUNDARY` with only source-supported boundary rows and expected results. Triggered items are mandatory narrow contract gates, not optional `NOT_VERIFIED` gaps or broad-suite triggers. Open phrases such as “related files,” “fix appropriately,” “as needed,” or “check everything” are not valid boundaries. Delegation is one direct stateless invocation. `GOAL` is a plain-text field, not a goal command or persistent task. Leader has no `todo` tool and must not use memory, other tools, or prose to simulate a Worker lifecycle, polling loop, or automatic reinvocation. Workers stop at `DONE`, do not pursue incidental findings, and return `NEEDS_LEADER` before a new product choice, boundary expansion, high-risk action, or materially deeper validation.

## Parallelism

The workflow is a parallel-read, serial-write funnel. Leader may fan out distinct read-only questions when they have no output dependency, use non-overlapping boundaries, can be synthesized independently, and create no shared side effects. Each Analyzer answers one question; parallelism never authorizes duplicate broad scans.

Implementation stays serial in the shared workspace by default. Tester and Reviewer may run concurrently after the diff is stable only when their commands do not contend for caches, generated artifacts, data, or environment state. Parallelism exists to shorten the critical path, not to increase total work.

## Decision ownership

- User owns product intent, explicit boundaries, new authority, and high-risk approval.
- Leader owns interpretation, safe defaults, technical tradeoffs, Worker selection, work depth, and final acceptance.
- Workers own factual investigation and execution inside the brief; they do not enlarge it.

When a Worker reports conflict, Leader first decides whether existing direct evidence already supports `DONE`. `NEEDS_LEADER`, `NOT_VERIFIED`, theoretical risk, suggested expansion, and incidental findings do not trigger more work by themselves. Only new concrete evidence that directly threatens a named `DONE` item permits one targeted rework round and one direct recheck. If the conflict turns on a specific source location, Leader may inspect that location directly with `read/search` while retaining the full user conversation. After the recheck, Leader must accept the supported result or report unsupported items and remaining risk instead of opening another validation chain.

## Verification

Verification climbs only on evidence: direct diff/behavior, target check, module check on shared impact or failure, then broad validation only for confirmed cross-module/high-risk needs. A declared `PUBLIC_TYPESCRIPT_API` requires Tester compiler evidence and narrow Reviewer export/consumer review; a public input/output `BEHAVIOR_BOUNDARY` requires Tester matrix evidence. Leader owns the stopping decision. High-risk completion still requires independent Tester and Reviewer PASS, but failure or incomplete evidence does not authorize an unbounded loop: after the single rework and recheck budget, Leader stops and reports the task as unsupported or incomplete.

## Authorization boundary

High-risk confirmation covers only the stated plan and does not authorize later expansion. Native VS Code cannot bind natural-language approval to a durable capability token, so semantic scope remains protocol-enforced even though tool availability and Hook decisions are structural controls.
