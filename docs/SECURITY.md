# Security model

The global PreToolUse hook blocks or requests confirmation for:

- Git history and branch writes
- Exact single-file deletion (confirmation required)
- Directory, recursive, and destructive filesystem deletion (blocked)
- Destructive SQL
- Dependency installation and system package installation
- Database migrations
- Deployment and infrastructure mutation commands
- Sensitive configuration and credential file edits
- GitHub write and unknown GitHub actions; named read-only GitHub actions remain available

The Leader has only `agent` and `todo`, so supported workspace operations are structurally routed to workers and unsupported tool requests stop. The guard is defense in depth for worker tool calls. Leader risk classification and high-risk scope remain protocol-enforced, and the Hook cannot determine what the user most recently confirmed.

No API keys, tokens, endpoints, or GCMP credentials are read, copied, logged, or stored by this project.
