# ZCode support

This repository ships a portable ZCode plugin while preserving the VS Code Copilot and Codex editions.

## What is included

- `zcode/marketplace.json`: local/team marketplace entry.
- `zcode/plugins/leader-worker/agents/`: four bounded Worker subagents.
- `zcode/plugins/leader-worker/skills/`: the ZCode-specific orchestration skill.
- `zcode/plugins/leader-worker/hooks/`: a `PreToolUse` guard for the primary-Agent boundary and shared safety decisions.
- `zcode/AGENTS.md`: the primary ZCode Agent's Leader protocol.

The guard reads exactly one execution-mode declaration inside the managed `AGENTS.md` block. Missing, malformed, or duplicate state fails closed to `strict`; legacy manual copies containing the old heading also remain strict. When no project root is supplied by the host, lookup walks from the current directory to the filesystem root.

## Execution modes

- `strict` denies primary-Agent `Edit`, `Write`, `Bash`, and `mcp__*` calls and routes the work to Workers.
- `adaptive` still denies `mcp__*`; an ordinary direct edit or command becomes a per-call approval request. Approval is not proof that the shared adaptive conditions hold: the Leader must declare `DIRECT:` first and may perform only the contract's single bounded action.
- ZCode 0.8.0 has no model-fallback variant. Eligible deterministic rejection or exhausted transient retry stops and reports the configuration problem.

Global safety rules run before the adaptive catch-all and inspect only structured command/path fields, never edit bodies. Git-writing and unsafe deletion are denied. Literal deletion, dependency, migration, deployment, and sensitive-path operations retain their specialized confirmation decisions. In 0.8.0, sensitive-path edit confirmation also applies when no Leader/Worker block is active; this is an intentional cross-platform safety change for `.env`, credential, lockfile, workflow, infrastructure, and migration paths.

The existing runtime probe observed the Hook on primary-Agent calls and not on Worker subagent calls. Repeat the source-reach check for the release and record the observed payload; do not generalize one client build's behavior to all versions.

## Install and activate

1. Open the target project in ZCode and connect a provider that exposes GLM-5.3-Flash.
2. Open **Settings → Plugins → Create → Add marketplace**. Select this repository's `zcode` directory, or use the repository marketplace entry for team distribution.
3. Install and enable **leader-worker**.
4. Use the portable installer to stage the marketplace and safely merge the complete managed policy:

```bash
python3 scripts/install_zcode.py --project /path/to/project
python3 scripts/install_zcode.py --project /path/to/project --mode adaptive
```

The default for a project without mode state is strict. Omitting `--mode` on reinstall preserves a valid installed choice. Use `--marketplace-dir /another/path` to choose the staging destination or `--dry-run` to preview. Existing targets are backed up.

The script does not modify ZCode's installed-plugin registry, databases, credentials, transcripts, or caches. Marketplace selection and plugin enablement remain UI actions. Start a new session after changing the managed block. Do not enable ZCode Goal Mode: Worker `GOAL` is ordinary one-invocation brief text.

All four Workers request canonical `glm-5.3-flash` with `thoughtLevel: high`. Provider mapping and availability require a live check. A 2026-09-10 probe found the connected provider deterministically rejected `medium`; an unsupported model or thought level must be reported rather than retried with the same configuration.

## Required smoke test

Use a disposable Git workspace and new sessions:

1. In `strict`, request a bounded investigation, edit, and command. Confirm Analyzer/Implementer routing and primary edit/command denial.
2. In `adaptive`, verify one eligible edit and one eligible command each produce a per-call approval request only after `DIRECT:`; verify scope growth transfers to Implementer.
3. In both modes, verify Git-writing and unsafe deletion remain denied, while dependency and literal deletion use their specialized confirmation messages rather than the generic adaptive message.
4. With the boundary inactive, verify an ordinary edit proceeds and a sensitive-path edit requests confirmation. Verify edit body text mentioning a Git command, dependency command, or lockfile name does not trigger a rule when the actual command/path is benign.
5. Run a primary action and a Worker action that would match the Hook. Record whether the Hook receives each source and whether a source discriminator exists; do not infer reach from static registration.
6. Verify Workers use the intended model/thought level, cannot spawn subagents, respect role tool lists, and stop without model fallback after eligible failure.
7. Verify independent packages can run in parallel, overlapping write packages are staged, and rework/recheck limits hold.

Repository validation proves static plugin layout, parser decisions, guard ordering, installer mode preservation, and policy tokens. It does not prove installed state, Hook loading/reach, provider routing, credit usage, or primary-Agent compliance.
