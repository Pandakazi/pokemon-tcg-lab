param(
    [ValidateSet('Start','Stop','Restart')][string]$Action = 'Start',
    [string]$SourceRepository = 'C:\Users\Mike\Documents\pokemon-tcg-lab',
    [int]$ApiPort = 8003,
    [int]$WebPort = 5175
)
$ErrorActionPreference = 'Stop'
$phase5Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$qaRoot = Join-Path $phase5Root '.cache\manual-qa'
New-Item -ItemType Directory -Path $qaRoot -Force | Out-Null
$processFile = Join-Path $qaRoot 'processes.json'

if (Test-Path -LiteralPath $processFile) {
    $recorded = Get-Content -LiteralPath $processFile -Raw | ConvertFrom-Json
    $running = @()
    foreach ($taskPid in @($recorded.apiPid, $recorded.webPid)) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$taskPid"
        if ($process) {
            $expectedRoot = $phase5Root.Replace('\','/').ToLowerInvariant()
            $actualCommand = ([string]$process.CommandLine).Replace('\','/').ToLowerInvariant()
            if (-not $actualCommand.Contains($expectedRoot)) {
                throw "Recorded process $taskPid no longer belongs to this QA checkout. No process was stopped."
            }
            $running += $process
        }
    }
    if ($Action -eq 'Start' -and $running.Count -eq 2) {
        Write-Output "Phase 5 QA is already running: http://127.0.0.1:$($recorded.webPort)/deck-builder"
        return
    }
    foreach ($process in $running) { Stop-Process -Id $process.ProcessId }
    Remove-Item -LiteralPath $processFile
}
if ($Action -eq 'Stop') { Write-Output 'Phase 5 QA stopped. Stored QA decks are preserved.'; return }
foreach ($port in @($ApiPort,$WebPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Choose another port; no unrelated server was stopped."
    }
}
$python = Join-Path $SourceRepository '.venv\Scripts\python.exe'
$vite = Join-Path $phase5Root 'web\node_modules\vite\bin\vite.js'
if (-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $vite)) {
    throw 'The existing Python environment or this checkout''s npm dependencies are missing.'
}
$collectionCopy = Join-Path $qaRoot 'user-state.sqlite3'
if (-not (Test-Path -LiteralPath $collectionCopy)) {
    # SQLite backup safely snapshots collection state even if the certified app
    # is open. It never writes to the source collection database.
    $sourceState = Join-Path $SourceRepository 'data\user-state.sqlite3'
    if (Test-Path -LiteralPath $sourceState) {
        & $python -c 'import sqlite3,sys; from pathlib import Path; source=sqlite3.connect(Path(sys.argv[1]).resolve().as_uri()+"?mode=ro",uri=True); target=sqlite3.connect(sys.argv[2]); source.backup(target); target.close(); source.close()' $sourceState $collectionCopy
        if ($LASTEXITCODE -ne 0) { throw 'Unable to snapshot collection for QA.' }
    }
}
$env:TCG_CARDS_DB_PATH = Join-Path $SourceRepository 'data\cards.sqlite3'
$env:POKELAB_COMPETITIVE_DB_PATH = Join-Path $SourceRepository 'data\competitive.sqlite3'
$env:POKELAB_USER_DB_PATH = $collectionCopy
$env:POKELAB_DECK_DB_PATH = Join-Path $qaRoot 'deck-workspace.sqlite3'
$env:PYTHONPATH = Join-Path $phase5Root 'src'
$revision = git -c "safe.directory=$($phase5Root.Replace('\','/'))" -C $phase5Root rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or -not $revision) { throw 'Unable to identify the current QA commit.' }
$env:POKELAB_BUILD_REVISION = $revision.Trim()
$env:POKELAB_API_TARGET = "http://127.0.0.1:$ApiPort"
$apiArgs = @('-m','uvicorn','pokelab.api:app','--app-dir',('"'+(Join-Path $phase5Root 'src')+'"'),'--host','127.0.0.1','--port',"$ApiPort")
$apiProcess = Start-Process -FilePath $python -ArgumentList $apiArgs -WorkingDirectory $phase5Root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $qaRoot 'api.out.log') -RedirectStandardError (Join-Path $qaRoot 'api.err.log')
try {
    $webProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @(('"'+$vite+'"'),'--host','127.0.0.1','--port',"$WebPort",'--strictPort') -WorkingDirectory (Join-Path $phase5Root 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $qaRoot 'web.out.log') -RedirectStandardError (Join-Path $qaRoot 'web.err.log')
    @{apiPid=$apiProcess.Id;webPid=$webProcess.Id;apiPort=$ApiPort;webPort=$WebPort;root=$phase5Root} | ConvertTo-Json | Set-Content -LiteralPath $processFile
} catch { Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue; throw }
Write-Output "Phase 5 QA: http://127.0.0.1:$WebPort/deck-builder"
Write-Output "Uses an isolated collection snapshot and persistent QA decks in $qaRoot"
Write-Output 'After Restart, hard-refresh the browser with Ctrl+Shift+R.'
