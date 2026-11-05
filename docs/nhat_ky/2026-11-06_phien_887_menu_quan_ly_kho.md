# Phiên 887 — Gọn menu quản lý kho

## Phạm vi

Theo xác nhận người dùng, menu Quản lý chỉ giữ sửa thông tin, tạo thư mục, lưu trữ và xóa kho theo quyền hiện có. Bỏ lối “Hỏi đáp trên kho”; người dùng dùng Trợ lý AI. Chuyển liên kết chỉ mục và đánh giá RAG sang Công cụ nâng cao trong thanh danh sách tài liệu, tách khỏi menu quản lý trên đầu trang.

## Thay đổi

- `frontendV1/src/features/knowledge/knowledge-detail-page.tsx`: chuyển hai liên kết, bỏ import MessageSquare không còn dùng; thêm tên truy cập cho menu quản lý trên mobile. Toolbar cho phép xuống dòng khi hẹp. Giữ đường dẫn/phạm vi collection, quyền canManage và xác nhận lưu trữ/xóa hiện có; không đổi server hoặc chức năng tự lập chỉ mục.
- `frontendV1/tests/knowledge-actions-708.test.tsx`: kiểm menu admin đúng bốn mục, công cụ nâng cao đúng hai đích, member không có quyền không thấy menu, editor không được nâng quyền xóa. Mock Link truyền tiếp thuộc tính Radix asChild như role/ref và giữ tham số đường dẫn.

## Kiểm chứng

Cwd `frontendV1`:

- `npm exec -- vitest run tests/knowledge-actions-708.test.tsx tests/knowledge-drag-and-drop.test.tsx --reporter=dot`: lần đầu 39 pass/1 fail vì mock Link không truyền role của menu item. Sửa mock cho đúng hợp đồng asChild, giữ assertion; chạy cuối **PASS**, exit 0, 40/40 ca.
- `npm exec -- biome check src/features/knowledge/knowledge-detail-page.tsx tests/knowledge-actions-708.test.tsx`: exit 0, 0 lỗi; còn một warning optional-chain cũ ở parentFolder.
- `npm run build`: **PASS**, exit 0, gồm Vite và TypeScript; cảnh báo bundle lớn vẫn còn.

Cwd root:

- Chromium trên app local đang chạy, chỉ đọc và mở menu tại 390px/1280px: **PASS**, menu quản lý bốn mục, nâng cao hai mục. Đã xem ảnh; không kích hoạt liên kết chỉ mục, lưu trữ hoặc xóa. Lượt đọc đầu chưa chờ dữ liệu nên không thấy kho; lượt kiểm cuối chờ link thật tải xong rồi kiểm, không ghi dữ liệu.
- `git diff --check`: **PASS**. Log/ảnh ở `tmp/check-887-*` và `tmp/fix-887-*`, không đưa vào Git.

Backend/full suite **NOT RUN** vì chỉ đổi giao diện, không đổi contract/quyền server. Không restart/reset/reindex/push hoặc thay dữ liệu thật. Tải lại trang để xem menu mới.
