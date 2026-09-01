# VS Code Copilot Leader Agents

A native VS Code Copilot Chat setup that spends a high-capability Leader model on user intent, key decisions, narrow fact checks, orchestration, and acceptance while a configured low-cost model performs workspace investigation, implementation, testing, and review.

中文文档见 [README.zh-CN.md](README.zh-CN.md)。

## Architecture

```text
User <-> Leader (current model; agent, bounded read/search/web)
           |-- Analyzer     (worker model; read-only investigation)
           |-- Implementer  (worker model; scoped edits and self-checks)
           |-- Tester       (worker model; targeted commands)
           `-- Reviewer     (worker model; diff and risk review)
```

Leader has no edit, execute, general VS Code operation, browser, GitHub, todo, or external-write tools. Routine workspace work stays on workers. Leader may use `read` and `search` only for a small decisive source fact when worker evidence conflicts or is insufficient. Its single `web` tool is limited to a bounded public fact or authoritative document unavailable from the workspace; it cannot log in, write externally, or transmit workspace content or credentials. `vscode/askQuestions` is reserved for user decisions that change the result, boundary, or authority. `vscode/memory` may retain only stable preferences or reusable project facts the user explicitly asks to remember; it never stores task state or triggers work.

Leader fixes the default submodel to `GLM-5.3-Flash (CodingPlan) (gcmp.zhipu)` and explicitly specifies it on each initial Analyzer, Implementer, Tester, or Reviewer invocation. Its GCMP catalog model ID is `glm-5.3-flash`; the VS Code selector route is `gcmp.zhipu:::glm-5.3-flash`. On an invocation error or `MODEL_UNAVAILABLE`, it retries that same stateless Worker once with the original brief and checkpoint. If both requests fail for that model reason, Leader invokes the same Worker role without a Worker-model override so it inherits the current Leader model and completes the remaining in-scope task. Worker manifests remain model-neutral. `FAIL`, `BLOCKED`, `NEEDS_LEADER`, and weak results are handled as task evidence, not model retries; no third model is discovered.

The current VS Code subagent interface does not expose an independent per-subagent reasoning-effort call parameter. Even when the GCMP catalog advertises model reasoning levels, this project does not claim or fabricate a `max` setting. Complex briefs name the exact analysis dimensions, decision rules, and required evidence instead; that is prompt guidance, not a platform reasoning-effort configuration.

Before modification, Leader aligns the user-visible goal and asks one to three concrete questions only when the answer changes the result, boundary, or authority. Because GLM-5.3-Flash is the low-cost execution model, Leader resolves intent, decomposes the task, and makes key choices before sending each Worker a mechanically executable brief:

- `GOAL`: one concrete, observable result;
- `BOUNDARIES`: exact paths, symbols, or command scope; known facts; allowed actions; preserved behavior; and non-goals;
- `DONE`: itemized acceptance criteria and the file diff, target behavior, command, or other direct evidence sufficient to pass each one;
- `STOP_AND_REPORT`: new choices, expansion, risk, or validation needs that return to Leader.

This is a semantic boundary, not a form or quota. Before the first Worker call, a task-topology gate permits the single-Worker fast path only for one observable result, one bounded work surface, and one independent acceptance chain. Compound work becomes dependency-ordered stage waves of independently acceptable packages. Two packages that can be accepted independently must not be merged into one large `GOAL`; every dependency-ready package that can safely coexist starts in the same parallel wave. Serial execution must name a concrete data dependency, contract owner, overlapping file, generated-artifact conflict, or command side effect—not merely task length, one shared user goal, or a generic shared-workspace concern.

A change brief also includes direct evidence of the problem, required behavior, allowed files or symbols, and dependency order when one exists. It never hides scope or quality behind phrases such as “related files,” “fix appropriately,” “as needed,” or “check everything.” If the change location is not yet bounded, Leader first gives Analyzer one bounded fact question. Each package is one direct stateless Worker invocation: `GOAL` is plain text, not a command or persistent task. Leader has no `todo` tool and must not use memory, other tools, or prose to simulate a persistent Worker lifecycle, polling loop, or automatic reinvocation. A later call is valid only for a predeclared next-wave package with direct dependency evidence, or targeted rework for a named unmet `DONE` item supported by new evidence. Workers stop at the first sufficient evidence, report incidental findings without pursuing them, and return `NEEDS_LEADER` before expanding the task.

For a direct public TypeScript contract change, Leader writes `PUBLIC_TYPESCRIPT_API` into `DONE`: a named isolated type check plus, for changed public exports, an external-consumer compile fixture with positive and `@ts-expect-error` negative cases. For observable empty/missing/nullish/zero/edge/no-data behavior, it writes `BEHAVIOR_BOUNDARY` into `DONE` with only the source-supported boundary rows and expected outcomes. A triggered requirement is not an optional `NOT_VERIFIED` gap: Tester verifies it, and public TypeScript changes also receive a narrow Reviewer check.

Leader runs distinct read-only investigations in parallel when they are independent, non-overlapping, independently composable, and free of shared side effects. Multiple Implementers also run concurrently when exact file ownership, public contracts, generated artifacts, and commands do not overlap; conflicting packages move to later dependency waves instead of being collapsed into one oversized Worker assignment. Tester, Reviewer, and other independent validation packages run concurrently after a stable implementation wave when their commands do not contend for caches, generated artifacts, data, or environment state. Parallelism shortens the critical path; it does not increase the investigation budget.

## Cost-first, risk-based workflow

- **Tool-free:** Leader handles conversation, intent alignment, synthesis, and acceptance.
- **Read-only investigation:** Analyzer gathers focused workspace facts.
- **Routine change:** Implementer performs the smallest sufficient change and narrowest direct self-check. Tester or Reviewer is added only when it materially improves confidence.
- **High risk:** deletion, dependencies or lockfiles, configuration or secrets, migrations or persistent data writes, external services or deployment, permissions/security boundaries, cross-module unknown impact, or difficult rollback requires an explicit plan and user confirmation. Independent Tester and Reviewer PASS are mandatory afterward.

Verification is evidence-triggered: direct behavior and diff, then a targeted check, then module or broad validation only when shared impact, a direct failure, a concrete contract risk, or the confirmed plan requires it. `PUBLIC_TYPESCRIPT_API` and `BEHAVIOR_BOUNDARY` make their named narrow check a concrete contract risk; they do not default to a broad suite. Leader owns validation depth and final acceptance; it stops when direct evidence supports `DONE`, and may continue only for new concrete evidence that directly threatens a named `DONE` item. `NOT_VERIFIED`, theoretical risk, suggested expansion, and incidental findings are reported gaps, not automatic gates. Each task permits at most one targeted rework round and one direct recheck before Leader must accept the supported result or report what remains unsupported.

The one-task main-model fallback preserves the original brief, boundaries, confirmed authority, and `DONE`; it never gives Leader implementation tools or becomes the default model for later tasks. Native VS Code cannot prove that an unpinned subagent inherits the requested current model, so this route needs a real VS Code smoke test. Requests requiring tools absent from every worker still leave this mode.

## Requirements

- VS Code Stable 1.128 or newer
- GitHub Copilot Chat with local agents enabled
- Python 3.9 or newer
- VS Code `code` command on `PATH`
- GCMP extension (`vicanent.gcmp`) with a Zhipu catalog that contains `gcmp.zhipu:::glm-5.3-flash`

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

If GCMP is already installed, run `./install.sh --update-extension` before installation when the selector does not list the default model.

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
