param(
    [string]$Model,
    [ValidateSet("strict", "adaptive")]
    [string]$Leader,
    [switch]$SkipExtension,
    [switch]$UpdateExtension,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $python = @("py", "-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = @("python")
} else {
    throw "Python 3.9+ is required."
}

$argsList = @("$ScriptDir\scripts\install.py")
if ($Model) { $argsList += @("--model", $Model) }
if ($Leader) { $argsList += @("--leader", $Leader) }
if ($SkipExtension) { $argsList += "--skip-extension" }
if ($UpdateExtension) { $argsList += "--update-extension" }
if ($DryRun) { $argsList += "--dry-run" }

if ($python.Count -eq 2) {
    & $python[0] $python[1] @argsList
} else {
    & $python[0] @argsList
}
exit $LASTEXITCODE
