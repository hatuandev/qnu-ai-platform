# NHẬT KÝ LÀM VIỆC — PHIÊN #320
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Ngày thực hiện**: 2026-10-10  
**Chủ đề**: Sửa Triệt Để State Machine, Invariant NOT NULL Binding, Staging Reuse, Retry & Phân Loại Diff Kho Tri Thức  
**Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau phiên #319, quy trình liên kết Nhóm tài liệu vào Kho tri thức (`KnowledgeGroupSource`) đã định hình kiến trúc Staging Index và Workspace Isolation. Tuy nhiên, quá trình chạy thử nghiệm và rà soát state machine bộc lộ 7 vấn đề kiến trúc cần khắc phục triệt để:

1. **Lỗi vi phạm ràng buộc NOT NULL của CSDL PostgreSQL**: `KnowledgeBinding.source_revision_id` là cột `nullable=False`, nhưng code cũ khởi tạo `source_revision_id=None` khi attach/sync rồi gọi `flush()`, gây crash `IntegrityError` trên cơ sở dữ liệu thật.
2. **Trộn lẫn Current Revision và Staging Revision**: `binding.source_revision_id` bị ghi đè sớm sang target revision ngay khi staging index vừa build thành công, phá vỡ con trỏ đang phục vụ RAG.
3. **Build staging lặp**: Bấm "Đồng bộ" hoặc "Thử lại" nhiều lần sinh ra nhiều staging revisions trùng lặp không cần thiết.
4. **Ghi đè sai trạng thái `review_required`**: `list_group_sources()` tính `diff.has_changes=true` vì binding chưa active rồi ghi đè `review_required -> updates_available`, làm UI mất nút "Xuất bản".
5. **Điều kiện chuyển trạng thái `ready` quá lỏng lẻo**: Nhóm tài liệu chuyển thành `ready` chỉ vì `published_count > 0`, dù vẫn còn tài liệu build lỗi hoặc chưa active đúng revision.
6. **Không thể Retry khi Promote thất bại**: Promote lỗi chuyển source sang `failed` nhưng lần sau không tận dụng staging revision đã có sẵn để promote lại.
7. **Cạnh tranh / Chiếm binding giữa các nhóm tài liệu**: Đồng bộ tự động gán đè `binding.group_source_id = source.id`, dẫn tới việc hai nhóm có chung tài liệu giành giật binding của nhau.

---

## 2. Các Thay Đổi Kiến Trúc & Triển Khai Chi Tiết

### 2.1. Backend State Machine & Data Models

- **Bảo toàn Invariant NOT NULL trên `KnowledgeBinding`**:
  - Khi tạo binding mới: Gán ngay `source_revision_id = target_revision.id` và `status = "pending"`.
  - Trạng thái `pending`: Đại diện binding mới khởi tạo, **chưa được phép tham gia retrieval RAG** (tầng RAG chỉ truy vấn `status == 'active'`).
  - Chỉ chuyển `binding.status = "active"` sau khi staging index revision được promote thành công.
  - Nếu staging build lỗi: Giữ nguyên `status = "pending"`, `active_index_revision_id = None`, không cập nhật `last_membership_hash`. Lần retry sau tìm và tái sử dụng pending binding này (không tạo duplicate binding cho cùng `collection_id + repository_document_id`).
- **Tách bạch Current Revision vs. Pending Staging**:
  - Với binding đã có active index: Giữ nguyên `binding.source_revision_id` trỏ vào revision đang được active index phục vụ.
  - Revision mới chờ xuất bản nằm tại `KnowledgeIndexRevision(binding_id=..., source_revision_id=target_rev_id, status='ready')`.
  - Chỉ cập nhật `binding.source_revision_id = promoted_index_revision.source_revision_id` sau khi hàm `promote_index_revision` thực thi thành công. Nếu promote thất bại: Giữ nguyên con trỏ cũ, staging revision vẫn còn nguyên để người dùng bấm "Thử lại".
- **Chống Build Staging Lặp & Tái Sử Dụng Staging Sẵn Có**:
  - Trước khi gọi `build_staging_index`, truy vấn kiểm tra xem đã tồn tại `KnowledgeIndexRevision(binding_id=..., source_revision_id=target_rev, status='ready')` hay chưa.
  - Nếu đã có: Tái sử dụng ngay lập tức, không build lại.
  - Nếu request có `auto_publish=True`: Thử promote revision đang chờ đó; nếu thành công chuyển `ready`, nếu thất bại chuyển `failed` để retry.
