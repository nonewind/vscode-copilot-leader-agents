# Codex support

This repository ships a project-scoped Codex Leader/Worker setup alongside the VS Code Copilot and ZCode editions.

## What is included

- `codex/agents/*.toml`: four custom Codex agents, all fixed to `gpt-5.6-luna` with high reasoning effort.
- `codex/config.toml`: the managed `[agents]` defaults and a four-Worker concurrency cap.
- `codex/skills/leader-worker-mode/SKILL.md`: the repository workflow skill installed under `.agents/skills`.
- `codex/AGENTS.md`: the primary-thread Leader protocol merged into a target project's root instructions.
- `scripts/install_codex.py`: a portable installer that preserves unrelated project instructions and Codex settings.

Analyzer and Reviewer use `sandbox_mode = "read-only"`. Implementer and Tester use `sandbox_mode = "workspace-write"`; Tester needs that sandbox for ordinary commands that write caches, coverage, compiled output, or other test artifacts, while its instructions still forbid source edits and repairs. The parent turn's live permission and approval choices apply to every child, so a stricter parent can prevent either write-capable Worker from running its intended work.

## Install

Preview first:

```bash
python3 scripts/install_codex.py --project /path/to/project --dry-run
```

Install:

```bash
python3 scripts/install_codex.py --project /path/to/project
```

The installer:

1. merges the required `[agents]` keys into `.codex/config.toml`;
2. installs the four project agents under `.codex/agents/`;
3. installs the workflow skill under `.agents/skills/leader-worker-mode/`;
4. merges a marked block into the root `AGENTS.md` without replacing unrelated instructions.

Existing changed files are backed up beside the originals. If an existing managed `[agents]` key conflicts with the required value, installation stops instead of overwriting it. Start a new Codex session after installation because `AGENTS.md` is loaded at session start.

## Native boundary difference

The ZCode edition can deny only the primary Agent's edit and terminal calls because its plugin Hook does not run for Workers. Codex project Hooks run for both the primary thread and subagents, and current `PreToolUse` input does not expose a reliable primary-vs-subagent discriminator. A shared Hook that blocks Leader writes would also block the Implementer.

Therefore the Codex edition deliberately does not claim structural isolation for the Leader. Its primary no-edit/no-terminal rule is enforced by `AGENTS.md` and the workflow skill. Analyzer and Reviewer are structurally read-only; Implementer and Tester are write-capable, with Tester kept from source edits by its role protocol. This is the closest functional native mapping without a custom MCP execution broker or separate external Worker process.

## Required smoke test

Use a disposable Git workspace and a fresh Codex session:

1. Ask for a bounded call-chain investigation. Confirm the primary thread dispatches `leader_analyzer` and the child reports model `gpt-5.6-luna`.
2. Ask for one reversible edit. Confirm only `leader_implementer` writes and its thread uses `gpt-5.6-luna`.
3. Ask `leader_analyzer` or `leader_reviewer` to edit. Confirm the read-only sandbox denies it. Ask `leader_tester` to repair a failure and confirm it reports rather than editing.
4. Confirm no Worker spawns another subagent and every package contains `GOAL`, `BOUNDARIES`, `DONE`, and `STOP_AND_REPORT`.
5. Confirm independent non-overlapping packages run in parallel, while overlapping writes are staged.
6. Trigger an unmet `DONE` item. Confirm at most one evidence-backed rework and one direct recheck occur.
7. Ask the primary thread itself to edit or run a workspace command. Confirm it delegates. Record this as prompt/runtime behavior, not structural proof.
8. Start the parent in read-only mode and confirm Implementer cannot override that live parent restriction; then choose the intended permission mode before real implementation work.

Repository validation proves only source layout, TOML validity, fixed model declarations, installer behavior, and policy tokens. It does not prove the installed files were loaded, the actual model route, token billing, primary-thread compliance, or live sandbox behavior.
