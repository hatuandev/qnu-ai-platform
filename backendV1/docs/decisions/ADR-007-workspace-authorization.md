# ADR-007 — Workspace là biên giới quyền trong backendV1

**Trạng thái:** chấp thuận (2026-10-26). **Phạm vi:** chỉ `backendV1/`.

## Bối cảnh

Legacy dùng một phạm vi dữ liệu chung: `workspace_id` chỉ là hằng tương thích
(`workspace_qnu`), không phải căn cứ cấp quyền. Yêu cầu mới: mỗi đơn vị có
workspace, thành viên truy cập theo membership + role, và ModelOps cấp danh sách
model cho từng workspace.

Ngoại lệ này đã được ghi một dòng trong `AGENTS.md` (bất biến 2), giới hạn ở
`backendV1/`; `backend/` giữ nguyên hành vi cũ.

## Quyết định

1. **Workspace là biên giới quyền**, không phải phân vùng vật lý. Dữ liệu vẫn nằm
   trong một PostgreSQL; truy vấn tài nguyên phải qua `resolve_workspace_access`.
2. **Định danh thành viên** là `actor_ref` = SSO `sub` phân biệt hoa/thường, không dùng email.
3. **Hai tầng quyền tách biệt**: platform admin (`ai.workspaces.manage`) và
   workspace admin (role `admin` trong `workspace_members`). Workspace admin
   **không** tạo được workspace và không có quyền nền tảng.
4. **Mã lỗi truy cập**: 404 khi không phải thành viên (không lộ sự tồn tại);
   403 khi là thành viên nhưng thiếu role hoặc workspace đang tạm dừng.
5. **Không xoá cứng thành viên**: `DELETE` = `status=revoked`, giữ lịch sử; mời lại
   thì tái kích hoạt đúng bản ghi cũ.
6. **Admin đơn vị không hạ/thu hồi admin hoạt động cuối cùng** (`last_admin_required`). Platform admin có quyền phục hồi quản trị, kể cả thu hồi admin cuối. Workspace mới chưa được bổ nhiệm admin đơn vị vẫn do platform quản lý. Khóa row workspace trước khi thay membership để chặn race.
7. **Audit theo nghiệp vụ**: `workspace_events` ghi create/update/suspend/reactivate
   và member.added/restored/role_changed/revoked.

## Dữ liệu (backendV1 sở hữu)

`workspaces`, `workspace_members`, `workspace_events` — tên không trùng bất kỳ bảng
legacy nào (đã kiểm chứng với `LEGACY_TABLES`). Migration dùng
`alembic_version_backendv1`; `include_object` loại toàn bộ bảng legacy.

## Hệ quả

- `backend/` không đổi; hai chuỗi migration song song, không stamp chéo.
- Collection/Assistant/ModelOps sau này phải gọi `resolve_workspace_access`
  (hoặc `require_workspace_role`) trước khi chạm dữ liệu.
- ModelOps cấp model theo `workspace_allowed_providers`; provider/key là catalog
  toàn cục do platform admin quản lý.

## Ngoài phạm vi batch này

Upload/OCR/RAG/inference và chia sẻ tài nguyên giữa workspace. Batch636 đã thêm xác minh SSO RS256/JWKS (chưa live QNU), quota/usage nội bộ và model defaults theo capability; xem [API](../workspaces-modelops.md).
