# Nhật Ký Phiên Làm Việc #313: Hoàn Thiện Toàn Diện Quy Trình Kho Tài Liệu & Intake Bất Đồng Bộ V2

- **Thời gian**: 2026-10-10
- **Chủ đề**: Chuẩn hóa luồng nghiệp vụ Kho tài liệu, tích hợp Intake V2 bất đồng bộ, bảo vệ isolation & dedup, chuẩn hóa Chunk Strategy Registry, và khôi phục cầu nối Kho tài liệu → Kho tri thức.
- **Tác giả**: Antigravity (Senior Full-Stack Architect & Enterprise AI Systems Specialist)

---

## 1. Mục Tiêu Phiên Làm Việc

Hoàn thiện toàn diện quy trình Kho tài liệu trên `qnu-ai-platform` theo đúng kịch bản vận hành thực tế:
```text
Danh sách Kho tài liệu (/documents)
→ Tạo Kho tài liệu “Tuyển sinh”
→ Kho mới xuất hiện trong danh sách (refetch/invalidate cache, giữ context người dùng)
→ Mở trang chi tiết Kho Tuyển sinh (/documents/groups/:groupId)
→ Tải tài liệu trực tiếp vào kho này (gọi /documents/intake V2, lưu trữ MinIO S3, bảo vệ dedup & isolation)
→ Theo dõi trạng thái bóc tách (queued, processing, validating, review_required, ready, failed, cancelled)
→ Đưa toàn bộ tài liệu hợp lệ vào một Kho tri thức (preview đầy đủ, strict_ready=True mặc định, hỗ trợ xuất bản một phần)
```

Tôn trọng các giới hạn:
- **Tuyệt đối không sửa `qnu-sso`**.
- Không breaking change schema cũ: giữ nguyên `DocumentGroup`, `DocumentGroupMembership` và deep route `/documents/groups/:groupId` ở application boundary, nhưng **100% UI, thông báo, dialog dùng thuật ngữ "Kho tài liệu" (loại bỏ hoàn toàn từ "nhóm")**.
- Tuân thủ `AGENTS.md` và các skill: `qnu-backend-architect`, `qnu-frontend-architect`, `qnu-knowledge-ingestion`, `qnu-rag-pipeline`.

---

## 2. Các Thay Đổi Kiến Trúc & Kỹ Thuật

### 2.1 CSDL & Migration (Scoped Deduplication)
- **Alembic Migration**: `backend/alembic/versions/20261010_composite_file_hash_deduplication.py`
  - Chuyển `file_hash` unique toàn cục sang composite unique index `uq_repo_docs_tenant_ws_file_hash` trên `(tenant_id, workspace_id, file_hash)`.
  - Giúp bảo vệ đa người thuê (multi-tenant) và đa không gian làm việc (multi-workspace) mà không gây rò rỉ document giữa các phòng ban/đơn vị.
- **Model Update**: `backend/app/modules/documents/models.py`
  - Khai báo `__table_args__` với `UniqueConstraint("tenant_id", "workspace_id", "file_hash", name="uq_repo_docs_tenant_ws_file_hash")`.

