# VS Code Copilot Leader Agents

A native VS Code Copilot Chat setup that keeps a high-quality Leader focused on understanding, orchestration, and acceptance while low-cost workers perform supported tool-using tasks.

中文文档见 [README.zh-CN.md](README.zh-CN.md)。

## Architecture

```text
User -> Leader (current model)
          |
          +-> Analyzer     (DeepSeek V4 Flash, read-only)
          +-> Implementer  (DeepSeek V4 Flash, scoped edits)
          +-> Tester       (DeepSeek V4 Flash, read-only + commands)
          +-> Reviewer     (DeepSeek V4 Flash, read-only + commands)
```

The Leader has only the `agent` and `todo` tools. It can handle tool-free conversation and clarification directly, but supported workspace investigation, code changes, and commands must be delegated to the configured low-cost workers. A clearly scoped change can go straight to Implementer, so cost-first routing does not require a mechanical four-stage pipeline. Requests that need tools absent from every worker, such as the removed Leader-only browser or GitHub tools, stop with an instruction to leave this mode instead of silently spending the current high-cost model.

## Requirements

- VS Code Stable 1.128 or newer
- GitHub Copilot Chat with local agents enabled
- Python 3.9 or newer
- VS Code `code` command on `PATH`
- GCMP extension (`vicanent.gcmp`); the installer adds it automatically

## Install

### macOS / Linux

```bash
./install.sh
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Optional explicit worker model:

```bash
./install.sh --model "DeepSeek-V4-Flash (gcmp.deepseek)"
```

```powershell
.\install.ps1 -Model "DeepSeek-V4-Flash (gcmp.deepseek)"
```

Existing files with the same names and every modified VS Code `settings.json` are backed up before changes are applied.
The installer normalizes modified JSONC settings to standard JSON; comments are preserved in the backup, not in the rewritten file.

After installation, reload VS Code and select **Leader** from the agent picker. VS Code Stable does not currently expose a supported setting for automatically making a custom agent the default, so this final selection is manual.

## Cost-first, risk-based workflow

Leader selects the smallest worker workflow that is sufficient for the task:

- **Tool-free:** Leader handles conversation, clarification, synthesis, and acceptance directly.
- **Read-only investigation:** Analyzer inspects workspace facts.
- **Low risk or routine change:** Implementer investigates, changes, and self-verifies in one focused invocation when practical. Tester and Reviewer are added only when they materially improve confidence.
- **High risk:** an explicit plan and user confirmation before changes involving deletion, dependencies or lockfiles, configuration or secrets, migrations or data writes, external services or deployment, permissions or security boundaries, unclear scope, or difficult rollback. Independent Tester and Reviewer PASS are mandatory after implementation.

If the configured worker model is unavailable or inadequate, Leader stops and asks for an explicit replacement worker model or asks the user to leave this mode. It never silently takes over tool-using work with the current high-cost model.

This cost boundary intentionally narrows the mode's capabilities: the bundled workers cover workspace analysis, implementation, testing, and review. A request that needs a tool not listed by any worker must be handled outside this mode.

`批准执行` is a recommended short form for high-risk confirmation; clear natural-language confirmation is also valid. A high-risk confirmation does not authorize later material expansion.

## Native limitations

This project uses only VS Code native custom agents, subagents, skills, settings, and hooks. Native VS Code can block known dangerous operations, require confirmation for exact single-file deletion, and require confirmation for GitHub writes. It cannot cryptographically bind a chat confirmation to an exact future edit set. Risk classification and high-risk scope control are therefore protocol-enforced. See [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md).

## Validate

Validate repository templates:

```bash
python3 scripts/validate.py
```

Validate an installed configuration:

```bash
python3 scripts/validate.py --installed
```

## License

MIT
