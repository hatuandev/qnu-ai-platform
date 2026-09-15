# Hướng Dẫn Triển Khai — QNU.AI Platform

Tài liệu này hướng dẫn chi tiết các bước cài đặt và vận hành hệ thống QNU.AI Platform trên môi trường máy cá nhân (Local Dev) và máy chủ Production.

## 1. Yêu Cầu Tiên Quyết
- **Python**: Phiên bản 3.11 hoặc 3.12 (khuyến nghị dùng trình quản lý `uv`)
- **Node.js**: Phiên bản 20.x trở lên (kèm `npm`)
- **Docker & Docker Compose**: Để khởi chạy PostgreSQL, Qdrant và Redis

## 2. Môi Trường Phát Triển Cục Bộ (Local Dev)

### Bước 1: Khởi động Hạ tầng Dữ liệu
```powershell
# Tại thư mục gốc qnu-ai-platform/
docker compose up -d
```

### Bước 2: Khởi động Backend API (Port 8001)
```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --env-file ../.env
```

### Bước 3: Khởi động Frontend Studio UI (Port 3000)
```powershell
cd frontend
npm install
npm run dev
```

Truy cập:
- Studio UI: `http://localhost:3000`
- API Docs: `http://localhost:8001/docs`

## 3. Môi Trường Triển Khai Production & Dokploy PaaS

Để triển khai toàn diện trên máy chủ Production sử dụng **Dokploy PaaS** (kèm Traefik SSL tự động, bảo vệ CSDL nội bộ và cơ chế đệm SSE Streaming), vui lòng xem chi tiết tại:

👉 [**Cẩm Nang Triển Khai & Công Nghệ Hạ Tầng (docs/trien_khai/)**](./trien_khai/README.md)
- [**Phân tích chuyên sâu công nghệ hạ tầng (01_cong_nghe_ha_tang.md)**](./trien_khai/01_cong_nghe_ha_tang.md)
- [**Quy trình 6 bước triển khai thực tế trên Dokploy (02_quy_trinh_trien_khai_dokploy.md)**](./trien_khai/02_quy_trinh_trien_khai_dokploy.md)
- [**An toàn dữ liệu, sao lưu & xử lý sự cố (03_an_toan_du_lieu_va_van_hanh.md)**](./trien_khai/03_an_toan_du_lieu_va_van_hanh.md)
