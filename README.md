# VS Code Copilot Leader Agents

A native VS Code Copilot Chat coordinator/worker setup designed to minimize model cost while keeping planning and acceptance under a high-quality Leader model.

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

The Leader normally uses only isolated subagents. It can perform read-only verification itself only when worker reports conflict or direct verification is necessary. It never edits files.

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

## Approval workflow

1. Start every development request in `Leader`.
2. Leader may invoke only the read-only Analyzer before authorization.
3. Leader presents a factual plan.
4. The exact user reply `批准执行` authorizes the current plan and its declared scope.
5. Implementer edits only the authorized scope.
6. Tester must pass before Reviewer runs.
7. Reviewer must pass before Leader reports completion.
8. Any expansion of goal, file scope, risk, dependency, database, environment, or external-service impact stops execution and requires a new plan plus a new `批准执行`.

## Native limitations

This project uses only VS Code native custom agents, subagents, skills, settings, and hooks. Native VS Code can strongly enforce tool separation and block known dangerous operations. It cannot cryptographically bind a chat approval phrase to an exact future edit set. Plan authorization and path scope are therefore protocol-enforced, while destructive operations are hook-enforced. See [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md).

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
