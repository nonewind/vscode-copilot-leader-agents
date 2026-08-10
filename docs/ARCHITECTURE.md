# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | `agent`, `todo` | Understand, assess risk, dispatch, reconcile, and accept; no workspace or external tool use |
| Leader Analyzer | Worker model | No | `read`, `search` | Pre-authorization facts and implementation analysis |
| Leader Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Leader-delegated code changes, exact-path high-risk deletion, and self-verification |
| Leader Tester | Worker model | No | `read`, `search`, `execute` | Tests, builds, static analysis |
| Leader Reviewer | Worker model | No | `read`, `search`, `execute` | Diff, correctness, scope and risk review |
| Leader Arbiter | Current Leader model | No | `read`, `search` | One-shot verification of at most three decisive claims and isolated decision inside existing authorization |

Leader tool isolation makes worker delegation a structural boundary for every supported workspace operation. Unsupported tool requests stop instead of falling back to Leader. Implementer deletion is protocol-limited to exact file paths listed in the Leader's confirmed high-risk scope; the Hook requires confirmation for single-file deletion and denies directory or recursive deletion. Workers have no `agent` tool, and nested subagents are disabled globally.

The bundled worker manifests cover workspace analysis, implementation, testing, and review. Browser, GitHub, and other tools that existed only on Leader are intentionally unavailable in this mode; such requests stop and require the user to choose another agent rather than triggering an expensive fallback.

Leader Arbiter is not a normal workspace worker and is the only exception to the low-cost subagent model. It has no fixed `model` field, so an isolated invocation inherits the current Leader model. It receives only a structured arbitration packet and may use `read` and `search` to verify at most three named decisive claims at their exact cited files and symbols. It cannot execute commands, edit files, broadly scan the repository, expand scope, grant authority, or replace an independent quality gate.

All workers attach a compact evidence ledger to material claims. Each claim separates facts from recommendations and records `VERIFIED | PARTIAL | INFERRED`, decision impact, exact source, minimal evidence, counter-evidence, and coverage gaps. Report conflicts and decisions that depend on partial or inferred facts receive a focused low-cost Analyzer or Reviewer check before any high-cost first-hand verification.

## Risk-based workflow

```text
REQUEST
  -> LEADER_TOOL_AND_RISK_ASSESSMENT
      -> TOOL_FREE_CONVERSATION -> LEADER_RESPONSE
      -> READ_ONLY_FACTS -> ANALYZER -> LEADER_SYNTHESIS
      -> LOW_OR_ROUTINE_CHANGE -> IMPLEMENTER -> PROPORTIONATE_VERIFICATION -> COMPLETE
      -> HIGH_RISK_PLAN -> USER_CONFIRMATION -> IMPLEMENT -> TEST -> REVIEW -> COMPLETE
      -> MATERIAL_TECHNICAL_FORK
          -> MISSING_FACTS -> LOW_COST_WORKER_EVIDENCE
          -> PRODUCT_OR_AUTHORITY_DECISION -> USER
          -> COMPLETE_IN_SCOPE_PACKET -> ARBITER_VERIFIES_AT_MOST_3_CLAIMS_ONCE -> NEW_WORKER_INVOCATION -> WORKFLOW
```

Failure transitions:

- Analysis uncertainty -> one focused Analyzer task
- Routine validation failure -> Implementer rework with targeted re-validation
- High-risk test or review failure -> rework inside confirmed scope, then independent re-validation
- Routine scope expansion -> Leader re-assesses impact; high-risk expansion -> STOPPED_USER_CONFIRMATION_REQUIRED
- Worker model unavailable -> STOPPED_USER_MODEL_SELECTION_REQUIRED or EXIT_POOR_MODE
- Required tool absent from all workers -> EXIT_POOR_MODE
- Material technical fork with no safe default -> ARBITRATION_REQUIRED
- Arbiter requests facts -> one focused low-cost evidence task; do not guess
- Arbiter requires product intent or new authority -> USER_DECISION_REQUIRED
- Arbiter selects an option -> replay checkpoint and decision into a new invocation of the same worker role
- Second arbitration need in the same user task -> STOPPED_USER_DECISION_REQUIRED

## Decision-escalation fuse

The fuse is intentionally narrower than ordinary uncertainty. A worker first gathers reasonably available evidence inside its assigned scope, records its material claims in the evidence ledger, and performs one disconfirming check. It escalates only when multiple technically plausible options remain, the choice materially affects behavior, contracts, security boundaries, architectural responsibility, or rollback characteristics, and no evidence-backed safe default exists.

Routine reversible choices, facts that can still be gathered safely, ordinary test failures, proven review findings, scope expansion, and missing authorization keep their existing paths. Product intent, business tradeoffs, new authority, and material high-risk expansion always go to the user.

Each user task permits at most one automatic Arbiter invocation and at most three decisive claims in its first-hand read budget. Runtime facts stay with low-cost Tester or Reviewer because Arbiter has no execute tool. Native subagent invocations are stateless, so Leader cannot resume or send a follow-up to the original worker. A successful selection starts a new invocation of the same worker role with the original objective, unchanged authorization, exact checkpoint, arbitration decision, constraints, and acceptance criteria. The new worker verifies current workspace state before continuing.

## Authorization boundary

High-risk user confirmation covers only the stated high-risk plan; it does not cover a later material expansion. `批准执行` is a recommended confirmation phrase, but clear natural-language confirmation is also valid. Because native VS Code has no durable approval token API for custom agents, this boundary is instruction-enforced rather than cryptographically enforced.

An Arbiter selection is technical guidance within that boundary. It is never evidence of user confirmation and cannot enlarge the confirmed plan.
