# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | Full configured VS Code, execution, edit, search, browser, and extension tool sets | Assess risk, directly execute or delegate, choose verification depth, reconcile and accept |
| Leader Analyzer | Worker model | No | `read`, `search` | Pre-authorization facts and implementation analysis |
| Leader Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Leader-delegated code changes, exact-path high-risk deletion, and self-verification |
| Leader Tester | Worker model | No | `read`, `search`, `execute` | Tests, builds, static analysis |
| Leader Reviewer | Worker model | No | `read`, `search`, `execute` | Diff, correctness, scope and risk review |

Tool availability does not grant semantic authorization. Leader selects direct execution or delegation based on task risk, while high-risk writes require user confirmation. Implementer deletion is protocol-limited to exact file paths listed in the Leader's confirmed high-risk scope; the Hook requires confirmation for single-file deletion and denies directory or recursive deletion. Workers have no `agent` tool, and nested subagents are disabled globally.

## Risk-based workflow

```text
REQUEST
  -> LEADER_RISK_ASSESSMENT
      -> LOW_RISK_DIRECT_WORK -> PROPORTIONATE_VERIFICATION -> COMPLETE
      -> ROUTINE_WORK -> DIRECT_OR_TARGETED_DELEGATION -> PROPORTIONATE_VERIFICATION -> COMPLETE
      -> HIGH_RISK_PLAN -> USER_CONFIRMATION -> IMPLEMENT -> TEST -> REVIEW -> COMPLETE
```

Failure transitions:

- Analysis uncertainty -> Leader chooses direct investigation or one focused Analyzer task
- Routine validation failure -> direct or delegated rework with targeted re-validation
- High-risk test or review failure -> rework inside confirmed scope, then independent re-validation
- Routine scope expansion -> Leader re-assesses impact; high-risk expansion -> STOPPED_USER_CONFIRMATION_REQUIRED
- Worker model unavailable -> Leader direct execution or USER_MODEL_SELECTION_REQUIRED when delegation is necessary

## Authorization boundary

High-risk user confirmation covers only the stated high-risk plan; it does not cover a later material expansion. `批准执行` is a recommended confirmation phrase, but clear natural-language confirmation is also valid. Because native VS Code has no durable approval token API for custom agents, this boundary is instruction-enforced rather than cryptographically enforced.
