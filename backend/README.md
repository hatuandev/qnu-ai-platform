# QNU AI Platform — Enterprise Backend Service

Hệ thống Backend trung gian điều phối Trí tuệ Nhân tạo & Động cơ RAG Lai (Hybrid RAG) hiệu năng cao cho Trường Đại học Quy Nhơn (**QNU AI Platform**), xây dựng trên nền tảng **FastAPI (Python 3.12+)**, kiến trúc **Modular Monolith** kết hợp 6 Design Patterns và 5 Trụ cột Production-Ready.

---

## 🏛️ Kiến Trúc Hệ Thống (Modular Monolith)

Hệ thống được tổ chức theo chuẩn phân rã tính năng (**Feature-Driven Modular Architecture**). Mỗi module nội bộ tuân thủ nghiêm ngặt mô hình 4 file chuẩn:
1. `models.py`: Định nghĩa lược đồ dữ liệu SQLAlchemy 2.0 (PostgreSQL `asyncpg`).
2. `schemas.py`: Xác thực dữ liệu đầu vào / đầu ra Pydantic v2.
3. `service.py`: Toàn bộ nghiệp vụ kinh doanh lõi (100% Async I/O, Thin Controller).
4. `router.py`: Tiếp nhận HTTP requests, kiểm tra quyền và định tuyến mã lỗi RFC 7807.

```
backend/
├── alembic/                 # Quản lý phiên bản CSDL (Database Migrations Async)
├── app/
│   ├── core/                # Hạ tầng dùng chung (Security, Storage, Redis, Database, Exceptions, Cost Tracker)
│   ├── modules/
│   │   ├── assistants/      # Quản lý Trợ lý AI & Danh mục 05 Trợ lý Chuyên trách Chuẩn QNU
│   │   ├── evaluation/      # Bộ kiểm định chất lượng liên tục Ragas TM-08 (Faithfulness, Relevance, Precision)
│   │   ├── knowledge/       # Trích xuất văn bản (PDF, DOCX, XLSX, TXT) & Chunking (Điều/Khoản, Semantic)
│   │   ├── modelops/        # Điều phối Multi-Provider LLM, Circuit Breaker 3 trạng thái & Fallback Cascade
│   │   ├── ocr/             # Nhận dạng tài liệu scan (PyMuPDF, PaddleOCR) với cơ chế Graceful Fallback
│   │   ├── rag/             # Động cơ Hybrid RAG: Qdrant Dense + Postgres FTS, RRF k=60, Cross-Encoder Rerank
│   │   ├── tools/           # Gateway Function Calling, Xuất Word NĐ 30, Ma trận Bloom XLSX, Tra cứu điểm chuẩn
│   │   └── workflows/       # DAG Workflow Engine thực thi quy trình nhiều bước & Human-in-the-loop
│   ├── workers/             # ARQ Background Job Queue (Redis) xử lý tác vụ nặng bất đồng bộ
│   └── main.py              # Entrypoint ứng dụng FastAPI, Lifespan, Middlewares & Health Probes
├── tests/                   # Bộ kiểm thử tự động 68 Unit & Integration Tests (Pass 100%)
├── pyproject.toml           # Quản lý phụ thuộc gói qua UV
└── README.md
```

---

## 🤖 05 Trợ Lý AI Chuyên Trách Chuẩn QNU

Nền tảng tích hợp sẵn 5 Trợ lý AI hạt nhân được thiết kế theo đúng quy trình 7 bước (chuẩn `qnu-chatbot-builder`):

