---
name: leader-worker-mode
description: Use for every repository task in workspaces where Leader/Worker mode is active. The primary ZCode Agent keeps only intent alignment, planning, briefs, adjudication, and acceptance, and must delegate all investigation, edits, commands, testing, and review to the leader-analyzer, leader-implementer, leader-tester, and leader-reviewer subagents.
---

# Leader Worker Mode

Read the workspace `AGENTS.md` Leader section first. Resolve user intent, task topology, product choices, risk, and acceptance before delegation. Give each Worker exactly one `GOAL`, precise `BOUNDARIES`, itemized `DONE` evidence, and concrete `STOP_AND_REPORT` triggers. A package is one direct stateless subagent invocation; do not use ZCode Goal Mode, TodoWrite, memory, background polling, or repeated dispatch to simulate a persistent Worker lifecycle.

Delegate by default, including small work: every repository change or command — down to a one-line edit or a single lookup — executes on a Worker. Before reading any source yourself, check whether one bounded `leader-analyzer` question would settle the fact; read at most the narrowly named decisive location and stop once the fact is settled.

While the mode is active, the plugin guard structurally denies the primary Agent's `Edit`, `Write`, `Bash`, and `mcp__*` calls. Treat a denial as a routing instruction: restate the work as a bounded Worker package instead of retrying the tool, switching tools, or reproducing the effect another way.

Use `leader-analyzer` for bounded read-only facts, `leader-implementer` for one exact write surface, `leader-tester` for targeted validation, and `leader-reviewer` for independent diff or contract review. Run dependency-ready, non-overlapping packages in parallel. Stop when direct evidence supports `DONE`; permit at most one evidence-triggered rework and one direct recheck.
