# QNU.AI Platform — Nền Tảng Điều Phối Trợ Lý AI Toàn Diện

> **QNU.AI Platform** là nền tảng AI trung gian (AI Middleware & Workflow Platform) và bộ công cụ điều hành Trợ lý Số Thông minh phục vụ Chuyển đổi số Trường Đại học Quy Nhơn.
> Hệ thống thiết kế và vận hành 05 mô-đun trợ lý ảo chuyên trách theo thuyết minh đề tài:
> 1. **Mô-đun trợ lý ảo tư vấn tuyển sinh** — Trợ lý AI: *Trợ lý ảo Tư vấn Tuyển sinh* (`admissions`) \| Kho tri thức: *Kho Tri Thức Đề Án Tuyển Sinh* (`col_admissions`)
> 2. **Mô-đun trợ lý ảo tư vấn quy chế, quy định** — Trợ lý AI: *Trợ lý ảo Tư vấn Quy chế, Quy định* (`regulations`) \| Kho tri thức: *Kho Tri Thức Quy Chế & Quy Định Đào Tạo* (`col_regulations`)
> 3. **Mô-đun trợ lý ảo hỗ trợ soạn thảo văn bản** — Trợ lý AI: *Trợ lý ảo Hỗ trợ Soạn thảo Văn bản* (`drafting`) \| Kho tri thức: *Kho Tri Thức Thể Thức & Biểu Mẫu Văn Bản* (`col_drafting`)
> 4. **Mô-đun trợ lý ảo tra cứu, tư vấn khai thác tài nguyên thư viện** — Trợ lý AI: *Trợ lý ảo Tra cứu & Khai thác Tài nguyên Thư viện* (`library`) \| Kho tri thức: *Kho Tri Thức Tài Nguyên Thư Viện & Học Liệu Số* (`col_library`)
> 5. **Mô-đun trợ lý ảo hỗ trợ tạo câu hỏi, ngân hàng câu hỏi theo chuẩn đầu ra** — Trợ lý AI: *Trợ lý ảo Hỗ trợ Tạo Câu hỏi & Ngân hàng Đề thi theo Chuẩn Đầu ra* (`question_bank`) \| Kho tri thức: *Kho Tri Thức Ngân Hàng Câu Hỏi & Chuẩn Đầu Ra* (`col_question_bank`)

---

## 📌 Phân Bổ Cổng Dịch Vụ (Port Layout)

| Dịch vụ | Địa chỉ URL | Cổng (Port) | Chức năng |
| :--- | :--- | :---: | :--- |
| **QNU Studio UI** | `http://localhost:3000` | `3000` | Giao diện Quản trị, Visual DAG Canvas & Điều phối Trợ lý AI |
| **Backend Core API** | `http://localhost:8001` | `8001` | Cổng REST API, WebSocket & Background Workers |
| **Swagger API Docs** | `http://localhost:8001/docs` | `8001` | Tài liệu tương tác & Kiểm thử toàn bộ REST API |
| **Qdrant Vector DB** | `http://localhost:6333` | `6333` | Cơ sở dữ liệu Vector lưu trữ Embeddings BGE-M3 (1024 chiều) |
| **PostgreSQL 16** | `localhost:5432` | `5432` | CSDL quan hệ lưu Facts, Metadata & Full-text Search tiếng Việt |
| **Redis Cache** | `localhost:6379` | `6379` | Semantic Cache & Hàng đợi tác vụ bất đồng bộ (ARQ) |

---

## 🏗️ Kiến Trúc Hệ Thống (Feature-Driven Architecture)

```
qnu-ai-platform/
├── backend/                  # FastAPI Backend API & ARQ Async Workers (Python 3.12+)
│   ├── app/
│   │   ├── core/             # Cấu hình tập trung, DB, Redis, Storage Driver, Security
│   │   ├── modules/          # Các phân hệ tính năng độc lập (Feature-Driven)
│   │   │   ├── knowledge/    # Kho tri thức: Upload, Ingest, Chunk, Fact Extraction
│   │   │   ├── rag/          # Động cơ RAG: BGE-M3 Dense + FTS Sparse + BGE-Reranker v2
│   │   │   ├── assistants/   # Quản lý Trợ lý AI & Tự động gieo mầm (Seeder) 5 trợ lý chuẩn
│   │   │   ├── workflows/    # Runtime thực thi DAG Workflow & thư viện các Node
│   │   │   ├── channels/     # Đa kênh phân phối, Chat Widget nhúng & Live Human Handoff
│   │   │   ├── modelops/     # Quản trị đa nhà cung cấp LLM (OpenAI, Gemini, vLLM, Ollama)
│   │   │   ├── tools/        # Cổng tích hợp API ngoại vi (UIS, tính học phí) kèm che PII
│   │   │   ├── ocr/          # Định tuyến đa bộ máy OCR (PaddleOCR, RapidOCR, PyMuPDF)
│   │   │   ├── evaluation/   # Đo lường chất lượng Ragas (Hit Rate, Faithfulness, TM-08)
│   │   │   └── system/       # Quản lý API Key, Giám sát Worker & Backup 1-Click
│   │   └── workers/          # Background worker xử lý tác vụ nặng ngầm
│   ├── alembic/              # Quản lý phiên bản CSDL quan hệ (Database Migrations)
│   └── pyproject.toml        # Quản lý dependencies với UV
│
├── frontend/                 # Giao diện Studio UI (Next.js 15, React 19, TypeScript)
│   ├── app/                  # App Router: Dashboard, Assistants, Knowledge, Models...
│   ├── components/           # Micro-components chuẩn Design System (Hỗ trợ Dark/Light Mode)
│   └── lib/                  # API Client & TypeScript Schema Contracts
│
├── configs/                  # Cấu hình 05 lĩnh vực nghiệp vụ & DAG templates (.json)
├── storage/                  # Thư mục lưu trữ tệp cục bộ khi dev (Local Storage Driver)
└── docker-compose.yml        # Cụm dịch vụ hạ tầng (PostgreSQL 16, Qdrant, Redis)
```

