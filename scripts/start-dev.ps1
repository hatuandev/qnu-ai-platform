# Start V1 API/worker/frontend in this terminal; Ctrl+C stops this session.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$RunnerArguments)
& (Join-Path (Split-Path $PSScriptRoot -Parent) "make.ps1") dev @RunnerArguments
exit $LASTEXITCODE
