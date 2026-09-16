@echo off
if "%~1"=="dev" goto do_dev
if "%~1"=="test" goto do_test
goto show_usage

:do_dev
echo [QNU AI Platform] Dang khoi chay Backend va Frontend...
start "QNU Backend API (Port 8001)" cmd /k "cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"
goto end

:do_test
echo [QNU AI Platform] Dang chay kiem thu toan he thong...
cd backend && uv run --extra dev pytest
cd frontend && npm run test:e2e
goto end

:show_usage
echo Su dung:
echo   make dev   : Khoi chay ca Backend 8001 va Frontend 3000
echo   make test  : Chay toan bo test Pytest va Playwright

:end
