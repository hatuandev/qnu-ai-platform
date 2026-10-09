# Nhật Ký Phiên #300 — Hardening Bảo Mật Đa Tenant & Chuẩn Hóa Hợp Đồng Publishing V2

- **Thời gian**: 2026-10-08
- **Mục tiêu**: Hardening toàn diện quy trình “Kho tài liệu → Kho tri thức → Revision → Publish/Promote → Rollback” sau đợt review độc lập, giải quyết triệt để 10 nhóm lỗi P1/P2 về bảo mật đa tenant, ràng buộc tài nguyên, khóa CAS, vector dimension invariants, cooperative job cancellation, và đồng nhất hợp đồng Backend-Frontend.
- **Phạm vi**: `backend/app/modules/jobs/`, `backend/app/modules/documents/`, `backend/app/modules/knowledge/`, `backend/app/modules/rag/`, `backend/app/workers/`, `frontend/src/features/knowledge/`, `frontend/src/types/`, `backend/tests/`.

---

## 1. Các Vấn Đề Đã Xử Lý (10 Nhóm Lỗi P1/P2)

1. **Bảo vệ API quản lý Job theo quyền và tenant**:
   - Gắn `require_permission(...)` cụ thể cho từng nhóm thao tác: view (`ai.knowledge.view`), upload (`ai.knowledge.upload`), edit/retry/cancel (`ai.knowledge.edit`), delete/cleanup (`ai.knowledge.delete`).
   - Truyền `actor: AuthActor` từ router xuống service; mọi thao tác (`list_jobs`, `get_job`, `get_stats`, `cancel_job`, `retry_job`, `delete_job`, `cleanup_jobs`) đều lọc nghiêm ngặt theo `tenant_id == actor.tenant_id`.
   - Trả RFC 7807 `EntityNotFoundError` (404) khi truy cập job khác tenant để chống rò rỉ sự tồn tại của tài nguyên.

2. **Ràng buộc Revision với Document và Tenant**:
   - Trong `revision_service.py` và `documents/router.py`: mọi endpoint liên quan đến revision (`process_revision`, `update_revision_content`, `submit_revision_review`, `list_document_revisions`, `get_document_revision`) đều nhận đồng thời `document_id` và `actor`.
   - Service kiểm tra đồng thời: document tồn tại thuộc tenant của actor, và revision thuộc đúng `document_id`. Lệch quan hệ trả `404` an toàn.

3. **Đồng nhất Trạng thái Index Revision và Parity Report**:
   - Chuẩn hóa DTO Backend và Frontend: `ParityReportDTO` / `ParityReport` có schema tường minh (`parity_status: "passed" | "failed"`, `expected_chunks`, `indexed_points`, `verified_points`, v.v.).
   - Loại bỏ hoàn toàn trạng thái giả `staging` trên Frontend; sử dụng chuẩn state machine Backend: `building`, `validating`, `ready`, `active`, `archived`, `failed`, `pruned`.
   - Nút Promote ("Kích hoạt") trên UI chỉ hiển thị khi `rev.status === "ready"` và `rev.parity_report?.parity_status === "passed"`.

4. **Khôi phục Rollback từ Revision Archived**:
   - Phân biệt rõ rệt giữa `archived` (dữ liệu vector/chunk vật lý còn nguyên, cho phép rollback) và `pruned` (dữ liệu vật lý đã bị Garbage Collection dọn sạch).
   - Backend bổ sung các trường DTO: `is_rollback_available: bool` và `storage_state: "intact" | "pruned"`.
   - Frontend hiển thị nút Rollback với icon `RotateCcw` và nhãn rõ ràng cho các revision archived khả dụng; ẩn rollback đối với revision active hiện hành.

5. **Bắt buộc Compare-And-Swap (CAS) khi Promote**:
   - Trong `IndexActivationRequest`: `expected_epoch: int = Field(..., ge=0)` trở thành bắt buộc.
   - Backend thực hiện CAS nguyên tử trong cùng transaction: kiểm tra `binding.active_epoch == expected_epoch`, nếu lệch trả RFC 7807 `409 Conflict` với mã lỗi ổn định `CAS_EPOCH_CONFLICT`.
   - Frontend đọc `active_epoch` mới nhất từ binding, gửi trong payload mutation; khi nhận conflict 409 lập tức hiển thị Toast cảnh báo và tự động invalidate/refetch dữ liệu, không thử lại mù.