### 2.2 Backend Intake Service Layer V2 Orchestration
- **Tập tin**: `backend/app/modules/documents/intake_service.py`
  - **Kiểm tra kho & phân quyền**: Kiểm tra `group_id` tồn tại và thuộc đúng `tenant_id`, `workspace_id` của `AuthActor` trước bất kỳ thao tác lưu trữ nào (trả RFC 7807 404 hoặc 403 nếu vi phạm, không sinh orphan documents).
  - **Scoped Deduplication**:
    - Khi file trùng hash đã tồn tại trong cùng kho: trả kết quả `deduplicated=True`, không tạo document/revision mới, đảm bảo membership idempotent.
    - Khi file đã tồn tại trong workspace nhưng chưa thuộc kho hiện tại: tái sử dụng document, tạo membership vào kho mới, không upload lại S3.
  - **Atomic Orchestration Unit**: Gom việc tạo `RepositoryDocument`, `DocumentRevision`, `DocumentGroupMembership` và `JobRecord` vào cùng một transaction unit với `db.flush()`, commit bền vững một lần trước khi dispatch broker.
  - **MinIO Compensation**: Nếu DB transaction thất bại, cơ chế compensation tự động xóa object đã upload trên MinIO S3, ngăn chặn rác lưu trữ.
  - **Redis Resilient Dispatch**: Nếu Redis broker offline, `JobRecord` giữ nguyên trạng thái `dispatch_status='pending'` với ghi nhận lỗi chi tiết, không rollback transaction tài liệu đã tiếp nhận thành công.

### 2.3 Chuẩn Hóa State Machine & Service
- **Tập tin**: `backend/app/modules/documents/group_service.py`
  - Chuẩn hóa bộ lọc và tính toán KPI theo 7 trạng thái chuẩn của `DocumentRevision`:
    - Chờ xử lý: `queued`
    - Đang xử lý: `processing`, `validating`
    - Cần duyệt: `review_required`
    - Sẵn sàng: `ready`
    - Lỗi: `failed`, `cancelled`
  - Thay thế toàn bộ microcopy "nhóm tài liệu" sang "kho tài liệu".
- **Tập tin**: `backend/app/modules/knowledge/services/binding_service.py`
  - Đổi trạng thái lỗi sang `failed` và `cancelled`.
  - Cập nhật thông điệp lỗi và cảnh báo sang thuật ngữ "kho tài liệu".

### 2.4 Chuẩn Hóa Chunk Strategy Registry
- **Tập tin**: `backend/app/modules/knowledge/chunker.py`
  - Xây dựng `CHUNK_STRATEGY_REGISTRY` chuẩn hóa 4 chiến lược bóc tách cốt lõi:
    - `ClauseBasedChunker`
    - `SemanticChunker`
    - `AdmissionsRecordChunker`
    - `ImplementationTaskChunker`
  - Factory `get_chunker()` trả về đối tượng tương ứng; nếu strategy không hợp lệ, ném `AppException(code="INVALID_CHUNK_STRATEGY", status_code=400)`, tuyệt đối không fallback âm thầm.
- **Frontend Cleanup**:
  - Gỡ bỏ `FixedSizeChunker` khỏi UI `add-documents-page.tsx` và `binding-detail-page.tsx`.

### 2.5 Cập Nhật Frontend & Giao Diện Người Dùng
- **API Client**: `frontend/src/services/documents-api.ts`
  - Bổ sung typed API method `intakeDocument()` gọi `/documents/intake` (HTTP 202) hỗ trợ file, metadata, `group_id`, `idempotency_key`.
  - Chuẩn hóa cấu trúc `Headers` cho fetch.
- **Upload Modal**: `frontend/src/features/documents/components/document-upload-modal.tsx`
  - Chuyển hoàn toàn sang gọi `intakeDocument()`.
  - Quản lý trạng thái theo từng file với 7 trạng thái chuẩn tiếng Việt: `Chờ xử lý`, `Đang xử lý`, `Đang kiểm tra`, `Cần duyệt`, `Sẵn sàng`, `Lỗi`, `Đã hủy`.
  - Không hiển thị thông báo "đã bóc tách thành công" khi server mới chỉ trả HTTP 202 `queued`.
- **Trang Danh Sách Kho**: `frontend/src/features/documents/document-groups-page.tsx`
  - Đổi nhãn nút chính thành `Thêm kho`.
  - Sau khi tạo kho thành công: invalidate cache TanStack Query, giữ nguyên vị trí người dùng trên trang danh sách để thấy kho mới xuất hiện.
  - Sử dụng `<ViewModeToggle />` chuẩn từ `@/components/ui/view-mode-toggle`.
