# Dependency-free regression checks; never stop a real process.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'dev-processes.ps1')
function Assert-DevTest {
    param([bool]$Condition, [string]$Description)
    if (-not $Condition) { throw "FAILED: $Description" }
}
function New-TestDevProcess {
    param([int]$Number, [int]$Parent, [string]$Name, [string]$Line, [datetime]$Created)
    [pscustomobject]@{ ProcessId = $Number; ParentProcessId = $Parent; Name = $Name; CommandLine = $Line; CreationDate = $Created; ExecutablePath = '' }
}
$TestRepoRoot = 'D:\Projects\QNU Repo'
$TestCreated = [datetime]'2026-10-12T12:00:00Z'
$Backend = New-TestDevProcess 101 1 'python.exe' '"D:\Projects\QNU Repo\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8001 --reload' $TestCreated
$Worker = New-TestDevProcess 102 1 'python.exe' '"D:\Projects\QNU Repo\backend\.venv\Scripts\python.exe" -m arq app.workers.arq_worker.WorkerSettings' $TestCreated
$Frontend = New-TestDevProcess 103 1 'node.exe' 'node "D:\Projects\QNU Repo\frontend\node_modules\vite\bin\vite.js"' $TestCreated
$Foreign = New-TestDevProcess 104 1 'python.exe' '"D:\Projects\QNU Repo-other\backend\python.exe" -m uvicorn app.main:app --port 8001' $TestCreated
$Editor = New-TestDevProcess 105 1 'Code.exe' 'code "D:\Projects\QNU Repo"' $TestCreated
$Terminal = New-TestDevProcess 106 1 'powershell.exe' '-NoExit -File "D:\Projects\QNU Repo\scripts\start-dev-service.ps1" -Service Frontend' $TestCreated
$WorkerTerminal = New-TestDevProcess 107 1 'powershell.exe' '-NoExit -File "D:\Projects\QNU Repo\scripts\start-dev-service.ps1" -Service Worker' $TestCreated
Assert-DevTest ((Get-RepoDevRole $Backend $TestRepoRoot) -eq 'Backend') 'backend owner'
Assert-DevTest ((Get-RepoDevRole $Worker $TestRepoRoot) -eq 'Worker') 'worker owner'
Assert-DevTest ((Get-RepoDevRole $Frontend $TestRepoRoot) -eq 'Frontend') 'frontend owner'
Assert-DevTest ((Get-RepoDevRole $Terminal $TestRepoRoot) -eq 'Frontend') 'managed terminal with spaces'
Assert-DevTest ((Get-RepoDevRole $WorkerTerminal $TestRepoRoot) -eq 'Worker') 'managed worker terminal with spaces'
Assert-DevTest (-not (Get-RepoDevRole $Foreign $TestRepoRoot)) 'similar repo name is not owned'
Assert-DevTest (-not (Get-RepoDevRole $Editor $TestRepoRoot)) 'editor must remain running'
$Child = New-TestDevProcess 201 101 'python.exe' 'multiprocessing.spawn' $TestCreated.AddSeconds(1)
$Grandchild = New-TestDevProcess 202 201 'python.exe' 'helper' $TestCreated.AddSeconds(2)
$ReusedParent = New-TestDevProcess 203 101 'node.exe' 'unrelated' $TestCreated.AddSeconds(-1)
$Tree = @(Get-DevProcessTree $Backend @($Backend, $Child, $Grandchild, $ReusedParent, $Editor))
Assert-DevTest ($Tree.Count -eq 3 -and 203 -notin $Tree.ProcessId -and 105 -notin $Tree.ProcessId) 'descendants and recycled parent IDs'
Assert-DevPortsOwned @([pscustomobject]@{ LocalPort = 8001; OwningProcess = 201 }) $Tree
$Blocked = $false
try { Assert-DevPortsOwned @([pscustomobject]@{ LocalPort = 3000; OwningProcess = 999 }) $Tree } catch { $Blocked = $true }
Assert-DevTest $Blocked 'foreign listener blocks restart'
$script:DevTestStopped = @()
$script:DevTestCurrent = $Backend
function Get-CimInstance { param($ClassName, $Filter, $ErrorAction) $script:DevTestCurrent }
function Stop-Process { param($Id, $ErrorAction) $script:DevTestStopped += $Id }
Stop-VerifiedDevProcess $Backend
Assert-DevTest ($script:DevTestStopped.Count -eq 1 -and $script:DevTestStopped[0] -eq 101) 'verified PID stopped once'
$script:DevTestCurrent = New-TestDevProcess 101 1 'python.exe' 'another task' $TestCreated.AddSeconds(10)
$Blocked = $false
try { Stop-VerifiedDevProcess $Backend } catch { $Blocked = $true }
Assert-DevTest ($Blocked -and $script:DevTestStopped.Count -eq 1) 'recycled PID must not be stopped'
$ChildRaceHandled = $true
try { Stop-VerifiedDevProcess $Backend -IgnoreChangedIdentity } catch { $ChildRaceHandled = $false }
Assert-DevTest ($ChildRaceHandled -and $script:DevTestStopped.Count -eq 1) 'changed descendant identity is skipped without aborting restart'
$script:DevTestCurrent = New-TestDevProcess 101 1 'python.exe' '' $TestCreated
$ChildRaceHandled = $true
try { Stop-VerifiedDevProcess $Backend -IgnoreChangedIdentity } catch { $ChildRaceHandled = $false }
Assert-DevTest ($ChildRaceHandled -and $script:DevTestStopped.Count -eq 1) 'closing descendant with empty command line is skipped'
$script:DevTestCurrent = $null
Stop-VerifiedDevProcess $Backend
Assert-DevTest ($script:DevTestStopped.Count -eq 1) 'already exited process is harmless'
$TestEntryRoot = Split-Path $PSScriptRoot -Parent
foreach ($EntryPoint in 'make.ps1', 'make.bat', 'Makefile', 'make') {
    $EntryText = Get-Content -LiteralPath (Join-Path $TestEntryRoot $EntryPoint) -Raw
    Assert-DevTest ($EntryText.Contains('start-dev.ps1')) "shared dev launcher: $EntryPoint"
}
Write-Host 'Dev process ownership regression checks passed (18 assertions).'
