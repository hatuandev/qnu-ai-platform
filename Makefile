.PHONY: dev test infra-up infra-down infra-status infra-logs seed reset-db reseed be fe fe2 dev1 dev2

# Khởi tạo CSDL migration và nạp toàn bộ seed data mặc định
seed:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db bootstrap

# Xóa sạch toàn bộ CSDL PostgreSQL & Qdrant, sau đó seed lại toàn bộ 5 mô-đun
reset-db:
	cd backend && .\.venv\Scripts\python.exe scripts/reset_and_reseed.py

reseed: reset-db

# Khởi chạy toàn bộ cụm hạ tầng Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)
infra-up:
	docker compose -f docker-compose.infra.yml up -d

# Dừng cụm hạ tầng Docker
infra-down:
	docker compose -f docker-compose.infra.yml down

# Kiểm tra trạng thái các container hạ tầng Docker
infra-status:
	docker compose -f docker-compose.infra.yml ps

# Theo dõi logs của các container hạ tầng Docker
infra-logs:
	docker compose -f docker-compose.infra.yml logs -f

# Khởi chạy đồng thời cả Backend (Port 8001) và Frontend Studio (Port 3000)
dev:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db ensure-ready
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

# Alias dev1, dev2 -> dev
dev1: dev
dev2: dev

# Khởi chạy riêng Backend API (Port 8001)
be:
	cd backend && .\.venv\Scripts\python.exe -m app.cli db ensure-ready
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

# Khởi chạy riêng Frontend Studio (Port 3000)
fe:
	cmd /c start "QNU Frontend Studio (Port 3000)" cmd /k "cd frontend && npm run dev"

# Alias fe2 -> fe
fe2: fe

# Chạy toàn bộ kiểm thử tự động
test:
	cd backend && uv run --extra dev pytest
	cd frontend && npm run test:e2e
