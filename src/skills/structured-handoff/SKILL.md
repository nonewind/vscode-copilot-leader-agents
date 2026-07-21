---
name: structured-handoff
description: Defines concise evidence-based handoff contracts between Analyzer, Implementer, Tester, Reviewer, and Leader without sharing full contexts.
---

# Structured handoff

Each worker returns only a final structured report. Do not relay private reasoning or the entire worker transcript.

Every report must include:

- machine-readable status token;
- exact scope examined or changed;
- evidence;
- risks and blockers;
- recommendation to Leader.

Leader passes only the minimum information required for the next worker. Workers must not communicate directly with one another or with the user.
