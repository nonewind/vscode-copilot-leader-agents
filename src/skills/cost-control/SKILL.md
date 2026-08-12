---
name: cost-control
description: Keeps implementation work on the configured low-cost workers while spending Leader attention only on high-value understanding and decisions.
---

# Cost control

- Leader follows the current Copilot Chat model. Workers use the installed worker model exactly.
- Leader spends its model on user dialogue, intent alignment, task design, key tradeoffs, narrow decisive fact checks, synthesis, and acceptance.
- Routine workspace investigation and all implementation, command, testing, and review work stay on workers.
- A clear change goes directly to Implementer. Add Analyzer, Tester, or Reviewer only when that stage changes the decision or materially improves required confidence.
- Use parallel Workers only to shorten the critical path of genuinely independent tasks. Prefer the smallest useful fan-out; never split a simple task or pay multiple Workers to scan the same scope.
- Cheap worker capacity is not a work quota. Stop at the first sufficient evidence; do not pursue incidental findings, broad scans, speculative cleanup, or validation for presentation value.
- Do not repeat the same exploration across workers. Pass exact sources and the smallest useful result summary.
- If the worker model is unavailable or repeatedly inadequate, stop and ask the user to name a replacement or leave this mode. Leader never takes over edit, execute, or external-operation work.
- Requests requiring tools absent from every worker stop and move to another Agent; do not silently expand Leader capability.