- **Trang Chi Tiết Kho**: `frontend/src/features/documents/document-group-detail-page.tsx`
  - Header trang bố trí rõ 2 nút hành động chính: `Tải lên` và `Đưa vào kho tri thức`.
  - Hiển thị badge trạng thái chuẩn tiếng Việt (`Sẵn sàng`, `Chờ xử lý`, `Đang xử lý`, `Cần duyệt`, `Lỗi`).
  - Hỗ trợ Skeleton khi đang tải, EmptyState và Alert trung thực khi lỗi mạng.
  - Hộp thoại gỡ tài liệu khỏi kho giải thích rõ: chỉ xóa liên kết kho, bảo toàn tài liệu gốc và snapshot đã xuất bản.
- **Hộp Thoại Xuất Bản Tri Thức**: `frontend/src/features/documents/components/attach-group-to-knowledge-dialog.tsx`
  - Tái sử dụng component hiện có, chuẩn hóa 100% microcopy sang "kho tài liệu".
  - Hiển thị tên kho tài liệu nguồn và danh sách chọn kho tri thức đích.
  - Khối preview chi tiết: tổng tài liệu, sẵn sàng, chưa sẵn sàng, đã liên kết.
  - Mặc định `strict_ready = true`: nếu còn file chưa sẵn sàng thì khóa nút xuất bản.
  - Hỗ trợ checkbox chủ động `Cho phép xuất bản một phần` (chỉ đưa các revision `ready` vào kho tri thức, hiển thị số file bị bỏ qua).
  - Invalidate toàn bộ cache sau khi xuất bản thành công.

---

## 3. Danh Sách Tệp Đã Chỉnh Sửa / Tạo Mới

| Tệp | Trạng thái | Mô tả |
| :--- | :--- | :--- |
| `backend/alembic/versions/20261010_composite_file_hash_deduplication.py` | Tạo mới | Migration đổi file_hash unique sang composite (tenant, workspace, file_hash) |
| `backend/app/modules/documents/models.py` | Cập nhật | UniqueConstraint composite cho RepositoryDocument |
| `backend/app/modules/documents/intake_service.py` | Cập nhật | Orchestration atomic unit, isolation, S3 compensation, Redis resilient dispatch |
| `backend/app/modules/documents/router.py` | Cập nhật | Endpoint /documents/intake nhận group_id & actor context |
| `backend/app/modules/documents/group_service.py` | Cập nhật | Chuẩn hóa KPI & bộ lọc theo 7 trạng thái DocumentRevision, đổi terminology |
| `backend/app/modules/knowledge/services/binding_service.py` | Cập nhật | Đổi trạng thái lỗi failed/cancelled, terminology kho tài liệu |
| `backend/app/modules/knowledge/chunker.py` | Cập nhật | CHUNK_STRATEGY_REGISTRY & get_chunker() raise RFC 7807 INVALID_CHUNK_STRATEGY |
| `backend/tests/test_document_repository_workflow.py` | Tạo mới | Suite kiểm thử 12 ca nghiệp vụ thực tế của Kho tài liệu & Intake V2 |
| `frontend/src/services/documents-api.ts` | Cập nhật | Typed method intakeDocument, Headers fix, terminology kho tài liệu |
| `frontend/src/features/documents/components/document-upload-modal.tsx` | Cập nhật | Gọi intake V2, quản lý 7 trạng thái file, trung thực khi queued |
| `frontend/src/features/documents/document-groups-page.tsx` | Cập nhật | Nút "Thêm kho", invalidate cache danh sách, terminology kho tài liệu |
| `frontend/src/features/documents/document-group-detail-page.tsx` | Cập nhật | 2 nút Tải lên & Đưa vào kho tri thức, Skeleton, ConfirmDialog gỡ kho |
| `frontend/src/features/documents/components/attach-group-to-knowledge-dialog.tsx` | Cập nhật | Preview chi tiết, strict_ready mặc định, xuất bản một phần chủ động |
| `frontend/src/features/knowledge/add-documents-page.tsx` | Cập nhật | Loại bỏ FixedSizeChunker khỏi UI options |
| `frontend/src/features/knowledge/binding-detail-page.tsx` | Cập nhật | Loại bỏ FixedSizeChunker khỏi UI options |

