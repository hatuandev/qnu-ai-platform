#!/usr/bin/env bash

CMD="${1:-dev}"

case "$CMD" in
  infra-up)
    docker compose -f docker-compose.infra.yml up -d
    ;;
  infra-down)
    docker compose -f docker-compose.infra.yml down
    ;;
  infra-status)
    docker compose -f docker-compose.infra.yml ps
    ;;
  infra-logs)
    docker compose -f docker-compose.infra.yml logs -f
    ;;
  seed)
    echo "[QNU AI Platform] Khoi tao CSDL va seed toan bo du lieu mac dinh..."
    (cd backend && ./.venv/Scripts/python.exe -m app.cli db bootstrap)
    ;;
  reset-db|reseed)
    echo "[QNU AI Platform] Dang xoa sach toan bo CSDL PostgreSQL va Qdrant, sau do seed lai toan bo 5 mo-dun..."
    (cd backend && ./.venv/Scripts/python.exe scripts/reset_and_reseed.py)
    ;;
  dev)
    echo "[QNU AI Platform] Kiem tra CSDL va du lieu mau..."
    (cd backend && ./.venv/Scripts/python.exe -m app.cli db ensure-ready)
    echo "[QNU AI Platform] Khoi chay Backend (Port 8001) va Frontend cu (Port 3001)..."
    cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    cmd.exe /c start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"
    ;;
  dev1|dev2)
    echo "[QNU AI Platform] Kiem tra CSDL va du lieu mau..."
    (cd backend && ./.venv/Scripts/python.exe -m app.cli db ensure-ready)
    echo "[QNU AI Platform] Khoi chay Backend (Port 8001) va Frontend 2 Moi (Port 3000)..."
    cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    cmd.exe /c start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"
    ;;
  be)
    echo "[QNU AI Platform] Kiem tra CSDL va du lieu mau..."
    (cd backend && ./.venv/Scripts/python.exe -m app.cli db ensure-ready)
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
    echo "  ./make seed         : Khoi tao va seed du lieu CSDL mac dinh"
    echo "  ./make reset-db     : Xoa sach toan bo CSDL PostgreSQL & Qdrant, sau do seed lai toan bo 5 mo-dun"
    echo "  ./make reseed       : Alias cua reset-db"
    echo "  ./make dev          : Khoi chay ca Backend 8001 va Frontend cu (Port 3001)"
    echo "  ./make dev1         : Khoi chay ca Backend 8001 va Frontend 2 Moi (Port 3000)"
    echo "  ./make be           : Khoi chay rieng Backend API 8001"
    echo "  ./make fe           : Khoi chay rieng Frontend Studio cu (Port 3001)"
    echo "  ./make fe2          : Khoi chay rieng Frontend 2 Studio Moi (Port 3000)"
    echo "  ./make test         : Chay toan bo test Pytest va Playwright"
    ;;
esac
