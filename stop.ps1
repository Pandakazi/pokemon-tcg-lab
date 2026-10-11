$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'scripts/Local-Web.ps1')
    Stop-LocalWeb
    Write-Host 'PokeLab stopped. Your saved collection and decks are preserved.'
} catch { Write-Host "PokeLab could not stop: $($_.Exception.Message)"; exit 1 }
