---
name: evidence-handoff
description: Preserves provenance across stateless worker handoffs with compact claim-level evidence ledgers and focused low-cost verification before any high-cost first-hand check.
---

# Evidence handoff

A worker summary is not evidence by itself. Material claims that affect scope, behavior, contracts, risk, implementation choice, or acceptance must be traceable.

## Evidence ledger

Every worker report includes a compact evidence ledger for its material claims, normally no more than five entries. Each entry contains:

- `CLAIM_ID`: stable within the user task;
- `CLAIM`: one factual statement, separate from recommendations;
- `STATUS`: `VERIFIED`, `PARTIAL`, or `INFERRED`;
- `DECISION_IMPACT`: what changes if the claim is false;
- `SOURCE`: exact file and symbol or line, or exact command/test and exit code;
- `EVIDENCE`: the smallest relevant excerpt or raw result summary;
- `COUNTER_EVIDENCE`: the disconfirming check and its result;
- `COVERAGE_GAPS`: what was not examined.

`VERIFIED` requires direct evidence. A plausible interpretation, convention-based expectation, or unexecuted runtime prediction is `INFERRED`. Mixed or incomplete support is `PARTIAL`. Do not hide uncertainty by omitting the entry.

Keep evidence minimal and decision-relevant. Do not relay full files, full transcripts, private reasoning, or large command logs.

## Focused low-cost verification

Leader requests a narrow evidence check when:

- two worker reports conflict on a material claim;
- a completion or acceptance decision depends on a `PARTIAL` or `INFERRED` claim;
- cited evidence does not visibly support the claim;
- a high-risk gate depends on an unverified contract, permission, data, or scope fact.

Use Analyzer for source and dependency facts. Use Reviewer for changed behavior, scope, contract, and acceptance facts. Verify only the named claim IDs; do not repeat the full task investigation.

Return:

```markdown
EVIDENCE_CHECK: CONFIRMED | CONTRADICTED | INSUFFICIENT_EVIDENCE

## Claim results
- CLAIM_ID: result, exact first-hand source, counter-evidence, and remaining gap

## Recommendation to Leader
- CONTINUE | REWORK | COLLECT_MORE_EVIDENCE | USER_DECISION_REQUIRED
```

## Escalation

If a material technical fork remains after the evidence ledger and any necessary low-cost check, Leader may invoke Leader Arbiter once. The arbitration packet identifies at most three decisive claim IDs for first-hand verification. Runtime claims that require command execution remain with low-cost Tester or Reviewer because Arbiter has no execute tool.
