# Start a local ARQ worker without a visible helper window; keep logs for diagnosis.
$ErrorActionPreference = "Stop"
$WorkerRepoDir = Split-Path $PSScriptRoot -Parent
$WorkerBackendDir = Join-Path $WorkerRepoDir "backend"
$WorkerPythonExe = Join-Path $WorkerBackendDir ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $WorkerPythonExe)) {
    throw "Backend virtual environment missing: $WorkerPythonExe"
}
$WorkerLogDir = Join-Path $WorkerBackendDir "storage\worker_logs"
New-Item -ItemType Directory -Path $WorkerLogDir -Force | Out-Null
$WorkerStatePath = Join-Path $WorkerLogDir "local-worker.json"
if (Test-Path -LiteralPath $WorkerStatePath) {
    $WorkerState = Get-Content -LiteralPath $WorkerStatePath -Raw | ConvertFrom-Json
    $ExistingWorker = Get-Process -Id $WorkerState.pid -ErrorAction SilentlyContinue
    if ($ExistingWorker -and $ExistingWorker.StartTime.ToUniversalTime().Ticks.ToString() -eq $WorkerState.startTicks) {
        Write-Host "Worker already running (PID $($ExistingWorker.Id)). Logs: $WorkerLogDir"
        return
    }
}
$WorkerRunId = [guid]::NewGuid().ToString("N")
$WorkerStdout = Join-Path $WorkerLogDir "$WorkerRunId.stdout.log"
$WorkerStderr = Join-Path $WorkerLogDir "$WorkerRunId.stderr.log"
$WorkerProcess = Start-Process -FilePath $WorkerPythonExe -WorkingDirectory $WorkerBackendDir `
    -ArgumentList "-m", "arq", "app.workers.arq_worker.WorkerSettings" `
    -WindowStyle Hidden -RedirectStandardOutput $WorkerStdout -RedirectStandardError $WorkerStderr -PassThru
$WorkerState = @{ pid = $WorkerProcess.Id; startTicks = $WorkerProcess.StartTime.ToUniversalTime().Ticks.ToString() }
[System.IO.File]::WriteAllText($WorkerStatePath, ($WorkerState | ConvertTo-Json), [System.Text.UTF8Encoding]::new($false))
Write-Host "Worker started (PID $($WorkerProcess.Id)). Logs: $WorkerLogDir"
