# NHẬT KÝ PHIÊN LÀM VIỆC — PHIÊN #139
# Ngày: 2026-09-20 | Nội dung: Tinh Giản Giao Diện OCR Studio & Chuẩn Hóa Nhận Dạng Theo Mistral Document AI

## 1. Mục Tiêu Phiên Làm Việc
1. Lược bỏ các tính năng nhỏ thừa thãi làm chật chội và chiếm dụng không gian hiển thị của trang đối soát OCR.
2. Chuẩn hóa hệ thống nhãn nhận dạng Bounding Box theo chuẩn Mistral Document AI:
   - Hiển thị liên tục nhãn Pill Badge (`opacity-100`) ở góc trên bên trái từng hộp: `header`, `title`, `text`, `table`, `signature`.
   - Màu sắc và viền hộp đồng bộ sắc nét, nền trong suốt không che chữ.
3. Xóa bỏ dải đen ngang ghi "Trang 1 / 351 từ" đè lên đầu mỗi trang giấy trong Canvas.
4. Tinh giản thanh Toolbar Canvas còn 3 cụm căn giữa: Phân trang, Zoom và Toggle Khung scan.
5. Tinh giản cột Inspector bên phải: Chỉ giữ tab Thực thể, tab Markdown và tab Bảng tính; xóa bỏ tab Regions và JSON AST.
6. Tinh giản Header Topbar: Bỏ dải KPI meta strip và nút Mã API, thu gọn nút Tải xuống.

---

## 2. Các Tệp Tin Đã Thay Đổi

| Tệp | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`frontend/src/components/knowledge/ocr/types.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/types.ts) | MODIFY | Cập nhật `REGION_COLORS` theo bảng màu Mistral Document AI |
| [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) | MODIFY | Xóa dải đen đầu trang giấy, hiển thị Pill Badge nhãn nhận dạng ở góc trên bên trái |
| [`frontend/src/components/knowledge/ocr/ocr-toolbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-toolbar.tsx) | MODIFY | Tinh giản toolbar căn giữa: `< 1 / 14 >`, `- 100% +`, toggle Khung scan |
| [`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-inspector.tsx) | MODIFY | Rút gọn tabs, xóa tab Regions và JSON AST, dọn sạch dead code |
| [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) | MODIFY | Bỏ KPI meta strip, bỏ nút Mã API, thu gọn nút Tải xuống |

---

## 3. Kết Quả Kiểm Thử
- `npm run format`: 165 files passed (0 thay đổi mới).
- `npm run lint`: Biome check 165 files — 0 lỗi, 0 cảnh báo.
- `npm run typecheck`: TypeScript tsc --noEmit — 0 lỗi.
- `npm run build`: Vite build hoàn tất thành công trong 9.07s.
