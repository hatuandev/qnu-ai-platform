# Nhật Ký Phiên Làm Việc #292 — 2026-10-07

## 1. Mục tiêu phiên làm việc
- **Thực hiện Phiên 7 (Pha 6)** theo [Kế hoạch triển khai quy trình tiếp nhận một lần & xuất bản tri thức an toàn (Kế hoạch 11)](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và [ADR-011](../adr/011_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md).
- Xây dựng **Legacy Data Backfill & Classification Service** (`CanaryService`):
  - Kiểm kê và phân loại dữ liệu legacy của các tài liệu cũ (`active-parity-ok`, `needs-rebuild`, `pending-intake`).
  - Thực hiện migration an toàn (idempotent), tự động sinh `RepositoryDocument`, `DocumentRevision`, `KnowledgeBinding`, `KnowledgeIndexRevision` v1, gắn thẻ chunks/facts cũ và promote pointer v1.
- Triển khai **Shadow Retrieval Verification Engine**:
  - Đối soát song song giữa luồng truy vấn V1 Legacy và V2 Snapshot Isolation trên cùng câu hỏi.
  - Đo lường độ trễ delta latency p95, xác nhận bất biến rò rỉ tri thức `retrieval_revision_leak_total = 0`.
- Xây dựng bộ kiểm thử tự động toàn diện **End-to-End Canary Testing Suite** (`tests/test_publishing_v2_e2e_canary.py`) bao phủ đầy đủ 10 Bất biến theo ADR-011.

---

## 2. Các tệp đã thay đổi và tạo mới

### Backend
1. [`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py):
   - Thêm `RollbackIndexRevisionRequest`.
   - Thêm `LegacyAuditItem`, `LegacyAuditReport`.
   - Thêm `BackfillRequest`, `BackfillItemResult`, `BackfillReport`.
   - Thêm `ShadowRetrievalRequest`, `ShadowRetrievalReport`.
2. [`backend/app/modules/knowledge/services/canary_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/canary_service.py) *(Mới)*:
   - `audit_collection_legacy_state`: Phân loại tài liệu legacy theo trạng thái chunk và Qdrant point alignment.
   - `backfill_legacy_collection`: Cơ chế di trú an toàn idempotent, liên kết tự động vào V2, gắn nhãn chunk/fact metadata `backfilled=True`, tăng epoch collection.
   - `run_shadow_retrieval_comparison`: Chạy song song V1 vs V2, đo lường Jaccard similarity, latency delta %, và kiểm định `retrieval_revision_leak_total == 0`.
3. [`backend/app/modules/knowledge/services/index_build_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/index_build_service.py):
   - Bổ sung tham số `expected_epoch: int | None = None` trong `promote_index_revision` để bảo vệ Compare-And-Swap (Bất biến 6), trả về HTTP 409 `CAS_EPOCH_CONFLICT` nếu xung đột epoch.
   - Bổ sung hàm `rollback_index_revision` hỗ trợ Instant Zero-Reindex Rollback (Bất biến 8) trong $O(1)$.
4. [`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py):
   - Bổ sung phương thức `count_points_by_document(collection_id, document_id) -> int` tra cứu chính xác số điểm vector trong Qdrant.
5. [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) & [`services/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/__init__.py):
   - Đăng ký `canary_service`, tích hợp các phương thức Canary, Backfill, Shadow test và Rollback vào Facade `KnowledgeService`.
6. [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py):
   - `POST /knowledge/bindings/{binding_id}/rollback`
   - `POST /knowledge/collections/{collection_id}/canary/audit`
   - `POST /knowledge/collections/{collection_id}/canary/backfill`
   - `POST /knowledge/collections/{collection_id}/canary/shadow-test`
7. [`backend/tests/test_publishing_v2_e2e_canary.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_publishing_v2_e2e_canary.py) *(Mới)*:
   - 9 test cases bao phủ toàn diện:
     * `test_e2e_publishing_lifecycle_intake_to_auditable_citations`: Full lifecycle từ intake -> binding -> staging build -> parity gate -> atomic promote -> snapshot resolution -> citations audit trail.
     * `test_staging_isolation_zero_leak`: Staging draft chunks tuyệt đối không xuất hiện trong retrieval.
     * `test_parity_gate_failure_blocks_promotion`: Chặn kích hoạt khi mismatch số lượng, bảo toàn pointer cũ.
     * `test_atomic_cas_concurrency_conflict`: Concurrency compare-and-swap trả về 409 `CAS_EPOCH_CONFLICT`.
     * `test_instant_zero_reindex_rollback`: Rollback tức thì không cần re-index.
     * `test_legacy_audit_and_classification`: Kiểm tra phân loại `active-parity-ok`, `needs-rebuild`, `pending-intake`.
     * `test_idempotent_legacy_backfill`: Di trú an toàn, chạy nhiều lần không trùng lặp.
     * `test_shadow_retrieval_zero_leak_and_latency`: Xác nhận zero leakage và tính toán delta latency.
     * `test_api_routes_canary_and_rollback`: Kiểm tra 4 endpoint REST API V2 mới.

---

## 3. Kết quả kiểm thử & Tiêu chuẩn chất lượng
- **Ruff linter**:
  ```bash
  .venv\Scripts\ruff.exe check app tests
  # All checks passed! (0 lỗi linter)
  ```
- **Bộ kiểm thử E2E Canary V2**:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_publishing_v2_e2e_canary.py -v
  # 9 passed in 5.03s (100% PASS)
  ```
- **Hệ thống Regression Test Suite Toàn Diện (Publishing V2)**:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_document_revisions_schema.py tests/test_document_revisions_lifecycle.py tests/test_knowledge_publishing_v2.py tests/test_retrieval_engine_v2.py tests/test_publishing_v2_e2e_canary.py -v
  # 40 passed in 69.09s (100% PASS)
  ```

---

## 4. Bài học & Điểm lưu ý kiến trúc
1. **Compare-and-Swap (CAS) Protection**: Việc kiểm tra `expected_epoch` trước khi cập nhật pointer giúp loại bỏ triệt để hiện tượng race condition giữa hai phiên phê duyệt đồng thời của cán bộ quản trị.
2. **Deterministic Entity ID**: Khởi tạo thực thể ORM bằng các hàm sinh ID rõ ràng (`rep_doc_...`, `drev_...`) giúp tránh các phụ thuộc ngầm vào cơ chế `default=lambda` của database engine trong môi trường kiểm thử đơn vị hoặc staging backfill.
3. **Shadow Verification Invariant**: Bất biến `retrieval_revision_leak_total = 0` là chốt chặn quan trọng bảo đảm không có bất kỳ chunk rác hoặc chunk đang nháp (staging) nào bị rò rỉ vào câu trả lời của trợ lý AI trước khi cán bộ quản trị bấm duyệt xuất bản.
