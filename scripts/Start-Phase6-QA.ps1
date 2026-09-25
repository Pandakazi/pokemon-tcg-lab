param(
    [ValidateSet('Start','Stop','Restart')][string]$Action = 'Restart',
    [string]$SourceRepository = 'C:\Users\Mike\Documents\pokemon-tcg-lab',
    [int]$ApiPort = 8003,
    [int]$WebPort = 5175
)
# Reuse the guarded process lifecycle and existing persistent QA databases.
# Restart is the default so an earlier API can never be mistaken for Phase 6.
& (Join-Path $PSScriptRoot 'Start-Phase5-QA.ps1') -Action $Action -SourceRepository $SourceRepository -ApiPort $ApiPort -WebPort $WebPort -PhaseLabel 'Phase 6'
if ($Action -ne 'Stop') {
    Write-Output 'Open Card Detail > Competitive research > an archetype or Explore decks. Hard-refresh with Ctrl+Shift+R.'
    Write-Output 'Compare /api/v1/deck-workspace runtime_revision with git rev-parse HEAD before PM QA.'
}
