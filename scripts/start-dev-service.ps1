# Visible service terminals launched with an absolute script path for ownership checks.
param([ValidateSet('Backend', 'Frontend', 'Worker')][string]$Service)
$ErrorActionPreference = 'Stop'
$ServiceRepoDir = Split-Path $PSScriptRoot -Parent
if ($Service -eq 'Backend') {
    $host.UI.RawUI.WindowTitle = 'QNU Backend API (Port 8001)'
    Set-Location -LiteralPath (Join-Path $ServiceRepoDir 'backend')
    & (Join-Path $ServiceRepoDir 'backend\.venv\Scripts\python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
} elseif ($Service -eq 'Frontend') {
    $host.UI.RawUI.WindowTitle = 'QNU Frontend Studio (Port 3000)'
    Set-Location -LiteralPath (Join-Path $ServiceRepoDir 'frontend')
    npm run dev -- --strictPort
} elseif ($Service -eq 'Worker') {
    $host.UI.RawUI.WindowTitle = 'QNU ARQ Worker'
    Set-Location -LiteralPath (Join-Path $ServiceRepoDir 'backend')
    & (Join-Path $ServiceRepoDir 'backend\.venv\Scripts\python.exe') -m arq app.workers.arq_worker.WorkerSettings
}
