# Restart only this checkout's BE, FE and ARQ worker once per invocation.
[CmdletBinding(SupportsShouldProcess)]
param()
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'dev-processes.ps1')
$DevRepoDir = Split-Path $PSScriptRoot -Parent
$DevBackendDir = Join-Path $DevRepoDir 'backend'
$DevPythonExe = Join-Path $DevBackendDir '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $DevPythonExe)) { throw 'Backend virtual environment missing.' }
$RootBytes = [System.Text.Encoding]::UTF8.GetBytes($DevRepoDir.ToLowerInvariant())
$Hasher = [System.Security.Cryptography.SHA256]::Create()
try { $RootHash = ([BitConverter]::ToString($Hasher.ComputeHash($RootBytes))).Replace('-', '') } finally { $Hasher.Dispose() }
$DevMutex = [System.Threading.Mutex]::new($false, "Local\QNU.Dev.$RootHash")
$HasDevMutex = $false
try {
    try { $HasDevMutex = $DevMutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $HasDevMutex = $true }
    if (-not $HasDevMutex) { throw 'Another dev restart is already running for this checkout.' }
    $Inventory = @(Get-CimInstance Win32_Process -ErrorAction Stop)
    $Roots = @($Inventory | Where-Object { Get-RepoDevRole $_ $DevRepoDir })
    $TargetMap = @{}
    foreach ($Root in $Roots) {
        foreach ($Entry in @(Get-DevProcessTree $Root $Inventory)) { $TargetMap[[int]$Entry.ProcessId] = $Entry }
    }
    $Targets = @($TargetMap.Values)
    $Listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 3000, 8001 })
    Assert-DevPortsOwned $Listeners $Targets
    Write-Host 'Dev restart: Backend 8001, Frontend 3000, ARQ worker. Docker/DB are kept running.' -ForegroundColor Cyan
    Write-Host 'Running dev requests/jobs may be interrupted; unfinished jobs use the existing recovery mechanism.' -ForegroundColor Yellow
    foreach ($Root in $Roots) { Write-Host "  $(Get-RepoDevRole $Root $DevRepoDir): PID $($Root.ProcessId)" }
    if (-not $PSCmdlet.ShouldProcess($DevRepoDir, 'Restart Backend, Frontend and Worker')) { return }
    Push-Location -LiteralPath $DevBackendDir
    try {
        & $DevPythonExe -m app.cli db ensure-ready
        if ($LASTEXITCODE -ne 0) { throw 'Database is not ready; existing dev services were not stopped.' }
    } finally { Pop-Location }
    # Stop verified roots first so reloaders cannot respawn children during shutdown.
    foreach ($Root in $Roots) { Stop-VerifiedDevProcess $Root }
    foreach ($Entry in $Targets) {
        if ($Entry.ProcessId -notin @($Roots.ProcessId)) { Stop-VerifiedDevProcess $Entry -IgnoreChangedIdentity }
    }
    $ReleaseDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $Remaining = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object { $_.LocalPort -in 3000, 8001 })
        $AliveTargets = @($Targets | Where-Object {
            $Live = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.ProcessId)" -ErrorAction Stop
            $Live -and $Live.CreationDate -eq $_.CreationDate
        })
        if (-not $Remaining -and -not $AliveTargets) { break }
        if ([DateTime]::UtcNow -ge $ReleaseDeadline) { throw 'Old dev services did not fully stop; no new services were launched.' }
        Start-Sleep -Milliseconds 250
    } while ($true)
    $ServiceScript = Join-Path $PSScriptRoot 'start-dev-service.ps1'
    foreach ($Service in 'Backend', 'Frontend', 'Worker') {
        Write-Host "Starting $Service..." -ForegroundColor Green
        Start-Process powershell -WindowStyle Normal -WorkingDirectory $DevRepoDir -ArgumentList '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$ServiceScript`"", '-Service', $Service | Out-Null
    }
    Write-Host 'Backend, Frontend, and Worker terminals opened. Check terminals for startup readiness.' -ForegroundColor Green
} finally {
    if ($HasDevMutex) { $DevMutex.ReleaseMutex() }
    $DevMutex.Dispose()
}
