# Contributing

Changes must preserve these invariants:

- Leader owns risk classification and may directly complete low-risk or routine local work; high-risk changes require user confirmation and independent test/review gates.
- Implementer has edit and execute capability within a Leader-declared scope; deletion requires a confirmed high-risk exact file path and Hook confirmation.
- Workers are hidden and cannot invoke subagents.
- Workers are optional and use the configured worker model exactly; when delegation is not useful or unavailable, Leader may work directly.
- Test and review are independent mandatory gates for high-risk work and discretionary, evidence-based gates for routine work.
- GitHub writes and unknown GitHub actions require Hook confirmation; named read-only GitHub actions remain available.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python scripts/validate.py` before submitting changes.
