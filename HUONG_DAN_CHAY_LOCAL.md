# 🚀 HƯỚNG DẪN KHỞI CHẠY DỰ ÁN CỤC BỘ (LOCAL RUN GUIDE)

> Tài liệu này hướng dẫn chi tiết cách khởi chạy toàn bộ nền tảng **QNU AI Platform** trên máy tính cá nhân (Localhost).  
> Tệp gốc chi tiết: [`docs/huong_dan_chay_local.md`](./docs/huong_dan_chay_local.md)

---

## ⚡ KHỞI CHẠY NHANH TRONG 3 BƯỚC

### 1. Chuẩn bị biến môi trường
```powershell
# Copy tệp môi trường từ mẫu
cp .env.example .env
```

### 2. Khởi động cụm hạ tầng nền (Postgres, Qdrant, Redis, MinIO, Gotenberg)
*(Chỉ cần mở Docker Desktop và chạy 1 dòng lệnh siêu nhẹ, mất ~3 giây)*:
```powershell
docker compose up -d
# hoặc dùng: make infra-up / .\run.ps1 infra-up
```

### 3. Khởi động Backend API (Port 8001) & Frontend Studio (Port 3000)

> 💡 **Cách nhanh nhất (Khuyên dùng)**:
> - Sử dụng Makefile: `make dev` (hoặc `make be` / `make fe` từng phân hệ)
> - Sử dụng PowerShell: `.\run.ps1 dev` (hoặc `.\run.ps1 be` / `.\run.ps1 fe`)
> Lệnh này sẽ tự động mở 2 cửa sổ chạy song song cả Backend và Frontend!

**Hoặc chạy thủ công trong 2 Terminal riêng biệt:**

**Terminal 1 — Backend FastAPI**:
```powershell
cd backend
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
👉 Kiểm tra API Docs: [http://localhost:8001/docs](http://localhost:8001/docs)

**Terminal 2 — Frontend Studio UI**:
```powershell
cd frontend
npm install
npm run dev
```
👉 Mở giao diện ứng dụng: [http://localhost:3000](http://localhost:3000)

---

## 📌 BẢNG ĐỊA CHỈ TRUY CẬP

| Dịch Vụ | Địa Chỉ URL | Tài Khoản / Ghi Chú |
| :--- | :--- | :--- |
| **QNU Studio UI** | [http://localhost:3000](http://localhost:3000) | Giao diện Quản trị & Chat Studio (13 màn hình) |
| **Backend REST API** | [http://localhost:8001](http://localhost:8001) | Endpoint FastAPI Core |
| **Swagger API Docs** | [http://localhost:8001/docs](http://localhost:8001/docs) | 30+ endpoints tương tác |
| **MinIO S3 Console** | [http://localhost:9001](http://localhost:9001) | User: `qnu_minio_admin` / Pass: `qnu_minio_secret_2026` |
| **Qdrant Vector DB** | [http://localhost:6333](http://localhost:6333) | Vector DB REST API |
| **Gotenberg 8 PDF** | [http://localhost:3005](http://localhost:3005) | Chuyển đổi PDF Nghị định 30 (LibreOffice headless) |

---

📖 *Để xem hướng dẫn chi tiết về khắc phục sự cố, cài đặt UV, chạy Async Worker ngầm và kiểm thử chất lượng mã nguồn, vui lòng đọc tệp đầy đủ tại:*  
👉 [**`docs/huong_dan_chay_local.md`**](./docs/huong_dan_chay_local.md)