| Mã Trợ Lý | Tên Trợ Lý | Lĩnh Vực Chuyên Môn | Công Cụ & RAG Ràng Buộc |
| :--- | :--- | :--- | :--- |
| `admissions_assistant` | **Trợ lý Tuyển sinh QNU** | Điểm chuẩn, chỉ tiêu, học phí, phương thức xét tuyển | `lookup_admission_score`, RAG Tuyển sinh, Structured Facts |
| `regulations_assistant` | **Trợ lý Quy chế Học vụ** | Quy chế tín chỉ, điểm rèn luyện, tốt nghiệp, học bổng | `ClauseBasedChunker` (Điều/Khoản), Hotline điều hướng |
| `library_assistant` | **Trợ lý Thư viện QNU** | Tra cứu giáo trình, luận văn, tài liệu số, giờ mở cửa | Semantic RAG, Khảo sát sách |
| `drafting_assistant` | **Trợ lý Soạn thảo Văn bản** | Soạn thảo thông báo, tờ trình, kế hoạch, quyết định | `export_administrative_document` (Chuẩn NĐ 30/2020/NĐ-CP) |
| `question_bank_assistant` | **Trợ lý Ngân hàng Đề thi** | Sinh câu hỏi trắc nghiệm, tự luận, phân bổ Bloom | `export_exam_matrix` (Xuất ma trận Bloom Excel `.xlsx`) |

---

## 🛡️ 5 Trụ Cột Production-Ready

1. **Security & Guardrails**:
   - Tự động che giấu thông tin định danh cá nhân (**PII Masking**): CCCD, Số điện thoại, Email.
   - Ngăn chặn tấn công **Prompt Injection**, bẻ khóa Jailbreak và rò rỉ System Prompt / API Keys.
   - Cơ chế từ chối an toàn (**No-Answer Policy**): Khi tài liệu thiếu căn cứ xác thực, trợ lý từ chối suy đoán và cung cấp đường dây nóng tuyển sinh chính thức `0256.3846.156`.
2. **Resilience & Fault-Tolerance**:
   - **Circuit Breaker** 3 trạng thái (*Closed, Open, Half-Open*) giám sát sức khỏe từng nhà cung cấp LLM (OpenAI, Gemini, Local vLLM).
   - **Dynamic Fallback Cascade**: Tự động chuyển vùng dự phòng sang LLM hoặc OCR phụ khi engine chính gặp sự cố timeout/hết hạn ngạch.
3. **Observability & FinOps**:
   - Ghi log JSON có cấu trúc tích hợp `correlation_id` xuyên suốt mọi tầng dịch vụ.
   - Bộ theo dõi chi phí (**Cost Tracker**): Tính toán tức thời token và chi phí USD cho từng truy vấn theo biểu giá mô hình.
4. **Data Lifecycle & Ingestion**:
   - Bóc tách đa định dạng: PDF, DOCX, XLSX, TXT kết hợp thuật toán bóc tách cấu trúc Điều/Khoản (`ClauseBasedChunker`).
5. **Quality Evaluation (Ragas TM-08)**:
   - Hệ thống đánh giá chất lượng tự động liên tục theo 3 chỉ số bắt buộc:
     - **Faithfulness** $\ge 0.90$ (Độ trung thực bám sát tài liệu gốc, triệt tiêu bịa đặt).
     - **Answer Relevance** $\ge 0.85$ (Độ phù hợp giải quyết câu hỏi).
     - **Context Precision** $\ge 0.80$ (Độ chính xác xếp hạng ngữ cảnh trích xuất).

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Khởi động Hạ tầng Docker (PostgreSQL, Qdrant, Redis)
Từ thư mục gốc `qnu-ai-platform`:
```bash
docker compose up -d
```

### 2. Cài đặt Môi trường Ảo (với UV)
```bash
cd backend
uv sync
```

### 3. Áp dụng CSDL Migration (Alembic)
```bash
uv run alembic upgrade head
```

### 4. Khởi chạy Backend Server (Hot-Reload)
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
- Swagger API Docs: `http://localhost:8001/docs`
- Redoc Docs: `http://localhost:8001/redoc`
- Liveness Probe: `http://localhost:8001/health/live`
- Readiness Probe: `http://localhost:8001/health/ready`

### 5. Khởi chạy ARQ Background Worker
```bash
uv run arq app.workers.arq_worker.WorkerSettings
```

---

## 🧪 Kiểm Thử Tự Động (Test Suites)

Toàn bộ 68 Unit & Integration tests được tự động hóa 100%:

```bash
# Kiểm tra định dạng mã nguồn & linter
uv run ruff check .

# Chạy toàn bộ test suites
uv run pytest -v
```

Kết quả kiểm thử:
```
======================= 68 passed, 4 warnings in 18.89s =======================
All checks passed!
```
