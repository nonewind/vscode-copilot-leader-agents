---
name: scope-arbitration
description: Handles conflicts between global Leader rules and workspace-specific instructions, pauses for user arbitration, and records the local-only decision inside the project.
---

# Scope arbitration

When global and workspace rules conflict:

1. Stop all execution.
2. State both rules and the practical impact.
3. Ask the user to choose.
4. After the user decides, Leader writes `.copilot-leader/arbitration.local.md` directly.
5. Add `.copilot-leader/` to `.git/info/exclude` without committing it.
6. Apply the recorded decision only to this local project.

Do not weaken non-conflicting safety constraints.
