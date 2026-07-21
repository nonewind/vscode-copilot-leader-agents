# Architecture

## Components

| Component | Model | User visible | Tools | Responsibility |
|---|---|---:|---|---|
| Leader | Current chat model | Yes | `agent`, `read`, `search`, `runCommands` | Plan, authorize, delegate, reconcile, accept |
| Leader Analyzer | Worker model | No | `read`, `search` | Pre-authorization facts and implementation analysis |
| Leader Implementer | Worker model | No | `read`, `search`, `edit` | Authorized code changes only |
| Leader Tester | Worker model | No | `read`, `search`, `runCommands` | Tests, builds, static analysis |
| Leader Reviewer | Worker model | No | `read`, `search`, `runCommands` | Diff, correctness, scope and risk review |

Leader has no edit tool. Workers have no `agent` tool. Nested subagents are disabled globally.

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
