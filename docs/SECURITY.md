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

The guard is defense in depth. Tool lists define available mechanics, while the latest approved plan and exact-path scope remain protocol-enforced. The Hook cannot determine which plan the user most recently approved.

No API keys, tokens, endpoints, or GCMP credentials are read, copied, logged, or stored by this project.
