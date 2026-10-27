# 29 — Nối hậu OCR, review tự động và sửa Compiler backendV1

Phạm vi Context654: ba bước backend người dùng đã chọn; UI làm sau.

1. Người dùng đọc/sửa văn bản OCR và lưu một text version gồm MD/JSON đồng bộ.
2. Tạo Compiler, chọn chính xác số version cho từng OCR run. Chọn0/bỏ trống dùng
   gốc. Server ghim bản được chọn; bản sửa mới hơn không thay lượt Compiler cũ.
3. Compiler hoàn tất và lưu intent review trong cùng transaction. Queue v1 chạy
   review độc lập; reconcile khôi phục giao việc thiếu. Key cố định chống gọi model
   lặp; failed/uncertain cần thao tác kiểm tra mới rõ ràng, không retry âm thầm.
4. Đọc báo cáo có nguồn và đoạn biên soạn. Người dùng sửa title/sections/unknowns,
   tạo preview trước/sau, rồi chấp nhận đúng preview bằng hash và Idempotency-Key.
5. Server tạo run con `origin=user_edit`, giữ parent, bảng/citation/nguồn bảo vệ,
   lưu MD/JSON mới và tạo review riêng. Không gọi lại Compiler hoặc ghi đè bản cũ.
6. Đăng ký phiên bản, duyệt và xuất bản theo quyết định riêng như trước. Index/search
   dùng bản đã xuất bản với cùng text-version/source hashes. Review chưa phải cổng
   publication bắt buộc và verdict không thay phê duyệt con người.

Quyền được giải quyết ở server qua workspace membership/role của backendV1.
Model/OCR/tài liệu là dữ liệu không tin cậy, không tự cấp quyền lưu hoặc xuất bản.
Preview hết hạn, khác actor, khác bundle/report, nguồn có revision mới hoặc có
bản sửa cạnh tranh bị chặn. Lỗi lưu tệp không tạo child hiển thị dở dang.

Chi tiết request/response, provider và giới hạn: [Compiler workflow](../../backendV1/docs/compiler-workflow.md).
Các hình Context653 là ảnh chụp trạng thái trước bước nối này.
