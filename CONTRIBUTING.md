# Contributing

Changes must preserve these invariants:

- Leader owns intent alignment, key decisions, risk classification, worker routing, synthesis, and acceptance. It has `agent`, `todo`, `read`, and `search`, but uses read-only tools only for narrow decisive facts; it never edits, executes, or takes over external operations.
- Implementer has edit and execute capability within a Leader-declared scope; deletion requires a confirmed high-risk exact file path and Hook confirmation.
- Workers are hidden and cannot invoke subagents.
- Workers use the configured worker model exactly. Analyzer handles focused read-only facts; Implementer handles the smallest sufficient change and direct self-verification. Clear changes may go directly to Implementer without a redundant Analyzer stage.
- Every Worker receives a proportional brief with `GOAL`, `BOUNDARIES`, `DONE`, and `STOP_AND_REPORT`. It stops at sufficient evidence, does not pursue incidental findings, and returns `NEEDS_LEADER` before expanding product choices, boundaries, risk, or validation depth.
- Parallelize only independent, non-overlapping, side-effect-free read tasks. Shared-workspace implementation remains serial by default; Tester and Reviewer may overlap only when their commands do not contend for caches, generated artifacts, data, or environment state.
- Worker reports stay concise and evidence-based: exact source or command result, actual boundary, gaps, and one concrete decision request when needed. Do not reintroduce routine evidence ledgers, consensus stages, or an isolated arbitration agent.
- Native Worker invocations are stateless. Follow-up work starts a new invocation from the concise brief, reported checkpoint, and current filesystem state; never claim an in-place resume.
- When the worker model is unavailable or inadequate, Leader stops for explicit model selection or asks the user to leave this mode; it never silently takes over tool-using work.
- Do not add implementation capability to Leader. Add it to the least-privileged suitable Worker with matching guard coverage, or document that the request must leave this mode.
- Test and review are independent mandatory gates for high-risk work and discretionary, evidence-based gates for routine work.
- GitHub writes and unknown GitHub actions require Hook confirmation; named read-only GitHub actions remain available.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python3 scripts/validate.py` and `python3 -m unittest discover -s tests -v` before submitting changes.
