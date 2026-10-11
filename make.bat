@echo off
setlocal

set "PYTHON_EXE=backend\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

if "%~1"=="" goto do_help
if "%~1"=="help" goto do_help
if "%~1"=="infra-up" goto do_infra_up
if "%~1"=="infra-down" goto do_infra_down
if "%~1"=="infra-status" goto do_infra_status
if "%~1"=="infra-logs" goto do_infra_logs
if "%~1"=="migrate" goto do_migrate
if "%~1"=="db-check" goto do_db_check
if "%~1"=="db-ready" goto do_db_ready
if "%~1"=="seed" goto do_seed
if "%~1"=="reset-db" goto do_reset_db
if "%~1"=="reseed" goto do_reset_db
if "%~1"=="reconcile" goto do_reconcile
if "%~1"=="reindex" goto do_reindex
if "%~1"=="dev" goto do_dev
if "%~1"=="dev1" goto do_dev
if "%~1"=="dev2" goto do_dev
if "%~1"=="worker" goto do_worker
if "%~1"=="be" goto do_be
if "%~1"=="fe" goto do_fe
if "%~1"=="fe2" goto do_fe
if "%~1"=="test" goto do_test
if "%~1"=="test-be" goto do_test_be
if "%~1"=="test-fe" goto do_test_fe
if "%~1"=="lint" goto do_lint
if "%~1"=="lint-fix" goto do_lint_fix
if "%~1"=="typecheck" goto do_typecheck
if "%~1"=="build" goto do_build

echo [QNU AI Platform] Lenh khong hop le: "%~1"
echo Chay "make help" de xem danh sach lenh ho tro.
goto end

:do_infra_up
echo [QNU AI Platform] Dang khoi dong ha tang Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)...
docker compose -f docker-compose.infra.yml up -d
goto end

:do_infra_down
echo [QNU AI Platform] Dang dung ha tang Docker...
docker compose -f docker-compose.infra.yml down
goto end

:do_infra_status
docker compose -f docker-compose.infra.yml ps
goto end

:do_infra_logs
docker compose -f docker-compose.infra.yml logs -f
goto end

:do_migrate
echo [QNU AI Platform] Dang chay migration CSDL len Alembic HEAD...
cd backend && %PYTHON_EXE% -m app.cli db migrate
cd ..
goto end

:do_db_check
echo [QNU AI Platform] Kiem tra ket noi, schema va cac bang cot loi CSDL...
cd backend && %PYTHON_EXE% -m app.cli db check
cd ..
goto end

:do_db_ready
echo [QNU AI Platform] Kiem tra va dam bao CSDL, migration, du lieu seed san sang...
cd backend && %PYTHON_EXE% -m app.cli db ensure-ready
cd ..
goto end

:do_seed
echo [QNU AI Platform] Dang khoi tao CSDL va seed toan bo du lieu mac dinh...
cd backend && %PYTHON_EXE% -m app.cli db bootstrap
cd ..
goto end

:do_reset_db
echo [QNU AI Platform] Dang xoa sach toan bo CSDL PostgreSQL va Qdrant, sau do seed lai toan bo 5 mo-dun...
cd backend && %PYTHON_EXE% scripts\reset_and_reseed.py
cd ..
goto end

:do_reconcile
echo [QNU AI Platform] Dang doi soat 4 tang CSDL, Qdrant, MinIO va Redis...
cd backend && %PYTHON_EXE% -m app.cli knowledge reconcile
cd ..
goto end

:do_reindex
echo [QNU AI Platform] Dang danh lai toan bo chi muc vector Qdrant...
cd backend && %PYTHON_EXE% -m app.cli knowledge reindex
cd ..
goto end

:do_dev
echo [QNU AI Platform] Kiem tra CSDL va du lieu mau...
cd backend && %PYTHON_EXE% -m app.cli db ensure-ready
cd ..
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-worker.ps1"
if errorlevel 1 goto end
echo [QNU AI Platform] Dang khoi chay Backend (Port 8001) va Frontend Studio (Port 3000)...
start "QNU Backend API (Port 8001)" cmd /k "cd backend && %PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
timeout /t 2 /nobreak >nul
start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"
goto end

:do_worker
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-worker.ps1"
goto end

