# Phiên 889 — Hiển thị ô Chọn tất cả trong OCR

Thanh tab của màn hiệu đính chiếm hết chiều ngang và đẩy ô Chọn tất cả ra khỏi khung. `ocr-comparison-view.tsx` cho thanh tab chia sẻ chiều rộng với các thao tác và cho cụm thao tác xuống hàng khi khung hẹp. Phạm vi sửa theo yêu cầu là bố cục OCR. Việc lược các nút tải là chủ ý của người dùng. Câu chữ hộp tải phiên bản được giải thích trong trao đổi.

- Trong `frontendV1`, `npm exec -- biome check src/features/knowledge/ocr-comparison-view.tsx` và `npm run build` đều đạt, exit 0. Build gồm TypeScript và còn cảnh báo kích thước gói.
- Từ root, `node tmp/check-889-browser.mjs` đạt tại 320, 390 và 1280 px. Chromium kiểm ô chọn và nhãn nằm trong khung, chọn bằng chuột, bỏ chọn bằng phím Space và các nút thao tác Markdown/JSON. Đã xem ảnh thanh công cụ ở 390 và 1280 px.
- Unit suite và backend test chưa chạy cho thay đổi bố cục này. Kiểm tra trình duyệt dùng trạng thái chọn tại chỗ, không gửi yêu cầu OCR hoặc sửa tài liệu.
