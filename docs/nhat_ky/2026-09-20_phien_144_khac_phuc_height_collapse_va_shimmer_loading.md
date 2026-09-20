# Nhật Ký Làm Việc — Phiên 144 (2026-09-20)
## Khắc Phục Triệt Để Lỗi Sụp Đổ Chiều Cao (Height Collapse) & Thêm Shimmer Loading Cho OCR Canvas

### 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-20 14:28 UTC+7
- **Mục tiêu**:
  - Khắc phục triệt để hiện tượng khi vừa tải tệp lên hoặc khi ảnh chưa nạp xong, trang giấy trắng biến mất và các Bounding Boxes bị sụp chiều cao về 0, co cụm thành các đường chỉ ngang mỏng dính xếp sát rạt nhau trên nền đen.
  - Cố định tỷ lệ khung trang chuẩn A4 `aspect-[1/1.414]` cho `page-canvas`, bảo đảm tờ giấy A4 luôn giữ nguyên kích thước và hình dáng trên màn hình kể cả khi ảnh đang tải từ Backend.
  - Trang bị Shimmer Loading Placeholder (`animate-pulse`) kèm icon trang tài liệu và thông báo trạng thái `Đang nạp trang X...` trong thời gian chờ ảnh scan tải về.
  - Hiệu ứng chuyển cảnh ảnh scan mượt mà (`transition-opacity duration-300`).

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)
- [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx):
  - Thêm state `loadedImages: Record<number, boolean>` theo dõi trạng thái tải ảnh của từng trang.
  - Gán `aspect-[1/1.414] overflow-hidden` vào thẻ `div#page-canvas-${page.pageNumber}`: Khóa cứng tỷ lệ khổ A4 quốc tế ($210 / 297$), chấm dứt hoàn toàn hiện tượng Height Collapse.
  - Bổ sung Shimmer Placeholder khi `!isLoaded`: Hiển thị nền mờ và icon `FileText` nhấp nháy êm dịu, không gây chớp mắt.
  - Thẻ `<img>`: Chuyển sang `w-full h-full object-fill block transition-opacity duration-300` với `opacity-0` khi đang tải và `opacity-100` khi đã tải xong.
  - Lớp Bounding Boxes gán `z-10` nằm chuẩn xác trên nền A4 trắng ngay từ giây đầu tiên mà không bị xẹp lép.

### 3. Kết Quả Kiểm Thử (Verification)
- **Frontend**:
  - `npm run lint`: Checked 165 files in 162ms. 0 errors, 0 warnings.
  - `npm run typecheck`: `tsc --noEmit` đạt 0 errors.
  - `npm run build`: `vite v6.4.3` đóng gói thành công trong 6.39s.