---

## 4. Kết Quả Kiểm Thử & Đảm Bảo Chất Lượng

### 4.1 Backend Ruff & Pytest
- **Linter Ruff**:
  ```bash
  uv run ruff check app/modules/documents app/modules/knowledge tests/test_document_repository_workflow.py tests/test_document_groups_and_knowledge_attach.py
  # Output: All checks passed! (0 errors)
  ```
- **Bộ Kiểm Thử Mới (`test_document_repository_workflow.py`)**:
  ```bash
  .venv/Scripts/python.exe -m pytest tests/test_document_repository_workflow.py -v
  # Output: 12 passed in 2.69s (100% pass)
  ```
  1. `test_01_create_document_repository_group_success`: PASSED
  2. `test_02_intake_upload_creates_doc_rev_membership_and_job_in_one_transaction`: PASSED
  3. `test_03_intake_nonexistent_group_raises_404_and_no_orphan_doc`: PASSED
  4. `test_04_intake_mismatched_tenant_workspace_raises_403_no_leak`: PASSED
  5. `test_05_intake_duplicate_upload_same_group_idempotent`: PASSED
  6. `test_06_intake_existing_doc_in_workspace_attaches_to_new_group_no_s3_reupload`: PASSED
  7. `test_07_intake_redis_offline_retains_pending_job_without_rollback`: PASSED
  8. `test_08_publish_only_ready_revisions_to_knowledge_collection`: PASSED
  9. `test_09_strict_ready_rejects_publishing_when_unready_revisions_exist`: PASSED
  10. `test_10_chunk_strategy_factory_resolves_all_canonical_classes`: PASSED
  11. `test_11_invalid_chunk_strategy_raises_rfc7807_no_silent_fallback`: PASSED
  12. `test_12_e2e_workflow_contract_create_group_intake_preview_and_attach`: PASSED

- **Bộ Kiểm Thử Hồi Quy (`test_document_groups_and_knowledge_attach.py`, `test_document_repository.py`)**:
  ```bash
  .venv/Scripts/python.exe -m pytest tests/test_document_groups_and_knowledge_attach.py tests/test_document_repository.py -v
  # Output: 20 passed in 4.60s (100% pass)
  ```

### 4.2 Frontend Biome & Vite Build
- **Biome Linter**:
  ```bash
  npx biome check src/features/documents src/services/documents-api.ts src/routes
  # Output: Checked 120 files in 106ms. No fixes applied. (0 errors)
  ```
- **Vite Build**:
  ```bash
  npm run build
  # Output: ✓ built in 3.96s (Exit code 0, 0 compilation/typecheck errors)
  ```

---

## 5. Kết Luận & Hướng Dẫn Vận Hành

Toàn bộ chu trình nghiệp vụ Kho tài liệu đã được hoàn thiện chặt chẽ, đáp ứng trọn vẹn yêu cầu vận hành sản xuất:
1. Tạo kho tài liệu hiển thị ngay lập tức trên UI danh sách.
2. Tải tài liệu trực tiếp vào kho được tiếp nhận qua cơ chế Intake V2 bất đồng bộ với tính toàn vẹn giao dịch cao và deduplication an toàn theo tenant/workspace.
3. Trạng thái bóc tách được theo dõi minh bạch theo từng file.
4. Việc đưa tài liệu vào Kho tri thức tuân thủ hợp đồng xuất bản an toàn với kiểm tra `strict_ready` bảo vệ chất lượng dữ liệu RAG.
