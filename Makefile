.PHONY: dev test infra-up infra-down infra-status infra-logs be fe

# Khởi chạy toàn bộ cụm hạ tầng Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)
infra-up:
	docker compose up -d

# Dừng cụm hạ tầng Docker
infra-down:
	docker compose down

# Kiểm tra trạng thái các container hạ tầng Docker
infra-status:
	docker compose ps

# Theo dõi logs của các container hạ tầng Docker
infra-logs:
	docker compose logs -f

# Khởi chạy đồng thời cả Backend (Port 8001) và Frontend (Port 3000)
dev:
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

# Khởi chạy riêng Backend API (Port 8001)
be:
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

# Khởi chạy riêng Frontend Studio (Port 3000)
fe:
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

# Chạy toàn bộ kiểm thử tự động (68 Pytest Backend + 12 Playwright E2E Frontend)
test:
	cd backend && uv run --extra dev pytest
	cd frontend && npm run test:e2e
