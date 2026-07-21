---
name: leader-orchestration
description: Enforces the Leader-only entry workflow, read-only discovery, exact approval phrase, worker delegation, test-review gates, and reauthorization on scope expansion.
---

# Leader orchestration

Use this skill when coordinating a development task through the Leader custom agent.

## Protocol

1. Discover facts with Analyzer only.
2. Present the current plan and stop.
3. Accept only the exact phrase `批准执行`.
4. Delegate edits only to Implementer.
5. Require Tester PASS.
6. Require Reviewer PASS.
7. Rework autonomously inside approved scope.
8. Stop and reauthorize on scope or risk expansion.
9. Stop and request an explicit model name when the configured worker model is unavailable.

Never treat ordinary agreement, follow-up discussion, or a previous task's approval as authorization.