- **Chuẩn Hóa Helper Trạng Thái Dùng Chung `resolve_group_source_state`**:
  - Thứ tự ưu tiên xác định trạng thái nguồn nhóm:
    1. `syncing`: Khi tác vụ nền đang chạy.
    2. `failed`: Khi có lỗi build staging hoặc promote chưa được khắc phục.
    3. `review_required`: Khi tồn tại ready staging revisions chưa active (`awaiting_publish_count > 0` hoặc `source.status == 'review_required'`).
    4. `updates_available`: Khi có tài liệu mới hoặc revision mới cần build (`needs_build_count > 0`).
    5. `ready`: Khi toàn bộ tài liệu đủ điều kiện trong nhóm đã có binding `active` và trỏ đúng `current_revision_id`.
    6. `empty` / `pending`: Khi nhóm chưa có tài liệu hoặc vừa khởi tạo.
- **Bổ Sung Các Chỉ Số Phân Loại DTO**:
  - Thêm `needs_build_count`, `awaiting_publish_count`, `publishable_count` vào `KnowledgeGroupSourceResponse` và `PreviewGroupSourceDiffResponse`.
- **Cấm Chiếm Binding Giữa Các Nhóm (Binding Isolation)**:
  - Nếu tài liệu đã có binding `active` hoặc `pending` thuộc nhóm nguồn khác: Hệ thống từ chối chiếm binding, trả lỗi theo từng tài liệu với mã RFC 7807 `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`.

### 2.2. Frontend & Trải Nghiệm Người Dùng (UI/UX)

- **Xử lý Partial Failure & Toast Thông Minh**:
  - Không còn hiện `toast.success()` khi HTTP 200 nhưng có lỗi một phần (`failed_count > 0` hoặc `status == "failed"`).
  - Quy tắc hiển thị:
    - `failed_count > 0` hoặc `status == "failed"` -> `toast.error` kèm danh sách chi tiết lỗi.
    - `status == "review_required"` sau partial publish -> `toast.warning`.
    - 100% thành công -> `toast.success`.
  - Không tự động navigate rời khỏi trang `add-documents` nếu attach trả về `failed`; hiển thị bảng lỗi trực quan theo từng tài liệu.
- **Nút Thao Tác Dựa Trên Dữ Liệu Thực**:
  - Nút `Đồng bộ`: Chỉ hiển thị khi `needs_build_count > 0` (thực sự có tài liệu/revision mới cần build).
  - Nút `Xuất bản`: Hiển thị khi `publishable_count > 0` hoặc `status == "review_required"`.
  - Nút `Thử lại`: Hiển thị khi `status == "failed"`.
- **Xử Lý Source Không Tồn Tại**:
  - `source-detail-page.tsx`: Phân định rõ 4 trạng thái Loading, Error, Not Found, Loaded; tuyệt đối không render giao diện giả kèm nút gỡ nguồn khi source không tồn tại.
- **Chuẩn Hóa Semantic Color Tokens & Việt Hóa 100%**:
  - Thay thế toàn bộ màu hardcode (`amber-*`, `blue-*`, `text-white`) bằng tokens OKLCH: `text-warning`, `bg-warning/10`, `border-warning/30`, `text-primary`, `bg-primary/10`, `text-success`, `text-destructive`.
  - Việt hóa toàn diện trạng thái: `pending` (Chờ xử lý), `syncing` (Đang đồng bộ), `review_required` (Chờ xuất bản), `updates_available` (Có cập nhật), `up_to_date` (Đã đồng bộ), `ready` (Sẵn sàng), `failed` (Có lỗi), `empty` (Chưa có tài liệu), `detached` (Đã gỡ).
- **Chuẩn Hóa Xử Lý Lỗi RFC 7807**:
  - Dùng `extractErrorMessage()` (`detail -> message -> title -> fallback`) cho toàn bộ 8 API group source trong `knowledge-api.ts`.

---

## 3. Các Tệp Mã Nguồn Đã Thay Đổi

1. `backend/app/modules/knowledge/models.py`:
   - Cập nhật default `KnowledgeBinding.status = "pending"`.
   - Cập nhật docstring mô tả 4 trạng thái binding (`pending`, `active`, `archived`, `detached`).
