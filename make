#!/usr/bin/env bash

CMD="${1:-dev}"

case "$CMD" in
  infra-up)
    docker compose up -d
    ;;
  infra-down)
    docker compose down
    ;;
  infra-status)
    docker compose ps
    ;;
  infra-logs)
    docker compose logs -f
    ;;
  dev)
    echo "[QNU AI Platform] Khoi chay Backend (Port 8001) va Frontend cu (Port 3001)..."
    cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    cmd.exe /c start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"
    ;;
  dev1|dev2)
    echo "[QNU AI Platform] Khoi chay Backend (Port 8001) va Frontend 2 Moi (Port 3000)..."
    cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    cmd.exe /c start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"
    ;;
  be)
    cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    ;;
  fe)
    cmd.exe /c start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"
    ;;
  fe2)
    cmd.exe /c start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"
    ;;
  test)
    (cd backend && uv run --extra dev pytest)
    (cd frontend && npm run test:e2e)
    ;;
  *)
    echo "Su dung:"
    echo "  ./make infra-up     : Khoi dong cum ha tang Docker"
    echo "  ./make infra-down   : Dung cum ha tang Docker"
    echo "  ./make infra-status : Kiem tra trang thai cac container Docker"
    echo "  ./make infra-logs   : Theo doi logs cua cum Docker"
    echo "  ./make dev          : Khoi chay ca Backend 8001 va Frontend cu (Port 3001)"
    echo "  ./make dev1         : Khoi chay ca Backend 8001 va Frontend 2 Moi (Port 3000)"
    echo "  ./make be           : Khoi chay rieng Backend API 8001"
    echo "  ./make fe           : Khoi chay rieng Frontend Studio cu (Port 3001)"
    echo "  ./make fe2          : Khoi chay rieng Frontend 2 Studio Moi (Port 3000)"
    echo "  ./make test         : Chay toan bo test Pytest va Playwright"
    ;;
esac
