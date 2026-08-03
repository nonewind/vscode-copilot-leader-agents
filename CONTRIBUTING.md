# Contributing

Changes must preserve these invariants:

- Leader owns risk classification, worker routing, synthesis, and acceptance, but has only `agent` and `todo`; supported workspace operations must be delegated and unsupported tool requests must stop.
- Implementer has edit and execute capability within a Leader-declared scope; deletion requires a confirmed high-risk exact file path and Hook confirmation.
- Workers are hidden and cannot invoke subagents.
- Workers use the configured worker model exactly. Analyzer handles read-only investigation; Implementer handles changes and proportionate self-verification. Clear changes may go directly to Implementer without a redundant Analyzer stage.
- When the worker model is unavailable or inadequate, Leader stops for explicit model selection or asks the user to leave this mode; it never silently takes over tool-using work.
- Do not add a capability only to Leader. Add it to the least-privileged suitable worker with matching guard coverage, or document that the request must leave this mode.
- Test and review are independent mandatory gates for high-risk work and discretionary, evidence-based gates for routine work.
- GitHub writes and unknown GitHub actions require Hook confirmation; named read-only GitHub actions remain available.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python scripts/validate.py` before submitting changes.
