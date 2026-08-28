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

Leader owns the decision to stop. Continuing validation requires new, concrete evidence that directly threatens a named `DONE` item. Except for an explicitly declared `PUBLIC_TYPESCRIPT_API` or `BEHAVIOR_BOUNDARY`, `NOT_VERIFIED`, theoretical risk, incomplete coverage, a Worker suggestion to expand, or an incidental finding is a gap to report, not an automatic gate or follow-up task.

## Triggered contract gates

Before a change brief, Leader classifies only the directly affected contract. `PUBLIC_TYPESCRIPT_API` applies to changed consumer-visible TypeScript exports, public types/interfaces, generics, overloads, optionality, DTOs, type guards, or public signatures. `BEHAVIOR_BOUNDARY` applies to changes that can alter observable empty, missing, nullish, zero, edge, no-match, no-data, or failure behavior.

A triggered item becomes an explicit `DONE` requirement, not a theoretical risk. `PUBLIC_TYPESCRIPT_API` requires a named isolated type check and, for a changed public export, a compile-only consumer fixture with a positive case and an `@ts-expect-error` negative case; historical repository type-error baselines must not mask it. `BEHAVIOR_BOUNDARY` requires only the relevant, source-supported rows and expected results in a named boundary matrix. Do not invent business inputs or require a broad suite. A triggered item that is `NOT_VERIFIED` is unsatisfied, so it cannot be accepted as a gap.

For `PUBLIC_TYPESCRIPT_API`, Tester runs the named compiler evidence and Reviewer checks the declared export/consumer surface. For a public input/output `BEHAVIOR_BOUNDARY`, Tester runs the named matrix. These are narrow contract gates, not a reason to scan or test unrelated modules.

For high-risk changes, completion requires:

- an explicitly confirmed plan;
- Implementer completion inside that plan;
- Tester PASS with actual command evidence;
- Reviewer PASS with no boundary violation;
- Leader resolution of any material conflict or unverified acceptance fact.

Rework stays inside the original goal, boundary, and approval. Allow at most one targeted rework round for a directly evidenced acceptance problem, followed by one direct recheck of that problem. Then stop: accept only the supported `DONE` items and report any failure, block, or remaining gap without opening another validation chain. A new product choice, authority, high-risk effect, material boundary expansion, or user-requested deeper validation returns to the user as a new decision.
