# Contributing

Changes must preserve these invariants:

- Leader exposes the configured full tool set, but direct writes require explicit current-task user assignment and an approved exact scope.
- Implementer has edit and execute capability; deletion requires an approved exact file path and independent confirmation.
- Workers are hidden and cannot invoke subagents.
- Worker model does not silently fall back to Leader.
- Test and review are independent mandatory gates.
- Installers back up same-name files and settings before mutation.
- No credential handling is introduced.

Run `python scripts/validate.py` before submitting changes.
