$ErrorActionPreference = "SilentlyContinue"
$raw = [Console]::In.ReadToEnd()
try { $data = $raw | ConvertFrom-Json } catch { Write-Output '{"continue":true}'; exit 0 }

$toolName = [string]$data.tool_name
$command = [string]$data.tool_input.command

function Get-PathText($value) {
    if ($null -eq $value) { return '' }
    $parts = @()
    foreach ($property in $value.PSObject.Properties) {
        $name = $property.Name.ToLowerInvariant()
        $item = $property.Value
        if ($name -in @('path', 'file', 'file_path', 'target', 'target_path', 'uri', 'notebook_path') -or $name.EndsWith('_path')) {
            $parts += [string]$item
        } elseif ($item -is [System.Collections.IEnumerable] -and $item -isnot [string]) {
            foreach ($entry in $item) {
                $nested = Get-PathText $entry
                if ($nested) { $parts += $nested }
            }
        } elseif ($null -ne $item -and $item -isnot [string] -and $item.PSObject.Properties.Count -gt 0) {
            $nested = Get-PathText $item
            if ($nested) { $parts += $nested }
        }
    }
    return ($parts -join ' ')
}

$pathText = Get-PathText $data.tool_input

function Emit-Decision([string]$decision, [string]$reason) {
    $obj = @{ hookSpecificOutput = @{ permissionDecision = $decision; permissionDecisionReason = $reason } }
    $obj | ConvertTo-Json -Depth 5 -Compress
}

if ($toolName -match '(?i)(^|[./:_-])github([./:_-]|$)') {
    $action = ''
    if ($toolName -match '(?i)github[./:_-]+(.+)$') {
        $action = $Matches[1].ToLowerInvariant()
    }
    $readOnlyPrefixes = @('get', 'list', 'search', 'read', 'view', 'fetch', 'compare', 'diff', 'status', 'download')
    $isReadOnly = $false
    foreach ($prefix in $readOnlyPrefixes) {
        if ($action.StartsWith($prefix)) { $isReadOnly = $true; break }
    }
    if (-not $isReadOnly) {
        Emit-Decision "ask" "GitHub write or unknown action requires explicit user confirmation."
        exit 0
    }
}

$hardDeny = @(
    '\bgit\s+(commit|push|pull|merge|rebase|reset|revert|cherry-pick|switch|checkout|clean|stash|tag)\b',
    '\bgit\s+branch\s+(-d|-D|-m|-M|--delete|--move)\b'
)
foreach ($pattern in $hardDeny) {
    if ($command -match $pattern) {
        Emit-Decision "deny" "Destructive or Git-writing operation blocked by the Leader security policy."
        exit 0
    }
}

$hasDelete = $command -match '(?i)\b(rm|unlink|del|erase|remove-item|rmdir|rd)\b|\bfind\b[^\n]*\s-delete\b|\bgit\s+rm\b'
$safeDelete = $command -match '(?i)^\s*(?:(?:cmd(?:\.exe)?\s+(?:/d\s+)?/c\s+)?del\s+(?:(?:/[fqs])\s+)*(?:"[^"%!^&|<>()*?`$\[\]{}~#=]+"|[^\s"%!^&|<>()*?`$\[\]{}~#=]+)(?:\s+(?:"[^"%!^&|<>()*?`$\[\]{}~#=]+"|[^\s"%!^&|<>()*?`$\[\]{}~#=]+))*|(?:cmd(?:\.exe)?\s+(?:/d\s+)?/c\s+)?(?:rd|rmdir)\s+(?:(?:/[sq])\s+)*(?:"[^"%!^&|<>()*?`$\[\]{}~#=]+"|[^\s"%!^&|<>()*?`$\[\]{}~#=]+)(?:\s+(?:"[^"%!^&|<>()*?`$\[\]{}~#=]+"|[^\s"%!^&|<>()*?`$\[\]{}~#=]+))*|(?:rm|unlink|remove-item)\b[^;&|><*?`$\[\]{}~#=]+)\s*$'
if ($hasDelete -and (-not $safeDelete -or $command -match '(?:&&|[;&|><])')) {
    Emit-Decision "deny" "Deletion is allowed only as one standalone command with literal, non-expanded targets."
    exit 0
}

if ($toolName -match '(?i)delete.?file|remove.?file' -or $safeDelete) {
    Emit-Decision "ask" "This deletion plan requires one explicit confirmation for the current command; approval does not carry to later commands."
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
    if ($command -match $pattern) {
        Emit-Decision "ask" "Environment, dependency, migration, deployment, or external mutation requires explicit user confirmation."
        exit 0
    }
}

if ($toolName -match '(?i)edit|replace|create_file|write') {
    if ($pathText -match '(^|[\\/])\.env(?:\.|$)|(^|[\\/])(?:credentials|secrets?)(?:\.|[\\/]|$)|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|poetry\.lock|uv\.lock|(^|[\\/])(?:Dockerfile|docker-compose[^\\/]*\.ya?ml)$|(^|[\\/])(?:\.github[\\/]workflows|k8s|kubernetes|terraform|migrations?)([\\/]|$)') {
        Emit-Decision "ask" "Sensitive configuration, lockfile, infrastructure, migration, or credential-related edit requires explicit confirmation."
        exit 0
    }
}

Write-Output '{"continue":true}'
