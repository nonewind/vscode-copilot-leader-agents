---
name: cost-control
description: Keeps tool-using work on the configured low-cost worker model while avoiding redundant worker stages and silent Leader fallback.
---

# Cost control

- Leader follows the current Copilot Chat model.
- Workers use the installed worker model exactly.
- Leader handles only tool-free conversation, clarification, orchestration, synthesis, and acceptance.
- Delegate every supported workspace task. Use Analyzer for read-only investigation and Implementer for changes.
- If a request needs browser, GitHub, extension, or other capabilities absent from all worker tool manifests, stop and ask the user to leave this mode. Never re-enable or fall back to Leader tools.
- When a change is already scoped clearly, invoke Implementer directly instead of paying for a redundant Analyzer stage.
- Use parallel workers only for independent tasks.
- Prefer one focused worker invocation over repeated broad scans.
- Do not duplicate the same codebase exploration across workers; pass a compact evidence summary when a follow-up worker is necessary.
- Never silently fall back to Leader's model.
- If the worker model is unavailable or repeatedly inadequate, stop and ask the user to name a replacement worker model or leave this mode. Leader must not take over tool-using work.
- Leader Arbiter is the only exception to low-cost subagent routing. It inherits the current Leader model and is invoked only for a material technical fork with no evidence-backed safe default. Its first-hand budget is limited to `read` and `search` for at most three named decisive claims; it has no execute or edit tools and does not broadly scan the repository.
- Permit at most one automatic Arbiter invocation per user task. Missing facts go back to a low-cost worker; product intent and new authority go to the user. Do not use Arbiter as routine review, consensus polling, or a response to an ordinary test failure.
- Require compact claim-level evidence ledgers in worker reports. Resolve report conflicts and material `PARTIAL` or `INFERRED` claims through one focused low-cost evidence check before spending the Arbiter budget.
