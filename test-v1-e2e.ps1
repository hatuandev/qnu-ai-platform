param(
    [Parameter(Position=0)][string]$Command = "help",
    [Parameter(Position=1)][string]$Stage,
    [Parameter(ValueFromRemainingArguments=$true)][string[]]$Options
)
$Python = Join-Path $PSScriptRoot "backendV1/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $Python)) { throw "Chưa cài môi trường backendV1." }
$Arguments = @($Command)
if ($Stage) { $Arguments += $Stage }
if ($Options) { $Arguments += $Options }
& $Python -X utf8 (Join-Path $PSScriptRoot "scripts/v1_e2e_session.py") @Arguments
exit $LASTEXITCODE
