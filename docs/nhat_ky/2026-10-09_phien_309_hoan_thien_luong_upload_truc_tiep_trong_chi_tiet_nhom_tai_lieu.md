# Nhật Ký Phiên 309: Hoàn Thiện Luồng Tạo Nhóm Tài Liệu & Tải Lên Trực Tiếp Trong Chi Tiết Nhóm

**Ngày thực hiện**: 2026-10-09  
**Mục tiêu**: Hỗ trợ luồng người dùng tạo Nhóm Tài Liệu chuyên đề (ví dụ "Kho tài liệu tuyển sinh"), tự động điều hướng sang chi tiết nhóm, và bổ sung chức năng tải lên tài liệu trực tiếp từ máy tính vào ngay trong màn hình chi tiết nhóm.

---

## 1. Bối Cảnh & Vấn Đề

- Người dùng tiếp cận phân hệ Kho Tài Liệu (`/documents`) với nhu cầu: Tạo một nhóm/kho riêng mang tên *"Kho tài liệu tuyển sinh"*, sau đó click vào nhóm để mở màn hình chi tiết, và tải các file tài liệu trực tiếp vào riêng nhóm đó.
- **Trở ngại trước đó**:
  1. Trong màn hình chi tiết nhóm (`/documents/groups/:groupId`), chỉ có nút *"Thêm Tài Liệu"* (chọn từ các tài liệu đã có trong kho chung), chưa có nút *"Tải Lên Tệp Mới"* trực tiếp từ máy tính.
  2. Khi tạo nhóm mới tại `/documents/groups`, người dùng chỉ nhận được thông báo toast và đóng modal, phải tự tìm thẻ nhóm để bấm vào.
  3. API tải lên `/documents/upload` và `/documents/intake` chưa hỗ trợ tham số `group_id` để tự động gán tài liệu vào nhóm ngay trong một giao dịch.

---

## 2. Các Thay Đổi & Giải Pháp Kỹ Thuật

### 2.1 Backend (FastAPI + SQLAlchemy)
- **File**: `backend/app/modules/documents/router.py`:
  - Cập nhật endpoint `POST /documents/upload` và `POST /documents/intake` nhận thêm tham số form `group_id: str | None = Form(None)`.
  - Khi có `group_id`, sau khi lưu tệp vào MinIO S3 và tạo `RepositoryDocument`, hệ thống tự động gọi `document_group_service.add_documents_to_group(...)` để gán quan hệ `DocumentGroupMembership` ngay lập tức.
  - Sử dụng `actor: AuthActor` từ dependency để bảo đảm audit logging chính xác.
- **File**: `backend/tests/test_document_groups_and_knowledge_attach.py`:
  - Thêm test case `test_upload_with_group_id_calls_add_documents_to_group`: kiểm thử luồng upload tự động liên kết nhóm thành công 100%.

### 2.2 Frontend (React + Vite + TanStack Query)
- **File**: `frontend/src/services/documents-api.ts`:
  - Mở rộng hàm `uploadDocument` hỗ trợ `meta.group_id?: string`, tự động đính kèm vào `FormData` khi gửi API.
- **File**: `frontend/src/features/documents/components/document-upload-modal.tsx`:
  - Mở rộng `DocumentUploadModalProps` nhận `groupId?: string` và `groupName?: string`.
  - Hiển thị tiêu đề ngữ cảnh: *"Tải Lên Tài Liệu Vào Nhóm: [Tên Nhóm]"*, mô tả rõ ràng tệp sẽ tự động được thêm vào nhóm.
  - Tự động invalidate queries: `["group-documents", groupId]`, `["document-group", groupId]`, `["document-groups"]`.
  - Nút bấm và thông báo toast ngữ nghĩa rõ ràng: *"Đã nạp thành công X tệp vào nhóm [Tên Nhóm]!"*.
- **File**: `frontend/src/features/documents/document-group-detail-page.tsx`:
  - Bổ sung nút **"Tải Lên Tệp Mới"** (`Upload` icon, button `variant="default"` màu teal nổi bật) trên Action Toolbar.
  - Cập nhật `EmptyState` khi nhóm chưa có tài liệu: hành động chính là nút *"Tải Lên Tệp Mới"*.
  - Tích hợp `DocumentUploadModal` vào trang chi tiết nhóm với `groupId={group.id}` và `groupName={group.name}`.
- **File**: `frontend/src/features/documents/document-groups-page.tsx`:
  - Khi tạo nhóm tài liệu thành công, tự động điều hướng người dùng thẳng vào trang chi tiết nhóm vừa tạo (`/documents/groups/{newGrp.id}`).

---

## 3. Kết Quả Kiểm Thử

| Kiểm tra | Lệnh | Kết quả |
| :--- | :--- | :---: |
| **Backend Tests** | `pytest tests/test_document_groups_and_knowledge_attach.py` | **14/14 PASSED (100%)** |
| **Backend Linter** | `ruff check backend/app/modules/documents/router.py backend/tests/test_document_groups_and_knowledge_attach.py` | **0 errors (100% clean)** |
| **Frontend Build** | `npm run build` (`vite build && tsc --noEmit`) | **PASSED (3833 modules, 0 error)** |
