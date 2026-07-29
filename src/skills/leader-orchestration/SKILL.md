---
name: leader-orchestration
description: Lets the Leader choose a proportionate direct or delegated workflow while preserving explicit confirmation and full quality gates for high-risk changes.
---

# Leader orchestration

Use this skill when coordinating a development task through the Leader custom agent.

## Protocol

1. Classify the task by reversibility, impact scope, and verification needs.
2. For low-risk, explicit, localized work, investigate, implement, and self-verify directly.
3. For routine work, choose direct execution or the smallest useful delegation; do not create workers merely to satisfy a stage.
4. For destructive, configuration, dependency, migration, data-write, external-service, permission/security, unclear-scope, or otherwise high-risk work, present the scope and risks and wait for explicit user confirmation.
5. Require independent Tester and Reviewer PASS only for high-risk work; use them selectively for routine work when they add material assurance.
6. Rework autonomously while the risk class and confirmed boundary remain unchanged.
7. Pause and seek clarification when work becomes high-risk or the user intent is unclear.
8. If a worker is unavailable, Leader may complete the task directly or ask the user for a replacement model when delegation is necessary.

Do not treat a prior task's confirmation as authorization for a new high-risk action. `批准执行` is a recommended confirmation phrase, not the only valid form of clear user confirmation.
