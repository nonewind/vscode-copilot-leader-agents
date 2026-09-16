# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | strict: `vscode/askQuestions`, `vscode/memory`, `agent`, `read`, `search`, `web`; adaptive also: `edit`, `execute` | Intent, key decisions, bounded checks, routing, synthesis, acceptance; one adaptive direct action only when all gates hold |
| Analyzer | Worker model | No | `read`, `search` | Focused read-only facts |
| Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Minimum sufficient scoped changes and direct self-checks |
| Tester | Worker model | No | `read`, `search`, `execute` | Targeted acceptance validation |
| Reviewer | Worker model | No | `read`, `search`, `execute` | Independent diff, boundary, correctness, and risk review |

The default strict Leader cannot edit or execute commands. The optional adaptive Leader adds `edit` and `execute`, but may use them only after `DIRECT:` for one exact reversible source edit or one non-writing local diagnostic/validation command satisfying every shared-contract exclusion. Scope growth ends direct execution and transfers Writer ownership. Neither variant can perform general VS Code operations, use a browser, call GitHub, or write to external services. Read-only tools remain bounded; routine repository exploration stays on the low-cost model.

The installed Leader configuration owns model routing. Its default Worker model is `GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)`, backed by GCMP catalog ID `glm-5.3-flash` and selector route `gcmp.zhipu:::glm-5.3-flash`. Worker manifests are model-neutral. Dispatch failures are classified before retrying; VS Code permits one disclosed same-role call without a model override after eligible failure. `FAIL`, `BLOCKED`, `NEEDS_LEADER`, and inadequate output never trigger model fallback. ZCode pins its Worker model and stops after eligible exhausted failure in 0.8.0. Codex pins four base roles and optionally installs paired fallback roles that omit both model and effort; those may be used only when the independent fallback mode is explicitly `parent-worker`. Actual inheritance remains a live-test claim.

Workers are hidden, have no `agent` tool, and cannot create nested subagents. Implementer is the only role with edit capability. Hooks remain defense in depth for known dangerous operations.

## Control loop

