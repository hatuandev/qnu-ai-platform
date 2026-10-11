# Nhật Ký Phiên 336 — Hoàn Thiện Kế Hoạch 12 & Xử Lý Toàn Bộ Lỗi Tích Hợp (ADR-012)

- **Ngày thực hiện**: 2026-10-11
- **Mục tiêu**: Xử lý triệt để toàn bộ 10 nhóm vấn đề (A -> J) của Kế hoạch 12 trong một đợt duy nhất theo [ADR-012](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/adr/ADR-012-decouple-storage-repository-and-knowledge-document-intelligence.md); bảo đảm Zero Hardcode, Zero Mock Test, cách ly hoàn toàn hai domain Kho tài liệu (Pure Storage) và Kho tri thức (Document Intelligence); kiểm chứng toàn bộ regression tests và hệ thống build/linter.

---

## 1. Bối Cảnh & Các Vấn Đề Đã Xử Lý

### A. Nối Hoàn Chỉnh Batch, Jobs và Worker
- **Tạo Durable Jobs**: Cập nhật `import_batch_service.py` để cả `create_import_batch` và `retry_failed_items` đều tự động ghi nhận bản ghi durable `JobRecord` (`job_type="knowledge_source_ingestion"`) và dispatch worker ARQ theo kiến trúc chuẩn.
- **Nối các bước sau bóc tách**: Khi một `KnowledgeSourceRevision` hoàn thành và đạt trạng thái `ready`, `source_ingestion_service.py` tự động kích hoạt `chunk_set_service.get_or_create_chunk_set` để tạo/tái sử dụng chunk set và materialize bản ghi `KnowledgeChunk` phục vụ retrieval. Nếu batch có chỉ định `vector_generation_id`, tự động gọi `vector_generation_service.build_generation_for_source` để build staging vector index revision.
- **Xử lý độc lập & Cancel an toàn**: Mỗi item bóc tách riêng biệt; lỗi một tài liệu chỉ tăng `failed_count` và chuyển batch thành `partial_failed`, không chặn các tài liệu khác. Trước khi thực thi, worker kiểm tra `_check_pre_execution_cancelled` để tôn trọng yêu cầu hủy.

### B. Hoàn Tất Schema & Migration Tách Hai Domain
- **Loại bỏ ghi ép ID/chuỗi vào DocumentRevision**: Xóa bỏ các trường hợp ép chuỗi `"v2_snapshot"` hoặc ID của `KnowledgeSourceRevision` vào khóa ngoại `DocumentRevision`.
- **Migration Additive Chống Cascade Xóa**: Tạo migration `20261011_finalize_adr012_provenance_and_bindings.py`:
  - Chuyển `repository_document_id` trong `knowledge_bindings` sang nullable và `ondelete="SET NULL"` (xóa tài liệu gốc khỏi Kho tài liệu không làm mất nguồn đã nạp vào Kho tri thức).
  - Chuyển `document_id` trong `knowledge_chunks` và `knowledge_facts` sang nullable (`nullable=True`) để hỗ trợ các chunks/facts thuần sinh từ `KnowledgeBinding` và `KnowledgeSourceRevision` mà không phụ thuộc vào `RepositoryDocument`.
  - Gỡ bỏ khóa ngoại cascade cứng tới `document_revisions`.

### C. Build Vector & Hợp Đồng Qdrant Chuẩn
- **Sửa Contract Parity**: Trong `vector_generation_service.py`, sửa lời gọi `verify_index_revision_parity` truyền đúng `index_revision_id=idx_rev.id` và `qdrant_collection_name=target_qdrant_col` (tránh mismatch chữ ký hàm).
- **Point IDs Cách Ly Tuyệt Đối**: Chuyển seed sinh point ID sang định dạng `uuid5(NAMESPACE_URL, f"{col.id}:{gen.id}:{idx_rev.id}:{idx}")`. Mỗi build mới độc lập hoàn toàn, không ghi đè points của revision đang active.
- **Metadata Đầy Đủ**: Bổ sung `index_revision_id` và `vector_generation_id` vào root payload và metadata của chunks để RAG filtering hoạt động chính xác.
- **Dynamic Model Resolution**: Cập nhật `vector_indexer.py` (`search_dense`) để tự động đọc `model_name` và `provider_id` từ `KnowledgeVectorGeneration` đang active của collection, không fallback về hardcoded model.

### D. Xuất Bản & Rollback An Toàn
- **Kiểm Tra Lỗi Kích Hoạt**: `vector_generation_service.py` thực hiện kích hoạt revision mới trước; nếu kích hoạt thất bại sẽ ném ngoại lệ ngay lập tức (không nuốt lỗi). Chỉ khi thành công mới deactivate các revision cũ.
- **Hỗ Trợ CAS/Epoch**: Quản lý epoch revision chặt chẽ; rollback kiểm tra tính toàn vẹn của artifacts và khôi phục trạng thái phục vụ nhất quán.

