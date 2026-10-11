# Windows PowerShell 5.1 compatible. Compose the existing uvicorn/Vite launch path.
$localRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$localState = Join-Path $localRoot '.cache/local-web'
$localProcessFile = Join-Path $localState 'processes.json'
$localApiPort = 8001
$localWebPort = 5173

function Assert-LocalTools {
    if (-not (Get-Command node.exe -ErrorAction SilentlyContinue) -or -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
        throw 'Node.js is required. Install Node.js LTS from nodejs.org, reopen PowerShell, then rerun setup.'
    }
    & node.exe -e "const [a,b]=process.versions.node.split('.').map(Number); process.exit((a===22 && b>=12)||a>=24?0:1)"
    if ($LASTEXITCODE -ne 0) { throw 'Install Node.js LTS (22.12+ or 24+), reopen PowerShell, then rerun setup.' }
}

function Get-LocalTasks {
    if (-not (Test-Path -LiteralPath $localProcessFile)) { return @() }
    $record = Get-Content -LiteralPath $localProcessFile -Raw | ConvertFrom-Json
    if ($record.root -ne $localRoot) { throw 'The startup record belongs to another folder. No process was stopped.' }
    $result = @()
    foreach ($entry in @($record.api, $record.web)) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($entry.pid)"
        if ($process) {
            $command = ([string]$process.CommandLine).Replace('\','/').ToLowerInvariant()
            if ($process.CreationDate.ToUniversalTime() -ne ([datetime]$entry.created).ToUniversalTime() -or -not $command.Contains($localRoot.Replace('\','/').ToLowerInvariant())) {
                throw "Recorded process $($entry.pid) no longer belongs to this launch. No process was stopped."
            }
            $result += $process
        }
    }
    return $result
}

function Stop-LocalTasks {
    param([object[]]$Tasks)
    $tasks = @($Tasks)
    # Windows venv python.exe is a redirector with a child Python process.
    # Stop the owned tree so the actual API listener cannot be orphaned.
    $queue = @($tasks)
    while ($queue.Count) {
        $parent = $queue[0]; $queue = @($queue | Select-Object -Skip 1)
        foreach ($child in @(Get-CimInstance Win32_Process -Filter "ParentProcessId=$($parent.ProcessId)")) {
            # Windows owns the hidden console host; it exits with its console.
            if ($child.ExecutablePath -eq (Join-Path $env:SystemRoot 'System32/conhost.exe')) { continue }
            $command = ([string]$child.CommandLine).Replace('\','/').ToLowerInvariant()
            if (-not $command.Contains($localRoot.Replace('\','/').ToLowerInvariant())) {
                throw "Child process $($child.ProcessId) could not be identified as this checkout. No process was stopped."
            }
            $tasks += $child; $queue += $child
        }
    }
    [array]::Reverse($tasks)
    foreach ($task in $tasks) { Stop-Process -Id $task.ProcessId -ErrorAction SilentlyContinue }
    if (Test-Path -LiteralPath $localProcessFile) { Remove-Item -LiteralPath $localProcessFile }
    $deadline = (Get-Date).AddSeconds(10)
    while (@($tasks | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }).Count) {
        if ((Get-Date) -gt $deadline) { throw 'The previous server did not stop within 10 seconds. Close it and run start again.' }
        Start-Sleep -Milliseconds 200
    }
}

function Stop-LocalWeb {
    $tasks = @(Get-LocalTasks) # Validate every PID before stopping any.
    Stop-LocalTasks -Tasks $tasks
}

function Test-LocalHealth {
    try {
        $status = Invoke-RestMethod "http://127.0.0.1:$localApiPort/api/v1/status" -TimeoutSec 2
        $web = Invoke-WebRequest "http://127.0.0.1:$localWebPort/" -UseBasicParsing -TimeoutSec 2
        $proxy = Invoke-RestMethod "http://127.0.0.1:$localWebPort/api/v1/status" -TimeoutSec 2
        # ASCII identity field also works with PowerShell 5.1's JSON decoding.
        return ($status.ready -and $status.source -eq 'TCGdex SQLite' -and $status.cards -gt 0 -and $proxy.ready -and $proxy.source -eq $status.source -and $web.StatusCode -eq 200)
    } catch { return $false }
}

function Start-LocalWeb {
    param([switch]$NoBrowser)
    Assert-LocalTools
    $python = Join-Path $localRoot '.venv/Scripts/python.exe'
    $vite = Join-Path $localRoot 'web/node_modules/vite/bin/vite.js'
    if (-not (Test-Path $python) -or -not (Test-Path $vite) -or -not (Test-Path (Join-Path $localRoot 'data/cards.sqlite3'))) {
        throw 'Setup is required first. Run .\setup.ps1, then .\start.ps1.'
    }
    New-Item -ItemType Directory -Path $localState -Force | Out-Null
    # Prevent two simultaneous starts from spawning duplicate servers.
    try { $lock = [System.IO.File]::Open((Join-Path $localState 'launch.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch { throw 'Another start is in progress. Wait for it to finish, then try again.' }
    try {
        $tasks = @(Get-LocalTasks)
        if ($tasks.Count -eq 2 -and (Test-LocalHealth)) {
            Write-Host 'PokeLab is already running.'
        } else {
            Stop-LocalWeb # Separate Stop, then Start. Never the interactive QA Restart path.
            foreach ($port in @($localApiPort,$localWebPort)) {
                if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
                    throw "Port $port is already in use by another program. Close that program, then run start again. No unrelated process was stopped."
                }
            }
            & $python (Join-Path $localRoot 'scripts/bootstrap-web.py') --offline
            if ($LASTEXITCODE -ne 0) { throw 'Local database/index preparation failed. Rerun .\setup.ps1.' }
            $names = @('TCG_CARDS_DB_PATH','POKELAB_USER_DB_PATH','POKELAB_DECK_DB_PATH','POKELAB_COMPETITIVE_DB_PATH','PYTHONPATH','POKELAB_API_TARGET','POKELAB_BUILD_REVISION')
            $previous = @{}
            foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
            $api = $null; $web = $null
            try {
                $env:TCG_CARDS_DB_PATH = Join-Path $localRoot 'data/cards.sqlite3'
                $env:POKELAB_USER_DB_PATH = Join-Path $localRoot 'data/user-state.sqlite3'
                $env:POKELAB_DECK_DB_PATH = Join-Path $localRoot 'data/deck-workspace.sqlite3'
                $env:POKELAB_COMPETITIVE_DB_PATH = Join-Path $localRoot 'data/competitive.sqlite3'
                $env:PYTHONPATH = Join-Path $localRoot 'src'
                $env:POKELAB_API_TARGET = "http://127.0.0.1:$localApiPort"
                $env:POKELAB_BUILD_REVISION = 'local-preview'
                if (Get-Command git -ErrorAction SilentlyContinue) {
                    $revision = & git -C $localRoot rev-parse HEAD 2>$null
                    if ($LASTEXITCODE -eq 0) { $env:POKELAB_BUILD_REVISION = "$revision".Trim() }
                }
                $api = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','pokelab.api:app','--app-dir',('"'+(Join-Path $localRoot 'src')+'"'),'--host','127.0.0.1','--port',"$localApiPort") -WorkingDirectory $localRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localState 'api.out.log') -RedirectStandardError (Join-Path $localState 'api.err.log')
                $web = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @(('"'+$vite+'"'),'--host','127.0.0.1','--port',"$localWebPort",'--strictPort') -WorkingDirectory (Join-Path $localRoot 'web') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $localState 'web.out.log') -RedirectStandardError (Join-Path $localState 'web.err.log')
                $apiInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($api.Id)"
                $webInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$($web.Id)"
                @{root=$localRoot;api=@{pid=$api.Id;created=$apiInfo.CreationDate.ToUniversalTime().ToString('o')};web=@{pid=$web.Id;created=$webInfo.CreationDate.ToUniversalTime().ToString('o')}} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $localProcessFile
                $deadline = (Get-Date).AddSeconds(60)
                while (-not (Test-LocalHealth)) {
                    if ($api.HasExited -or $web.HasExited -or (Get-Date) -gt $deadline) {
                        throw "Servers did not become ready within 60 seconds. See logs in $localState, then rerun setup/start."
                    }
                    Start-Sleep -Milliseconds 300
                }
                foreach ($port in @($localApiPort,$localWebPort)) {
                    if (-not (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)) { throw "Port $port is not listening." }
                }
            } catch {
                if (Test-Path $localProcessFile) { Stop-LocalWeb }
                else {
                    $owned = @()
                    foreach ($process in @($api,$web)) {
                        if ($process -and -not $process.HasExited) {
                            $owned += Get-CimInstance Win32_Process -Filter "ProcessId=$($process.Id)"
                        }
                    }
                    Stop-LocalTasks -Tasks $owned
                }
                throw
            } finally {
                foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
            }
        }
        $url = "http://127.0.0.1:$localWebPort/"
        Write-Host "PokeLab ready: $url (API: http://127.0.0.1:$localApiPort)"
        Write-Host 'Stop: .\stop.ps1    Restart: run .\stop.ps1, then .\start.ps1'
        if (-not $NoBrowser) {
            try { Start-Process $url } catch { Write-Host "Open $url in your browser." }
        }
    } finally { $lock.Dispose() }
}
