# NHẬT KÝ PHIÊN LÀM VIỆC SỐ 305

- **Thời gian**: 2026-10-09
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên**: Triển khai tính năng “Nhóm tài liệu” (Document Groups) để người quản trị gom nhiều tài liệu trong Kho tài liệu (`RepositoryDocument`) và đưa toàn bộ nhóm vào một Kho tri thức (`KnowledgeCollection`) theo cơ chế Snapshot thủ công idempotent.

---

## 1. Bối Cảnh & Ranh Giới Kiến Trúc

Nền tảng đã có phân hệ Kho Tài Liệu Tập Trung (`RepositoryDocument`, lưu trữ MinIO S3, SHA-256 deduplication, chuỗi Revision bất biến `DocumentRevision`) và Kho Tri Thức V2 (`KnowledgeCollection`, `KnowledgeBinding`, Staging Indexing, Atomic Pointer Swap).
Yêu cầu nghiệp vụ mới:
1. Cho phép người quản trị tạo các nhóm tài liệu logic (ví dụ "Tuyển sinh 2026", "Quy chế đào tạo") để gom nhiều tài liệu.
2. Một tài liệu có thể thuộc nhiều nhóm (quan hệ nhiều-nhiều).
3. Người dùng có thể chọn hàng loạt tài liệu trong `/documents` và đưa vào nhóm.
4. Trang chi tiết riêng cho nhóm tài liệu theo kiến trúc Master-Detail Deep Routing (`/documents/groups/:groupId`).
5. Từ trang chi tiết nhóm, người dùng chọn "Đưa vào kho", chọn Kho tri thức, xem trước snapshot và thực hiện liên kết.
6. Tái sử dụng hoàn toàn `KnowledgeBindingService.create_bindings`, không tạo pipeline indexing mới, tôn trọng staging gate, snapshot thủ công (tài liệu thêm sau này không tự động bind), idempotent.
7. Ranh giới kiến trúc: Tách bạch rõ rệt giữa file nguồn (`RepositoryDocument`), nhóm logic (`DocumentGroup`), quan hệ nhiều-nhiều (`DocumentGroupMembership`), không gian RAG (`KnowledgeCollection`), và liên kết tri thức (`KnowledgeBinding`). Tuyệt đối không thêm `group_id` trực tiếp vào `RepositoryDocument`, không dùng `catalog_metadata` cho quan hệ chính, không hardcode tên nhóm.
8. Khắc phục 2 vi phạm UI trên `/documents`: bỏ khung Card viền bao quanh toolbar filter (chuyển sang seamless layout); loại bỏ `helper` lặp lại ý nghĩa trên KPI metrics.

---

## 2. Chi Tiết Các Thay Đổi & Hiện Thực Kỹ Thuật

### 2.1. CSDL PostgreSQL & Alembic Migration
- **Model `DocumentGroup`** (`app/modules/documents/models.py`):
  - `id`: Khóa chính `doc_grp_<hex12>`.
  - `tenant_id`, `workspace_id`: Phân tách đa tenant/workspace.
  - `name`: Tên nhóm (unique theo tenant/workspace).
  - `description`: Mô tả chi tiết.
  - `created_by`, `created_at`, `updated_at`.
  - `lock_version`: Khóa lạc quan (Optimistic Locking).
  - Index trên `(tenant_id, workspace_id, name)`.
- **Model `DocumentGroupMembership`** (`app/modules/documents/models.py`):
  - `group_id`: FK cascade tới `document_groups.id`.
  - `document_id`: FK cascade tới `repository_documents.id`.
  - `added_by`, `added_at`.
  - Composite Primary Key `(group_id, document_id)` bảo đảm tính duy nhất và không tạo bản ghi trùng.
- **Migration Alembic** `alembic/versions/20261009_document_groups.py`:
  - `down_revision = "20261008_publishing_v2_hardening"`.
  - Tạo bảng `document_groups` và `document_group_memberships` với index đầy đủ.
  - Xóa nhóm (`CASCADE`) chỉ xóa memberships, bảo toàn 100% tài liệu gốc và các bindings.

### 2.2. Backend Service & Schemas
- **Schemas DTOs** (`app/modules/documents/schemas.py` & `app/modules/knowledge/schemas.py`):
  - `DocumentGroupCreate`, `DocumentGroupUpdate`, `DocumentGroupResponse`, `DocumentGroupListItem`, `DocumentGroupListResponse`.
  - `AddGroupDocumentsRequest`, `AddGroupDocumentsResultItem`, `AddGroupDocumentsResponse`.
  - `GroupDocumentItem`, `GroupDocumentsResponse`.
  - `AttachDocumentGroupRequest`, `AttachDocumentGroupItemResult`, `AttachDocumentGroupResponse`.
