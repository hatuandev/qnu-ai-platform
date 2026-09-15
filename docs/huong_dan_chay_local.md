# HƯỚNG DẪN KHỞI CHẠY DỰ ÁN CỤC BỘ (LOCAL DEVELOPMENT GUIDE)

> **Dự án**: QNU AI Platform — Nền Tảng Điều Phối Trợ Lý AI Toàn Diện ĐH Quy Nhơn  
> **Cập nhật**: Tháng 09/2026  
> **Hệ điều hành hỗ trợ**: Windows 10/11, macOS, Linux (Khuyến nghị dùng PowerShell trên Windows)

---

## 📋 MỤC LỤC

1. [Kiến Trúc & Phân Bổ Cổng Dịch Vụ](#1-kiến-trúc--phân-bổ-cổng-dịch-vụ)
2. [Yêu Cầu Tiên Quyết (Prerequisites)](#2-yêu-cầu-tiên-quyết-prerequisites)
3. [Quy Trình Khởi Chạy Từng Bước](#3-quy-trình-khởi-chạy-từng-bước)
   - [Bước 1: Chuẩn bị tệp cấu hình `.env`](#bước-1-chuẩn-bị-tệp-cấu-hình-env)
   - [Bước 2: Khởi động Cơ sở dữ liệu & Dịch vụ nền](#bước-2-khởi-động-cơ-sở-dữ-liệu--dịch-vụ-nền)
   - [Bước 3: Khởi chạy Backend FastAPI](#bước-3-khởi-chạy-backend-fastapi)
   - [Bước 4: Khởi chạy Async Task Worker (Tùy chọn)](#bước-4-khởi-chạy-async-task-worker-tùy-chọn)
   - [Bước 5: Khởi chạy Frontend Studio UI](#bước-5-khởi-chạy-frontend-studio-ui)
4. [Bảng Địa Chỉ & Tài Khoản Mặc Định](#4-bảng-địa-chỉ--tài-khoản-mặc-định)
5. [Kiểm Thử Chất Lượng Mã Nguồn (Verification)](#5-kiểm-thử-chất-lượng-mã-nguồn-verification)
6. [Xử Lý Sự Cố Thường Gặp (Troubleshooting)](#6-xử-lý-sự-cố-thường-gặp-troubleshooting)

---

## 1. KIẾN TRÚC & PHÂN BỔ CỔNG DỊCH VỤ

Khi chạy cục bộ, hệ thống chia thành 3 phần rõ ràng:

```
[ Trình Duyệt Web ]
       │
       ├───► Port 3000 : Frontend Studio UI (Vite 6 + React 19 + Tailwind v4)
       │         │ (Tự động reverse proxy các request /platform/v1alpha1/ sang Backend)
       │         ▼
       ├───► Port 8001 : Backend Core API (FastAPI + Python 3.12 + UV)
       │         │
       │         ├───► Port 5432 : PostgreSQL 16 (Facts, FTS tiếng Việt)
       │         ├───► Port 6333 : Qdrant Vector DB (Embeddings 1024D)
       │         ├───► Port 6379 : Redis 7 (Cache + ARQ Job Queue)
       │         └───► Port 9000 : MinIO S3 (Tài liệu gốc & OCR processed)
       │
       └───► Port 9001 : MinIO Web Console (Quản trị bucket và tệp tin)
```

---

## 2. YÊU CẦU TIÊN QUYẾT (PREREQUISITES)

Trước khi bắt đầu, hãy đảm bảo máy tính của bạn đã cài đặt:

| Phần Mềm | Phiên Bản | Cách Kiểm Tra | Hướng Dẫn Cài Nhanh |
| :--- | :---: | :--- | :--- |
| **Node.js & npm** | `v20+` hoặc `v22+` | `node -v`<br>`npm -v` | Tải tại [nodejs.org](https://nodejs.org/) (LTS) |
| **Python** | `3.12+` | `python --version` | Tải tại [python.org](https://www.python.org/) |
| **Astral UV** | `v0.4+` | `uv --version` | Xem lệnh cài đặt PowerShell bên dưới |
| **Docker Desktop** | Mới nhất | `docker --version` | Dùng để bật nhanh cụm CSDL (PostgreSQL, Qdrant, Redis, MinIO) |

### Cài đặt nhanh trình quản lý gói `uv` (Nếu máy chưa có)

Mở **PowerShell** và chạy lệnh:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
*(Sau khi cài đặt, khởi động lại PowerShell để nhận lệnh `uv`)*.

---

## 3. QUY TRÌNH KHỞI CHẠY TỪNG BƯỚC

### Bước 1: Chuẩn bị tệp cấu hình `.env`

Tại thư mục gốc của dự án (`d:\DuAnPhanMem\qnu-ai-platform`), sao chép tệp mẫu:

```powershell
# Trên Windows PowerShell:
Copy-Item .env.example .env

# Hoặc trên Linux/macOS/Git Bash:
cp .env.example .env
```

Mở tệp `.env` vừa tạo và cập nhật các thông số cần thiết:
- `OPENAI_API_KEY`: Khóa API OpenAI của bạn (hoặc `GEMINI_API_KEY` nếu dùng Google Gemini).
- Nếu chạy thuần bộ nhớ cục bộ mà không muốn dùng S3: đặt `STORAGE_DRIVER=local`.

---

### Bước 2: Khởi động Cơ sở dữ liệu & Dịch vụ nền

Để không phải cài đặt thủ công PostgreSQL, Qdrant, Redis và MinIO lên máy tính, bạn chỉ cần mở **Docker Desktop** và chạy **1 dòng lệnh duy nhất** tại thư mục gốc dự án:

```powershell
docker compose up -d postgres qdrant redis minio
```

> **Ghi chú**: Lệnh trên chỉ khởi động 4 dịch vụ cơ sở dữ liệu hạ tầng rất nhẹ, không build ứng dụng nên mất chưa tới 5 giây để sẵn sàng.

Kiểm tra 4 container đang chạy:
```powershell
docker compose ps
```
Kết quả hiển thị: `qnu_postgres`, `qnu_qdrant`, `qnu_redis`, `qnu_minio` đều ở trạng thái `healthy` hoặc `running`.

---

### Bước 3: Khởi chạy Backend FastAPI

Mở một cửa sổ Terminal/PowerShell thứ nhất:

```powershell
# 1. Đi vào thư mục backend
cd backend

# 2. Cài đặt toàn bộ dependencies tự động qua UV (siêu tốc ~5-10s)
uv sync

# 3. Khởi động Backend API Server với chế độ tự động tải lại khi sửa code (--reload)
uv run uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Khi màn hình xuất hiện:
```text
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```
Backend đã sẵn sàng phục vụ!
👉 **Kiểm tra ngay**: Mở trình duyệt truy cập: [**`http://localhost:8001/docs`**](http://localhost:8001/docs) để xem tài liệu Swagger API tương tác.

---

### Bước 4: Khởi chạy Async Task Worker (Tùy chọn)

Nếu bạn cần thực hiện các tác vụ nặng chạy ngầm (như bóc tách OCR đa tầng, embedding vector số lượng lớn, xuất văn bản Word Nghị định 30):

Mở một cửa sổ Terminal/PowerShell thứ hai:

```powershell
cd backend
uv run arq app.workers.tasks.WorkerSettings
```

---

### Bước 5: Khởi chạy Frontend Studio UI

Mở một cửa sổ Terminal/PowerShell thứ ba:

```powershell
# 1. Đi vào thư mục frontend
cd frontend

# 2. Cài đặt các thư viện Node.js (chỉ cần chạy lần đầu)
npm install

# 3. Khởi động máy chủ phát triển Vite
npm run dev
```

Khi màn hình xuất hiện:
```text
  VITE v6.x.x  ready in 180 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```
Frontend đã sẵn sàng!
👉 **Kiểm tra ngay**: Mở trình duyệt truy cập: [**`http://localhost:3000`**](http://localhost:3000)

> **💡 Tính năng thông minh Offline Seed Fallback**:  
> Nếu bạn chưa bật Backend hoặc Backend tạm thời ngắt kết nối, Frontend vẫn hiển thị **100% giao diện mượt mà** với dữ liệu mẫu chuẩn QNU (05 Trợ lý, Kho tri thức, ModelOps, DAG Studio, Chat Playground) mà **không bị lỗi hay sập trang**!

---

## 4. BẢNG ĐỊA CHỈ & TÀI KHOẢN MẶC ĐỊNH

| Phân Hệ / Dịch Vụ | Địa Chỉ Truy Cập (URL) | Tài Khoản / Mật Khẩu Mặc Định |
| :--- | :--- | :--- |
| **QNU Studio UI** | [http://localhost:3000](http://localhost:3000) | Không yêu cầu đăng nhập (Dev Mode) |
| **Backend REST API** | [http://localhost:8001](http://localhost:8001) | Endpoint gốc |
| **Swagger Interactive Docs** | [http://localhost:8001/docs](http://localhost:8001/docs) | Thử nghiệm trực tiếp 30+ REST endpoints |
| **Redoc API Documentation** | [http://localhost:8001/redoc](http://localhost:8001/redoc) | Xem đặc tả OpenAPI chi tiết |
| **MinIO Object Storage Console**| [http://localhost:9001](http://localhost:9001) | User: `qnu_minio_admin`<br>Pass: `qnu_minio_secret_2026` |
| **Qdrant Vector DB REST** | [http://localhost:6333](http://localhost:6333) | Vector Search & Collections |
| **PostgreSQL 16** | `localhost:5432` | User: `qnu`<br>Pass: `qnu_password_secure_2026`<br>DB: `qnu_ai_platform` |
| **Redis Cache** | `localhost:6379` | Không yêu cầu mật khẩu |

---

## 5. KIỂM THỬ CHẤT LƯỢNG MÃ NGUỒN (VERIFICATION)

Bạn có thể chạy kiểm thử độc lập bất kỳ lúc nào để bảo đảm hệ thống đạt chuẩn 100%:

### 5.1. Kiểm thử Frontend
```powershell
cd frontend

# Kiểm tra Linter cú pháp & định dạng (Biome)
npm run lint

# Kiểm tra tính toàn vẹn kiểu dữ liệu TypeScript
npm run typecheck

# Đóng gói kiểm tra bản build Production
npm run build
```

### 5.2. Kiểm thử Backend
```powershell
cd backend

# Kiểm tra linter code style (Ruff)
uv run ruff check .

# Chạy trọn bộ 68 ca kiểm thử đơn vị & tích hợp (Pytest)
uv run --extra dev pytest -v
```

---

## 6. XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### 🔴 Lỗi 1: Trùng cổng (Port Already in Use - 3000 hoặc 8001)
Nếu có ứng dụng khác đang chiếm cổng `8001` hoặc `3000`:
- **Tìm tiến trình đang chiếm cổng** (trên Windows PowerShell):
  ```powershell
  netstat -ano | findstr :8001
  ```
- **Tắt tiến trình bằng PID**:
  ```powershell
  taskkill /PID <MÃ_PID_TÌM_ĐƯỢC> /F
  ```

### 🔴 Lỗi 2: Không thể kết nối tới PostgreSQL hoặc Qdrant
- Kiểm tra xem Docker Desktop đã được bật hay chưa.
- Chạy lại lệnh:
  ```powershell
  docker compose up -d postgres qdrant redis minio
  ```
- Kiểm tra log của container để xem nguyên nhân:
  ```powershell
  docker compose logs postgres
  docker compose logs qdrant
  ```

### 🔴 Lỗi 3: Chưa có API Key của OpenAI / Gemini
- Nếu chưa có API key của bên thứ 3, bạn vẫn có thể trải nghiệm toàn bộ các màn hình Quản trị, Xem cấu trúc DAG Canvas, Quản lý kho tri thức và tra cứu quy chế.
- Đối với tính năng chat AI: Bạn có thể đăng ký tài khoản Google AI Studio miễn phí để lấy `GEMINI_API_KEY` và điền vào tệp `.env`.

---

## 7. CÁCH DỪNG VÀ TẮT DỊCH VỤ

1. **Tắt ứng dụng Frontend và Backend**:
   - Bấm tổ hợp phím `Ctrl + C` trên các cửa sổ Terminal đang chạy `npm run dev` và `uvicorn`.
2. **Dừng các container cơ sở dữ liệu**:
   ```powershell
   # Tạm dừng các container (giữ nguyên dữ liệu)
   docker compose stop

   # Hoặc tắt hoàn toàn các container
   docker compose down
   ```
