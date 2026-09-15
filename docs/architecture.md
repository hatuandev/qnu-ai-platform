# Thuyết Minh Kiến Trúc Hệ Thống — QNU.AI Platform

## 1. Tầm Nhìn & Mục Tiêu

QNU.AI Platform là nền tảng AI trung gian (AI Middleware & Workflow Platform) phục vụ toàn diện công tác Chuyển đổi số Trường Đại học Quy Nhơn, hợp nhất 05 lĩnh vực trọng điểm:
1. **Tư vấn Tuyển sinh** (`admissions`)
2. **Quy chế & Quy định Đào tạo** (`regulations`)
3. **Khai thác Tài nguyên Thư viện** (`library`)
4. **Hỗ trợ Soạn thảo Văn bản Hành chính** (`drafting`) theo chuẩn Nghị định 30/2020/NĐ-CP
5. **Ngân hàng Câu hỏi & Đề thi** (`question_bank`) theo chuẩn đầu ra Bloom

## 2. Kiến Trúc Phân Tầng Theo Tính Năng (Feature-Driven)

```
[ Frontend: QNU Studio UI (Next.js 15, React 19) ]
                       │ (REST / WebSocket / SSE)
                       ▼
[ Backend API Gateway & Routers (FastAPI) ]
  ├── /knowledge   : Quản lý bộ sưu tập tri thức, Ingest đa định dạng, Chunking
  ├── /rag         : Hybrid Search (Dense BGE-M3 + Sparse Postgres FTS + BGE-Reranker v2)
  ├── /assistants  : Quản lý Trợ lý AI, Seeder 5 trợ lý chuẩn, Bundle Packaging
  ├── /workflows   : DAG Runtime Engine, Thư viện Nodes (Input, Route, Approval, Tool, Export)
  ├── /channels    : Đa kênh phân phối (Web Widget nhúng, Messenger, Zalo) & Live Human Handoff
  ├── /modelops    : Quản lý LLM Providers (OpenAI, Gemini, Local vLLM/Ollama), Model Profiles
  ├── /tools       : Tool Gateway tích hợp cổng UIS đào tạo, tính học phí, kèm PII Masking
  ├── /ocr         : Đa bộ máy OCR (PaddleOCR, RapidOCR, PyMuPDF)
  ├── /evaluation  : Đánh giá chất lượng Ragas (Hit Rate >= 90%, Faithfulness >= 95%, TM-08)
  └── /system      : Quản lý API Keys, Giám sát Worker & Sao lưu Snapshot 1-Click
                        │
        ┌───────────────┼───────────────┬───────────────┐
        ▼               ▼               ▼               ▼
 [ PostgreSQL 16 ]  [ Qdrant DB ]   [ Redis 7 ]   [ MinIO S3 ]
 (Metadata, Facts,  (Vectors 1024D  (Semantic     (Raw Documents,
  FTS tiếng Việt)    BGE-M3)         Cache, ARQ)   Artifacts NĐ30)
```

## 3. Các Đặc Tuyến Kỹ Thuật Nổi Bật

1. **MinIO Object Storage Pipeline**: Toàn bộ tệp tải lên (PDF tuyển sinh, Word quy chế) được lưu trữ bền vững tại MinIO Object Storage trước khi chuyển sang tầng bóc tách dữ liệu; các thành phẩm do AI sinh ra (Word NĐ 30, Excel Bloom) cũng được lưu trữ an toàn tại MinIO.
2. **Structured Fact Layer**: Trích xuất bảng biểu thành các bản ghi sự thật (điểm chuẩn, học phí, chỉ tiêu, mã ngành) giúp truy xuất chính xác 100% không bị hallucination.
3. **Citation Guard & Groundedness Policy**: Bắt buộc câu trả lời RAG phải có trích dẫn nguồn có kiểm định.
4. **Worker Bất đồng bộ ARQ**: Thuần `asyncio` Python, nhẹ, nhanh, tương thích tốt từ Windows đến Linux.