- **`DocumentGroupService`** (`app/modules/documents/group_service.py`):
  - Quản lý vòng đời nhóm: `create_group`, `get_group`, `list_groups`, `update_group` (optimistic locking), `delete_group`.
  - Quản lý thành viên: `get_group_documents` (kèm lọc trạng thái và tìm kiếm), `add_documents_to_group` (xử lý idempotent, kiểm tra tenant, trả về thống kê `added_count`, `skipped_existing_count`, `failed_count`), `remove_document_from_group`.
  - Ngoại lệ RFC 7807 chuẩn: `DOCUMENT_GROUP_NOT_FOUND`, `DOCUMENT_GROUP_NAME_CONFLICT`, `DOCUMENT_GROUP_ACCESS_DENIED`, `DOCUMENT_GROUP_EMPTY`, `NO_READY_DOCUMENTS`.
- **Mở rộng `DocumentRepositoryService.list_documents`**:
  - Hỗ trợ tham số `group_id: str | None = None` lọc tài liệu thuộc nhóm qua join `DocumentGroupMembership`.
  - Tự động nạp tối ưu mảng `groups: list[DocumentGroupMinimalItem]` cho từng tài liệu trả về.
- **`BindingService.attach_document_group`** (`app/modules/knowledge/services/binding_service.py`):
  - Mở rộng thành viên từ CSDL phía server, không tin danh sách từ client.
  - Phân loại tài liệu có `DocumentRevision.status == "ready"`.
  - Tái sử dụng `create_bindings` để tạo `KnowledgeBinding` chuẩn, xử lý idempotent `already_bound_count`.
  - Báo cáo rõ ràng: `total_documents`, `created_count`, `already_bound_count`, `not_ready_count`, `failed_count`.
  - Hỗ trợ cờ `strict_ready` (nếu true và có tài liệu chưa ready thì từ chối với `NO_READY_DOCUMENTS`).

### 2.3. Backend Routers & Phân Quyền Chuẩn
- **`app/modules/documents/router.py`**:
  - `GET /documents`: Bổ sung query `group_id` (`ai.knowledge.view`).
  - `GET /documents/groups`: Danh sách nhóm (`ai.knowledge.view`).
  - `POST /documents/groups`: Tạo nhóm (`ai.knowledge.upload`).
  - `GET /documents/groups/{group_id}`: Chi tiết nhóm (`ai.knowledge.view`).
  - `PATCH /documents/groups/{group_id}`: Sửa nhóm (`ai.knowledge.upload`).
  - `DELETE /documents/groups/{group_id}`: Xóa nhóm (`ai.knowledge.upload`).
  - `GET /documents/groups/{group_id}/documents`: Tài liệu trong nhóm (`ai.knowledge.view`).
  - `POST /documents/groups/{group_id}/documents`: Thêm tài liệu vào nhóm (`ai.knowledge.upload`).
  - `DELETE /documents/groups/{group_id}/documents/{document_id}`: Gỡ tài liệu khỏi nhóm (`ai.knowledge.upload`).
- **`app/modules/knowledge/router.py`**:
  - `POST /knowledge/collections/{collection_id}/attach-document-group`: Snapshot đưa nhóm vào Kho Tri Thức (`ai.knowledge.sync`).

### 2.4. Frontend Implementation & UI/UX Gold Standard
- **Types & API Client**:
  - `types/documents.ts` & `types/knowledge.ts`: Khai báo types chuẩn.
  - `services/documents-api.ts`: Bổ sung 8 methods quản trị nhóm và tham số `group_id` cho `getDocuments`.
  - `services/knowledge-api.ts`: Bổ sung `attachDocumentGroup`.
- **Trang Danh Sách Nhóm `/documents/groups`** (`document-groups-page.tsx`):
  - Route TanStack: `documents.groups.index.tsx`.
  - Bento KPI: Tổng nhóm, tổng tài liệu, sẵn sàng, đang xử lý.
  - Thẻ nhóm hiển thị tên, mô tả, badges breakdown trạng thái, nút "Mở", "Sửa", "Xóa".
  - Dialog tạo nhóm và sửa nhóm.
