# NHẬT KÝ PHIÊN LÀM VIỆC #330: CANDIDATE DIFF VÀ SNAPSHOT IMPORT BATCH ENGINE (ADR-012 PHIÊN 3)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Thời gian thực hiện**: 2026-10-10  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Thực hiện **Phiên 3 của Kế Hoạch 12** ([`docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md)):
1. Xây dựng API và Service duyệt nhóm / tài liệu ứng viên từ phía Knowledge ([`CandidateService`](../../backend/app/modules/knowledge/services/candidate_service.py)).
2. Đánh giá trạng thái 2 chiều trực quan theo ADR-012: `source_state` (`not_imported`, `current`, `update_available`, `processing`, `failed`) và `vector_state` (`not_indexed`, `indexed`, `indexing`, `index_failed`), kèm quy tắc chọn hàng loạt `selectable` & `unselectable_reason`.
3. Xây dựng API và Service quản lý đợt nạp tài liệu hàng loạt ([`ImportBatchService`](../../backend/app/modules/knowledge/services/import_batch_service.py)) hỗ trợ snapshot provenance một chiều, Idempotency-Key và replay chống xử lý trùng, cơ chế `retry-failed` và `cancel`.
4. Bảo đảm bất biến ADR-012: 100% không tạo bản ghi `KnowledgeGroupSource` nào trong toàn bộ quy trình import batch.

---

## 1. Chi Tiết Các Thay Đổi Kiến Trúc & Mã Nguồn

### 1.1. Schemas Mở Rộng ([`backend/app/modules/knowledge/schemas.py`](../../backend/app/modules/knowledge/schemas.py))
- Bổ sung `CandidateGroupItem` và `CandidateGroupListResponse` để tổng hợp số lượng tệp tổng và tệp đã nạp cho từng nhóm tài liệu.
- Hoàn thiện các trường trạng thái 2 chiều trên `RepositoryCandidateItem`: `source_state`, `vector_state`, `imported_file_hash`, `selectable`, `unselectable_reason`.
- Định nghĩa chuẩn `KnowledgeImportBatchCreateRequest`, `KnowledgeImportBatchResponse`, `KnowledgeImportItemResponse`.

### 1.2. Candidate Service ([`backend/app/modules/knowledge/services/candidate_service.py`](../../backend/app/modules/knowledge/services/candidate_service.py))
- `get_candidate_groups`: Duyệt danh sách các `DocumentGroup` trong workspace, đếm chính xác `total_documents` qua `DocumentGroupMembership` và `imported_documents` qua `KnowledgeBinding` trong collection.
- `get_candidate_documents`:
  - Phân giải thế hệ vector mục tiêu `effective_generation_id` (nếu không truyền sẽ tự động tìm active generation của collection).
  - So khớp `RepositoryDocument` (`is_active=True`) với các bản ghi `KnowledgeBinding` và `KnowledgeSourceRevision`:
    - `source_state = "not_imported"` nếu tài liệu chưa từng được nạp.
    - `source_state = "current"` nếu hash hiện tại khớp hash đã nạp (`origin_file_hash` hoặc `canonical_hash`).
    - `source_state = "update_available"` nếu hash tệp gốc đã thay đổi so với bản đã nạp.
  - Đánh giá `vector_state` theo `KnowledgeIndexRevision` gắn với `effective_generation_id` (`indexed`, `indexing`, `index_failed`, `not_indexed`).
  - Xác lập quy tắc chọn thông minh:
    - Cho phép chọn (`selectable=True`) nếu là tài liệu mới, tài liệu cần cập nhật, tài liệu đã có nhưng chưa được embed generation mục tiêu, hoặc tài liệu bị lỗi.
    - Khóa chọn (`selectable=False`) kèm giải thích nếu tài liệu đã có và đã được lập chỉ mục đầy đủ, hoặc đang trong tiến trình xử lý.

