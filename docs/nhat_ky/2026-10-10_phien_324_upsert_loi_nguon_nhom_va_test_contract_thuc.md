# NHẬT KÝ LÀM VIỆC — PHIÊN #324: UPSERT LỖI NGUỒN NHÓM & TEST ĐÚNG CONTRACT THỰC

- **Thời gian**: 2026-10-10
- **Dự án**: QNU AI Platform
- **Mục tiêu**: Khép lại hai phát hiện sau review phiên #323 mà không thay đổi schema, API contract hoặc repository `qnu-sso`.

## 1. Thay đổi đã thực hiện

### 1.1. Đồng bộ tuyệt đối giữa `failed_count` và `items`

- Bổ sung helper `_upsert_failed_item` trong `group_source_diff_service.py`.
- Mỗi `document_id` chỉ giữ một kết quả trong response.
- Conflict ownership luôn có độ ưu tiên cao nhất và thay thế cả item `success` hoặc lỗi tổng quát đã tồn tại.
- Revision failed thay thế item thành công nhưng không ghi đè lỗi nghiệp vụ cụ thể đã có.
- Loại bỏ trường hợp response báo `failed_count > 0` trong khi item của cùng tài liệu vẫn mang `status="success"`.

### 1.2. Sửa regression test theo contract thật

- Sửa fixture conflict để giữ `(document_id, revision_id)` trong `desired_pairs`, đúng với thứ tự phân loại thực tế của `evaluate_group_diff`.
- Bổ sung test trực tiếp xác nhận conflict upsert thay thế item thành công và `DOCUMENT_REVISION_FAILED` bằng `DOCUMENT_BOUND_TO_ANOTHER_GROUP_SOURCE`.
- Bảo đảm danh sách response không sinh item trùng tài liệu.

## 2. Tệp thay đổi

- `backend/app/modules/knowledge/services/group_source_diff_service.py`
- `backend/tests/test_knowledge_group_sources.py`
- `docs/nhat_ky/2026-10-10_phien_324_upsert_loi_nguon_nhom_va_test_contract_thuc.md`
- `docs/nhat_ky/README.md`
- `docs/memory/PROJECT_CONTEXT.md`
- `docs/WORK_LOG.md`

## 3. Kết quả kiểm thử

- Ruff phạm vi Knowledge: **All checks passed**.
- Test riêng nguồn nhóm: **32 passed, 1 skipped**.
- Backend targeted suites: **90 passed, 1 skipped**, 2 cảnh báo Qdrant compatibility.
- Frontend unit tests: **10/10 passed**.
- Vite build + TypeScript: thành công, **built in 3.90s**.
- `git diff --check`: exit code 0; chỉ có cảnh báo chuyển LF/CRLF trên các tệp cũ.

## 4. Kết luận

Response của sync/publish hiện giữ bất biến: `failed_count`, `items[].status` và `items[].error_code` thống nhất theo từng tài liệu; conflict ownership không còn bị che bởi success hoặc lỗi revision tổng quát. Không sửa `qnu-sso`, không tạo migration và không thay đổi database schema.
