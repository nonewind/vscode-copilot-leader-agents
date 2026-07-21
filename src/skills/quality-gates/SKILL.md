---
name: quality-gates
description: Requires independent implementation, testing, and review stages and controls the rework loop before Leader acceptance.
---

# Quality gates

A task is complete only when:

- Implementer reports PASS;
- Tester reports PASS with command evidence;
- Reviewer reports PASS with no scope violation;
- Leader resolves any report conflict.

A failed test or review returns to Implementer within the approved scope. Reauthorization is mandatory when the fix requires new files, new directories, dependency changes, configuration changes, database changes, external services, or higher risk.
