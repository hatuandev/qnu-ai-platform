# Start the V1 worker in the foreground; do not reuse an unknown process.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$RunnerArguments)
& (Join-Path (Split-Path $PSScriptRoot -Parent) "make.ps1") worker @RunnerArguments
exit $LASTEXITCODE
