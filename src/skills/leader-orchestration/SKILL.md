---
name: leader-orchestration
description: Keeps the Leader dispatch-only for tool-using work, delegates code tasks to low-cost workers, and preserves confirmation and quality gates for high-risk changes.
---

# Leader orchestration

Use this skill when coordinating a development task through the Leader custom agent.

## Protocol

1. Classify the task by tool need, reversibility, impact scope, and verification needs.
2. Complete only tool-free conversation, clarification, synthesis, and acceptance directly.
3. Delegate read-only workspace investigation to Analyzer.
4. Delegate code or file changes to Implementer. When the goal and allowed scope are clear, let Implementer investigate, change, and self-verify in one invocation instead of requiring Analyzer first.
5. For destructive, configuration, dependency, migration, data-write, external-service, permission/security, unclear-scope, or otherwise high-risk work, gather facts through Analyzer as needed, present the scope and risks, and wait for explicit user confirmation.
6. Require independent Tester and Reviewer PASS only for high-risk work; use them selectively for routine work when they add material assurance.
7. Rework through the appropriate worker while the risk class and confirmed boundary remain unchanged.
8. Pause and seek clarification when work becomes high-risk or the user intent is unclear.
9. If a worker is unavailable, or the request requires tools absent from every worker manifest, stop and request an explicit replacement worker model or tell the user to leave this mode; never fall back to Leader tool use.
10. Require a compact claim-level evidence ledger for material scope, behavior, contract, risk, and acceptance facts. A recommendation is not evidence. When reports conflict or a decision depends on a `PARTIAL` or `INFERRED` claim, send only the named claim IDs to Analyzer or Reviewer for a focused low-cost evidence check.
11. Treat `ARBITRATION_REQUIRED` as a critical-decision fuse, not a routine review stage. Verify that the worker supplied an evidence ledger, counter-evidence, one material technical fork, a checkpoint, and at most three decisive claim IDs. Collect missing facts with a low-cost worker; route product intent or new authority to the user.
12. For a complete technical fork inside the existing authorization, invoke Leader Arbiter at most once for the user task. Do not pass the worker model override: Arbiter inherits the current Leader model in an isolated invocation and uses only bounded `read` and `search` to verify the named decisive claims.
13. After a selection, start a new invocation of the same worker role with the unchanged authorization, checkpoint, decision, constraints, and acceptance criteria. Never claim that the original stateless worker context was resumed.

Do not treat a prior task's confirmation as authorization for a new high-risk action. `批准执行` is a recommended confirmation phrase, not the only valid form of clear user confirmation.
An Arbiter decision is technical guidance, not user authorization, and does not replace Tester or Reviewer quality gates.
