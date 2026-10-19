# Delete only the task-owned runtime after the Python harness verifies DB removal.
param([string]$StateFile = (Join-Path $PSScriptRoot '..\storage\context548-isolation.json'), [string]$EvidenceDirectory = (Join-Path $PSScriptRoot '..\storage\context548-evidence'))
$ErrorActionPreference = 'Stop'
$taskRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$statePath = [System.IO.Path]::GetFullPath($StateFile)
$evidencePath = [System.IO.Path]::GetFullPath($EvidenceDirectory)
if (-not $statePath.StartsWith((Join-Path $taskRoot 'backend\storage\'), [System.StringComparison]::OrdinalIgnoreCase) -or -not $evidencePath.StartsWith((Join-Path $taskRoot 'backend\storage\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'State/evidence outside workspace Storage.' }
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
if ($state.status -ne 'database_removed_storage_pending') { throw 'Verify DB ownership and removal first.' }
if ($state.nonce -notmatch '^[a-f0-9]{32}$') { throw 'Invalid runtime ownership nonce.' }
$suffix = $state.nonce.Substring(0, 12)
if ($state.name -ne "qnu_test_context548_$suffix") { throw 'Unexpected test database.' }
$expected = [System.IO.Path]::GetFullPath((Join-Path $taskRoot "backend\storage\context548-runtime-$suffix"))
if ([System.IO.Path]::GetFullPath($state.runtime) -ne $expected) { throw 'Unexpected runtime path.' }
if (-not $expected.StartsWith((Join-Path $taskRoot 'backend\storage\'), [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime outside intended Storage.' }
if (Test-Path -LiteralPath $expected) {
    $links = @(Get-Item -LiteralPath $expected -Force; Get-ChildItem -LiteralPath $expected -Recurse -Force) | Where-Object { $_.Attributes -band [System.IO.FileAttributes]::ReparsePoint }
    if ($links) { throw 'Refuse runtime with reparse points.' }
    Remove-Item -LiteralPath $expected -Recurse -Force
}
if (Test-Path -LiteralPath $expected) { throw 'Runtime cleanup incomplete.' }
$state.status = 'cleaned'
$result = [pscustomobject]@{ status = 'cleaned'; test_database = $state.name; database_removed_verified = $true; runtime = $expected; runtime_exists_after = $false; production_migrations = $false; retained = 'Allowlisted evidence dossier, no database/Storage dump' }
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($statePath, ($state | ConvertTo-Json -Depth 8).Replace("`r`n", "`n") + "`n", $utf8)
[System.IO.File]::WriteAllText((Join-Path $evidencePath 'cleanup.json'), ($result | ConvertTo-Json -Depth 8).Replace("`r`n", "`n") + "`n", $utf8)
$result | ConvertTo-Json -Depth 8
