# QNU AI Platform - Task Runner (PowerShell: .\make.ps1 hoặc .\make)
param (
    [Parameter(Position = 0)]
    [ValidateSet(
        "infra-up", "infra-down", "infra-status", "infra-logs",
        "migrate", "db-check", "db-ready", "seed", "reset-db", "reseed",
        "reconcile", "reindex",
        "dev", "dev1", "dev2", "be", "fe", "fe2", "worker",
        "test", "test-be", "test-fe",
        "lint", "lint-fix", "typecheck", "build",
        "help"
    )]
    [string]$Command = "help"
)

$BackendDir = "$PSScriptRoot\backend"
$FrontendDir = "$PSScriptRoot\frontend"
$PythonExe = "$BackendDir\.venv\Scripts\python.exe"

# Kiem tra neu venv chua co thi thu dung python he thong
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

switch ($Command) {
    # --- Cum ha tang Docker ---
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

    # --- Co so du lieu & Migration ---
    "migrate" {
        Write-Host "Dang chay migration CSDL len Alembic HEAD..." -ForegroundColor Green
        Set-Location $BackendDir
        & $PythonExe -m app.cli db migrate
        Set-Location $PSScriptRoot
    }
    "db-check" {
        Write-Host "Kiem tra ket noi, schema va cac bang cot loi CSDL..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m app.cli db check
        Set-Location $PSScriptRoot
    }
    "db-ready" {
        Write-Host "Kiem tra va dam bao CSDL, migration, du lieu seed san sang..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m app.cli db ensure-ready
        Set-Location $PSScriptRoot
    }
    "seed" {
        Write-Host "Dang khoi tao CSDL va seed toan bo du lieu mac dinh QNU AI Platform..." -ForegroundColor Green
        Set-Location $BackendDir
        & $PythonExe -m app.cli db bootstrap
        Set-Location $PSScriptRoot
    }
    { $_ -in "reset-db", "reseed" } {
        Write-Host "Dang xoa sach toan bo CSDL PostgreSQL va Qdrant, sau do seed lai toan bo 5 mo-dun..." -ForegroundColor Yellow
        Set-Location $BackendDir
        & $PythonExe "scripts\reset_and_reseed.py"
        Set-Location $PSScriptRoot
    }
    "reconcile" {
        Write-Host "Dang doi soat 4 tang CSDL, Qdrant, MinIO va Redis..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m app.cli knowledge reconcile
        Set-Location $PSScriptRoot
    }
    "reindex" {
        Write-Host "Dang danh lai toan bo chi muc vector Qdrant..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m app.cli knowledge reindex
        Set-Location $PSScriptRoot
    }

    # --- Phat trien (Dev Servers) ---
    { $_ -in "dev", "dev1", "dev2" } {
        Write-Host "Kiem tra CSDL va du lieu mau (PostgreSQL, Schema, Seed data)..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m app.cli db ensure-ready
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[CANH BAO] CSDL chua san sang hoac gap loi khi khoi tao." -ForegroundColor Red
            Write-Host "Neu PostgreSQL chua chay, vui long chay: .\make.ps1 infra-up" -ForegroundColor Yellow
            Set-Location $PSScriptRoot
            return
        }
        Set-Location $PSScriptRoot

        & "$PSScriptRoot\scripts\start-worker.ps1"
        Write-Host "Dang khoi chay Backend (Port 8001)..." -ForegroundColor Green
        Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd backend; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
        Write-Host "Doi Backend khoi dong trong 2 giay..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
        Write-Host "Dang khoi chay Frontend Studio (Port 3000)..." -ForegroundColor Green
        Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
    }
    "worker" {
        & "$PSScriptRoot\scripts\start-worker.ps1"
    }
    "be" {
        Write-Host "Kiem tra CSDL va khoi chay Backend API (Port 8001)..." -ForegroundColor Green
        Set-Location $BackendDir
        & $PythonExe -m app.cli db ensure-ready
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; & '$PythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
        Set-Location $PSScriptRoot
    }
    { $_ -in "fe", "fe2" } {
        Write-Host "Dang khoi chay Frontend Studio (Port 3000)..." -ForegroundColor Green
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"
    }

    # --- Kiem thu ---
    "test" {
        Write-Host "[1/2] Dang chay kiem thu Backend Pytest..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m pytest

        Write-Host "[2/2] Dang chay kiem thu Frontend (npm test)..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm test
        Set-Location $PSScriptRoot
    }
    "test-be" {
        Write-Host "Dang chay kiem thu Backend Pytest..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m pytest
        Set-Location $PSScriptRoot
    }
    "test-fe" {
        Write-Host "Dang chay kiem thu Frontend (npm test)..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm test
        Set-Location $PSScriptRoot
    }

    # --- Chat luong ma nguon (Lint, Typecheck, Build) ---
    "lint" {
        Write-Host "[1/2] Dang kiem tra linter Backend voi Ruff..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m ruff check .
        Write-Host "[2/2] Dang kiem tra linter Frontend voi Biome..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm run lint
        Set-Location $PSScriptRoot
    }
    "lint-fix" {
        Write-Host "[1/2] Dang tu dong sua loi linter Backend..." -ForegroundColor Cyan
        Set-Location $BackendDir
        & $PythonExe -m ruff check --fix .
        Write-Host "[2/2] Dang tu dong sua loi linter Frontend..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm run lint:fix
        Set-Location $PSScriptRoot
    }
    "typecheck" {
        Write-Host "Dang kiem tra TypeScript types Frontend..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm run typecheck
        Set-Location $PSScriptRoot
    }
    "build" {
        Write-Host "Dang kiem tra build bundle Frontend..." -ForegroundColor Cyan
        Set-Location $FrontendDir
        npm run build
        Set-Location $PSScriptRoot
    }

    # --- Huong dan su dung ---
    "help" {
        Write-Host "==============================================================================" -ForegroundColor DarkCyan
        Write-Host "           QNU AI Platform - Task Runner (PowerShell: .\make.ps1)             " -ForegroundColor White
        Write-Host "==============================================================================" -ForegroundColor DarkCyan
        Write-Host "[Ha tang Docker]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 infra-up     : Khoi dong cum ha tang Docker (Postgres, Qdrant, Redis, MinIO, Gotenberg)"
        Write-Host "  .\make.ps1 infra-down   : Dung cum ha tang Docker"
        Write-Host "  .\make.ps1 infra-status : Kiem tra trang thai cac container Docker"
        Write-Host "  .\make.ps1 infra-logs   : Theo doi logs cua cum Docker"
        Write-Host ""
        Write-Host "[Phat trien - Local Dev]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 dev          : Khoi chay Backend (8001), Frontend (3000) va ARQ worker"
        Write-Host "  .\make.ps1 worker       : Khoi chay worker nen, co log va tranh mo trung"
        Write-Host "  .\make.ps1 be           : Khoi chay rieng Backend API (Port 8001)"
        Write-Host "  .\make.ps1 fe           : Khoi chay rieng Frontend Studio (Port 3000)"
        Write-Host ""
        Write-Host "[Co so du lieu & Migration]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 migrate      : Chay migration CSDL len Alembic HEAD (python -m app.cli db migrate)"
        Write-Host "  .\make.ps1 db-check     : Kiem tra ket noi, schema va cac bang cot loi CSDL"
        Write-Host "  .\make.ps1 db-ready     : Kiem tra va tu dong khoi tao CSDL / seed neu con thieu"
        Write-Host "  .\make.ps1 seed         : Khoi tao CSDL va seed toan bo du lieu mac dinh QNU"
        Write-Host "  .\make.ps1 reset-db     : Xoa sach CSDL PostgreSQL va Qdrant, sau do seed lai toan bo"
        Write-Host "  .\make.ps1 reseed       : Alias cua reset-db"
        Write-Host ""
        Write-Host "[Kiem thu tu dong]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 test         : Chay toan bo kiem thu Backend (Pytest) va Frontend (npm test)"
        Write-Host "  .\make.ps1 test-be      : Chay rieng kiem thu Backend voi Pytest"
        Write-Host "  .\make.ps1 test-fe      : Chay rieng kiem thu Frontend (npm test)"
        Write-Host ""
        Write-Host "[Chat luong ma nguon - Code Quality]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 lint         : Kiem tra linter Backend (Ruff) va Frontend (Biome)"
        Write-Host "  .\make.ps1 lint-fix     : Tu dong sua loi linter ca Backend va Frontend"
        Write-Host "  .\make.ps1 typecheck    : Kiem tra kieu du lieu TypeScript Frontend (tsc --noEmit)"
        Write-Host "  .\make.ps1 build        : Kiem tra dong goi build Frontend bundle (vite build)"
        Write-Host ""
        Write-Host "[Kho tri thuc - Knowledge Operations]" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 reconcile    : Kiem tra doi soat 4 tang (Postgres, Qdrant, MinIO, Redis)"
        Write-Host "  .\make.ps1 reindex      : Danh lai chi muc vector Qdrant"
        Write-Host "==============================================================================" -ForegroundColor DarkCyan
    }
}
