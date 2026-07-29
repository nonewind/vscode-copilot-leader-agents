# VS Code Copilot Leader Agents

A native VS Code Copilot Chat setup that lets a high-quality Leader decide when to work directly and when low-cost workers add enough value to justify delegation.

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

The Leader has the full configured VS Code tool set and acts as the task's risk and quality authority. It may investigate, implement, and verify low-risk work directly; workers are optional, isolated support for tasks where delegation adds value. Tool availability never bypasses the high-risk safety boundary.

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

## Risk-based workflow

Leader selects the smallest workflow that is sufficient for the task:

- **Low risk:** direct investigation, implementation, and proportionate self-verification for explicit, local, reversible work.
- **Routine:** direct work or targeted worker delegation, with verification chosen for the actual uncertainty and impact.
- **High risk:** an explicit plan and user confirmation before changes involving deletion, dependencies or lockfiles, configuration or secrets, migrations or data writes, external services or deployment, permissions or security boundaries, unclear scope, or difficult rollback. Independent Tester and Reviewer PASS are mandatory after implementation.

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