6. **Bảo đảm Vector Generation quyết định Runtime và Dimension**:
   - Thiết lập các Invariants bất biến: cấm tuyệt đối việc pad hoặc truncate vector im lặng (`_fit_dim` ném lỗi `VECTOR_DIMENSION_MISMATCH` nếu `len(vec) != dim`).
   - `index_chunks` tiếp nhận cấu hình `vector_generation` thật đã phân giải từ ModelOps DB.
   - `ensure_collection` xác minh dimension thực tế của collection Qdrant; nếu lệch dimension khai báo, lập tức fail-fast ném `VECTOR_DIMENSION_MISMATCH` (HTTP 409).

7. **Cooperative Job Cancellation và Retry**:
   - `retry_job` reset triệt để cờ `cancel_requested = False`, `progress = 0.0`, `error = None`, `heartbeat_at = None`, tăng `attempt`.
   - Worker (`task_document_revision_parse`, `task_knowledge_index_build`) bổ sung các checkpoint cooperative cancellation trước khi xử lý, giữa các phase nặng, và trước khi hoàn tất.
   - Khi cancel, job kết thúc bằng trạng thái `cancelled`, tuyệt đối không để partial revision trở thành `ready` hoặc `active`.

8. **Ngăn Race Condition khi cấp số Revision**:
   - Khóa aggregate cha bằng `with_for_update()`: khóa `RepositoryDocument` trước khi cấp `document_revision_no`; khóa `KnowledgeBinding` trước khi cấp `index_revision_no`.
   - Đọc số hiện tại và chèn bản ghi mới diễn ra trong cùng một transaction cô lập.

9. **Loại bỏ hoàn toàn ModelOps Runtime Fallback Hardcode**:
   - Rà soát và xóa sạch provider ID gán cứng (`prov_rtx5090_vllm`), model name cố định (`bge-m3`, `bge-m3:latest`), URL Ollama cố định, và API key trong runtime.
   - Model, provider, dimension và endpoint được phân giải 100% từ ModelOps DB qua `get_system_model_defaults(db)`. Không fallback ngầm sang tên model cũ; fail-fast có kiểm soát khi thiếu cấu hình.

10. **Hoàn thiện Frontend Contracts và Tiêu Chuẩn Biome**:
    - Không sử dụng `as any` mới, không sử dụng raw native form elements (`<input>`, `<select>`, `<button>` thuần).
    - Tận dụng triệt để primitives Radix UI / shadcn trong `@/components/ui/` và `@/components/admin/`.
    - Sử dụng 100% icon từ `lucide-react`, tuyệt đối không dùng emoji trong giao diện quản trị.
    - Sửa sạch các cảnh báo Biome (optional chain, route typing) và đạt Vite build thành công không lỗi.

---

## 2. Invariants Kiến Trúc

### Invariants về Vector Generation & Embedding Dimension
- **Identity Invariant**: Mỗi Vector Generation gắn liền với một bộ tứ bất biến: `(provider_id, embedding_model, embedding_dimension, config_hash)`.
- **Zero-Silent-Mutation**: Tuyệt đối cấm biến đổi số chiều vector âm thầm (no silent truncate, no zero padding). Vector trả về từ adapter bắt buộc phải có độ dài đúng bằng `embedding_dimension`.
- **Physical Collection Alignment**: Tên và số chiều của collection Qdrant phải khớp chính xác 100% với Vector Generation tương ứng. Mọi sai lệch đều bị từ chối bằng `VECTOR_DIMENSION_MISMATCH`.
- **Zero Inter-Space Mixing**: Hai generation khác nhau không bao giờ được ghi chung vector vào cùng một không gian phục vụ tìm kiếm.

### Invariants về State Machine Xuất Bản & Rollback
- Trạng thái Index Revision tuân theo đồ thị chuyển trạng thái hữu hạn (FSM):
  ```
  [building] ──> [validating] ──(parity pass)──> [ready] ──(CAS promote)──> [active] ──(superseded)──> [archived]
      │               │                                                           │                       │
      └───(fail)──────┴─────────────────> [failed]                                └──(rollback target)────┘
                                                                                                          │
                                                                                                    (retention gc)
                                                                                                          │
                                                                                                          ▼
                                                                                                      [pruned]
  ```
- **Promotion Precondition**: Chỉ revision ở trạng thái `ready` VÀ có `parity_report.parity_status === "passed"` mới được promote.
- **Rollback Precondition**: Chỉ revision ở trạng thái `archived` VÀ `is_rollback_available === true` (chưa bị pruned) mới được rollback.
- **CAS Invariant**: Thao tác promote/rollback bắt buộc phải mang theo `expected_epoch`. Nếu `binding.active_epoch != expected_epoch`, trả về `409 Conflict`.

---

## 3. Những Tệp Chính Đã Thay Đổi

