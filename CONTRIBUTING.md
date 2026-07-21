# Contributing

Changes must preserve these invariants:

- Leader has no edit tool.
- Only Implementer has edit capability.
- Workers are hidden and cannot invoke subagents.
- Worker model does not silently fall back to Leader.
- Test and review are independent mandatory gates.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python scripts/validate.py` before submitting changes.
