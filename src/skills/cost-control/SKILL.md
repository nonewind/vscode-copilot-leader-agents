---
name: cost-control
description: Routes all worker tasks to the configured DeepSeek V4 Flash model, prevents silent fallback to the Leader model, and stops for explicit user model selection on failure.
---

# Cost control

- Leader follows the current Copilot Chat model.
- Workers use the installed worker model exactly.
- Use parallel workers only for independent tasks.
- Prefer one focused worker invocation over repeated broad scans.
- Do not duplicate the same codebase exploration across workers; pass a compact evidence summary.
- Never silently fall back to Leader's model.
- If the worker model is unavailable or repeatedly inadequate, stop and ask the user to name the replacement model explicitly.
