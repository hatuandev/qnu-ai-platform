# Nhật Ký Làm Việc — Phiên 142 (2026-09-20)
## Phân Loại Ngữ Nghĩa Khối Văn Bản & Khắc Phục Lỗi Đè Chữ Của Badge Chuẩn Mistral Document AI

### 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-20 14:15 UTC+7
- **Mục tiêu**:
  - Khắc phục triệt để tình trạng toàn bộ các khối văn bản bị gán nhãn cứng thành `text` (màu tím), bao gồm cả tiêu đề La Mã in hoa (`II. TUYỂN SINH...`), các tiểu mục danh sách có dấu cộng (`+ Phương thức 1`, `+ Phương thức 2`), và các đề mục đánh số.
  - Xây dựng bộ phân loại ngữ nghĩa Heuristic (`classify_text_block` ở Backend và `classifyStudioRegion` ở Frontend) tự động phân loại chính xác thành `title` (xanh dương), `list` (xanh ngọc), `header` (xám), `signature` (hồng đỏ), và `text` (tím).
  - Khắc phục triệt để lỗi đè chữ của Pill Badge: Chuyển vị trí từ `-top-2.5 left-1` (nhô ra ngoài đè vào dòng chữ bên trên) sang `top-0 left-0 rounded-tl-[1px] rounded-br-[3px]` nằm gọn gàng bên trong góc trên bên trái của khung bao.

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)
- [`backend/app/modules/knowledge/parsers/blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py):
  - Thêm `import re`.
  - Triển khai hàm `classify_text_block(text, top_percent, bottom_percent) -> tuple[str, str]`:
    - `header`: Tọa độ `top_percent <= 18.0` và chứa từ khóa hành chính ("BỘ GIÁO DỤC VÀ ĐÀO TẠO", "CỘNG HÒA XÃ HỘI...", "TRƯỜNG ĐẠI HỌC...", "Số:", "ngày...tháng...năm").
    - `signature`: Tọa độ `bottom_percent >= 68.0` hoặc `top_percent >= 65.0` và chứa chức danh ("HIỆU TRƯỞNG", "KT. HIỆU TRƯỞNG", "TRƯỞNG PHÒNG", "GIÁM ĐỐC", "Nơi nhận:").
    - `title`: Bắt đầu bằng số La Mã (`^(?:I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.\s+`), `Điều \d+`, `Chương \d+`, `Mục \d+`, tiêu đề ngắn kết thúc bằng `:`, hoặc văn bản in hoa $\ge 75\%$.
    - `list`: Bắt đầu bằng dấu cộng (`+`), gạch đầu dòng (`-`, `–`), bullet (`•`), số thứ tự hoặc chữ cái danh mục (`1. `, `2. `, `a) `, `b) `).
    - `text`: Mặc định cho các đoạn văn xuôi, thuyết minh.
  - Tích hợp vào `extract_page_blocks` thay thế nhãn cứng `type: "text"`.
- [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx):
  - Bổ sung hàm `classifyStudioRegion(text, top, height, currentType)` trong `mapVerificationDataToStudioDoc` để dữ liệu cũ lẫn mới đều lập tức hiển thị màu sắc và nhãn chính xác trên UI mà không bắt buộc người dùng phải nạp lại tệp.
- [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx):
  - Điều chỉnh class của Pill Badge: Chuyển từ `-top-2.5 left-1` sang `top-0 left-0 px-1.5 py-0.5 text-[9px] font-mono font-medium lowercase rounded-tl-[1px] rounded-br-[3px] text-white shadow-xs pointer-events-none leading-none z-20 select-none`.
  - Đảm bảo 100% không còn hiện tượng badge che khuất dòng chữ của khối bên trên.

### 3. Kết Quả Kiểm Thử (Verification)
- **Backend**:
  - `uv run ruff check app/modules/knowledge/parsers/blocks.py`: Passed (0 errors).
  - `uv run ruff check .`: Passed (0 errors).
  - `uv run --extra dev pytest tests/test_knowledge.py -v`: 31 passed, 1 warning (100% pass).
- **Frontend**:
  - `npm run lint`: Checked 165 files in 165ms. 0 errors, 0 warnings.
  - `npm run typecheck`: `tsc --noEmit` hoàn thành với 0 errors.
  - `npm run build`: `vite v6.4.3` build thành công toàn bộ bundle trong 12.15s.
