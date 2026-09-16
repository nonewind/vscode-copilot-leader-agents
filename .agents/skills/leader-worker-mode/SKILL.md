---
name: leader-worker-mode
description: Use for every repository task where the Codex Leader/Worker managed block is active; keep decisions in the primary thread and delegate bounded workspace execution to the four configured Worker agents.
---

# Leader Worker Mode

Read the workspace `AGENTS.md` Leader section first. Resolve intent, topology, product choices, risk, and acceptance before delegation. Give each Worker exactly one `GOAL`, precise `BOUNDARIES`, itemized `DONE` evidence, and concrete `STOP_AND_REPORT` triggers.

In `strict` mode, delegate workspace investigation, edits, commands, testing, and review, including small work. In `adaptive` mode, direct work is allowed only for one action satisfying every condition in the shared contract and preceded by `DIRECT:`; otherwise delegate normally. Use `leader_analyzer` for bounded facts, `leader_implementer` for one exact write surface, `leader_tester` for targeted validation, and `leader_reviewer` for independent review. Run dependency-ready non-overlapping packages in parallel. Never ask a Worker to spawn another subagent.

The primary boundary is protocol-enforced in Codex; do not claim a structural main-thread tool restriction. Analyzer and Reviewer declare read-only defaults; Implementer and Tester declare workspace-write, with Tester protocol-forbidden from source edits or repairs. Parent-turn live sandbox and approval overrides are reapplied to children and can narrow or broaden those defaults, so do not call them immutable isolation. Base Workers are configured for `gpt-5.6-luna`, with `leader_analyzer` and `leader_tester` at `medium` reasoning effort and `leader_implementer` and `leader_reviewer` at `high`. Stop when direct evidence supports `DONE`; permit at most one evidence-triggered rework and one direct recheck.

Follow the shared Poor-mode execution contract embedded in the installed workspace `AGENTS.md`: choose only necessary roles, reuse current evidence, settle writer termination before retries, and keep unknown costs unknown. Deterministic model/effort rejection or exhausted transient retry stops the package unless `leader-worker-fallback-mode: parent-worker` is active. In that mode, disclose and invoke the matching `leader_*_fallback` role at most once; never silently fall back to direct Leader execution or discover another model.
