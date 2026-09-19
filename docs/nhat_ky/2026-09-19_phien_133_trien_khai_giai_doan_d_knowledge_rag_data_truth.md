# NHẬT KÝ LÀM VIỆC — PHIÊN #133 (GIAI ĐOẠN D: KHÔI PHỤC TÍNH ĐÚNG CỦA KNOWLEDGE & RAG)
# Ngày: 2026-09-19 | Người thực hiện: Senior Full-Stack Architect & Enterprise AI Systems Specialist

---

## 1. Mục Tiêu Phiên Làm Việc
Triển khai toàn diện **Giai đoạn D: Khôi Phục Tính Đúng Của Knowledge & RAG (Docs Truth, Vector Parity & RAG Retrieval Flow)** theo kế hoạch chuẩn hóa tại [08_huong_dan_cai_thien_code_tang_diem_danh_gia.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md) (Mục 7, dòng 177-255).

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Chuẩn Hóa Document Lifecycle State Machine (7 Bước Nghiêm Ngặt)
- Chuẩn hóa cỗ máy trạng thái: `uploaded` $\rightarrow$ `extracting` $\rightarrow$ `review_pending` $\rightarrow$ `approved` $\rightarrow$ `indexing` $\rightarrow$ `ready`, và `ready` $\rightarrow$ `archived`.
- **Tách bạch dứt khoát giữa `approved` và `ready`**:
  * `approved`: Trạng thái nghiệp vụ — Cán bộ con người đã xác nhận nội dung bóc tách/OCR là sạch sẽ và chính xác.
  * `ready`: Trạng thái kỹ thuật toàn vẹn — Tất cả chunks đã được tính toán embeddings và nạp thành công vào Qdrant Vector DB (`index_status = "indexed"`). Chỉ khi đạt `status = "ready"` (hoặc `ready`/`approved`), tài liệu mới được phép xuất hiện trong kết quả truy vấn RAG.
  * Nếu xảy ra lỗi vector indexing (mất mạng, Qdrant offline), tài liệu giữ nguyên `status = "approved"`, ghi nhận `index_status = "index_failed"` kèm `index_error` chi tiết để cán bộ reindex mà không làm mất công sức kiểm duyệt của con người.
- Cập nhật trong [backend/app/modules/knowledge/services/ingestion_service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py) và [backend/app/modules/knowledge/services/reconciliation_service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/reconciliation_service.py).

### 2.2. Quy Chuẩn Bắt Buộc 11 Metadata Fields Cho Qdrant Point Payload (Schema Version v1)
- Cập nhật `VectorIndexer.index_chunks` trong [backend/app/modules/rag/vector_indexer.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py):
  * Xác thực nghiêm ngặt 11 trường: `tenant_id`, `workspace_id`, `collection_id`, `document_id`, `document_revision`, `chunk_id`, `document_status`, `is_retrievable`, `content_hash`, `embedding_model`, `payload_schema_version`.
  * Cơ chế **Fail-Fast**: Ném `AppException(code="INVALID_POINT_PAYLOAD", status_code=400)` ngay khi thiếu bất kỳ trường nào, loại bỏ fallback ngầm.
  * Chuẩn hóa `point_id`: Tự động chuẩn hóa và sinh UUID deterministically từ `uuid5(NAMESPACE_URL, f"{collection_id}:{chunk_id}")` nếu không phải integer hoặc UUID hợp lệ, ngăn ngừa 100% lỗi BadRequest từ Qdrant.

### 2.3. Positive Allowlist Retrieval Cho Cả 3 Tầng Dữ Liệu
- Chuyển `VectorIndexer.search_dense` sang cơ chế **Positive Allowlist**:
  * Loại bỏ triệt để blacklist `must_not`.
  * Bắt buộc các điều kiện lọc `must`:
    - `is_active = True`
    - `is_retrievable = True`
    - `document_status in ["ready", "approved"]`
    - `tenant_id` và `workspace_id` khớp chính xác với ngữ cảnh truy vấn.
- Đồng bộ `HybridRetriever.search_sparse_fts` trong [backend/app/modules/rag/retriever.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py):
  * Lọc chỉ lấy documents có `status.in_(["ready", "approved"])`, `is_active=True`, cùng scope `tenant_id`/`workspace_id`.
- Đồng bộ `FactLayer.lookup_facts` trong [backend/app/modules/rag/facts.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/facts.py):
  * Lọc chỉ lấy facts thuộc documents có `status.in_(["ready", "approved"])`, `is_active=True`.
