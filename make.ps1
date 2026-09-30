# QNU AI Platform - Task Runner (PowerShell: .\make.ps1 hoặc .\make)
param (
    [Parameter(Position = 0)]
    [ValidateSet("infra-up", "infra-down", "infra-status", "infra-logs", "seed", "reset-db", "reseed", "dev", "dev1", "dev2", "be", "fe", "fe2", "test", "help")]
    [string]$Command = "dev"
)

switch ($Command) {
    "infra-up" {
        Write-Host "Dang khoi dong ha tang Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)..." -ForegroundColor Green
        docker compose -f "$PSScriptRoot\docker-compose.infra.yml" up -d
    }
    "infra-down" {
        Write-Host "Dang dung ha tang Docker..." -ForegroundColor Yellow
        docker compose -f "$PSScriptRoot\docker-compose.infra.yml" down
    }
    "infra-status" {
        Write-Host "Trang thai cum ha tang Docker:" -ForegroundColor Cyan
        docker compose -f "$PSScriptRoot\docker-compose.infra.yml" ps
    }
    "infra-logs" {
        docker compose -f "$PSScriptRoot\docker-compose.infra.yml" logs -f
    }
    "seed" {
        Write-Host "Dang khoi tao CSDL va seed toan bo du lieu mac dinh QNU AI Platform..." -ForegroundColor Green
        Set-Location "$PSScriptRoot\backend"
        .\.venv\Scripts\python.exe -m app.cli db bootstrap
        Set-Location $PSScriptRoot
    }
    { $_ -in "reset-db", "reseed" } {
        Write-Host "Dang xoa sach toan bo CSDL PostgreSQL va Qdrant, sau do seed lai toan bo 5 mo-dun..." -ForegroundColor Yellow
        Set-Location "$PSScriptRoot\backend"
        & ".\.venv\Scripts\python.exe" "scripts\reset_and_reseed.py"
        Set-Location $PSScriptRoot
    }
    "dev" {
        Write-Host "Kiem tra CSDL va du lieu mau (PostgreSQL, Schema, Seed data)..." -ForegroundColor Cyan
        Set-Location "$PSScriptRoot\backend"
        & ".\.venv\Scripts\python.exe" -m app.cli db ensure-ready
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[CANH BAO] CSDL chua san sang hoac gap loi khi khoi tao." -ForegroundColor Red
            Write-Host "Neu PostgreSQL chua chay, vui long chay: .\make infra-up" -ForegroundColor Yellow
        }
        Set-Location $PSScriptRoot

        Write-Host "Dang khoi chay Backend (Port 8001)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
        Write-Host "Doi Backend khoi dong trong 2 giay de tranh proxy error..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        Write-Host "Dang khoi chay Frontend Studio cu (Port 3001)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
    }
    { $_ -in "dev1", "dev2" } {
        Write-Host "Kiem tra CSDL va du lieu mau (PostgreSQL, Schema, Seed data)..." -ForegroundColor Cyan
        Set-Location "$PSScriptRoot\backend"
        & ".\.venv\Scripts\python.exe" -m app.cli db ensure-ready
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[CANH BAO] CSDL chua san sang hoac gap loi khi khoi tao." -ForegroundColor Red
            Write-Host "Neu PostgreSQL chua chay, vui long chay: .\make infra-up" -ForegroundColor Yellow
        }
        Set-Location $PSScriptRoot

        Write-Host "Dang khoi chay Backend (Port 8001)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
        Write-Host "Doi Backend khoi dong trong 2 giay de tranh proxy error..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        Write-Host "Dang khoi chay Frontend 2 Studio Moi (Port 3000)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend2; npm run dev"
    }
    "be" {
        Write-Host "Dang khoi chay Backend API (Port 8001)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    }
    "fe" {
        Write-Host "Dang khoi chay Frontend Studio cu (Port 3001)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
    }
    "fe2" {
        Write-Host "Dang khoi chay Frontend 2 Studio Moi (Port 3000)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend2; npm run dev"
    }
    "test" {
        Write-Host "[1/2] Dang chay kiem thu Backend Pytest (68 tests)..." -ForegroundColor Cyan
        Set-Location "$PSScriptRoot\backend"
        uv run --extra dev pytest

        Write-Host "[2/2] Dang chay kiem thu Frontend Playwright E2E (12 tests)..." -ForegroundColor Cyan
        Set-Location "$PSScriptRoot\frontend"
        npm run test:e2e
        Set-Location $PSScriptRoot
    }
    "help" {
        Write-Host "Huong dan su dung Task Runner:" -ForegroundColor Cyan
        Write-Host "  .\make infra-up     : Khoi dong cum ha tang Docker"
        Write-Host "  .\make infra-down   : Dung cum ha tang Docker"
        Write-Host "  .\make infra-status : Kiem tra trang thai cac container"
        Write-Host "  .\make infra-logs   : Xem logs cua cum Docker"
        Write-Host "  .\make seed         : Khoi tao CSDL va seed toan bo du lieu mac dinh"
        Write-Host "  .\make reset-db     : Xoa sach toan bo CSDL PostgreSQL & Qdrant, sau do seed lai toan bo 5 mo-dun"
        Write-Host "  .\make reseed       : Alias cua reset-db"
        Write-Host "  .\make dev          : Khoi chay ca Backend 8001 va Frontend cu (Port 3001)"
        Write-Host "  .\make dev1         : Khoi chay ca Backend 8001 va Frontend 2 Moi (Port 3000)"
        Write-Host "  .\make be           : Khoi chay rieng Backend API 8001"
        Write-Host "  .\make fe           : Khoi chay rieng Frontend Studio cu 3001"
        Write-Host "  .\make fe2          : Khoi chay rieng Frontend 2 Studio Moi 3000"
        Write-Host "  .\make test         : Chay toan bo test Pytest va Playwright"
    }
}