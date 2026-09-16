# Codex support

This repository ships a project-scoped Codex Leader/Worker setup alongside the VS Code Copilot and ZCode editions.

## What is included

- `codex/agents/leader-*.toml`: four base Workers fixed to `gpt-5.6-luna`, plus four optional `leader_*_fallback` variants that omit both model and reasoning effort.
- `codex/config.toml`: only the static managed `[agents]` enablement and four-thread cap. It deliberately does not set project-wide model or effort defaults.
- `codex/skills/leader-worker-mode/SKILL.md`: the repository workflow skill installed under `.agents/skills`.
- `codex/AGENTS.md`: the primary-thread Leader protocol merged into the target project's root instructions.
- `scripts/install_codex.py`: a portable installer with explicit execution, fallback, and legacy-default migration controls.

Base Analyzer and Reviewer declare `sandbox_mode = "read-only"`; base Implementer and Tester declare `workspace-write`. The fallback for each role preserves the same sandbox declaration and role body. These declarations are defaults, not immutable isolation: Codex reapplies the parent turn's live sandbox and approval overrides when spawning a child, so the parent can narrow or broaden them. See the [official subagent configuration documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Role instructions remain mandatory even when the runtime grants more access.

## Modes

Execution and model fallback are independent axes:

- `--mode strict` delegates every workspace edit and command.
- `--mode adaptive` permits only one action satisfying every condition in the shared Poor-mode contract, preceded by `DIRECT:`. This is protocol enforcement; Codex has no project Hook discriminator that can enforce it only on the primary thread.
- `--fallback stop` reports an eligible base-Worker model failure and stops.
- `--fallback parent-worker` installs the four unpinned fallback roles. After the base retry policy is exhausted, the Leader may disclose and invoke the matching fallback once for the remaining original package.

The defaults for a fresh install are `strict` and `stop`. Reinstalling without flags preserves one valid previously installed value for each axis.

## Install and migrate

Preview first:

```bash
python3 scripts/install_codex.py --project /path/to/project --dry-run
```

Install the defaults or opt in explicitly:

```bash
python3 scripts/install_codex.py --project /path/to/project
python3 scripts/install_codex.py --project /path/to/project --mode adaptive
python3 scripts/install_codex.py --project /path/to/project --fallback parent-worker
```

Older releases wrote exact project-wide defaults for `gpt-5.6-luna` and `high`. The 0.8.0 source baseline no longer owns those keys. If either exact legacy value remains, installation stops until the user reviews the project-wide inheritance impact and authorizes its removal:

```bash
python3 scripts/install_codex.py --project /path/to/project --migrate-agent-defaults
```

Migration removes only exact legacy values. Different user-configured values are preserved. `parent-worker` installation is refused while any custom project-wide model or effort default remains, because the fallback would not inherit the parent as promised. Removing defaults can change built-in or unmanaged custom agents that omit their own model or effort; the installer lists detectable unmanaged files that may be affected.

Before writing, the installer computes the whole plan. It backs up changed files with one batch timestamp, uses atomic per-file replacement, and is safe to rerun; it does not promise cross-file rollback. Base agents are always managed. Fallback agents are removed only when their hashes match the install state, so modified or unowned files are never deleted silently. Start a new Codex session after installation because root instructions are loaded at session start.

## Native boundary difference

The primary execution boundary is protocol-enforced. Codex project Hooks run in contexts where current input does not reliably identify primary versus child calls, so a shared write-blocking Hook could also block Implementer. Agent sandbox values also cannot be described as structural isolation because live parent overrides take precedence at spawn time.

Accordingly, this edition claims only the configured defaults and policy behavior. It does not claim immutable read-only children, enforced primary-thread abstention, actual fallback inheritance, model identity, or billing without a fresh live test.

## Required smoke test

Use a disposable Git workspace and a fresh Codex session for each material mode change:

1. In `strict`, request one bounded edit and one command; confirm the primary thread delegates both. Record this as protocol/runtime evidence, not structural proof.
2. In `adaptive`, request an eligible one-location reversible edit; confirm `DIRECT:` appears before one direct action and no Worker is called. Then expand the scope and confirm ownership transfers to Implementer instead of a second direct edit.
3. Dispatch each base role and confirm the actual model and effort match its file. A static TOML check is not sufficient.
4. Start the parent with a restrictive live sandbox and confirm it narrows a write-capable Worker. Separately, start with a permissive live sandbox and probe whether it broadens an Analyzer/Reviewer beyond the declared read-only default; the role must still refuse prohibited writes.
5. In `stop`, trigger an eligible deterministic base-model rejection and confirm no fallback is used. In `parent-worker`, confirm exactly one same-role fallback is disclosed, retains the original brief, and actually resolves through parent inheritance.
6. Confirm `FAIL`, `BLOCKED`, `NEEDS_LEADER`, or weak output does not trigger fallback.
7. Confirm no Worker spawns another subagent, independent non-overlapping packages may run in parallel, overlapping writers are staged, and the rework/recheck brake holds.

Repository validation proves source layout, TOML shape, base/fallback contract parity, migration decisions, file ownership protection, and policy synchronization. It does not prove files were loaded or any live routing, sandbox, token, cost, or billing result.
