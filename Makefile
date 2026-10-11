.PHONY: help dev dev1 dev2 be fe fe2 test test-be test-fe lint lint-fix typecheck build migrate db-check db-ready seed reset-db reseed reconcile reindex infra-up infra-down infra-status infra-logs

# Mac dinh hien thi huong dan su dung
help:
	@echo ==============================================================================
	@echo QNU AI Platform - Danh sach cac lenh Make
	@echo ==============================================================================
	@echo [Ha tang Docker]
	@echo   make infra-up       : Khoi dong cum ha tang Docker (Postgres, Qdrant, Redis, MinIO, Gotenberg)
	@echo   make infra-down     : Dung cum ha tang Docker
	@echo   make infra-status   : Kiem tra trang thai cac container Docker
	@echo   make infra-logs     : Theo doi logs cua cum Docker
	@echo.
	@echo [Phat trien - Local Dev]
	@echo   make dev            : Khoi chay Backend (8001), Frontend (3000) va ARQ worker
	@echo   make worker         : Khoi chay worker nen, co log va tranh mo trung
	@echo   make be             : Khoi chay rieng Backend API (Port 8001)
	@echo   make fe             : Khoi chay rieng Frontend Studio (Port 3000)
	@echo.
	@echo [Co so du lieu va Migration]
	@echo   make migrate        : Chay migration CSDL len Alembic HEAD
	@echo   make db-check       : Kiem tra ket noi, schema va cac bang cot loi CSDL
	@echo   make db-ready       : Kiem tra va tu dong khoi tao CSDL hoac seed neu thieu
	@echo   make seed           : Khoi tao CSDL va seed toan bo du lieu mac dinh QNU
	@echo   make reset-db       : Xoa sach CSDL PostgreSQL va Qdrant, sau do seed lai toan bo
	@echo   make reseed         : Alias cua reset-db
	@echo.
	@echo [Kiem thu tu dong]
	@echo   make test           : Chay toan bo kiem thu Backend (pytest) va Frontend
	@echo   make test-be        : Chay rieng kiem thu Backend voi Pytest
	@echo   make test-fe        : Chay rieng kiem thu Frontend (npm test)
	@echo.
	@echo [Chat luong ma nguon - Code Quality]
	@echo   make lint           : Kiem tra linter Backend (Ruff) va Frontend (Biome)
	@echo   make lint-fix       : Tu dong sua loi linter Backend va Frontend
	@echo   make typecheck      : Kiem tra kieu du lieu TypeScript Frontend
	@echo   make build          : Kiem tra dong goi build Frontend bundle
	@echo.
	@echo [Kho tri thuc - Knowledge Operations]
	@echo   make reconcile      : Kiem tra doi soat 4 tang (Postgres, Qdrant, MinIO, Redis)
	@echo   make reindex        : Danh lai chi muc vector Qdrant
	@echo ==============================================================================

# --- Cum ha tang Docker ---
infra-up:
	docker compose -f docker-compose.infra.yml up -d

infra-down:
	docker compose -f docker-compose.infra.yml down

infra-status:
	docker compose -f docker-compose.infra.yml ps

infra-logs:
	docker compose -f docker-compose.infra.yml logs -f

# --- Co so du lieu va Migration ---
migrate:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db migrate

db-check:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db check

db-ready:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db ensure-ready

seed:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db bootstrap

reset-db:
	cd backend && .\.venv\Scripts\python.exe scripts/reset_and_reseed.py

reseed: reset-db

reconcile:
	cd backend && .\.venv\Scripts\python.exe -m app.cli knowledge reconcile

reindex:
	cd backend && .\.venv\Scripts\python.exe -m app.cli knowledge reindex

# --- Phat trien (Dev Servers) ---
dev:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db ensure-ready
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-worker.ps1
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

dev1: dev
dev2: dev

.PHONY: worker
worker:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-worker.ps1

be:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db ensure-ready
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

fe:
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

fe2: fe

# --- Kiem thu ---
test: test-be test-fe

test-be:
	cd backend && .\.venv\Scripts\python.exe -m pytest

test-fe:
	cd frontend && npm test

# --- Chat luong ma nguon ---
lint:
	cd backend && .\.venv\Scripts\python.exe -m ruff check .
	cd frontend && npm run lint

lint-fix:
	cd backend && .\.venv\Scripts\python.exe -m ruff check --fix .
	cd frontend && npm run lint:fix

typecheck:
	cd frontend && npm run typecheck

build:
	cd frontend && npm run build