- **Trang Chi Tiết Nhóm `/documents/groups/:groupId`** (`document-group-detail-page.tsx`):
  - Route TanStack: `documents.groups.$groupId.tsx`.
  - Header Hero Banner kèm breadcrumb và nút quay lại.
  - Bento KPI tối giản: Tổng tài liệu, Ready, Đang xử lý, Lỗi.
  - Điều khiển: Search, filter trạng thái, `ViewModeToggle` chuẩn `@/components/ui/view-mode-toggle`.
  - Bảng / Lưới tài liệu với nút gỡ tài liệu khỏi nhóm (bảo toàn tài liệu gốc).
  - Dialog "Thêm tài liệu vào nhóm" (`SelectDocumentsForGroupModal`): Tìm kiếm và tick chọn các tài liệu chưa có trong nhóm.
  - Dialog "Đưa vào kho tri thức" (`AttachGroupToKnowledgeDialog`): Chọn Collection, chọn chunk strategy, preview số lượng ready / pending / error, cảnh báo snapshot thủ công, và sau khi hoàn tất cung cấp link chuyển đến trang chi tiết Kho Tri Thức.
- **Nâng Cấp Trang `/documents`** (`documents-page.tsx`):
  - Khắc phục vi phạm 1: Chuyển toolbar tìm kiếm / bộ lọc sang layout phẳng seamless, bỏ viền Card bao quanh.
  - Khắc phục vi phạm 2: Bỏ thuộc tính `helper` lặp lại ý nghĩa trên các thẻ `KpiMetric`.
  - Nút "Nhóm Tài Liệu" trên PageHeader dẫn sang `/documents/groups`.
  - Dropdown lọc theo nhóm tài liệu.
  - Checkbox chọn nhiều tài liệu đồng bộ cả trên chế độ Lưới (`DocumentCard`) và Bảng (`DocumentsTable`).
  - Floating Bottom Action Bar cố định đáy màn hình khi có tài liệu được chọn với nút "Thêm vào nhóm" và "Bỏ chọn".
  - Dialog "Thêm vào nhóm" (`AddToGroupDialog`): Cho phép chọn nhóm có sẵn hoặc tạo nhóm mới tức thì.

---

## 3. Kết Quả Kiểm Thử & Xác Minh

### 3.1. Backend Test Suites
- Đã tạo `tests/test_document_groups_and_knowledge_attach.py` phủ đầy đủ 11 ca kiểm thử bắt buộc:
  1. `test_group_crud_lifecycle`: PASSED
  2. `test_document_in_multiple_groups`: PASSED
  3. `test_add_membership_idempotent`: PASSED
  4. `test_tenant_workspace_isolation`: PASSED
  5. `test_delete_group_preserves_documents_and_bindings`: PASSED
  6. `test_attach_group_binds_only_ready_revisions`: PASSED
  7. `test_attach_group_idempotent`: PASSED
  8. `test_attach_group_manual_snapshot_boundary`: PASSED
  9. `test_attach_group_breakdown_counts_reporting`: PASSED
  10. `test_attach_group_empty_and_not_found_errors`: PASSED
  11. `test_attach_group_strict_ready_rejects_unready`: PASSED
- Kiểm thử hồi quy kho tài liệu `tests/test_document_repository.py`: 6/6 PASSED.
- Tổng kết pytest: **17/17 PASSED 100%**.
- Ruff linter: `.venv\Scripts\ruff.exe check app tests`: **All checks passed (0 errors)**.

### 3.2. Frontend Build & Quality Gate
- Chạy `npm run build`:
  - TanStack router biên dịch tự động các routes mới: `documents.groups.tsx`, `documents.groups.index.tsx`, `documents.groups.$groupId.tsx`.
  - Vite build hoàn tất.
  - **0 lỗi TypeScript, 0 lỗi Biome, 0 lỗi bundle**.

---

## 4. Hoàn Thiện Sau Code Review (Hardening & Isolation)

Sau đợt code review chi tiết, toàn bộ các vấn đề kỹ thuật còn tồn đọng đã được khắc phục triệt để:

1. **Frontend Build & Unused Imports Cleanup**:
   - Loại bỏ các import không sử dụng `ExternalLink` trong `attach-group-to-knowledge-dialog.tsx` và `Check` trong `select-documents-for-group-modal.tsx`.
   - Sửa an toàn kiểu `error` từ `unknown` trong `__root.tsx` (`error instanceof Error ? error.message : String(error)`).
   - Kiểm tra đóng gói `npm run build` (`vite build` + `tsc --noEmit`) thành công 100% (exit code 0).
2. **Loại Bỏ Rò Rỉ Mock Singleton Trong Pytest**:
   - Thay thế toàn bộ việc gán trực tiếp `binding_service.create_bindings` bằng `monkeypatch.setattr(binding_service, "create_bindings", AsyncMock(...))`.
   - Mock được tự động phục hồi sau mỗi test; chạy kiểm thử kết hợp `test_document_groups_and_knowledge_attach.py` và `test_knowledge_publishing_v2.py` đạt **26/26 PASSED (100%)**.
