# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | Full configured VS Code, execution, edit, search, browser, and extension tool sets | Plan, authorize, delegate, reconcile, accept; direct writes require explicit user assignment |
| Leader Analyzer | Worker model | No | `read`, `search` | Pre-authorization facts and implementation analysis |
| Leader Implementer | Worker model | No | `vscode`, `execute`, `read`, `search`, `edit` | Authorized code changes, exact-path file deletion, and self-verification |
| Leader Tester | Worker model | No | `read`, `search`, `execute` | Tests, builds, static analysis |
| Leader Reviewer | Worker model | No | `read`, `search`, `execute` | Diff, correctness, scope and risk review |

Tool availability does not grant semantic authorization. Leader direct writes are protocol-limited to explicit user assignment and an approved exact scope. Implementer deletion is protocol-limited to exact file paths in the latest approved plan; the Hook requires confirmation for single-file deletion and denies directory or recursive deletion. Workers have no `agent` tool, and nested subagents are disabled globally.

## State machine

```text
REQUEST
  -> READ_ONLY_DISCOVERY
  -> PLAN_PENDING_APPROVAL
  -> AUTHORIZED_IMPLEMENTATION
  -> TEST
  -> REVIEW
  -> COMPLETE
```

Failure transitions:

- Analysis uncertainty -> additional Analyzer task
- Implementation failure -> Implementer retry inside approved scope
- Test failure -> Implementer retry inside approved scope
- Review failure -> Implementer retry inside approved scope
- Scope/risk expansion -> STOPPED_REAUTHORIZATION_REQUIRED
- Worker model unavailable -> STOPPED_USER_MODEL_SELECTION_REQUIRED

## Authorization boundary

The exact phrase `批准执行` approves only the current plan. Approval does not cover later scope expansion. Because native VS Code has no durable approval token API for custom agents, this binding is instruction-enforced rather than cryptographically enforced.
