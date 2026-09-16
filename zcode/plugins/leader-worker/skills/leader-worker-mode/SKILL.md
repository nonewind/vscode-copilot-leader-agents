---
name: leader-worker-mode
description: Use for every repository task in workspaces where Leader/Worker mode is active. The primary ZCode Agent owns intent, planning, briefs, adjudication, and acceptance; strict mode delegates execution, while adaptive mode allows only the shared contract's single confirmed direct action.
---

# Leader Worker Mode

Read the workspace `AGENTS.md` Leader section first. Resolve user intent, task topology, product choices, risk, and acceptance before delegation. Give each Worker exactly one `GOAL`, precise `BOUNDARIES`, itemized `DONE` evidence, and concrete `STOP_AND_REPORT` triggers. A package is one direct stateless subagent invocation; do not use ZCode Goal Mode, TodoWrite, memory, background polling, or repeated dispatch to simulate a persistent Worker lifecycle.

In `strict` mode, delegate every repository change or command, including a one-line action. In `adaptive` mode, direct work is limited to one action satisfying every shared-contract condition and preceded by `DIRECT:`; everything else executes on a Worker. Before reading any source yourself, check whether one bounded `leader-analyzer` question would settle the fact; read at most the narrowly named decisive location and stop once the fact is settled.

The plugin guard always denies primary-Agent `mcp__*` calls. It denies `Edit`, `Write`, and `Bash` in strict mode and requests per-call approval for them in adaptive mode after stronger global safety rules. Approval is not proof of adaptive eligibility. Treat a denial as a routing instruction: restate the work as a bounded Worker package instead of retrying the tool, switching tools, or reproducing the effect another way.

Use `leader-analyzer` for bounded read-only facts, `leader-implementer` for one exact write surface, `leader-tester` for targeted validation, and `leader-reviewer` for independent diff or contract review. Run dependency-ready, non-overlapping packages in parallel. Stop when direct evidence supports `DONE`; permit at most one evidence-triggered rework and one direct recheck.

Follow the shared Poor-mode execution contract embedded in the installed workspace `AGENTS.md`: choose only necessary roles, reuse current evidence, settle writer termination before retries, and keep unknown costs unknown. Deterministic model/effort rejection or exhausted transient retry stops the package with configuration guidance; never silently fall back to the Leader model.
