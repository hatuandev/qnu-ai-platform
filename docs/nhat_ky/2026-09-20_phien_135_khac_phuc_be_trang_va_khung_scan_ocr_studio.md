# Nhật Ký Làm Việc — Phiên #135 (2026-09-20 00:08 UTC+7)

## Mục Tiêu
Khắc phục triệt để lỗi bể trang, khung nhận diện scan bị kéo giãn quá khổ (780%) và cột Markdown hiển thị dồn cục trong màn hình **Đối Soát & Hiệu Chỉnh OCR** (Verification Studio / Scan Studio).

## Bối Cảnh & Vấn Đề Phát Hiện
1. **Khung nhận diện scan bị tràn lề 780%**:
   - Trong `frontend/src/pages/scan-studio-page.tsx`, hàm `mapVerificationDataToStudioDoc` gán cứng `width: 780` và `height: 50` vào từng region.
   - Khi đưa vào `OcrCanvas` với CSS `style={{ width: `${region.width}%` }}`, thuộc tính trở thành `width: 780%` (rộng gấp 7.8 lần chiều rộng trang giấy ~6240px), đâm xuyên ra khỏi canvas và tạo thanh cuộn ngang ở đáy.
   - Dữ liệu `bounding_boxes` thực tế từ backend (mang tọa độ percent `x`, `y`, `width`, `height` chuẩn 0-100%) bị bỏ qua không được sử dụng.
2. **Khung trang giấy canvas**:
   - Container có kích thước cứng 800px x 1131px ở zoom 100%, khi màn hình hiển thị cột giữa hẹp hơn 800px sẽ sinh thanh cuộn ngang.
3. **Cột Markdown bên phải bị dồn cục**:
   - Văn bản bóc tách từ tài liệu DOCX hoặc OCR scan chỉ có ngắt dòng đơn `\n`. CommonMark coi đó là soft line break và nối thành 1 dòng liên tục, làm mất ngắt đoạn của văn bản hành chính Việt Nam.

## Chi Tiết Thay Đổi Kỹ Thuật
1. **`frontend/src/pages/scan-studio-page.tsx`**:
   - Sửa hàm `mapVerificationDataToStudioDoc`:
     - Ưu tiên sử dụng `p.bounding_boxes` trực tiếp từ backend.
     - Chuẩn hóa tọa độ `left`, `top`, `width`, `height` theo phần trăm `[0, 100%]`, clamp an toàn.
     - Bổ sung fallback an toàn cho `p.regions` với tọa độ phần trăm phân bổ đều trang (`left: 8%`, `width: 84%`, `height: 7%`), triệt tiêu hoàn toàn `width: 780`.
2. **`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`**:
   - Bổ sung cơ chế chuẩn hóa tọa độ 2 lớp (Safe Coordinate Normalization): Tự động nhận diện nếu tọa độ bị truyền dạng pixel (> 100) thì quy đổi về %, clamp nghiêm ngặt không cho bất kỳ box nào tràn ra ngoài lề trang giấy.
   - Bố cục căn giữa với `items-start`, `maxWidth: zoomLevel <= 100 ? "100%" : undefined` chống tràn lề ở zoom mặc định.
   - Nâng cấp hiển thị tag label sắc nét với semantic colors (Academic Teal, Blue, Purple, Amber, Rose).
3. **`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`**:
   - Bổ sung `formattedMarkdown`: Chuyển đổi các dòng ngắt đơn `\n` thành line break Markdown chuẩn (`  \n`) cho các dòng văn bản hành chính (tiêu đề, căn cứ, điều khoản, số hiệu).
   - Trang bị custom components phong cách QNU Academic Teal cho `ReactMarkdown`: Tiêu đề H1/H2/H3 phân cấp rõ ràng, Blockquote có viền teal nhạt, Bảng biểu có border và xen kẽ màu nền.

## Kết Quả Kiểm Thử (Verification)
- **Frontend**:
  * `npm run lint`: Checked 164 files, 0 lỗi linter (100% sạch).
  * `npm run typecheck`: 0 lỗi typecheck TypeScript (`tsc --noEmit`).
  * `npm run build`: Vite build đóng gói thành công trong **7.72s** (0 lỗi).
- **Backend**:
  * `uv run ruff check .`: All checks passed!
  * `uv run --extra dev pytest tests/test_knowledge.py -v`: **31/31 passed (100%)** trong 45.04s.
