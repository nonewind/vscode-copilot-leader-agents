# VS Code Copilot Leader Agents

A native VS Code Copilot Chat setup that spends a high-capability Leader model on user intent, key decisions, narrow fact checks, orchestration, and acceptance while a configured low-cost model performs workspace investigation, implementation, testing, and review.

中文文档见 [README.zh-CN.md](README.zh-CN.md)。

## Architecture

```text
User <-> Leader (current model; agent, todo, bounded read/search)
           |-- Analyzer     (worker model; read-only investigation)
           |-- Implementer  (worker model; scoped edits and self-checks)
           |-- Tester       (worker model; targeted commands)
           `-- Reviewer     (worker model; diff and risk review)
```

Leader has no edit, execute, VS Code operation, browser, GitHub, or external-service tools. Routine workspace work stays on workers. Leader may use `read` and `search` only for a small decisive fact when worker evidence conflicts or is insufficient, preserving the user's full conversation context without a separate arbitration agent.

Leader fixes the default submodel to `DeepSeek-V4-Flash (Go) (gcmp.opencode)` and explicitly specifies it on every Analyzer, Implementer, Tester, or Reviewer invocation. Worker manifests remain model-neutral. If that model is unavailable, Leader stops for a user-selected replacement; it does not discover or silently fall back to another model.

Before modification, Leader aligns the user-visible goal and asks one to three concrete questions only when the answer changes the result, boundary, or authority. Each worker receives a concise brief:

- `GOAL`: the result to produce or establish;
- `BOUNDARIES`: allowed scope, preserved behavior, and non-goals;
- `DONE`: direct evidence that is sufficient to stop;
- `STOP_AND_REPORT`: new choices, expansion, risk, or validation needs that return to Leader.

This is a semantic boundary, not a form or quota. Clear reversible work uses the fast path. Workers stop at the first sufficient evidence, report incidental findings without pursuing them, and return `NEEDS_LEADER` before expanding the task.

Leader may run distinct read-only investigations in parallel when they are independent, non-overlapping, independently composable, and free of shared side effects. Shared-workspace implementation remains serial by default. Tester and Reviewer may run concurrently after a stable change only when their commands do not contend for caches, generated artifacts, data, or environment state. Parallelism shortens the critical path; it does not increase the investigation budget.

## Cost-first, risk-based workflow

- **Tool-free:** Leader handles conversation, intent alignment, synthesis, and acceptance.
- **Read-only investigation:** Analyzer gathers focused workspace facts.
- **Routine change:** Implementer performs the smallest sufficient change and narrowest direct self-check. Tester or Reviewer is added only when it materially improves confidence.
- **High risk:** deletion, dependencies or lockfiles, configuration or secrets, migrations or persistent data writes, external services or deployment, permissions/security boundaries, cross-module unknown impact, or difficult rollback requires an explicit plan and user confirmation. Independent Tester and Reviewer PASS are mandatory afterward.

Verification is evidence-triggered: direct behavior and diff, then a targeted check, then module or broad validation only when shared impact, a direct failure, concrete contract risk, or the confirmed plan requires it.

If the Worker model is unavailable or repeatedly inadequate, Leader stops and asks for a user-selected replacement model or asks the user to leave this mode. It never auto-discovers, silently falls back, or takes over implementation tools. Requests requiring tools absent from every worker also leave this mode.

## Requirements

- VS Code Stable 1.128 or newer
- GitHub Copilot Chat with local agents enabled
- Python 3.9 or newer
- VS Code `code` command on `PATH`
- GCMP extension (`vicanent.gcmp`); the installer adds it automatically

## Install

macOS/Linux:

```bash
./install.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

Explicit replacement only when selected by the user:

```bash
./install.sh --model "exact-user-selected-model-id"
```

Existing managed files and modified VS Code settings are backed up. Upgrading to 0.4.0 removes the previously managed Arbiter agent and retired workflow skills after backing them up. Reload VS Code and select **Leader** after installation. GCMP credentials remain user-managed and are not read or stored.

## Native limitations

Tool manifests structurally separate Leader decisions from Worker implementation, and Hooks block or confirm known dangerous operations. Intent alignment, semantic boundaries, risk classification, and exact adherence remain prompt protocols; native VS Code cannot bind chat approval to a durable capability token or guarantee provider-side model/credit behavior. See [docs/NATIVE_LIMITATIONS.md](docs/NATIVE_LIMITATIONS.md).

## Validate

```bash
python3 scripts/validate.py
python3 scripts/validate.py --installed
python3 -m unittest discover -s tests -v
```

## License

MIT
