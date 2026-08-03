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