- Cập nhật DTO: Bổ sung `tenant_id` và `workspace_id` vào `SearchRequest` và `AskRequest` trong [backend/app/modules/rag/schemas.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/schemas.py).

### 2.4. Phân Vùng Đa Khách Thuê Cho Semantic Cache (`SemanticCache`)
- Cập nhật `_make_key` trong [backend/app/core/redis.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/redis.py):
  * `rag:cache:{tenant_id}:{workspace_id}:{collection_id}:{model_part}:{policy_version}:{hash}` với `policy_version = "v1"`.
- `invalidate_collection`: Hỗ trợ xóa cả pattern v1 (`rag:cache:*:*:{col}:*`) lẫn legacy (`rag:cache:*:{col}:*`).

### 2.5. Thanh Tra Đối Soát Bền Vững 4 Tầng & CLI Quản Trị
- Cập nhật `reconciliation_service.reconcile_collection` trong [backend/app/modules/knowledge/services/reconciliation_service.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/reconciliation_service.py):
  * Quét 4 tầng CSDL PostgreSQL, Qdrant Vector, MinIO/Local Storage, Redis Cache; phát hiện `orphan_qdrant_point`, `legacy_payload_schema`, `scope_mismatch`, `unretrievable_point_active`, `missing_storage_file`.
  * Hỗ trợ đếm chunk linh hoạt qua cả scalar count lẫn list chunks.
- Bổ sung CLI vào [backend/app/cli.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py):
  * `python -m app.cli knowledge reconcile [--collection-id ID] [--fix]`
  * `python -m app.cli knowledge reindex [--collection-id ID] [--document-id ID]`

### 2.6. Đồng Bộ Seeder Kho Tri Thức (`seeder.py`)
- Cập nhật [backend/app/modules/knowledge/seeder.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py):
  * 5 hàm seed tài liệu mặc định (`regulations`, `drafting`, `admissions`, `library`, `question_bank`) chuyển sang `status="ready"`, `index_status="indexed"`.
  * Cung cấp đủ 11 metadata fields chuẩn v1 cho `_ensure_qdrant_points`.

---

## 3. Bộ Kiểm Thử Mới ([backend/tests/test_rag_data_truth_and_lifecycle.py](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_rag_data_truth_and_lifecycle.py))
- Bao gồm 9 test cases chuyên sâu:
  1. `test_indexer_rejects_missing_metadata`: Kiểm tra fail-fast ném `INVALID_POINT_PAYLOAD` khi thiếu metadata.
  2. `test_indexer_accepts_valid_v1_payload`: Kiểm tra upsert thành công khi đủ 11 fields.
  3. `test_search_dense_positive_allowlist`: Kiểm tra bộ lọc Positive Allowlist không chứa `must_not`.
  4. `test_sparse_fts_positive_allowlist`: Kiểm tra Sparse FTS chỉ lấy tài liệu `ready`/`approved`.
  5. `test_facts_layer_positive_allowlist`: Kiểm tra Facts Layer chỉ lấy tài liệu `ready`/`approved`.
  6. `test_semantic_cache_key_partition`: Kiểm tra key phân vùng `v1` theo tenant và workspace.
  7. `test_document_approval_lifecycle_to_ready`: Kiểm tra chuyển `status = "ready"` khi vector indexing thành công.
  8. `test_document_approval_fails_indexing_stays_approved`: Kiểm tra giữ `status = "approved"` khi indexing thất bại.
  9. `test_reconciliation_detects_discrepancies`: Kiểm tra phát hiện orphan points và legacy schema v1.

---

## 4. Kết Quả Kiểm Thử (Verification)
- **Backend Lint**: `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**.
- **Backend Test Suite**: `uv run --extra dev pytest -v` $\rightarrow$ **280/280 passed (100%), 0 failed, 0 warnings (47.29s)**.
- **Frontend Lint**: `npm run lint` $\rightarrow$ **164 files checked, 0 lỗi**.
- **Frontend Typecheck**: `npm run typecheck` $\rightarrow$ **0 lỗi (tsc --noEmit passed)**.
- **Frontend Build**: `npm run build` $\rightarrow$ **Thành công (✓ built in 9.58s)**.
- **Quy Trình**: Đồng bộ [02_nap_tri_thuc_minio.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md) và [03_hybrid_rag_truy_xuat.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/03_hybrid_rag_truy_xuat.md).
- **Mã Hóa & UTF-8**: 338/338 files sạch Unicode NFC, Zero Mojibake.
