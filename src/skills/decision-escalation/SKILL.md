---
name: decision-escalation
description: Uses a one-shot independent main-model arbitration fuse only for material technical forks that have no evidence-backed safe default, then resumes through a stateless worker checkpoint replay.
---

# Decision escalation

This skill is a critical-decision fuse, not a default review stage.

## Worker trigger

Before escalating, the worker must gather reasonably available evidence inside its assigned scope and perform one disconfirming check against its preferred conclusion.

Return `ARBITRATION_REQUIRED` only when all of these are true:

- at least two technically plausible choices remain;
- the choice materially changes observable behavior, an API or data contract, a security boundary, architectural responsibility, or rollback characteristics;
- the evidence does not support a safe default;
- continuing locally could create a materially wrong result.

Do not escalate routine naming or formatting choices, reversible implementation details covered by repository conventions, facts that can still be gathered safely inside the assigned scope, ordinary test failures with a clear repair path, or decisions already fixed by the user's acceptance criteria.

Use the existing status instead when the real issue is missing authorization, scope expansion, an unsafe test, a model or environment blocker, or a proven test/review failure. Use `USER_DECISION_REQUIRED` for product intent, business tradeoffs, new authority, or a material high-risk expansion.

## Stop and report

Stop before the uncertain action. If partial changes already exist, make no further writes or commands and report the exact checkpoint. End the current stateless worker invocation with:

- a unique `ARBITRATION_ID`;
- original objective, authorized scope, risk class, and acceptance criteria;
- files read or changed, commands run, results, and current workspace checkpoint;
- one concrete decision question;
- verified facts, counter-evidence, and unexamined gaps;
- an evidence ledger and at most three decisive claim IDs for first-hand verification;
- options and their contract, risk, rollback, and acceptance consequences;
- worker recommendation and why no safe local default exists.

## Leader routing

Leader first checks whether the question is within the existing goal, risk class, and authorization.

- Missing accessible facts: collect evidence through the appropriate low-cost worker.
- Product intent, business choice, new authority, or material high-risk expansion: ask the user.
- Complete technical fork within current authority whose decisive source facts can be checked with bounded `read` and `search`: invoke Leader Arbiter once without a worker-model override.

Each user task permits at most one automatic Arbiter invocation. A non-convergent result stops for the user instead of starting an arbitration loop.

## Arbitration boundary

Leader Arbiter inherits the Leader's current model in an isolated subagent invocation and receives only the structured packet. It may use `read` and `search` solely to verify at most three named decisive claims at their exact cited files and symbols. It has no execute or edit capability and must not broadly scan the repository. It may select one supplied option, request missing evidence, require a user decision, or stop. It cannot expand scope, create a new option that needs additional authority, weaken acceptance criteria, or approve a high-risk operation.

## Stateless replay

A subagent invocation cannot be resumed. After a selection, Leader starts a new invocation of the same worker role and passes the original objective, unchanged authorization, checkpoint, arbitration decision, constraints, and acceptance criteria. The new worker must inspect the current workspace state before continuing and must not assume that private context from the earlier invocation survives.
