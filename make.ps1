# QNU AI Platform - Task Runner
param (
    [Parameter(Position = 0)]
    [ValidateSet("dev", "test")]
    [string]$Command = "dev"
)

if ($Command -eq "dev") {
    Write-Host "Dang khoi chay Backend (Port 8001) va Frontend (Port 3001)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
} elseif ($Command -eq "test") {
    Write-Host "[1/2] Dang chay kiem thu Backend Pytest (68 tests)..." -ForegroundColor Cyan
    Set-Location "$PSScriptRoot\backend"
    uv run --extra dev pytest

    Write-Host "[2/2] Dang chay kiem thu Frontend Playwright E2E (12 tests)..." -ForegroundColor Cyan
    Set-Location "$PSScriptRoot\frontend"
    npm run test:e2e
    Set-Location $PSScriptRoot
}
