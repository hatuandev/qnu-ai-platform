# Nhật Ký Phiên #317: Xác Minh Membership Race Sau IntegrityError

- **Thời gian**: 2026-10-10 13:47 (UTC+7)
- **Mục tiêu**: Không được coi mọi `IntegrityError` khi thêm tài liệu vào nhóm là một race duplicate hợp lệ.

## Thay đổi

### Backend

- `backend/app/modules/documents/intake_service.py`
  - Lưu các giá trị response dạng primitive trước khi một rollback có thể làm expire ORM objects.
  - Sau `IntegrityError` ở bước commit membership, rollback rồi truy vấn lại đúng cặp `(group_id, document_id)`.
  - Chỉ trả thành công idempotent khi membership thật sự tồn tại sau rollback.
  - Nếu không tìm thấy membership, trả RFC 7807 `DOCUMENT_GROUP_MEMBERSHIP_FAILED` (HTTP 409), không nuốt lỗi và không báo thành công giả.
  - Kiểm tra lại group theo tenant/workspace trước khi tạo membership.

- `backend/tests/test_document_repository_workflow.py`
  - Sửa test race để mô phỏng membership do request concurrent đã commit và được re-query thành công.
  - Thêm regression test xác nhận IntegrityError không có membership winner phải trả `DOCUMENT_GROUP_MEMBERSHIP_FAILED`.

## Bất biến nghiệp vụ

```text
membership commit thành công
  -> trả thành công

membership commit IntegrityError
  -> rollback
  -> re-query membership
      -> tồn tại: race duplicate hợp lệ, trả thành công idempotent
      -> không tồn tại: trả DOCUMENT_GROUP_MEMBERSHIP_FAILED
```

## Kiểm thử

- Test riêng `test_document_repository_workflow.py`: **27 passed**.
- Ba suite Documents mục tiêu: **48 passed**.
- Ruff toàn backend: **All checks passed**.
- Full backend suite: **685 passed, 1 skipped, 11 failed**.
  - 11 lỗi còn lại nằm ngoài phạm vi thay đổi: quyền RBAC của Knowledge publishing endpoints, dữ liệu Fact Layer/export, và kỳ vọng role đăng nhập.
  - Không có lỗi nào thuộc `documents/intake_service.py` hoặc các regression test vừa thêm.

## Phạm vi an toàn

- Không chỉnh sửa `qnu-sso`.
- Không chỉnh sửa frontend trong phiên này.
- Full pytest đã tự dọn thư mục runtime untracked `backend/storage/documents/tenant_qnu/` gồm hai fixture được tạo lúc 13:35 (`quyet_dinh_2139.txt`, `quy_che_dao_tao_2026.md`). Hai file không được Git theo dõi nên không thể khôi phục bằng Git và không thuộc diff bàn giao.

