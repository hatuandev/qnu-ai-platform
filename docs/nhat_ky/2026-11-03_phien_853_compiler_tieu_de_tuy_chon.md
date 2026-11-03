# Phiên 853 — Xuất Markdown cho nhóm Compiler không có tiêu đề

- Kiểm tra DB local và artifact bằng thao tác đọc. Model trả `finish_reason=stop` ở hai nhóm đã gửi. Nhóm 1 hợp schema với `title=null` nhưng Markdown gọi `html.escape` trên giá trị rỗng. Nhóm 2 hoàn tất, hai nhóm còn lại chưa chạy. Lượt đã ghim phiên bản văn bản hậu OCR đã lưu.
- Sửa renderer bỏ heading tài liệu của nhóm khi thiếu tiêu đề. JSON nhóm giữ giá trị null. Bản hợp nhất vẫn dùng quy tắc tiêu đề hiện có. Log worker ghi nhóm và loại ngoại lệ, còn trang chi tiết hiển thị lỗi và mã kỹ thuật khi mở rộng.
- Chạy lại parse và render từ hai phản hồi lưu sẵn. Nhóm 1 xuất 6 mục và nhóm 2 xuất 7 mục. Không gọi model thật mới và không đổi trạng thái lượt đã kết thúc.
- Ruff có phạm vi và `git diff --check` đạt. Vitest 13 ca và Biome 2 tệp đạt.
