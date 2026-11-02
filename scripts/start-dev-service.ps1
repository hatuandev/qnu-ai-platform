# Compatibility service selector, delegates to V1 foreground commands.
param(
    [Parameter(Mandatory = $true)][ValidateSet('Backend', 'Frontend', 'Worker')][string]$Service,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$RunnerArguments
)
$ServiceCommands = @{ Backend = 'be'; Frontend = 'fe'; Worker = 'worker' }
& (Join-Path (Split-Path $PSScriptRoot -Parent) "make.ps1") $ServiceCommands[$Service] @RunnerArguments
exit $LASTEXITCODE
