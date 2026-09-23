param([int]$Port = 0, [switch]$Check, [switch]$Repair)
# Compatible with Windows PowerShell 5.1. No policy or administrator changes.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$probe = 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (4,0) else 1)'
$candidates = @()
$localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (Test-Path -LiteralPath $localPython) { $candidates += ,@($localPython) }
if (Get-Command py -ErrorAction SilentlyContinue) { $candidates += ,@('py', '-3') }
foreach ($name in @('python', 'python3')) {
    if (Get-Command $name -ErrorAction SilentlyContinue) { $candidates += ,@($name) }
}
# Optional convenience on Codex computers; not required for distribution.
$bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (Test-Path -LiteralPath $bundledPython) { $candidates += ,@($bundledPython) }
foreach ($candidate in $candidates) {
    $command = $candidate[0]
    $prefix = @($candidate | Select-Object -Skip 1)
    try {
        $ErrorActionPreference = 'Continue'
        & $command @prefix -c $probe 2>$null
        $probeExit = $LASTEXITCODE
        $ErrorActionPreference = 'Stop'
        if ($probeExit -ne 0) { continue }
        $launchArgs = @((Join-Path $PSScriptRoot 'scripts/launcher.py'))
        if ($Port -ne 0) { $launchArgs += @('--port', "$Port") }
        if ($Check) { $launchArgs += '--check' }
        if ($Repair) { $launchArgs += '--repair' }
        & $command @prefix @launchArgs
        exit $LASTEXITCODE
    } catch {
        $ErrorActionPreference = 'Stop'
        Write-Host "Could not run Python: $($_.Exception.Message)"
        Write-Host 'See Troubleshooting in README.md. Your saved decks have not been deleted.'
        exit 1
    }
}
Write-Host 'Python 3.11 or newer was not found.'
Write-Host 'Install Python 3 from https://www.python.org/downloads/ (enable Add Python to PATH if offered).'
Write-Host 'Close this PowerShell window, open it again in this folder, and run .\Run-Local.ps1.'
exit 1