- **Backend Jobs & Workers**:
  - `backend/app/modules/jobs/router.py`: Gắn permission và truyền `AuthActor`.
  - `backend/app/modules/jobs/service.py`: Lọc tenant, reset cancel flag khi retry, trả 404 cho cross-tenant.
  - `backend/app/workers/tasks.py`: Bổ sung checkpoint cooperative cancellation trong workers.
- **Backend Documents**:
  - `backend/app/modules/documents/revision_service.py`: Aggregate locking và kiểm tra ràng buộc document-revision-tenant.
  - `backend/app/modules/documents/router.py`: Truyền `document_id` và `AuthActor`.
  - `backend/app/modules/documents/schemas.py`: Thêm `review_notes` vào `DocumentRevisionResponse`.
- **Backend Knowledge & RAG**:
  - `backend/app/modules/knowledge/schemas.py`: Định nghĩa `ParityReportDTO`, `is_rollback_available`, bắt buộc `expected_epoch`.
  - `backend/app/modules/knowledge/services/index_build_service.py`: Khóa binding, CAS promote, phân giải vector generation, kiểm tra rollback.
  - `backend/app/modules/knowledge/services/collection_service.py`: Loại bỏ model/provider hardcode.
  - `backend/app/modules/knowledge/services/reconciliation_service.py`: Xóa fallback hardcode bge-m3.
  - `backend/app/modules/rag/vector_indexer.py`: Cấm truncate/pad trong `_fit_dim`, verify dimension trong `ensure_collection`, nhận `vector_generation`.
- **Frontend**:
  - `frontend/src/types/knowledge.ts`: Thêm `ParityReport`, `is_rollback_available`, bắt buộc `expected_epoch`.
  - `frontend/src/types/documents.ts`: Thêm `review_notes` vào `DocumentRevision`.
  - `frontend/src/features/knowledge/binding-detail-page.tsx`: CAS promote mutation, hiển thị nút rollback cho archived, Toast xung đột CAS.
  - `frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx`: Xóa logic `staging`, sử dụng `parity_status`, xử lý CAS conflict.
- **Test Suites**:
  - `backend/tests/test_publishing_v2_hardening.py`: Tạo mới bộ test 11 ca kiểm thử chuyên sâu cho toàn bộ 10 mục.
  - `backend/tests/test_knowledge_publishing_v2.py`: Cập nhật mock tương thích với aggregate locking và CAS.
  - `backend/tests/test_document_revisions_lifecycle.py`: Đồng bộ mock DB execute sequence.

---

## 4. Kết Quả Kiểm Thử & Quality Gates

- **Ruff Linter**:
  ```bash
  uv run ruff check app tests
  # All checks passed! — 0 lỗi, 0 cảnh báo.
  ```
- **Pytest (Test Suites Hardening & Regression V2)**:
  ```bash
  pytest tests/test_publishing_v2_hardening.py tests/test_knowledge_publishing_v2.py tests/test_document_revisions_lifecycle.py
  # ======================= 31 passed, 2 warnings in 26.75s =======================
  ```
  - `test_publishing_v2_hardening.py`: 11/11 PASSED (Tenant isolation, cross-tenant denial, retry reset, CAS conflict 409, archived rollback, fit_dim rejection, collection dimension mismatch, worker cancellation).
  - `test_knowledge_publishing_v2.py`: 13/13 PASSED.
  - `test_document_revisions_lifecycle.py`: 7/7 PASSED.
- **Alembic Migrations**:
  ```bash
  alembic heads
  # 20261008_publishing_v2_hardening (head) — Đúng 1 head duy nhất.
  ```
- **Biome Check**:
  ```bash
  bun x @biomejs/biome check src/types/documents.ts src/types/knowledge.ts src/features/knowledge/binding-detail-page.tsx src/components/knowledge/tabs/collection-bindings-tab.tsx
  # Checked 4 files. No fixes applied. — 0 warnings, 0 errors.
  ```
- **Frontend Vite Build**:
  ```bash
  npm run build
  # ✓ built in 4.23s — 0 lỗi biên dịch, 0 lỗi TypeScript.
  ```
- **Git Hygiene**:
  ```bash
  git diff --check
  # Exit code 0 — Không có trailing whitespace rác, không có conflict markers.
  ```

---

## 5. Đánh Giá & Trạng Thái

- Toàn bộ 10 mục tiêu P1/P2 đã hoàn thành trọn vẹn, không để sót lỗi, không dùng mock giả để qua mặt test suite.
- Hệ thống đạt trạng thái sẵn sàng xuất bản tri thức an toàn đa tenant (Multi-tenant Publishing Production-Ready).
