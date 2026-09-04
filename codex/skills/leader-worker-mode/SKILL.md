---
name: leader-worker-mode
description: Use for every repository task where the Codex Leader/Worker managed block is active; keep decisions in the primary thread and delegate bounded workspace execution to the four configured Worker agents.
---

# Leader Worker Mode

Read the workspace `AGENTS.md` Leader section first. Resolve intent, topology, product choices, risk, and acceptance before delegation. Give each Worker exactly one `GOAL`, precise `BOUNDARIES`, itemized `DONE` evidence, and concrete `STOP_AND_REPORT` triggers.

Delegate workspace investigation, edits, commands, testing, and review, including small work. Use `leader_analyzer` for bounded facts, `leader_implementer` for one exact write surface, `leader_tester` for targeted validation, and `leader_reviewer` for independent review. Run dependency-ready non-overlapping packages in parallel. Never ask a Worker to spawn another subagent.

The primary no-edit/no-terminal boundary is protocol-enforced in Codex; do not claim a structural main-thread tool restriction. Analyzer and Reviewer are structurally read-only. Implementer and Tester use workspace-write, with Tester protocol-forbidden from source edits or repairs so normal validation commands may still write caches and artifacts. All Workers are configured for `gpt-5.6-luna`. Stop when direct evidence supports `DONE`; permit at most one evidence-triggered rework and one direct recheck.
