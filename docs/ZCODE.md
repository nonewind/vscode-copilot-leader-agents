# ZCode support

This repository also ships a native ZCode plugin while preserving the existing VS Code Copilot installation.

## What is included

- `zcode/marketplace.json`: local/team marketplace entry.
- `zcode/plugins/leader-worker/agents/`: four bounded Worker subagents.
- `zcode/plugins/leader-worker/skills/`: the ZCode-specific orchestration skill.
- `zcode/plugins/leader-worker/hooks/`: a ZCode `PreToolUse` guard that structurally enforces the primary Agent's no-edit/no-terminal boundary while Leader/Worker mode is active, and blocks or confirms dangerous operations otherwise.
- `zcode/AGENTS.md`: the primary ZCode Agent's Leader protocol.

ZCode keeps its first-party Agent as the primary entry point, so the Leader's execution boundary is enforced by the plugin `PreToolUse` guard: when the workspace `AGENTS.md` contains the Leader/Worker block (the installer's marked merge block or a manual copy of `zcode/AGENTS.md`), the guard denies the primary Agent's `Edit`, `Write`, `Bash`, and `mcp__*` calls and tells it to delegate. This matches the VS Code edition's structural Leader tool allowlist in effect. Plugin hooks fire only for the primary Agent's tool calls — Worker subagent calls do not pass through them (verified by probing the hook payload) — so Worker boundaries come from each Worker's tool allowlist and brief discipline, and ZCode itself prevents subagents from spawning subagents.

## Install and activate

1. Open the target project in ZCode and connect a provider that exposes GLM-5.3-Flash.
2. Open **Settings → Plugins → Create → Add marketplace**. For a cloned checkout, select this repository's `zcode` directory. For team distribution, add the GitHub repository `nonewind/vscode-copilot-leader-agents`; its root `marketplace.json` uses only a repository-relative plugin path.
3. Install and enable **leader-worker** from the Personal marketplace.
4. Copy `zcode/AGENTS.md` to the target workspace root as `AGENTS.md`, or merge its complete Leader/Worker section into an existing root `AGENTS.md`. Do not overwrite existing project instructions. This block is also the activation marker for the guard's structural Leader boundary.
5. Start a new ZCode session. Confirm the four plugin subagents appear under **Settings → Subagents** and the plugin Hook appears under **Settings → Hooks**.
6. Confirm each Worker resolves to the intended GLM-5.3-Flash channel. The definitions use the canonical `glm-5.3-flash` ID, but provider mappings and availability require a live check.

### Portable local installer

The installer derives paths from the current user's home and the arguments supplied at runtime; it never writes a developer username or checkout path into the distributed marketplace:

```bash
python3 scripts/install_zcode.py --project /path/to/target-project
```

By default it stages a self-contained marketplace under `~/.zcode/leader-worker-agents`, backs up an existing staged marketplace, and merges a marked Leader/Worker block into the target project's root `AGENTS.md` without replacing unrelated project rules. Use `--marketplace-dir /another/path` to choose a different staging location or `--dry-run` to preview.

ZCode does not currently document a supported CLI for mutating its installed-plugin registry. The script therefore does not edit `~/.zcode/cli/plugins/installed_plugins.json`, `known_marketplaces.json`, databases, credentials, session transcripts, or caches. The final marketplace selection and plugin enable action remains in the ZCode UI.

Do not enable ZCode Goal Mode for this workflow. A Worker `GOAL` is ordinary one-invocation brief text, not persistent objective state.

## Required smoke test

Run these checks in a disposable Git workspace before relying on the mode:

1. Ask the primary Agent for a read-only call-chain investigation and verify it dispatches `leader-analyzer` without editing.
2. Ask for one bounded reversible edit and verify only `leader-implementer` writes.
3. Verify Analyzer, Tester, and Reviewer cannot edit and no Worker can create a nested subagent.
4. Verify independent packages can run in parallel and overlapping write packages are staged.
5. Request `git commit`, a dependency install, and a literal deletion; verify the Hook denies the Git write and asks for the other two.
6. Trigger an unmet `DONE` item and verify there is at most one targeted rework plus one direct recheck, with no Goal Mode or todo loop.
7. Ask the primary Agent itself to edit a file or run a workspace command; verify the Hook denies the call with delegation guidance and the Agent routes the work to a Worker instead of retrying or switching tools. Removing the Leader/Worker block from `AGENTS.md` and starting a new session must restore unrestricted behavior.

Repository validation proves only the static plugin layout and policy tokens. It does not prove installed ZCode state, provider model routing, credit usage, primary-Agent compliance, or Hook execution.
