---
name: cost-control
description: Keeps implementation work on the configured low-cost workers while spending Leader attention only on high-value understanding and decisions.
---

# Cost control

- Leader follows the current Copilot Chat model and explicitly routes each initial Worker call to the installed Worker model. Worker manifests do not fix their own model.
- Leader spends its model on user dialogue, intent alignment, task design, key tradeoffs, narrow decisive fact checks, synthesis, and acceptance.
- Routine workspace investigation and all implementation, command, testing, and review work stay on workers.
- A simple change with one result, one bounded work surface, and one acceptance chain goes directly to one Implementer. Compound work first passes the task-topology gate and becomes dependency-ordered waves of independently acceptable packages.
- Use the smallest useful fan-out, but launch all dependency-ready packages that are genuinely independent. Never merge two independently acceptable packages merely to reduce Worker calls, and never split a simple task or pay multiple Workers to scan the same scope.
- Multiple Implementers should run concurrently when exact file ownership, contracts, generated artifacts, and command side effects do not overlap. Serial scheduling must name the concrete dependency or conflict; task length, one shared user goal, and generic shared-workspace caution are insufficient.
- Cheap worker capacity is not a work quota. Stop at the first sufficient evidence; do not pursue incidental findings, broad scans, speculative cleanup, or validation for presentation value.
- `NEEDS_LEADER` and `NOT_VERIFIED` do not create follow-up work by themselves. Continue only for concrete evidence that directly threatens `DONE`, with at most one targeted rework and one direct recheck.
- Do not repeat the same exploration across workers. Pass exact sources and the smallest useful result summary.
- Follow the Leader's shared Poor-mode execution contract for failure routing: deterministic rejection skips an identical retry; confirmed transient failure permits one retry after writer ownership is settled. VS Code permits one disclosed same-role fallback; task failures never trigger model retries. Keep user spending constraints and mandatory acceptance gates.
- Requests requiring tools absent from every worker stop and move to another Agent; do not silently expand Leader capability.