3. **Tenant & Workspace Isolation Cho Kho Tài Liệu**:
   - Router `/documents` chuyển sang dependency `actor: AuthActor` và truyền vào `list_documents(..., actor=actor)`.
   - Mọi query tài liệu bắt buộc lọc `RepositoryDocument.tenant_id == actor.tenant_id` và `workspace_id == actor.workspace_id`.
   - Khi có `group_id`, kiểm tra nhóm tồn tại và thuộc cùng tenant/workspace; nếu khác phạm vi, từ chối với RFC 7807 `DOCUMENT_GROUP_ACCESS_DENIED`.
   - Truy vấn nạp badges nhóm của mỗi tài liệu cũng được scope chặt chẽ theo tenant/workspace của actor.
4. **Server-side Preview API (`POST /knowledge/collections/{id}/preview-document-group`)**:
   - API read-only tính toán preview snapshot trên toàn bộ thành viên nhóm từ CSDL phía server, không phụ thuộc filter hay pagination của frontend.
   - Sử dụng chung helper nội bộ `_evaluate_group_members` với `attach_document_group` để bảo đảm tính nhất quán thuật toán phân loại (`ready`, `already_bound`, `not_ready`, `failed`).
5. **Chuẩn Hóa Dialog "Đưa Vào Kho Tri Thức"**:
   - Chuyển sang gọi API preview server-side với query key `["preview-document-group", collectionId, groupId]`.
   - Hiển thị Bento KPI preview và trạng thái từng tài liệu chính xác ngay cả với nhóm > 100 tài liệu.
   - Sau khi liên kết, tự động invalidate đồng bộ 5 query keys liên quan.
6. **Chuẩn Hóa Tên Nhóm & Chống Trùng Tên CSDL (PostgreSQL Unique Index)**:
   - Validator Pydantic chuẩn hóa Unicode NFC, trim khoảng trắng, gộp khoảng trắng thừa (`\s+`), từ chối chuỗi rỗng/chỉ chứa space và giới hạn $\le 128$ ký tự.
   - Thêm functional unique index `uq_doc_groups_tenant_ws_lower_name` trên `(tenant_id, workspace_id, lower(name))` trong model và migration Alembic.
   - Bắt `IntegrityError`, rollback transaction và chuyển thành HTTP 409 RFC 7807 với code `DOCUMENT_GROUP_NAME_CONFLICT`.
7. **Atomic Optimistic Locking**:
   - Chuyển `update_group` sang câu lệnh SQL atomic: `UPDATE document_groups SET ... WHERE id = :id AND tenant_id = :tenant_id AND workspace_id = :workspace_id AND lock_version = :expected_lock_version`.
   - Kiểm tra `rowcount == 0` để phân biệt không tồn tại, khác scope, hoặc xung đột phiên bản (`OPTIMISTIC_LOCK_CONFLICT`).
8. **Chuẩn Hóa Audit Actor**:
   - Thống nhất cơ chế phân giải actor: `actor.actor_id` -> `actor.username` -> `"system"`.
9. **Chuẩn Hóa KPI Trang Danh Sách Nhóm**:
   - Sửa KPI "Đang Xử Lý" dùng trường chính xác `g.processing_documents` (thay vì lấy tổng trừ ready làm lẫn tài liệu lỗi).
   - "Tổng Nhóm" sử dụng `groupsData.total`.
   - Gắn nhãn phân biệt rõ "Nhóm Tìm Thấy" và "(Trong kết quả)" khi người dùng đang tìm kiếm.
10. **Lọc Tài Liệu Có Sẵn Phía Server Trong Modal Chọn Tài Liệu**:
    - Mở rộng API `list_documents` với tham số `exclude_group_id`, loại trừ tài liệu đã thuộc nhóm bằng mệnh đề SQL `NOT EXISTS` có scope tenant/workspace.
11. **Validation API Nghiêm Ngặt**:
    - `chunk_strategy` kiểm tra theo `SUPPORTED_CHUNK_STRATEGIES`.
    - `sync_policy` giới hạn và mặc định là `manual`.
    - `strict_ready=true` trả chi tiết `STRICT_READY_VIOLATION` (`total_documents`, `ready_count`, `not_ready_count`) khi có tài liệu chưa ready.
12. **Chất Lượng Mã Nguồn & Định Dạng**:
    - `git diff --check`: 0 lỗi, loại bỏ toàn bộ blank line dư ở EOF.
    - Ruff: 0 lỗi trên toàn bộ các modules liên quan.
    - Alembic: 1 head duy nhất (`20261009_document_groups`).
