#!/usr/bin/env bash

# QNU AI Platform - Bash Task Runner (./make)
CMD="${1:-help}"

if [ -f "backend/.venv/Scripts/python.exe" ]; then
  PYTHON="backend/.venv/Scripts/python.exe"
elif [ -f "backend/.venv/bin/python" ]; then
  PYTHON="backend/.venv/bin/python"
else
  PYTHON="python"
fi

case "$CMD" in
  # --- Cum ha tang Docker ---
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

  # --- Co so du lieu & Migration ---
  migrate)
    echo "[QNU AI Platform] Dang chay migration CSDL len Alembic HEAD..."
    (cd backend && $PYTHON -m app.cli db migrate)
    ;;
  db-check)
    echo "[QNU AI Platform] Kiem tra ket noi, schema va cac bang cot loi CSDL..."
    (cd backend && $PYTHON -m app.cli db check)
    ;;
  db-ready)
    echo "[QNU AI Platform] Kiem tra va dam bao CSDL, migration, du lieu seed san sang..."
    (cd backend && $PYTHON -m app.cli db ensure-ready)
    ;;
  seed)
    echo "[QNU AI Platform] Khoi tao CSDL va seed toan bo du lieu mac dinh..."
    (cd backend && $PYTHON -m app.cli db bootstrap)
    ;;
  reset-db|reseed)
    echo "[QNU AI Platform] Dang xoa sach toan bo CSDL PostgreSQL va Qdrant, sau do seed lai toan bo 5 mo-dun..."
    (cd backend && $PYTHON scripts/reset_and_reseed.py)
    ;;
  reconcile)
    echo "[QNU AI Platform] Dang doi soat 4 tang CSDL, Qdrant, MinIO va Redis..."
    (cd backend && $PYTHON -m app.cli knowledge reconcile)
    ;;
  reindex)
    echo "[QNU AI Platform] Dang danh lai toan bo chi muc vector Qdrant..."
    (cd backend && $PYTHON -m app.cli knowledge reindex)
    ;;

  # --- Phat trien (Dev Servers) ---
  dev|dev1|dev2)
    echo "[QNU AI Platform] Kiem tra CSDL va du lieu mau..."
    (cd backend && $PYTHON -m app.cli db ensure-ready)
    echo "[QNU AI Platform] Khoi chay Backend (Port 8001) va Frontend Studio (Port 3000)..."
    if command -v cmd.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-worker.ps1 || exit 1
      cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
      cmd.exe /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"
    else
      echo "He dieu hanh khong phai Windows, vui long chay rieng: ./make be, ./make fe va ./make worker"
    fi
    ;;
  worker)
    if command -v powershell.exe >/dev/null 2>&1; then
      powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/start-worker.ps1
    else
      (cd backend && .venv/bin/python -m arq app.workers.arq_worker.WorkerSettings)
    fi
    ;;
  be)
    echo "[QNU AI Platform] Kiem tra CSDL va du lieu mau..."
    (cd backend && $PYTHON -m app.cli db ensure-ready)
    if command -v cmd.exe >/dev/null 2>&1; then
      cmd.exe /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
    else
      (cd backend && $PYTHON -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload)
    fi
    ;;
  fe|fe2)
    if command -v cmd.exe >/dev/null 2>&1; then
      cmd.exe /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"
    else
      (cd frontend && npm run dev)
    fi
    ;;

  # --- Kiem thu ---
  test)
    echo "[QNU AI Platform] [1/2] Dang chay kiem thu Backend Pytest..."
    (cd backend && $PYTHON -m pytest)
    echo "[QNU AI Platform] [2/2] Dang chay kiem thu Frontend (npm test)..."
    (cd frontend && npm test)
    ;;
  test-be)
    echo "[QNU AI Platform] Dang chay kiem thu Backend Pytest..."
    (cd backend && $PYTHON -m pytest)
    ;;
  test-fe)
    echo "[QNU AI Platform] Dang chay kiem thu Frontend (npm test)..."
    (cd frontend && npm test)
    ;;

  # --- Chat luong ma nguon (Lint, Typecheck, Build) ---
  lint)
    echo "[QNU AI Platform] [1/2] Kiem tra linter Backend voi Ruff..."
    (cd backend && $PYTHON -m ruff check .)
    echo "[QNU AI Platform] [2/2] Kiem tra linter Frontend voi Biome..."
    (cd frontend && npm run lint)
    ;;
  lint-fix)
    echo "[QNU AI Platform] [1/2] Tu dong sua loi linter Backend..."
    (cd backend && $PYTHON -m ruff check --fix .)
    echo "[QNU AI Platform] [2/2] Tu dong sua loi linter Frontend..."
    (cd frontend && npm run lint:fix)
    ;;
  typecheck)
    echo "[QNU AI Platform] Kiem tra TypeScript types Frontend..."
    (cd frontend && npm run typecheck)
    ;;
  build)
    echo "[QNU AI Platform] Kiem tra dong goi build bundle Frontend..."
    (cd frontend && npm run build)
    ;;

  # --- Huong dan su dung ---
  help|*)
    echo "=============================================================================="
    echo "           QNU AI Platform - Task Runner (Bash: ./make)                      "
    echo "=============================================================================="
    echo "[Ha tang Docker]"
    echo "  ./make infra-up     : Khoi dong cum ha tang Docker (Postgres, Qdrant, Redis, MinIO, Gotenberg)"
    echo "  ./make infra-down   : Dung cum ha tang Docker"
    echo "  ./make infra-status : Kiem tra trang thai cac container Docker"
    echo "  ./make infra-logs   : Theo doi logs cua cum Docker"
    echo ""
    echo "[Phat trien - Local Dev]"
    echo "  ./make dev          : Khoi chay Backend (8001), Frontend (3000) va ARQ worker"
    echo "  ./make worker       : Khoi chay worker, co log tren Windows"
    echo "  ./make be           : Khoi chay rieng Backend API (Port 8001)"
    echo "  ./make fe           : Khoi chay rieng Frontend Studio (Port 3000)"
    echo ""
    echo "[Co so du lieu & Migration]"
    echo "  ./make migrate      : Chay migration CSDL len Alembic HEAD (python -m app.cli db migrate)"
    echo "  ./make db-check     : Kiem tra ket noi, schema va cac bang cot loi CSDL"
    echo "  ./make db-ready     : Kiem tra va tu dong khoi tao CSDL / seed neu con thieu"
    echo "  ./make seed         : Khoi tao CSDL va seed toan bo du lieu mac dinh QNU"
    echo "  ./make reset-db     : Xoa sach CSDL PostgreSQL va Qdrant, sau do seed lai toan bo"
    echo "  ./make reseed       : Alias cua reset-db"
    echo ""
    echo "[Kiem thu tu dong]"
    echo "  ./make test         : Chay toan bo kiem thu Backend (Pytest) va Frontend (npm test)"
    echo "  ./make test-be      : Chay rieng kiem thu Backend voi Pytest"
    echo "  ./make test-fe      : Chay rieng kiem thu Frontend (npm test)"
    echo ""
    echo "[Chat luong ma nguon - Code Quality]"
    echo "  ./make lint         : Kiem tra linter Backend (Ruff) va Frontend (Biome)"
    echo "  ./make lint-fix     : Tu dong sua loi linter ca Backend va Frontend"
    echo "  ./make typecheck    : Kiem tra kieu du lieu TypeScript Frontend (tsc --noEmit)"
    echo "  ./make build        : Kiem tra dong goi build Frontend bundle (vite build)"
    echo ""
    echo "[Kho tri thuc - Knowledge Operations]"
    echo "  ./make reconcile    : Kiem tra doi soat 4 tang (Postgres, Qdrant, MinIO, Redis)"
    echo "  ./make reindex      : Danh lai chi muc vector Qdrant"
    echo "=============================================================================="
    ;;
esac
