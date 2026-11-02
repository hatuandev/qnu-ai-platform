# Compatibility entrypoint; same V1 commands and exit codes as make.ps1.
param(
    [Parameter(Position = 0)][string]$Command = "help",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$RunnerArguments
)
& (Join-Path $PSScriptRoot "make.ps1") $Command @RunnerArguments
exit $LASTEXITCODE