```text
REQUEST
  -> LEADER_INTENT_ALIGNMENT
      -> RESULT_CHANGING_AMBIGUITY -> USER_QUESTION -> INTENT_ALIGNMENT
      -> TASK_TOPOLOGY_GATE
          -> ADAPTIVE_ALL_GATES -> DIRECT_ONCE -> ACCEPT || TRANSFER_WRITER_OWNERSHIP
          -> SIMPLE_TASK -> ONE_WORKER_PACKAGE
          -> COMPOUND_TASK -> DEPENDENCY_ORDERED_WAVES
              -> WAVE_1 -> PACKAGE_A || PACKAGE_B || PACKAGE_C -> WAVE_BARRIER
              -> WAVE_2 -> PACKAGE_D || PACKAGE_E -> WAVE_BARRIER
          -> EACH_PACKAGE -> WORKER_BRIEF
          -> WORKER_MODEL_ERROR -> TRANSIENT_RETRY_ONCE || DETERMINISTIC_REJECTION -> MAIN_MODEL_SAME_WORKER_ROLE
          -> ROUTINE -> IMPLEMENTER_PACKAGE(S) -> NARROW_SELF_CHECK -> LEADER_ACCEPTANCE
          -> HIGH_RISK -> USER_CONFIRMATION -> IMPLEMENTER_PACKAGE(S) -> TESTER || REVIEWER -> LEADER_ACCEPTANCE
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

The brief is semantic and proportional, not a fixed field budget. GLM-5.3-Flash is treated as a low-cost executor: Leader resolves intent, task topology, package boundaries, and key choices before delegation. The topology gate permits one Worker only for one observable result, one bounded work surface, and one independent acceptance chain. Compound work is split into dependency-ordered stage waves and independently acceptable packages; independently acceptable packages cannot be collapsed into one large `GOAL`.

A change brief includes direct problem evidence, required behavior, exact allowed files or symbols, preserved behavior, non-goals, itemized evidence for every `DONE` item, and dependency order when one exists. For a changed consumer-visible TypeScript export/type/signature, Leader declares `PUBLIC_TYPESCRIPT_API` in `DONE` with named compiler evidence and a positive/negative external-consumer fixture. For a changed observable data or branch boundary, it declares `BEHAVIOR_BOUNDARY` with only source-supported boundary rows and expected results. Triggered items are mandatory narrow contract gates, not optional `NOT_VERIFIED` gaps or broad-suite triggers. Open phrases such as “related files,” “fix appropriately,” “as needed,” or “check everything” are not valid boundaries. Each package is one direct stateless invocation. `GOAL` is a plain-text field, not a goal command or persistent task. Leader has no `todo` tool and must not use memory, other tools, or prose to simulate a Worker lifecycle, polling loop, or automatic reinvocation. A later invocation must be a predeclared dependency-ready package or evidence-triggered rework for a named unmet `DONE` item. Workers stop at `DONE`, do not pursue incidental findings, and return `NEEDS_LEADER` before a new product choice, boundary expansion, high-risk action, or materially deeper validation.

Workers provide a second protocol guard: when one brief contains two or more independently acceptable packages that can be separated without a dependency, they return `NEEDS_LEADER` and request explicit package boundaries instead of silently completing the oversized assignment serially.

## Parallelism

The workflow is a dependency-wave graph, not a parallel-read/serial-write funnel. Leader fans out distinct read-only questions when they have no output dependency, use non-overlapping boundaries, can be synthesized independently, and create no shared side effects. Each Analyzer answers one question; parallelism never authorizes duplicate broad scans.

Multiple Implementers run concurrently when their exact file ownership, public contracts, generated artifacts, and command side effects do not overlap. A conflict moves the affected package to a later wave or a bounded integration package; it does not justify assigning all compound work to one Worker. Tester, Reviewer, and other independent validation packages run concurrently after an implementation wave is stable when their commands do not contend for caches, generated artifacts, data, or environment state. Any serial decision must name the concrete dependency or conflict. Parallelism exists to shorten the critical path, not to increase total work.

## Decision ownership

- User owns product intent, explicit boundaries, new authority, and high-risk approval.
- Leader owns interpretation, safe defaults, technical tradeoffs, Worker selection, work depth, and final acceptance.
- Workers own factual investigation and execution inside the brief; they do not enlarge it.

When a Worker reports conflict, Leader first decides whether existing direct evidence already supports `DONE`. `NEEDS_LEADER`, `NOT_VERIFIED`, theoretical risk, suggested expansion, and incidental findings do not trigger more work by themselves. Only new concrete evidence that directly threatens a named `DONE` item permits one targeted rework round and one direct recheck. If the conflict turns on a specific source location, Leader may inspect that location directly with `read/search` while retaining the full user conversation. After the recheck, Leader must accept the supported result or report unsupported items and remaining risk instead of opening another validation chain.

## Verification

Verification climbs only on evidence: direct diff/behavior, target check, module check on shared impact or failure, then broad validation only for confirmed cross-module/high-risk needs. A declared `PUBLIC_TYPESCRIPT_API` requires Tester compiler evidence and narrow Reviewer export/consumer review; a public input/output `BEHAVIOR_BOUNDARY` requires Tester matrix evidence. Leader owns the stopping decision. High-risk completion still requires independent Tester and Reviewer PASS, but failure or incomplete evidence does not authorize an unbounded loop: after the single rework and recheck budget, Leader stops and reports the task as unsupported or incomplete.

## Authorization boundary

High-risk confirmation covers only the stated plan and does not authorize later expansion. Native VS Code cannot bind natural-language approval to a durable capability token, so semantic scope remains protocol-enforced even though tool availability and Hook decisions are structural controls.

## Shared execution contract

Maintain cross-platform cost, direct-execution eligibility, context, writer ownership, retry, and acceptance rules in `src/protocols/poor-mode.md`. `scripts/sync_poor_mode.py --write` embeds identical blocks in four installable Leader policies: strict and adaptive VS Code, Codex, and ZCode. Repository validation rejects drift. See [the execution guide](POOR_MODE.md) for routing examples and measurement boundaries.
