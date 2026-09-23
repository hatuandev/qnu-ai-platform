@echo off
if "%~1"=="infra-up" goto do_infra_up
if "%~1"=="infra-down" goto do_infra_down
if "%~1"=="infra-status" goto do_infra_status
if "%~1"=="infra-logs" goto do_infra_logs
if "%~1"=="dev" goto do_dev
if "%~1"=="dev1" goto do_dev1
if "%~1"=="dev2" goto do_dev1
if "%~1"=="be" goto do_be
if "%~1"=="fe" goto do_fe
if "%~1"=="fe2" goto do_fe2
if "%~1"=="test" goto do_test
goto show_usage

:do_infra_up
echo [QNU AI Platform] Dang khoi dong ha tang Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)...
docker compose up -d
goto end

:do_infra_down
echo [QNU AI Platform] Dang dung ha tang Docker...
docker compose down
goto end

:do_infra_status
docker compose ps
goto end

:do_infra_logs
docker compose logs -f
goto end

:do_dev
echo [QNU AI Platform] Dang khoi chay Backend va Frontend (Port 3001)...
start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
timeout /t 2 /nobreak >nul
start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"
goto end

:do_dev1
:do_dev2
echo [QNU AI Platform] Dang khoi chay Backend va Frontend 2 (Port 3000)...
start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
timeout /t 2 /nobreak >nul
start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"
goto end

:do_be
echo [QNU AI Platform] Dang khoi chay Backend API...
start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
goto end

:do_fe
echo [QNU AI Platform] Dang khoi chay Frontend Studio (Port 3001)...
start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"
goto end

:do_fe2
echo [QNU AI Platform] Dang khoi chay Frontend 2 Studio (Port 3000)...
start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"
goto end

:do_test
echo [QNU AI Platform] Dang chay kiem thu toan he thong...
cd backend && uv run --extra dev pytest
cd frontend && npm run test:e2e
goto end

:show_usage
echo Su dung:
echo   make infra-up     : Khoi dong cum ha tang Docker
echo   make infra-down   : Dung cum ha tang Docker
echo   make infra-status : Kiem tra trang thai cac container Docker
echo   make infra-logs   : Theo doi logs cua cum Docker
echo   make dev          : Khoi chay ca Backend 8001 va Frontend cu (Port 3001)
echo   make dev1         : Khoi chay ca Backend 8001 va Frontend 2 Moi (Port 3000)
echo   make be           : Khoi chay rieng Backend API 8001
echo   make fe           : Khoi chay rieng Frontend Studio cu (Port 3001)
echo   make fe2          : Khoi chay rieng Frontend 2 Studio Moi (Port 3000)
echo   make test         : Chay toan bo test Pytest va Playwright

:end