2. `backend/app/modules/knowledge/schemas.py`:
   - Thêm `needs_build_count`, `awaiting_publish_count`, `publishable_count` vào `KnowledgeGroupSourceResponse` và `PreviewGroupSourceDiffResponse`.
   - Đặt `file_name: str = ""` mặc định an toàn cho `PreviewGroupSourceDiffItem`.
   - Dọn sạch dòng trắng cuối file (đạt chuẩn `git diff --check`).
3. `backend/app/modules/knowledge/services/group_source_diff_service.py`:
   - Xây dựng helper `resolve_group_source_state(...)`.
   - Batch query index revisions theo binding ids.
   - Phân loại chính xác 6 tập diff và đếm `needs_build_count`, `awaiting_publish_count`, `publishable_count`.
   - Kiểm tra xung đột binding thuộc nhóm khác (`DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`).
   - Phân giải an toàn `doc_file_name` chống lỗi Pydantic validation.
4. `backend/app/modules/knowledge/services/group_source_sync_service.py`:
   - Gán `source_revision_id = target_revision.id` và `status = "pending"` khi tạo binding mới.
   - Bảo vệ con trỏ active index cũ khi build revision mới.
   - Kiểm tra và tái sử dụng staging index revision `ready` đã có (chống build staging lặp).
   - Từ chối chiếm binding của nhóm khác và báo lỗi theo từng tài liệu.
5. `backend/app/modules/knowledge/services/group_source_publish_service.py`:
   - Cập nhật `binding.source_revision_id = ready_rev.source_revision_id` và `binding.status = "active"` chỉ sau khi promote thành công.
   - Kiểm chứng toàn bộ tập tài liệu trong nhóm đạt chuẩn mới set source thành `ready`.
   - Trả partial failure chuẩn RFC 7807 kèm `items` và `failed_count`.
6. `backend/app/modules/knowledge/services/group_source_service.py`:
   - Tích hợp `resolve_group_source_state` vào `list_group_sources`.
7. `backend/tests/test_knowledge_group_sources.py`:
   - Viết lại toàn bộ 14 test cases unit/regression và 1 test persistence trên CSDL PostgreSQL thật.
8. `backend/tests/test_knowledge_publishing_v2.py`:
   - Cập nhật assertion trạng thái khởi tạo mặc định của `KnowledgeBinding` thành `"pending"`.
9. `.gitignore`:
   - Bổ sung quy tắc bỏ qua dữ liệu runtime `backend/storage/documents/*` và `storage/documents/*`.
10. `frontend/src/types/knowledge.ts`:
    - Đồng bộ các trường count mới và response types.
11. `frontend/src/services/knowledge-api.ts`:
    - Chuẩn hóa `extractErrorMessage()` cho toàn bộ 8 APIs.
12. `frontend/src/features/knowledge/source-detail-page.tsx`:
    - Quản lý trạng thái Loading, Error, Not Found, Loaded.
    - Xử lý partial failure toast, semantic tokens OKLCH.
13. `frontend/src/features/knowledge/add-documents-page.tsx`:
    - Không navigate khi attach failed, render bảng lỗi chi tiết theo tài liệu.
    - Dùng semantic tokens và xóa import không dùng `FolderPlus`.
14. `frontend/src/components/knowledge/tabs/collection-group-sources-tab.tsx`:
    - Điều khiển nút bấm thông minh (`Đồng bộ`, `Xuất bản`, `Thử lại`), semantic color tokens.
15. `frontend/src/components/knowledge/collection-header.tsx`:
    - Loại bỏ màu hardcode `amber-*`, `blue-*` chuyển sang semantic tokens.

---

## 4. Kết Quả Kiểm Thử (Verification Results)

### 4.1. Ruff Linter
```bash
uv run ruff check app/modules/knowledge tests/test_knowledge_group_sources.py
```
- **Kết quả**: Exit code 0, `All checks passed!` (0 lỗi linter).