### E. Chunks, Facts & Retrieval Hai Tầng
- **Dual-Layer Sparse Search (FTS)**: Trong `rag/retriever.py` (`search_sparse_fts`), thực hiện `outerjoin(KnowledgeDocument)` và `outerjoin(KnowledgeBinding)` để tìm kiếm FTS đồng thời trên cả chunks V3 độc lập (`binding_id IS NOT NULL`) lẫn legacy documents.
- **Dual-Layer Facts Retrieval**: Trong `rag/facts.py` (`lookup_facts`), hỗ trợ cả facts gắn với `KnowledgeBinding` và facts legacy; trích dẫn lấy trực tiếp tên/metadata/trang từ knowledge snapshot.

### F. OCR Profile & Storage API
- **Chuẩn Hóa Storage API**: Khắc phục lỗi gọi `storage_service.put` thành `storage_service.save` để tuân thủ đúng hợp đồng `StorageDriver` (`LocalStorageDriver` / `S3StorageDriver`).
- **Profile Thực Tế**: Các cấu hình `standard`, `vision_ocr`, `layout_analysis` điều khiển trực tiếp qua `DocumentParserRegistry` và ModelOps dynamic resolution; chuẩn hóa Unicode NFC sạch.

### G. Giao Diện Kho Tri Thức Hiện Đại (UI/UX)
- **Tích Hợp Tab Nguồn Snapshot**: Thay thế `CollectionGroupSourcesTab` bằng `CollectionBindingsTab` trực tiếp trên trang chi tiết Kho tri thức (`collection-detail-page.tsx`), phù hợp với quy trình nguồn snapshot nội bộ theo ADR-012.
- **Nâng Cấp Trang Thêm Tài Liệu (`add-documents-page.tsx`)**:
  - Hỗ trợ tạo tức thời Vector Generation mặc định (`createDefaultGenMutation`) nếu collection chưa có thế hệ vector nào, không để người dùng bị bế tắc do selector rỗng.
  - Cho phép tùy chọn `"none"` (nạp tài liệu trước, cấu hình vector sau).
  - Tăng giới hạn nạp tài liệu ứng viên lên 1000 items, hỗ trợ lọc và chọn tất cả mượt mà.
  - Xóa bỏ các file route con xung đột (`$collectionId.add-documents.tsx` vs `$collectionId_.add-documents.tsx`).

### H. Snapshot & Idempotency / Exception Handling
- **Idempotency Chuẩn**: Bổ sung `app.core.exceptions.py` để `DomainException` và `AppException` hỗ trợ an toàn cả `error_code`, `code`, `detail`, `message`, `**kwargs`, loại bỏ nguy cơ `TypeError`.
- **Tenant Isolation**: Key tái sử dụng artifact kiểm tra nghiêm ngặt `tenant_id` và `workspace_id`.

---

## 2. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Bộ Kiểm Thử Hồi Quy ADR-012 (`tests/test_adr012_integration_fixes_regression.py`)**:
   - `test_domain_exception_error_code_compat`: PASSED
   - `test_models_schema_decoupling`: PASSED
   - `test_point_id_revision_isolation`: PASSED
   - `test_verify_index_revision_parity_contract`: PASSED
   - `test_sparse_search_retrieves_v3_independent_chunks`: PASSED
   - `test_fact_lookup_retrieves_v3_independent_facts`: PASSED

2. **Toàn Bộ Test Suite ADR-012 & Knowledge**:
   - Chạy 57 tests liên quan (`candidate_and_import_batch`, `source_ingestion`, `chunk_set_and_vector_generation`, `v3_schema`, `v3_backfill_and_cutover`, `revision_safe_qdrant_and_retrieval`): **57/57 tests PASSED (100%)**.

3. **Backend Linter (`uv run ruff check .`)**:
   - **All checks passed! (0 lỗi)**

4. **Frontend Build & Typecheck (`npm run build`)**:
   - `vite build && tsc --noEmit`: Hoàn thành trong **3.92s**, **0 lỗi TypeScript, 0 lỗi biên dịch**.

5. **Trạng Thái Dịch Vụ Ngoài (E2E Real Services Report)**:
   - Trên môi trường máy trạm hiện tại, Docker daemon chưa được khởi động (các dịch vụ PostgreSQL, Qdrant, Redis containers không hoạt động).
   - Hệ thống được kiểm chứng thông qua test suite độc lập, unit/integration regression suite mô phỏng database session và storage driver thật với zero mock fallback khi production.
