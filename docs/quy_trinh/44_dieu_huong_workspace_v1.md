# 44 — Điều hướng workspace V1

Header sidebar chọn workspace được phép truy cập. Các màn hình nghiệp vụ tiếp tục dùng ID nội bộ và kiểm quyền tại server; mã trong URL chỉ dùng chọn ngữ cảnh, không chứng minh quyền.

| Đường dẫn công khai | Nội dung |
|---|---|
| /:code/knowledge | Danh sách kho của workspace |
| /:code/knowledge/:collectionId | Chi tiết kho |
| /:code/files/:sourceId | Tài liệu và kết quả bóc tách |
| /:code/files/:sourceId?runId=... | Một lượt xử lý xác định |
| /:code/members | Thành viên workspace |

Các module khác giữ phần đuôi đường dẫn hiện có sau mã workspace. Link /workspaces/:id/... tiếp tục dùng được và được rút gọn bằng TanStack route mask. URL ngắn mới/F5 đi qua GET /platform/v1alpha1/workspaces/resolve-route với code và source_id tùy chọn; API kiểm resolve_workspace_access, source trong workspace và trạng thái lifecycle trước khi trả ID nội bộ. Các API nghiệp vụ giữ nguyên hợp đồng/quyền hiện hành.

Đổi workspace từ trang tài liệu về danh sách kho workspace mới; không chuyển source/run/revision cũ. Link chia sẻ tự khôi phục đúng workspace, độc lập với lựa chọn ở tab khác. Chưa chọn workspace thì header không gán nhầm đơn vị đầu danh sách. Workspace dùng mã trùng route hệ thống giữ URL cũ tương thích.

Quản lý workspace và tạo mới nằm trong dropdown của quản trị nền tảng. Nhà cung cấp giữ phạm vi nền tảng, còn các mục nghiệp vụ lấy workspace hiện hành. Trang chi tiết nguồn active Kho tri thức; trang OCR riêng vẫn active OCR và chính tả.

[Nhật ký triển khai và kiểm chứng](../nhat_ky/2026-10-29_phien_712_url_workspace_va_sidebar.md).
