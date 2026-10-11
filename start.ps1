param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'scripts/Local-Web.ps1')
    Start-LocalWeb -NoBrowser:$NoBrowser
} catch { Write-Host "PokeLab could not start: $($_.Exception.Message)"; exit 1 }
