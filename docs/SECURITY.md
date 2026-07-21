# Security model

The global PreToolUse hook blocks or requests confirmation for:

- Git history and branch writes
- File deletion and destructive filesystem commands
- Destructive SQL
- Dependency installation and system package installation
- Database migrations
- Deployment and infrastructure mutation commands
- Sensitive configuration and credential file edits

The guard is defense in depth. Agent tool lists remain the primary permission boundary.

No API keys, tokens, endpoints, or GCMP credentials are read, copied, logged, or stored by this project.
