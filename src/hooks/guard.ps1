$ErrorActionPreference = "SilentlyContinue"
$raw = [Console]::In.ReadToEnd()
try { $data = $raw | ConvertFrom-Json } catch { Write-Output '{"continue":true}'; exit 0 }

$toolName = [string]$data.tool_name
$inputText = ($data.tool_input | ConvertTo-Json -Depth 20 -Compress)
$combined = ($toolName + " " + $inputText).ToLowerInvariant()

function Emit-Decision([string]$decision, [string]$reason) {
    $obj = @{ hookSpecificOutput = @{ permissionDecision = $decision; permissionDecisionReason = $reason } }
    $obj | ConvertTo-Json -Depth 5 -Compress
}

$hardDeny = @(
    '\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b',
    '\bgit\s+branch\s+(-d|-D|-m|-M|--delete|--move)\b',
    '\brm\b[^\n]*(?:\s-[^\s]*[rR][^\s]*|\s--recursive)\b',
    '\b(?:rmdir|rd)\b',
    '\bdel\b[^\n]*\s/[^\s]*[sS][^\s]*',
    '\bremove-item\b[^\n]*-recurse\b',
    '\b(drop|truncate)\s+(table|database|schema)\b',
    '\bdelete\s+from\b',
    '\bupdate\s+[^\n]+\s+set\b',
    '\binsert\s+into\b',
    '\balter\s+table\b'
)
foreach ($pattern in $hardDeny) {
    if ($combined -match $pattern) {
        Emit-Decision "deny" "Destructive or Git-writing operation blocked by the Leader security policy."
        exit 0
    }
}

$command = [string]$data.tool_input.command
$hasDelete = $command -match '(?i)\b(rm|unlink|del|erase|remove-item)\b|\bfind\b[^\n]*\s-delete\b|\bgit\s+rm\b'
$safeSingleDelete = $command -match '(?i)^\s*cmd(?:\.exe)?\s+/d\s+/c\s+del\s+(?:(?:/[fq])\s+)*(?:"[^"%!^&|<>()*?`$\[\]{}~#=]+"|[^\s"%!^&|<>()*?`$\[\]{}~#=]+)\s*$'
if ($hasDelete -and (-not $safeSingleDelete -or $command -match '(?:&&|[;&|><])')) {
    Emit-Decision "deny" "Only a standalone, non-recursive deletion command with one literal target is allowed."
    exit 0
}

if ($toolName -match '(?i)delete.?file|remove.?file' -or $safeSingleDelete) {
    Emit-Decision "ask" "Exact single-file deletion requires explicit user confirmation; directory and recursive deletion are prohibited."
    exit 0
}

$approval = @(
    '\b(npm|pnpm|yarn|bun)\s+(install|add|remove|update|upgrade)\b',
    '\b(pip|pip3|poetry|uv|conda)\s+(install|add|remove|sync|update)\b',
    '\b(cargo\s+add|go\s+get|dotnet\s+add\s+package)\b',
    '\b(apt|apt-get|yum|dnf|pacman|brew|choco|winget)\s+(install|remove|upgrade|update)\b',
    '\b(alembic\s+upgrade|flask\s+db\s+upgrade|manage\.py\s+migrate|prisma\s+migrate|sequelize[^\n]*db:migrate|knex[^\n]*migrate|rails\s+db:migrate)\b',
    '\b(terraform\s+(apply|destroy)|kubectl\s+(apply|delete|patch|replace)|helm\s+(install|upgrade|uninstall)|docker\s+(push|rm|rmi)|aws\s+[^\n]*(deploy|update|delete)|gcloud\s+[^\n]*(deploy|delete)|az\s+[^\n]*(create|update|delete))\b'
)
foreach ($pattern in $approval) {
    if ($combined -match $pattern) {
        Emit-Decision "ask" "Environment, dependency, migration, deployment, or external mutation requires explicit user confirmation."
        exit 0
    }
}

if ($toolName -match '(?i)edit|replace|create_file|write') {
    if ($combined -match '(^|[\\/])\.env(?:\.|$)|(^|[\\/])(?:credentials|secrets?)(?:\.|[\\/]|$)|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock|(^|[\\/])(?:Dockerfile|docker-compose[^\\/]*\.ya?ml)$|(^|[\\/])(?:\.github[\\/]workflows|k8s|kubernetes|terraform|migrations?)([\\/]|$)') {
        Emit-Decision "ask" "Sensitive configuration, lockfile, infrastructure, migration, or credential-related edit requires explicit confirmation."
        exit 0
    }
}

Write-Output '{"continue":true}'
