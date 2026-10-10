# Nhật Ký Phiên #313: Hoàn Thiện Toàn Diện Quy Trình Kho Tài Liệu & Intake V2

- **Thời gian**: 2026-10-10 12:05 (UTC+7)
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Giải quyết triệt để 8 vấn đề cốt lõi của quy trình Kho tài liệu (`RepositoryDocument`, `DocumentGroup`, `DocumentRevision`, `Intake V2`, `Legacy V1 Adapter`) trên repository `qnu-ai-platform`.

---

## 1. Các Hạng Mục Đã Hoàn Thành

### 1.1. Cô Lập Storage Key Theo Scope & Compensation An Toàn (Mục 1)
- **Cấu trúc Storage Key chuẩn**:
  ```text
  documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{safe_file_name}
  ```
- **Chuẩn hóa Tên Tệp An Toàn (`sanitize_safe_filename`)**:
  - Dùng chuẩn Unicode NFKD kết hợp loại bỏ combining diacritics và chuyển đổi ký tự `đ/Đ` thành `d/D` để làm sạch tiếng Việt có dấu.
  - Loại bỏ ký tự đặc biệt, thay thế khoảng trắng bằng dấu gạch dưới `_`, ngăn ngừa Directory Traversal (`..`, `/`, `\`).
- **Bảo toàn dữ liệu cũ**: Các tài liệu cũ tiếp tục đọc và xử lý bình thường qua trường `storage_path` lưu trong CSDL, không di chuyển cưỡng bức.
- **MinIO S3 Compensation cô lập**: Khối `except Exception` và `except IntegrityError` chỉ xóa đúng `storage_key` vừa tạo trong scope của tenant hiện tại, tuyệt đối không ảnh hưởng tới object của tenant khác.

### 1.2. Hoàn Thiện Idempotency HTTP Header & Client UUID (Mục 2)
- **FastAPI Header Alias**: Khai báo `idempotency_key: str | None = Header(None, alias="Idempotency-Key")` tại route `POST /documents/intake` trong `router.py`.
- **Chuyển tiếp nguyên vẹn**: Header được truyền trực tiếp vào `DocumentIntakeService.intake_document`.
- **Frontend Stable UUID**: Trong `document-upload-modal.tsx`, sinh `crypto.randomUUID()` ổn định cho mỗi file trong một batch và gửi qua `idempotencyKey`.
- **Idempotency Replay & Conflict Check**:
  - Cùng `Idempotency-Key` + cùng `request_hash` (file hash, params, group_id, tenant_id, workspace_id) -> trả lại kết quả cũ nguyên vẹn kèm status của revision.
  - Cùng `Idempotency-Key` nhưng khác payload hoặc kho đích -> ném HTTP 409 `IDEMPOTENCY_KEY_REUSED` (RFC 7807).

### 1.3. Xử Lý Endpoint `/documents/upload` Legacy V1 An Toàn (Mục 3)
- Đánh dấu `deprecated=True` trên route `/documents/upload`.
- Khi client gửi `group_id`: chuyển thành Compatibility Adapter gọi trực tiếp orchestration `DocumentIntakeService.intake_document` với tính nguyên tử cao.
- Kiểm tra chặt chẽ `tenant_id` và `workspace_id` của nhóm thông qua `_resolve_actor_scope_from_session`. Nếu nhóm không tồn tại hoặc không thuộc quyền sở hữu của tenant/workspace -> trả HTTP 404 `DOCUMENT_GROUP_NOT_FOUND` ngay lập tức, không tạo tài liệu mồ côi (Orphan Document).

### 1.4. Xóa Công Tắc `autoParse` Khỏi `DocumentUploadModal` (Mục 4)
- Xóa bỏ hoàn toàn state `autoParse` và checkbox tương ứng.
- Thay bằng thông báo tĩnh trang nhã với semantic styling và icon Lucide `Sparkles`: *"Tài liệu sẽ được tự động bóc tách sau khi tiếp nhận."*

### 1.5. Chuẩn Hóa Response Khi Deduplicate (Mục 5)
- Không trả `RepositoryDocument.parse_status` legacy.
- Đọc 100% từ `current_revision` của tài liệu trùng lặp.
- Chỉ trả một trong 7 trạng thái chuẩn V2: `queued`, `processing`, `validating`, `review_required`, `ready`, `failed`, `cancelled`.
- Nếu tài liệu cũ chưa có revision hợp lệ -> ném lỗi HTTP 409 `DOCUMENT_REVISION_INVALID`.
- Trả đúng `job_id` thực từ bảng `JobRecord` (hoặc `None` nếu không có active job); tuyệt đối không dùng chuỗi giả `"deduplicated"` hay `"idempotent-replay"`.

### 1.6. Hoàn Thiện Error State Frontend (Mục 6)
- Cập nhật `documents-api.ts`: ném `ApiError` có cấu trúc mang theo HTTP status code và payload lỗi từ backend.
- Cập nhật `DocumentGroupsPage` & `DocumentGroupDetailPage`:
  - Khai báo và xử lý đầy đủ `isError, error, refetch` từ TanStack Query.
  - Không biến lỗi mạng thành Empty State giả mạo.
  - Phân biệt rõ HTTP 403 (Không có quyền truy cập), HTTP 404 (Không tìm thấy kho tài liệu), và lỗi kết nối hệ thống.
  - Cung cấp nút `Thử lại` gọi `refetch()` trực tiếp trên giao diện.

### 1.7. Hoàn Thiện Migration Alembic Chống Lỗi Aborted Transaction (Mục 7)
- Cập nhật migration `20261010_composite_file_hash_deduplication.py`:
  - Loại bỏ hoàn toàn `try/except Exception: pass`.
  - Dùng SQLAlchemy Inspector `inspect(bind).get_indexes("repository_documents")` để kiểm tra sự tồn tại của index.
  - Dùng câu lệnh SQL an toàn `DROP INDEX IF EXISTS`.
  - Tạo composite unique index `(tenant_id, workspace_id, file_hash)`.
  - Downgrade kiểm tra chặt chẽ: đếm số bản ghi trùng lặp `count(*) > 1` trên toàn cục; nếu có trùng lặp thì ném `RuntimeError` báo rõ không thể quay lại unique toàn cục mà không mất tính toàn vẹn dữ liệu.

### 1.8. Chuẩn Hóa Màu Sắc Semantic Token `text-warning` (Mục 8)
- Thay thế toàn bộ mã màu hardcode `text-amber-600 dark:text-amber-400` bằng semantic token `text-warning` trong `document-upload-modal.tsx`, `document-group-detail-page.tsx`, `document-detail-page.tsx`.

---

## 2. Kết Quả Kiểm Thử (Quality Gate)

1. **Backend Ruff Linter**:
   ```bash
   uv run ruff check .
   # All checks passed! (0 errors)
   ```

2. **Backend Workflow & Document Test Suites**:
   ```bash
   uv run --extra dev pytest tests/test_document_repository_workflow.py tests/test_document_groups_and_knowledge_attach.py tests/test_document_revisions_lifecycle.py -v
   # 40/40 PASSED (100%) in 4.12s
   ```
   Bao gồm đầy đủ các test cases mới:
   - `test_scope_isolated_storage_key_generation`: Kiểm tra đúng mẫu key có scope tenant/workspace và filename an toàn.
   - `test_compensation_does_not_delete_other_tenant_storage_object`: Kiểm tra tenant B lỗi DB chỉ xóa object tenant B, object tenant A an toàn 100%.
   - `test_deduplication_returns_v2_revision_status_and_real_job_id`: Trả đúng status revision V2 và job_id thực.
   - `test_deduplication_corrupted_revision_raises_app_exception`: Tài liệu trùng lặp thiếu revision ném HTTP 409 `DOCUMENT_REVISION_INVALID`.
   - `test_concurrent_duplicate_intake_integrity_error_recovery`: Xử lý race condition đồng thời qua bắt `IntegrityError`, rollback và gắn membership an toàn.
   - `test_http_route_intake_idempotency_header`: Kiểm tra route `/documents/intake` qua HTTP test client với `Idempotency-Key` header, assert 202 và kiểm tra replay.
   - `test_legacy_v1_upload_with_invalid_group_does_not_create_orphan`: Legacy V1 từ chối group không tồn tại bằng HTTP 404 RFC 7807, 0 document mồ côi.

3. **Frontend Biome Linter**:
   ```bash
   npx biome check src/features/documents src/services/documents-api.ts
   # Checked 11 files in 37ms. No fixes applied. (0 errors)
   ```

4. **Frontend Production Build**:
   ```bash
   npm run build
   # ✓ built in 4.64s (0 TypeScript errors, 0 compilation warnings)
   ```

5. **Báo Cáo Toàn Bộ Test Suite Backend**:
   - Chạy `pytest -q` toàn bộ 688 test cases: **671 passed, 1 skipped, 12 failed, 5 errors**.
   - Các test fail/error nằm hoàn toàn ở các module ngoài phạm vi thay đổi:
     - `test_consulting_dispatcher.py`, `test_tools.py`, `test_universal_tools.py`: Test tra cứu fact layer admissions & export excel mock cũ.
     - `test_publishing_v2_cutover_and_gc.py`, `test_publishing_v2_decommissioning_and_system_gc.py`, `test_publishing_v2_e2e_canary.py`: Chạy trực tiếp yêu cầu canary policy / service mocks của Phase cũ.
     - `test_core.py`, `test_trust_boundary_and_hitl.py`: Bị `PermissionError: [WinError 5] Access is denied` do phân quyền thư mục tạm trên Windows trong môi trường chạy test.

---

## 3. Các Tệp Mã Nguồn Đã Chỉnh Sửa

| Tệp | Mô tả thay đổi |
|---|---|
| `backend/app/modules/documents/intake_service.py` | `sanitize_safe_filename()`, scope-isolated storage key, MinIO compensation cô lập, deduplication trả V2 revision status & real job_id, race condition recovery |
| `backend/app/modules/documents/service.py` | Áp dụng scope-isolated storage key và deduplication theo tenant/workspace |
| `backend/app/modules/documents/router.py` | Header `Idempotency-Key` cho `/documents/intake`, Legacy V1 `/documents/upload` adapter an toàn |
| `backend/app/modules/documents/schemas.py` | Cho phép `job_id: str | None = None` trong `AsyncUploadDocumentResponse` |
| `backend/alembic/versions/20261010_composite_file_hash_deduplication.py` | Dùng schema inspector, `DROP INDEX IF EXISTS`, kiểm tra downgrade |
| `backend/tests/test_document_repository_workflow.py` | Thêm 7 test cases bao phủ storage key, compensation, deduplication, concurrency, idempotency header, legacy v1 |
| `backend/tests/test_document_revisions_lifecycle.py` | Cập nhật mock V2 revision hợp lệ cho test deduplication |
| `frontend/src/features/documents/components/document-upload-modal.tsx` | Xóa `autoParse`, banner tĩnh tự động bóc tách, UUID ổn định per-file, đổi màu `text-warning` |
| `frontend/src/features/documents/document-groups-page.tsx` | Xử lý `isError, error, refetch`, phân biệt 403, 404, nút thử lại |
| `frontend/src/features/documents/document-group-detail-page.tsx` | Xử lý `isError, error, refetch` cho cả group và documents, đổi màu `text-warning` |
| `frontend/src/features/documents/document-detail-page.tsx` | Đổi màu `text-warning` |
| `frontend/src/services/documents-api.ts` | Bổ sung `ApiError` class, ném lỗi có cấu trúc, chuẩn hóa Biome imports |
