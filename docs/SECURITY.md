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

The guard is defense in depth. Tool lists define available mechanics, while Leader risk classification and high-risk scope remain protocol-enforced. The Hook cannot determine what the user most recently confirmed.

No API keys, tokens, endpoints, or GCMP credentials are read, copied, logged, or stored by this project.