---

## 🚀 Khởi Chạy Nhanh Dự Án

### 1. Khởi động hạ tầng cơ sở dữ liệu khi phát triển (Local Dev)
```powershell
docker compose up -d
```

### 2. Khởi động Backend API trên máy Host (Port 8001)
```powershell
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload --env-file ../.env
```

### 3. Khởi động Async Background Worker trên máy Host
```powershell
cd backend
uv run arq app.workers.tasks.WorkerSettings
```

---

## 🚢 Triển Khai Toàn Diện Lên Máy Chủ (Production Deployment)

Hệ thống sử dụng tệp đóng gói duy nhất [`docker-compose.yml`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/docker-compose.yml) cho toàn bộ hạ tầng Backend và dịch vụ nền:

```bash
# 1. Đi vào thư mục dự án
cd qnu-ai-platform

# 2. Tạo tệp cấu hình môi trường từ mẫu và thiết lập các khóa bí mật
cp .env.prod.example .env

# 3. Khởi chạy toàn bộ hệ thống (build & start ngầm)
docker compose up -d --build

# 4. Kiểm tra trạng thái và logs của các container
docker compose ps
docker compose logs -f backend
```

### Danh mục Containers Hoạt Động Trên Production:
- **`qnu_backend`**: FastAPI Core API Engine (`app.main:app`, 4 async workers, cổng 8001).
- **`qnu_worker`**: ARQ Async Task Worker xử lý nền Ingestion, OCR, Reindex vector & Xuất tệp văn bản.
- **`qnu_postgres`**: PostgreSQL 16 lưu trữ Facts, quan hệ và Full-Text Search tiếng Việt (cổng 5432).
- **`qnu_qdrant`**: Qdrant Vector Database lưu trữ Embeddings BGE-M3 1024 chiều (cổng 6333, 6334).
- **`qnu_redis`**: Redis 7 làm Semantic Cache & Job Queue Broker (cổng 6379).
- **`qnu_minio`**: MinIO S3-compatible Object Storage lưu trữ tệp tài liệu thô (cổng 9000, 9001).
- **`qnu_gotenberg`**: Gotenberg 8 chuyển đổi tài liệu Word NĐ 30 sang PDF để xem trước trực tiếp trên web (cổng 3005).

---

## 🔬 Năng Lực Document Intelligence & Bóc Tách Bảng Đa Trang

Nền tảng trang bị bộ bóc tách tài liệu thông minh chuyên sâu cho văn bản hành chính Việt Nam (chuẩn Nghị định 30/2020/NĐ-CP):

- **Thuật toán Nhận diện Hình thái học & Cấu trúc (Zero-Keyword Morphological Table Header Detection)**:
  - 100% không phụ thuộc từ điển từ khóa cố định, tự động nhận diện chính xác tiêu đề bảng trên mọi lĩnh vực (Tài chính, Thời khóa biểu, Tuyển sinh, Y tế, Tiếng Anh).
  - Phân tích 5 tiêu chuẩn hình thái: loại trừ sequence key (`\d+`, `\d+\.\d+`, Roman, mã 7 số), bảo đảm định danh Cột 0, độ dài ô $\le 45$ ký tự, mật độ số/ngày $\le 20\%$, chứa ký tự chữ cái.
- **Tái Cấu Trúc Bảng Đa Trang (Multi-Page Table Stitching)**:
  - Hợp nhất các bảng phụ lục kéo dài từ 3 đến 20+ trang thành 1 Master Table duy nhất.
  - Tự động hàn gắn câu bị ngắt dòng qua trang (Orphan Continuation Rows) và điền tiến phân cấp (Forward-Fill).
  - Khử triệt để số trang rò rỉ ở lề trên ($\le 8\%$) và chân trang ($\ge 88\%$).
- **Hợp Nhất Bảng Song Song (Side-by-Side Fusion)**:
  - Tự động phát hiện các bảng in ngang cùng trục Y (như bảng IELTS và VSTEP) để gộp thành bảng chuẩn 4 cột.
- **Bảo Vệ Toàn Vẹn Dữ Liệu RAG**:
  - Chuẩn hóa Unicode NFC, chống Mojibake 100%, bảo toàn 100% dòng phân cách GFM `|:---|`.
