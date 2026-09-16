# NHẬT KÝ LÀM VIỆC — Cấu Hình Local Providers (SentenceTransformers, Docling) & Chuẩn Hóa Kiến Trúc MinIO / PostgreSQL

- **Thời gian**: 2026-09-16 15:08 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Thêm 2 Provider Local chuyên trách cho kho dữ liệu theo lựa chọn của người dùng:
     - **Local SentenceTransformers (PyTorch)**: nhúng vector `BAAI/bge-m3` (1024 chiều) chạy offline trên CPU/GPU máy chủ QNU.
     - **Docling Local (IBM Research)**: mô hình `docling-tableformer-local` bóc tách cấu trúc tài liệu và bảng biểu chuyên sâu.
  2. Chuẩn hóa kiến trúc lưu trữ dữ liệu theo đúng nguyên tắc:
     - **MinIO S3**: Lưu trữ 100% tệp tin gốc (PDF, DOCX, XLSX, scan) và tệp thành phẩm. Đặt `STORAGE_DRIVER=s3` mặc định trong `config.py` và `.env`.
     - **PostgreSQL 16**: Lưu toàn bộ siêu dữ liệu, collections, chunks kèm FTS Tiếng Việt và bảng số liệu sự thật (Structured Facts).
     - **Qdrant**: Lưu trữ vector nhúng 1024 chiều cho RAG retrieval.

---

## 1. Chi Tiết Thực Hiện

### 1.1. Cập Nhật CSDL PostgreSQL (`model_provider_configs`)
Hệ thống hiện tại quản lý chính xác 4 provider chất lượng cao:
1. `prov_mistral`: Mistral AI (Model: `mistral-ocr-latest`)
2. `prov_cloudflare`: Cloudflare Workers AI (Model: `@cf/baai/bge-m3`, `@cf/baai/bge-reranker-base`)
3. `prov_sentence_transformers`: Local SentenceTransformers (Model: `BAAI/bge-m3`)
4. `prov_docling`: Docling Local (Model: `docling-tableformer-local`)

### 1.2. Chuẩn Hóa Cấu Hình Storage (`app.core.config` & `app.core.storage`)
- Cập nhật giá trị mặc định của `STORAGE_DRIVER` thành `"s3"`.
- Đồng bộ thông tin xác thực MinIO: `S3_ENDPOINT=http://localhost:9000`, `S3_ACCESS_KEY=qnu_minio_admin`, `S3_SECRET_KEY=qnu_minio_secret_2026`, `S3_BUCKET=qnu-ai-documents`.
- Đảm bảo luồng Ingestion trong `app.modules.knowledge.service` đẩy file gốc trực tiếp lên MinIO thông qua `storage_service.save()`.

### 1.3. Cập Nhật Frontend & Presets
- Mở rộng `PROVIDER_PRESETS` trong backend `schemas.py` và `api-client.ts` frontend.
- Cập nhật `PRESET_SUGGESTED_MODELS` trong `modelops-page.tsx`.

---

## 2. Kết Quả Kiểm Thử (Verification)

1. **Backend Tests**:
   - `uv run ruff check .`: 0 errors.
   - `uv run --extra dev pytest -v`: 73/73 passed (100%).
2. **Frontend Checks**:
   - `npm run lint`: Biome 0 errors.
   - `npm run typecheck`: TypeScript 0 errors.
3. **Browser Visual Verification**:
   - Màn hình `/models` hiển thị đầy đủ 4 Card provider với giao diện tối giản, nhận diện thương hiệu rõ ràng.
