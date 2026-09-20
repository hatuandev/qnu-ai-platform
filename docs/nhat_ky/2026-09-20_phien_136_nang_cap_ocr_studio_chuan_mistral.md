# Nhật Ký Làm Việc — Phiên #136 (2026-09-20 13:10 UTC+7)

## Mục Tiêu
Nâng cấp toàn diện giao diện **Đối Soát & Hiệu Chỉnh OCR** (Verification Studio / Scan Studio) theo hình mẫu **Mistral Document AI OCR Playground** (`console.mistral.ai/build/document-ai/ocr-playground`), kết hợp nghiêm ngặt quy tắc nhận diện thương hiệu **QNU Academic Teal** và kiến trúc UI của dự án.

## Chi Tiết Thay Đổi Kỹ Thuật
1. **Header Top Bar & KPI Meta Strip Chuẩn Mistral**:
   - Tích hợp icon PDF màu đỏ nổi bật và tên file tài liệu.
   - Bổ sung dải KPI Meta Strip: Thời gian xử lý (`⚡ Latency`), Số trang (`📖 Trang`), Số từ (`🔤 Từ`), Dung lượng (`💾 Dung lượng`), và Bộ máy (`⚙️ Engine`).
   - Bổ sung các action buttons: `<> Mã API` (cURL / Python), `Tải xuống` (Download file Markdown bóc tách), và nút chính `✓ Xác nhận đối soát & Phê duyệt` (màu Academic Teal).

2. **Floating Pill Toolbar Lơ Lửng (Đỉnh Canvas)**:
   - Thay thế dải thanh toolbar chiếm diện tích bằng thanh viên nang nổi kính mờ sang trọng (`backdrop-blur-md bg-zinc-900/90 text-white rounded-full border border-zinc-700/70 shadow-2xl`).
   - Tích hợp đầy đủ: Phân trang `< Trang 1 / 14 >`, Zoom `- 100% +`, Fit Width (`Maximize2`), Toggle Chế độ xem (Trang đơn vs Cuộn liên tục), Toggle Bounding Boxes và Lọc loại vùng.

3. **High-Contrast Dark Canvas & Continuous Multi-Page Scroll**:
   - Nền canvas xám đen (`#121214`) tạo độ tương phản cực đại, tôn trang giấy A4 màu trắng sáng với bóng đổ `shadow-2xl`.
   - Hỗ trợ chế độ **Cuộn liên tục (Continuous Scroll)** qua `IntersectionObserver`, người dùng cuộn mượt mà qua tất cả các trang; số trang trên Floating Toolbar tự động cập nhật theo trang đang nằm trong tầm mắt.
   - Bounding boxes thanh mảnh `1.5px`, tag label siêu nhỏ gọn `text-[9px] font-mono uppercase px-1 py-0.2 rounded-xs font-semibold`, màu sắc ngữ nghĩa tinh tế (Teal, Blue, Violet, Amber, Rose, Emerald).

4. **Inspector Cột Phải (4 Tabs Chuẩn Mistral + Two-Way Sync)**:
   - **Tab Văn bản (Text Output)**: Phân đoạn từng trang `Page X of Y` kèm nút `[Sao chép]` riêng từng trang và liên kết nhảy nhanh tới trang trên Canvas.
   - **Tab Markdown**: Render GFM sắc nét (tiêu đề Teal, bảng biểu, danh sách), hỗ trợ toggle "Xem đẹp", "Mã nguồn", và "Sửa tay (Human-in-the-loop)".
   - **Tab Bảng tính (Visual)**: Excel Spreadsheet Viewer trực quan hóa bảng biểu.
   - **Tab JSON (AST)**: Cấu trúc bboxes và polygons.
   - Hỗ trợ đổi cỡ chữ `Aa` (nhỏ / vừa).

## Kết Quả Kiểm Thử (Verification)
- **Frontend**:
  * `npm run format`: 164 files, 0 fixes needed.
  * `npm run lint`: Checked 164 files, **0 lỗi linter** (100% sạch).
  * `npm run typecheck`: **0 lỗi TypeScript** (`tsc --noEmit`).
  * `npm run build`: Vite build thành công: **2575 modules transformed, ✓ built in 9.12s**.
- **Backend**:
  * `uv run ruff check .`: **All checks passed! (0 lỗi)**.
