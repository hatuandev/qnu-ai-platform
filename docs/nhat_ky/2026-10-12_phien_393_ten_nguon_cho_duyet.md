# Phiên 393 — Tên nguồn đang chờ duyệt

## Mục tiêu

Nguồn chưa có active_source_revision_id vẫn hiển thị tên/file gốc, không rơi về bnd_ID. Không duyệt revision hoặc thay pointer đang phục vụ.

## Thay đổi

- binding_display.py: đọc latest revision snapshot theo revision_no/created_at trong tập binding đã được xác minh quyền. Bulk DISTINCT ON tránh N+1. Nếu thiếu tên/file thì đọc snapshot import item mới nhất, join batch/binding tenant/collection; không phụ thuộc tệp Repository còn tồn tại. Field draft rỗng không xóa metadata active.
- binding_service.py: list_bindings/get_binding sử dụng metadata hiển thị riêng; source_status và active_source_revision_id vẫn đọc bản active như cũ. Không mở rộng scope quyền, không cập nhật DB.
- test_binding_display.py: 6 ca list/detail pending, import trước revision, field rỗng, empty list, lỗi DB không fake fallback. Không thay nhãn trạng thái FE trong task này.

## Kiểm chứng

6 focused passed, Ruff scoped và toàn backend đạt; full suite 968passed/13failed/2skipped (các lỗi ngoài scope export/GC/auth/reconciliation/facts tương tự #389). Full bắt đầu trước ca detail thêm, ca mới được kiểm riêng. uv dev tools lúc đầu thiếu do venv hiện tại không có pytest/ruff; dùng uv --extra dev phục hồi, AccessDenied trong sandbox được chạy kiểm thử ngoài sandbox.

Runtime service read-only xác nhận8nguồn ảnh user có tên và file đúng dù active_source vẫnnull: Phuong huong2024, Cacnganh2025, NQ57, HDnhaphoc, FLYER2026, BCkhaosat2022, BC2025draft, BC2024. Không sửa pointer/dữ liệu/phêduyệt/publish/reset/restartworker. Chưa browserE2E; backend reload cần nhận code mới, user làm mới danh sách.
