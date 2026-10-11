param([string]$CardsDatabase, [string]$CompetitiveDatabase, [switch]$Offline)
$ErrorActionPreference = 'Stop'
try {
    . (Join-Path $PSScriptRoot 'scripts/Local-Web.ps1')
    Assert-LocalTools
    $python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        $candidates = @()
        if (Get-Command py.exe -ErrorAction SilentlyContinue) { $candidates += ,@('py.exe','-3') }
        if (Get-Command python.exe -ErrorAction SilentlyContinue) { $candidates += ,@('python.exe') }
        $found = $false
        foreach ($candidate in $candidates) {
            $command = $candidate[0]; $prefix = @($candidate | Select-Object -Skip 1)
            & $command @prefix -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (4,0) else 1)' 2>$null
            if ($LASTEXITCODE -eq 0) {
                & $command @prefix -m venv (Join-Path $PSScriptRoot '.venv')
                if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. Reinstall Python with pip/venv, then rerun setup.' }
                $found = $true; break
            }
        }
        if (-not $found) { throw 'Python 3.11 or newer is required. Install Python from python.org (enable Add Python to PATH), reopen PowerShell, then rerun setup.' }
    }
    & $python -c 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] < (4,0) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'The local Python environment needs Python 3.11 or newer.' }
    Push-Location $PSScriptRoot
    try {
        $stamp = Join-Path $PSScriptRoot '.venv/pokelab-web-install.sha256'
        $expected = (Get-FileHash (Join-Path $PSScriptRoot 'pyproject.toml')).Hash
        & $python -c 'import fastapi,uvicorn,httpx,mcp,dotenv,pokelab.api' 2>$null
        $installed = $LASTEXITCODE -eq 0
        if (-not $installed -or -not (Test-Path $stamp) -or (Get-Content $stamp -Raw).Trim() -ne $expected) {
            $pipArgs = @('-m','pip','--disable-pip-version-check','install','-e','.[web]')
            if ($Offline) { $pipArgs += @('--no-index','--no-build-isolation') }
            & $python @pipArgs
            if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed. Check the installer message and your internet connection, then rerun setup.' }
            Set-Content -LiteralPath $stamp -Value $expected
        }
        & $python -m pip check
        if ($LASTEXITCODE -ne 0) { throw 'Python dependencies are inconsistent. Rerun setup after fixing the installer message above.' }
        $webStamp = Join-Path $PSScriptRoot 'web/node_modules/.pokelab-install.sha256'
        $webExpected = (Get-FileHash (Join-Path $PSScriptRoot 'web/package-lock.json')).Hash
        if (-not (Test-Path (Join-Path $PSScriptRoot 'web/node_modules/vite/bin/vite.js')) -or -not (Test-Path $webStamp) -or (Get-Content $webStamp -Raw).Trim() -ne $webExpected) {
            $npmArgs = @('--prefix','web','ci','--no-audit','--no-fund')
            if ($Offline) { $npmArgs += '--offline' }
            & npm.cmd @npmArgs
            if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed. Check your internet connection and rerun setup.' }
            Set-Content -LiteralPath $webStamp -Value $webExpected
        }
        $bootstrapArgs = @((Join-Path $PSScriptRoot 'scripts/bootstrap-web.py'))
        if ($CardsDatabase) { $bootstrapArgs += @('--cards-database',$CardsDatabase) }
        if ($CompetitiveDatabase) { $bootstrapArgs += @('--competitive-database',$CompetitiveDatabase) }
        if ($Offline) { $bootstrapArgs += '--offline' }
        & $python @bootstrapArgs
        if ($LASTEXITCODE -ne 0) { throw 'Local data preparation failed. See the message above, then rerun setup. Saved collections and decks are preserved.' }
        Write-Host 'Setup complete! Run .\start.ps1 to open PokeLab.'
        Write-Host 'Then open Settings > Agent Settings, paste your Gemini API key, and click Test & Apply.'
    } finally { Pop-Location }
} catch { Write-Host "Setup could not finish: $($_.Exception.Message)"; exit 1 }
