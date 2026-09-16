# Changelog

## 0.8.0 — unreleased

Adds bounded adaptive execution without weakening strict defaults.

- Adds separate strict/adaptive execution modes on all three platforms; adaptive permits only one declared, low-risk local action and transfers Writer ownership on scope growth.
- Adds the optional Codex `parent-worker` fallback mode with four unpinned same-role variants; fresh installs remain `stop`.
- Removes Codex project-wide model/effort defaults from the source baseline and adds an explicit exact-value migration with backup, custom-value preservation, and fallback conflict checks.
- Clarifies that Codex agent sandbox declarations are defaults overridden by live parent permissions, and expands the required smoke test in both directions.
- Adds VS Code `--leader` and ZCode `--mode` install switches that preserve prior valid selections.
- Scopes Python, PowerShell, and ZCode guard matching to actual command/path fields so command examples in edit bodies do not create false positives.
- Reorders the ZCode guard so global hard denials and confirmation classes retain priority over adaptive approval. Sensitive-path confirmation now deliberately applies even without an active Leader block.
- Keeps ZCode model fallback out of 0.8.0 pending a separate runtime inheritance probe.

Static tests do not establish live host Hook reach, model routing, sandbox inheritance, or billing. Run each platform's documented fresh-session smoke test before claiming those behaviors.

## 0.7.0

Consolidates the current working-tree changes into one repository baseline.

- Keeps Codex Workers on gpt-5.6-luna with medium effort for Analyzer/Tester and high for Implementer/Reviewer; keeps ZCode Workers at high effort.
- Distinguishes deterministic configuration rejection from transient dispatch failure across Leader policies and workflow skills.
- Adds one shared poor-mode contract with checked, installable copies for VS Code, Codex, and ZCode.
- Selects only necessary roles, reuses current evidence, and requires confirmed Worker termination before replacement after a timeout.
- Bounds and discloses VS Code fallback; Codex/ZCode stop on unavailable configuration or exhausted transient retry.
- Documents total-cost measurement and keeps unknown usage and unrun runtime checks explicit.

Repository validation is separate from installation, client activation, and live cost/model evidence. The fullstack benchmark retains its own version and historical results.
