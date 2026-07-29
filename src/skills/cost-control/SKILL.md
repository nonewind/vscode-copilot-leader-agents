---
name: cost-control
description: Routes delegated worker tasks to the configured DeepSeek V4 Flash model and avoids unnecessary delegation or duplicate exploration.
---

# Cost control

- Leader follows the current Copilot Chat model.
- Workers use the installed worker model exactly.
- Treat workers as optional cost-optimization tools, not mandatory workflow stages; Leader may directly finish work when delegation has no net value.
- Use parallel workers only for independent tasks.
- Prefer one focused worker invocation over repeated broad scans.
- Do not duplicate the same codebase exploration across workers; pass a compact evidence summary when a follow-up worker is necessary.
- Never silently fall back to Leader's model.
- If the worker model is unavailable or repeatedly inadequate, let Leader decide whether to finish directly; ask the user to name a replacement only when delegation remains necessary.
