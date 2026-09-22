# Nhật Ký Phiên Làm Việc #194 — Khắc Phục Lỗi Index Kho Tri Thức, Ánh Xạ Mô Hình BGE-M3 & Đồng Bộ Credentials Provider Lúc Khởi Động

- **Thời gian**: 2026-09-22 10:35 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Điều tra và khắc phục triệt để lỗi "Lỗi index" (index_failed) khi nạp tài liệu vào Kho Tri thức, tháo gỡ điểm nghẽn thiếu Cloudflare credentials ở startup và lỗi tải SentenceTransformers với tên model Cloudflare.

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Người dùng thực hiện nạp tệp tài liệu `Thong tin tuyen sinh dai hoc 2026_Lan2-1.pdf` vào Kho Tri thức Đề án Tuyển sinh (`col_admissions`), giao diện hiển thị badge màu đỏ **`! Lỗi index`** kèm biểu tượng tia sét vàng `⚡` (Reindex).

Qua điều tra dữ liệu tác vụ (`JobRecord`) và CSDL:
1. Bản ghi tác vụ `job_1c26a820413d` ghi nhận lỗi chính xác:
   ```json
   {
     "error": "Mô hình embedding (BGE-M3/Cloudflare) không khả dụng. Hệ thống từ chối nạp dữ liệu giả mạo.",
     "index_status": "index_failed",
     "points_reindexed": 0
   }
   ```
2. **Nguyên nhân 1 (Cloudflare Edge Embedding bị bỏ qua)**:
   - Cấu hình hệ thống đặt `EMBEDDING_PROVIDER="cloudflare"` và `EMBEDDING_MODEL="@cf/baai/bge-m3"`.
   - Thông tin Cloudflare `account_id` và token được lưu trong bảng `model_provider_configs` của PostgreSQL.
   - Khi khởi động server FastAPI, hệ thống chưa tự động nạp (sync) thông tin này từ DB vào `settings` của runtime. Do đó `settings.CLOUDFLARE_ACCOUNT_ID` mang giá trị `None`, khiến nhánh Cloudflare GPU nhanh bị bỏ qua.
3. **Nguyên nhân 2 (SentenceTransformer Local Fallback bị lỗi 404 Repository)**:
   - Khi rơi xuống nhánh Local CPU fallback, hàm `_load_model_sync()` gọi `SentenceTransformer(settings.EMBEDDING_MODEL)`.
   - Do `settings.EMBEDDING_MODEL = "@cf/baai/bge-m3"`, Hugging Face Hub từ chối tải vì không tồn tại repo mang tên `@cf/baai/bge-m3` (tên chuẩn trên Hugging Face là `BAAI/bge-m3`).
   - Cả 2 tầng embedding đều không khả dụng, kích hoạt chốt chặn an toàn chống nạp vector giả mạo (Anti-Mock Protection) theo chuẩn AGENTS.md Quy tắc 8.2, ném mã lỗi `EMBEDDING_UNAVAILABLE` 503 và đánh dấu `index_status = "index_failed"`.

---

## 2. Giải Pháp Kỹ Thuật Chi Tiết

### 2.1. Ánh Xạ Tên Mô Hình Chuẩn Hugging Face (`vector_indexer.py`)
- Xây dựng hàm `_resolve_local_model_name(model_name: str) -> str` tự động chuẩn hóa các định danh Cloudflare (`@cf/baai/bge-m3` $\rightarrow$ `BAAI/bge-m3`, `@cf/baai/bge-large` $\rightarrow$ `BAAI/bge-large-en-v1.5`,...).
- Giúp Local SentenceTransformer luôn tải chính xác từ local cache hoặc Hugging Face.

### 2.2. Tự Động Đồng Bộ Credentials Active Providers Lúc Khởi Động (`main.py` & `provider_service.py`)
- Bổ sung phương thức `sync_active_providers_to_runtime(db: AsyncSession)` vào `ProviderService` và `ModelOpsService`.
- Tích hợp vào hàm `lifespan` trong `app/main.py`: tự động quét các Provider đang hoạt động trong CSDL và tiêm credentials (`CLOUDFLARE_ACCOUNT_ID`, tokens, Mistral, OpenAI, Gemini) vào `settings` ngay khi server backend khởi động.
- Kích hoạt Cloudflare Workers AI Edge Embedding (1s) tức thì mà không cần người dùng phải mở trang Quản lý mô hình `/models` trước.

### 2.3. Tự Động Làm Mới Trạng Thái Chỉ Mục Phía Giao Diện (`collection-detail-page.tsx`)
- Thêm `refetchInterval` (3s) cho TanStack Query `allDocuments` khi phát hiện có tài liệu đang ở trạng thái `indexing` hoặc `processing`.
- Giúp giao diện tự động chuyển từ "Đang index" sang "Đã index" ngay khi hoàn tất mà người dùng không cần bấm F5.

---

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)

- **Backend Linter**: `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**.
- **Backend Tests**: `uv run --extra dev pytest tests/test_modelops.py tests/test_knowledge.py tests/test_rag.py` $\rightarrow$ **70/70 passed (100%)**.
- **Frontend Linter**: `npm run lint` $\rightarrow$ **Checked 170 files, 0 errors**.
- **Frontend Typecheck**: `npm run typecheck` $\rightarrow$ **0 errors**.
- **Kiểm tra thực tế**: Gọi `embed_texts` với Cloudflare thành công: 1 vector 1024-dim sinh ra trong <1s.
- **Tài liệu trong CSDL**: `doc_640939cf032e` đã được reindex thành công với 16 chunks đạt chuẩn Qdrant, `status = "ready"`, `index_status = "indexed"`.