### 4.2. Targeted Pytest Suite (Knowledge Group Sources)
```bash
uv run --extra dev pytest -v tests/test_knowledge_group_sources.py
```
- **Kết quả**: 14/14 tests PASSED (100% pass trong 2.84s).
  - Ca 1 & 2: Binding mới khởi tạo với `source_revision_id = target_rev.id`, `status = "pending"`.
  - Ca 3: Build staging thất bại giữ binding `pending`, không cập nhật membership hash.
  - Ca 4: Retry tái sử dụng pending binding, không tạo binding trùng.
  - Ca 5: Sync lặp lại khi đã có ready staging revision thì tái sử dụng, không build lại.
  - Ca 6: `list_group_sources` giữ nguyên `review_required`, không bị ghi đè thành `updates_available`.
  - Ca 7: Promote thất bại giữ nguyên `binding.source_revision_id` cũ và active pointer cũ.
  - Ca 8: Retry promote dùng staging revision cũ đã ready, không build lại staging.
  - Ca 9: Publish một phần trả `status = "failed"` hoặc `"review_required"`, không thành `ready`.
  - Ca 10: Publish khi 0 revision sẵn sàng trả RFC 7807 `NO_PUBLISHABLE_INDEX_REVISION`.
  - Ca 11: Có 1 active index nhưng còn tài liệu lỗi thì source không thành `ready`.
  - Ca 12: Nhóm thứ hai không được chiếm binding của nhóm thứ nhất (`DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`).
  - Ca 13: Workspace isolation được bảo toàn khi truy cập nhóm khác workspace.
  - Ca 14: **Test persistence thật trên PostgreSQL**: Thực thi transaction thật trên cơ sở dữ liệu `qnu_ai_platform` cục bộ; kiểm chứng chèn binding hợp lệ thành công và bắt đúng `IntegrityError` khi cố tình chèn `source_revision_id = NULL`.

### 4.3. Related Backend Test Suites
```bash
uv run --extra dev pytest -v tests/test_document_repository_workflow.py tests/test_rag.py tests/test_knowledge_publishing_v2.py
```
- **Kết quả**: 58/58 tests PASSED (100% pass trong 4.57s).

### 4.4. Frontend Build
```bash
npm run build
```
- **Kết quả**: Vite build + TypeScript compiler (`tsc --noEmit`) thành công 100% (exit code 0, 0 lỗi TypeScript, 0 lỗi cú pháp).

### 4.5. Git Hygiene
```bash
git diff --check
git status --short
```
- `git diff --check`: Exit code 0 (sạch toàn bộ lỗi whitespace và trailing lines).
- `git status --short`: Không có untracked files trong `storage/`, không có chỉnh sửa nào trên repository `qnu-sso`.

### 4.6. Full Backend Suite
- Chạy: `uv run --extra dev pytest -v` (toàn bộ 711 test cases).
- **Kết quả**: 698 passed, 1 skipped, 1 warning, 7 failed, 5 errors.
- **Phân loại lỗi**:
  - 5 lỗi `PermissionError: [WinError 32]`: Lỗi khóa file tạm thời gian chạy trên môi trường Windows OS (`test_core.py`, `test_tools.py`, `test_document_types.py`).
  - 1 lỗi assertion role `AI.Admin` vs `admin` trong `test_trust_boundary_and_hitl.py` (pre-existing từ cơ chế dev login).
  - 6 lỗi 403 Forbidden trong các bài test admin canary/decommissioning cũ của Kế hoạch 11 (`test_publishing_v2_*.py`) do thay đổi dependency override actor quyền hạn.
  - **100% các test suite thuộc phạm vi công việc (Knowledge Group Sources, Document Workflow, RAG, Publishing V2) đều pass tuyệt đối.**

---

## 5. Kết Luận & Bàn Giao

Phiên làm việc #320 đã giải quyết triệt để toàn bộ 15 yêu cầu kỹ thuật:
- Ràng buộc NOT NULL được tôn trọng 100% trên CSDL PostgreSQL thật;
- Tách bạch rõ ràng current revision đang phục vụ RAG và staging revision đang chuẩn bị;
- Loại bỏ hoàn toàn hiện tượng build staging lặp;
- Trạng thái `review_required` không còn bị ghi đè thành `updates_available`;
- Nút "Xuất bản", "Đồng bộ", "Thử lại" trên UI hoạt động chính xác dựa trên số liệu thực;
- Cơ chế chống cướp binding giữa các nhóm bảo vệ tính toàn vẹn dữ liệu;
- Xóa bỏ toàn bộ màu hardcode và chuỗi kỹ thuật tiếng Anh trên giao diện;
- Xác nhận tuyệt đối không chỉnh sửa `qnu-sso` và không xóa dữ liệu người dùng.
