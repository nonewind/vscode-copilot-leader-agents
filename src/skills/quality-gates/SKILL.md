---
name: quality-gates
description: Applies independent testing and review proportionately, with mandatory gates for high-risk changes and Leader discretion for routine work.
---

# Quality gates

For high-risk changes, a task is complete only when:

- the Implementer has completed the approved change;
- Tester reports PASS with command evidence;
- Reviewer reports PASS with no scope violation;
- Leader resolves any report conflict.

For low-risk and routine changes, Leader selects the smallest verification that supports the claim. Implementer self-verification is acceptable when it is proportionate and its limits are reported.

A failed test or review returns to implementation while the risk class and confirmed boundary remain unchanged. Seek renewed confirmation only when the fix crosses into a high-risk category or materially changes the confirmed impact.
