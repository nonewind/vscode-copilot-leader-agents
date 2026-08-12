# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | `agent`, `todo`, `read`, `search` | Intent, key decisions, narrow decisive source checks, routing, synthesis, acceptance |
| Analyzer | Worker model | No | `read`, `search` | Focused read-only facts |
| Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Minimum sufficient scoped changes and direct self-checks |
| Tester | Worker model | No | `read`, `search`, `execute` | Targeted acceptance validation |
| Reviewer | Worker model | No | `read`, `search`, `execute` | Independent diff, boundary, correctness, and risk review |

Leader cannot edit, execute commands, operate VS Code, or call external services. Its read-only tools are reserved for a small source fact that materially changes a decision and cannot be trusted from the current Worker evidence. Routine repository exploration stays on the low-cost model.

The installed Leader configuration owns model routing. Its default Worker model is `DeepSeek-V4-Flash (Go) (gcmp.opencode)`, which Leader explicitly specifies on every Worker invocation. Worker manifests are model-neutral. Model unavailability stops for user-selected replacement; there is no automatic discovery or silent fallback.

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
          -> ROUTINE -> IMPLEMENTER -> NARROW_SELF_CHECK -> LEADER_ACCEPTANCE
          -> HIGH_RISK -> USER_CONFIRMATION -> IMPLEMENTER -> TESTER || REVIEWER -> LEADER_ACCEPTANCE
          -> NEEDS_LEADER
              -> FOCUSED_WORKER_FACTS
              -> NARROW_LEADER_READ_SEARCH
              -> USER_DECISION
```

Every Worker brief states:

- `GOAL`: desired result;
- `BOUNDARIES`: scope, preserved behavior, non-goals;
- `DONE`: sufficient direct evidence;
- `STOP_AND_REPORT`: conditions that return control to Leader.

The brief is semantic and proportional, not a fixed field budget. Leader decides the necessary detail. Workers stop at `DONE`, do not pursue incidental findings, and return `NEEDS_LEADER` before a new product choice, boundary expansion, high-risk action, or materially deeper validation.

## Parallelism

The workflow is a parallel-read, serial-write funnel. Leader may fan out distinct read-only questions when they have no output dependency, use non-overlapping boundaries, can be synthesized independently, and create no shared side effects. Each Analyzer answers one question; parallelism never authorizes duplicate broad scans.

Implementation stays serial in the shared workspace by default. Tester and Reviewer may run concurrently after the diff is stable only when their commands do not contend for caches, generated artifacts, data, or environment state. Parallelism exists to shorten the critical path, not to increase total work.

## Decision ownership

- User owns product intent, explicit boundaries, new authority, and high-risk approval.
- Leader owns interpretation, safe defaults, technical tradeoffs, Worker selection, work depth, and final acceptance.
- Workers own factual investigation and execution inside the brief; they do not enlarge it.

When Worker reports conflict, Leader first asks for the smallest missing fact. If the conflict turns on a specific source location, Leader may inspect that location directly with `read/search` while retaining the full user conversation. Runtime facts remain with Tester or Reviewer because Leader has no execute tool.

## Verification

Verification climbs only on evidence: direct diff/behavior, target check, module check on shared impact or failure, then broad validation only for confirmed cross-module/high-risk needs. High-risk completion always requires independent Tester and Reviewer PASS.

## Authorization boundary

High-risk confirmation covers only the stated plan and does not authorize later expansion. Native VS Code cannot bind natural-language approval to a durable capability token, so semantic scope remains protocol-enforced even though tool availability and Hook decisions are structural controls.
