# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | `agent`, `todo` | Understand, assess risk, dispatch, reconcile, and accept; no workspace or external tool use |
| Leader Analyzer | Worker model | No | `read`, `search` | Pre-authorization facts and implementation analysis |
| Leader Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Leader-delegated code changes, exact-path high-risk deletion, and self-verification |
| Leader Tester | Worker model | No | `read`, `search`, `execute` | Tests, builds, static analysis |
| Leader Reviewer | Worker model | No | `read`, `search`, `execute` | Diff, correctness, scope and risk review |

Leader tool isolation makes worker delegation a structural boundary for every supported workspace operation. Unsupported tool requests stop instead of falling back to Leader. Implementer deletion is protocol-limited to exact file paths listed in the Leader's confirmed high-risk scope; the Hook requires confirmation for single-file deletion and denies directory or recursive deletion. Workers have no `agent` tool, and nested subagents are disabled globally.

The bundled worker manifests cover workspace analysis, implementation, testing, and review. Browser, GitHub, and other tools that existed only on Leader are intentionally unavailable in this mode; such requests stop and require the user to choose another agent rather than triggering an expensive fallback.

## Risk-based workflow

```text
REQUEST
  -> LEADER_TOOL_AND_RISK_ASSESSMENT
      -> TOOL_FREE_CONVERSATION -> LEADER_RESPONSE
      -> READ_ONLY_FACTS -> ANALYZER -> LEADER_SYNTHESIS
      -> LOW_OR_ROUTINE_CHANGE -> IMPLEMENTER -> PROPORTIONATE_VERIFICATION -> COMPLETE
      -> HIGH_RISK_PLAN -> USER_CONFIRMATION -> IMPLEMENT -> TEST -> REVIEW -> COMPLETE
```

Failure transitions:

- Analysis uncertainty -> one focused Analyzer task
- Routine validation failure -> Implementer rework with targeted re-validation
- High-risk test or review failure -> rework inside confirmed scope, then independent re-validation
- Routine scope expansion -> Leader re-assesses impact; high-risk expansion -> STOPPED_USER_CONFIRMATION_REQUIRED
- Worker model unavailable -> STOPPED_USER_MODEL_SELECTION_REQUIRED or EXIT_POOR_MODE
- Required tool absent from all workers -> EXIT_POOR_MODE

## Authorization boundary

High-risk user confirmation covers only the stated high-risk plan; it does not cover a later material expansion. `批准执行` is a recommended confirmation phrase, but clear natural-language confirmation is also valid. Because native VS Code has no durable approval token API for custom agents, this boundary is instruction-enforced rather than cryptographically enforced.