:do_be
echo [QNU AI Platform] Kiem tra CSDL va khoi chay Backend API (Port 8001)...
cd backend && %PYTHON_EXE% -m app.cli db ensure-ready
cd ..
start "QNU Backend API (Port 8001)" cmd /k "cd backend && %PYTHON_EXE% -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
goto end

:do_fe
echo [QNU AI Platform] Dang khoi chay Frontend Studio (Port 3000)...
start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"
goto end

:do_test
echo [QNU AI Platform] Dang chay kiem thu toan he thong...
echo [1/2] Kiem thu Backend Pytest...
cd backend && %PYTHON_EXE% -m pytest
cd ..
echo [2/2] Kiem thu Frontend (npm test)...
cd frontend && npm test
cd ..
goto end

:do_test_be
echo [QNU AI Platform] Dang chay kiem thu Backend Pytest...
cd backend && %PYTHON_EXE% -m pytest
cd ..
goto end

:do_test_fe
echo [QNU AI Platform] Dang chay kiem thu Frontend (npm test)...
cd frontend && npm test
cd ..
goto end

:do_lint
echo [QNU AI Platform] Dang kiem tra linter Backend (Ruff) va Frontend (Biome)...
cd backend && %PYTHON_EXE% -m ruff check .
cd ..
cd frontend && npm run lint
cd ..
goto end

:do_lint_fix
echo [QNU AI Platform] Dang tu dong sua loi linter Backend va Frontend...
cd backend && %PYTHON_EXE% -m ruff check --fix .
cd ..
cd frontend && npm run lint:fix
cd ..
goto end

:do_typecheck
echo [QNU AI Platform] Dang kiem tra TypeScript types Frontend...
cd frontend && npm run typecheck
cd ..
goto end

:do_build
echo [QNU AI Platform] Dang kiem tra build bundle Frontend...
cd frontend && npm run build
cd ..
goto end

:do_help
echo ==============================================================================
echo           QNU AI Platform - Task Runner (CMD: make.bat hoac make)
echo ==============================================================================
echo [Ha tang Docker]
echo   make infra-up       : Khoi dong cum ha tang Docker (Postgres, Qdrant, Redis, MinIO, Gotenberg)
echo   make infra-down     : Dung cum ha tang Docker
echo   make infra-status   : Kiem tra trang thai cac container Docker
echo   make infra-logs     : Theo doi logs cua cum Docker
echo.
echo [Phat trien - Local Dev]
echo   make dev            : Khoi chay Backend (8001), Frontend (3000) va ARQ worker
echo   make worker         : Khoi chay worker nen, co log va tranh mo trung
echo   make be             : Khoi chay rieng Backend API (Port 8001)
echo   make fe             : Khoi chay rieng Frontend Studio (Port 3000)
echo.
echo [Co so du lieu va Migration]
echo   make migrate        : Chay migration CSDL len Alembic HEAD (python -m app.cli db migrate)
echo   make db-check       : Kiem tra ket noi, schema va cac bang cot loi CSDL
echo   make db-ready       : Kiem tra va tu dong khoi tao CSDL / seed neu con thieu
echo   make seed           : Khoi tao CSDL va seed toan bo du lieu mac dinh QNU
echo   make reset-db       : Xoa sach CSDL PostgreSQL va Qdrant, sau do seed lai toan bo
echo   make reseed         : Alias cua reset-db
echo.
echo [Kiem thu tu dong]
echo   make test           : Chay toan bo kiem thu Backend (Pytest) va Frontend (npm test)
echo   make test-be        : Chay rieng kiem thu Backend voi Pytest
echo   make test-fe        : Chay rieng kiem thu Frontend (npm test)
echo.
echo [Chat luong ma nguon - Code Quality]
echo   make lint           : Kiem tra linter Backend (Ruff) va Frontend (Biome)
echo   make lint-fix       : Tu dong sua loi linter ca Backend va Frontend
echo   make typecheck      : Kiem tra kieu du lieu TypeScript Frontend (tsc --noEmit)
echo   make build          : Kiem tra dong goi build Frontend bundle (vite build)
echo.
echo [Kho tri thuc - Knowledge Operations]
echo   make reconcile      : Kiem tra doi soat 4 tang (Postgres, Qdrant, MinIO, Redis)
echo   make reindex        : Danh lai chi muc vector Qdrant
echo ==============================================================================

:end
endlocal
