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

Material claims use the `evidence-handoff` ledger: claim ID, factual claim, `VERIFIED | PARTIAL | INFERRED`, decision impact, exact source, minimal evidence, counter-evidence, and coverage gaps. A recommendation is never evidence. Normally include no more than five material claims.

Leader passes only the minimum information required for the next worker. Workers must not communicate directly with one another or with the user.

For `ARBITRATION_REQUIRED`, the final report is also the stateless replay checkpoint. It must include the original objective and unchanged authorization, one decision question, files read or changed, commands and results, the evidence ledger, options and consequences, worker recommendation, and why no safe local default exists. It identifies at most three decisive claim IDs for Arbiter to verify first-hand. Do not send private reasoning or an unbounded transcript.

Leader Arbiter returns only `SELECT_OPTION`, `MORE_EVIDENCE_REQUIRED`, `USER_DECISION_REQUIRED`, or `STOP`, with first-hand claim verification, decision evidence, unchanged constraints, acceptance consequences, and a recommendation to Leader. Its decision never expands scope or grants authority.

When work continues after `SELECT_OPTION`, Leader starts a new invocation of the same worker role. The replay packet includes the original objective, authorization, checkpoint, arbitration result, constraints, and acceptance criteria. The new worker must verify current workspace state before acting.
