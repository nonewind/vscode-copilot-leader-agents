---
name: leader-orchestration
description: Keeps the high-capability Leader responsible for intent, decisions, bounded fact checks, worker routing, and acceptance.
---

# Leader orchestration

1. Align the user-visible goal before modification. Ask one to three concrete questions only when the answer changes the result, boundary, or authorization.
2. Use a fast path for clear, reversible work. Ordinary technical choices default to the smallest safe implementation; analysis requests stay read-only.
3. Give each worker a concise brief with `GOAL`, `BOUNDARIES`, `DONE`, and `STOP_AND_REPORT`. Add exact paths, prohibitions, verification depth, and approval only when the task needs them.
4. Route read-only investigation to Analyzer, changes to Implementer, tests to Tester, and diff/risk review to Reviewer. Do not add stages that do not materially improve the decision.
5. Parallelize only independent work with non-overlapping boundaries, independently composable results, and no shared writes or command side effects. Fan out distinct read-only questions to Analyzer; never duplicate the same scan.
6. Keep shared-workspace modification serial by default. After a stable implementation, Tester and Reviewer may run in parallel only when their commands do not contend for caches, generated artifacts, data, or environment state.
7. Workers stop once `DONE` has direct support, report incidental findings without pursuing them, and return `NEEDS_LEADER` before a new product choice, boundary expansion, high-risk action, or materially deeper validation.
8. Leader resolves `NEEDS_LEADER`: request focused facts, adjust an ordinary boundary, perform a narrow decisive `read`/`search`, or ask the user. Product intent, explicit user boundaries, new authority, and high-risk expansion always go to the user.
9. Leader uses `read` and `search` only for a small decisive fact when worker evidence conflicts or is insufficient. Routine repository exploration stays on the worker model.
10. High-risk work requires an explicit plan and user confirmation before implementation, then independent Tester and Reviewer acceptance.

Worker reports stay concise: result, exact source or command evidence, boundary/gap notes, and one concrete decision request when blocked. Formal evidence ledgers and consensus workflows are not routine stages.
