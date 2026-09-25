.PHONY: dev test infra-up infra-down infra-status infra-logs be fe fe2 dev1 dev2

# Khởi chạy toàn bộ cụm hạ tầng Docker (PostgreSQL, Qdrant, Redis, MinIO, Gotenberg)
infra-up:
	docker compose --profile infra up -d

# Dừng cụm hạ tầng Docker
infra-down:
	docker compose down

# Kiểm tra trạng thái các container hạ tầng Docker
infra-status:
	docker compose ps

# Theo dõi logs của các container hạ tầng Docker
infra-logs:
	docker compose logs -f

# Khởi chạy đồng thời cả Backend (Port 8001) và Frontend cũ (Port 3001)
dev:
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	cmd /c start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"

# Khởi chạy đồng thời cả Backend (Port 8001) và Frontend 2 Mới (Port 3000)
dev1:
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"
	cmd /c start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"

# Alias dev2 -> dev1
dev2: dev1

# Khởi chạy riêng Backend API (Port 8001)
be:
	cmd /c start "QNU Backend API (Port 8001)" cmd /k "cd backend && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

# Khởi chạy riêng Frontend Studio (Port 3001)
fe:
	cmd /c start "QNU Frontend Studio (Port 3001)" cmd /k "cd frontend && npm run dev"

# Khởi chạy riêng Frontend 2 Studio Mới (Port 3000)
fe2:
	cmd /c start "QNU Frontend 2 Studio (Port 3000)" cmd /k "cd frontend2 && npm run dev"

# Chạy toàn bộ kiểm thử tự động
test:
	cd backend && uv run --extra dev pytest
	cd frontend && npm run test:e2e

