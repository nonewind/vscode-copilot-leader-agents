---
name: quality-gates
description: Selects the smallest direct verification that supports acceptance, with independent gates for high-risk changes.
---

# Quality gates

Verification is evidence-triggered:

1. inspect the actual change and directly affected behavior;
2. run the narrowest targeted test, type check, lint, or static check;
3. expand to module checks only for shared-code impact, a direct failure, or a concrete contract risk;
4. use full builds or broad suites only for cross-module/high-risk work or an explicit acceptance requirement.

Passing one level is a stop signal when acceptance is already supported, not a reason to run the next level. Unrelated failures are reported without automatic diagnosis or repair.

For high-risk changes, completion requires:

- an explicitly confirmed plan;
- Implementer completion inside that plan;
- Tester PASS with actual command evidence;
- Reviewer PASS with no boundary violation;
- Leader resolution of any material conflict or unverified acceptance fact.

Rework stays inside the original goal, boundary, and approval. A new product choice, authority, high-risk effect, or material boundary expansion returns to the user.
