# QNU task runner. All default commands select V1.
param(
    [Parameter(Position = 0)][string]$Command = "help",
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$RunnerArguments
)
$ErrorActionPreference = "Stop"
$RunnerPython = Join-Path $PSScriptRoot "backendV1/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $RunnerPython)) { $RunnerPython = "python" }
& $RunnerPython (Join-Path $PSScriptRoot "scripts/run_v1.py") $Command @RunnerArguments
exit $LASTEXITCODE