### 1.3. Import Batch Service ([`backend/app/modules/knowledge/services/import_batch_service.py`](../../backend/app/modules/knowledge/services/import_batch_service.py))
- `create_import_batch`:
  - Kiểm tra `Idempotency-Key`: replay bản ghi batch hiện có nếu trùng key (bảo đảm idempotent tuyệt đối).
  - Tính toán `request_hash` (SHA-256) từ danh sách document IDs, parser profile, chunk strategy, chunk config và vector generation ID.
  - Tạo `KnowledgeImportBatch` (`status = "queued"`).
  - Snapshot provenance cho từng item: `origin_document_id`, `origin_group_id`, `origin_file_hash`, `origin_title`, `origin_file_name`, `origin_file_type`, `origin_metadata` JSONB.
  - Mỗi item khởi tạo với `phase = "snapshot"` và `status = "queued"`.
- `get_import_batch`: Trả về chi tiết tiến độ batch và danh sách các items con.
- `retry_failed_items`: Khôi phục các item bị lỗi `failed` về `queued` và tăng `retry_count`.
- `cancel_import_batch`: Chuyển batch sang `cancelled` và các item đang chờ sang `skipped` với code `BATCH_CANCELLED`.

### 1.4. Router Knowledge ([`backend/app/modules/knowledge/router.py`](../../backend/app/modules/knowledge/router.py))
- Mở rộng 6 HTTP REST endpoints:
  - `GET /platform/v1alpha1/knowledge/collections/{id}/candidate-groups`
  - `GET /platform/v1alpha1/knowledge/collections/{id}/candidate-documents` (alias `repository-candidates`)
  - `POST /platform/v1alpha1/knowledge/collections/{id}/imports` (tiếp nhận `Idempotency-Key` header)
  - `GET /platform/v1alpha1/knowledge/collections/{id}/imports/{batch_id}`
  - `POST /platform/v1alpha1/knowledge/collections/{id}/imports/{batch_id}/retry-failed`
  - `POST /platform/v1alpha1/knowledge/collections/{id}/imports/{batch_id}/cancel`

---

## 2. Kết Quả Kiểm Thử (Verification)

1. **Kiểm tra Linter (`ruff`)**:
   ```bash
   .venv\Scripts\python.exe -m ruff check app/modules/knowledge/ tests/test_knowledge_candidate_and_import_batch.py
   # All checks passed! (0 lỗi linter)
   ```

2. **Bộ kiểm thử tính năng mới (`test_knowledge_candidate_and_import_batch.py`)**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_knowledge_candidate_and_import_batch.py -v
   # Kết quả: 6/6 passed (100%)
   ```
   - `test_candidate_service_get_candidate_groups`: PASSED
   - `test_candidate_service_state_classification_all_combinations`: PASSED
   - `test_import_batch_service_lifecycle_and_idempotency`: PASSED
   - `test_import_batch_retry_and_cancellation`: PASSED
   - `test_adr012_zero_knowledge_group_source_created`: PASSED
   - `test_api_candidate_and_imports_routes`: PASSED

3. **Kiểm thử hồi quy toàn diện 6 test suites liên quan**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_knowledge_candidate_and_import_batch.py tests/test_knowledge_v3_schema.py tests/test_document_repository_workflow.py tests/test_document_repository.py tests/test_document_revisions_lifecycle.py tests/test_document_revisions_schema.py -v
   # Kết quả: 58 passed, 1 warning in 4.52s (100% pass)
   ```

---

## 3. Kế Hoạch Tiếp Theo (Phiên 4)

Chuyển sang **Phiên 4 của Kế Hoạch 12**:
- Triển khai **Knowledge Source Ingestion Pipeline**:
  - Snapshot tệp gốc và metadata vào domain Knowledge (`KnowledgeSourceRevision`).
  - Di chuyển luồng Parser / Vision OCR / Vietnamese Normalizer (Unicode NFC) / Quality Gate sang service Knowledge.
  - Worker bất đồng bộ xử lý từng import item độc lập (`task_knowledge_source_ingestion`).
  - Hỗ trợ partial failure và review required trung thực.
