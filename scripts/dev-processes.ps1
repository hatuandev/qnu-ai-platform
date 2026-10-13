# Process ownership and identity checks shared by the local dev launcher.
function Get-RepoDevRole {
    param($Process, [string]$RepoRoot)
    $Root = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\', '/').Replace('\', '/').ToLowerInvariant() + '/'
    $Line = ([string]$Process.CommandLine).Replace('\', '/').ToLowerInvariant()
    $Executable = ([string]$Process.ExecutablePath).Replace('\', '/').ToLowerInvariant()
    $Name = ([string]$Process.Name).ToLowerInvariant()
    if (-not ($Line.Contains($Root) -or $Executable.StartsWith($Root))) { return $null }
    if ($Name -match '^powershell(?:\.exe)?$' -and $Line.Contains($Root + 'scripts/start-dev-service.ps1')) {
        if ($Line -match '-service\s+backend\b') { return 'Backend' }
        if ($Line -match '-service\s+frontend\b') { return 'Frontend' }
        if ($Line -match '-service\s+worker\b') { return 'Worker' }
    }
    if ($Name -match '^python(?:w)?(?:\.exe)?$') {
        if ($Line -match '-m\s+arq\s+app\.workers\.arq_worker\.workersettings\b') { return 'Worker' }
        if ($Line -match '-m\s+uvicorn\s+app\.main:app\b' -and $Line -match '--port\s+8001\b') { return 'Backend' }
    }
    if ($Name -match '^node(?:\.exe)?$' -and $Line.Contains($Root + 'frontend/node_modules/') -and $Line -match '/vite/(?:bin/)?vite(?:\.js)?\b') {
        return 'Frontend'
    }
    return $null
}

function Get-DevProcessTree {
    param($RootProcess, [object[]]$Inventory)
    $Queue = [System.Collections.Generic.Queue[object]]::new()
    $Seen = @{}
    $Queue.Enqueue($RootProcess)
    while ($Queue.Count -gt 0) {
        $Current = $Queue.Dequeue()
        if ($Seen.ContainsKey([int]$Current.ProcessId)) { continue }
        $Seen[[int]$Current.ProcessId] = $true
        $Current
        foreach ($Child in $Inventory) {
            if ($Child.ParentProcessId -eq $Current.ProcessId -and $Child.CreationDate -ge $Current.CreationDate) {
                $Queue.Enqueue($Child)
            }
        }
    }
}

function Assert-DevPortsOwned {
    param([object[]]$Listeners, [object[]]$Targets)
    $OwnedIds = @($Targets | ForEach-Object { [int]$_.ProcessId })
    foreach ($Listener in $Listeners) {
        if ([int]$Listener.OwningProcess -notin $OwnedIds) {
            throw "Port $($Listener.LocalPort) belongs to an unverified process (PID $($Listener.OwningProcess)). Nothing was stopped."
        }
    }
}

function Stop-VerifiedDevProcess {
    param($Expected, [switch]$IgnoreChangedIdentity)
    $Current = Get-CimInstance Win32_Process -Filter "ProcessId = $($Expected.ProcessId)" -ErrorAction Stop
    if (-not $Current) { return }
    if ($Current.CreationDate -ne $Expected.CreationDate -or $Current.CommandLine -ne $Expected.CommandLine) {
        if ($IgnoreChangedIdentity) {
            Write-Warning "Skipping descendant PID $($Expected.ProcessId): identity changed or process is closing."
            return
        }
        throw "PID $($Expected.ProcessId) changed identity; refusing to stop it."
    }
    try { Stop-Process -Id $Expected.ProcessId -ErrorAction Stop }
    catch {
        $AfterStop = Get-CimInstance Win32_Process -Filter "ProcessId = $($Expected.ProcessId)" -ErrorAction Stop
        if (-not $AfterStop -or $AfterStop.CreationDate -ne $Expected.CreationDate) { return }
        throw
    }
}
