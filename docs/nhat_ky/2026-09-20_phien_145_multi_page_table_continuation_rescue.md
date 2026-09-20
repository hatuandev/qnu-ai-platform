# Nhật Ký Làm Việc — Phiên 145 (2026-09-20)
## Triển Khai Cơ Chế Cứu Bảng Nối Trang (Multi-Page Table Continuation Rescue)

### 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-20 14:41 UTC+7
- **Mục tiêu**:
  - Khắc phục hiện tượng các hàng dữ liệu mồ côi (Orphan Table Rows) bị rớt sang trang sau khi ngắt trang (như hàng `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204` ở trang 14) bị thuật toán PyMuPDF `find_tables()` bỏ qua do thiếu dòng tiêu đề và số hàng < 2, dẫn đến bị gán nhãn nhầm thành `text` (màu tím).
  - Xây dựng cơ chế phát hiện và giải cứu thông minh **Table Continuation Rescue** ở cả Backend và Frontend:
    - Nếu trang trước kết thúc bằng một bảng ở đáy trang (`bottom >= 60%`), và trang sau bắt đầu ở đầu trang (`top <= 30%`) bằng một khối có đặc điểm dữ liệu bảng (chứa mã ngành đào tạo Việt Nam 7 chữ số `\b7\d{6}\b`, mã tổ hợp môn `A00|A01|...`, hoặc khoảng cách cột).
    - $\rightarrow$ Tự động chuyển đổi và gán nhãn chính xác thành `type: "table"`, `label: "Bảng dữ liệu (tiếp nối)"` với viền cam và nền cam pastel chuẩn Mistral.

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)
- [`backend/app/modules/knowledge/parsers/blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py):
  - Bổ sung quy tắc nhận diện hàng bảng ngắt trang trong `classify_text_block`: Kiểm tra `top_percent <= 25.0`, chiều cao $\le 12\%$, và khớp tín hiệu dữ liệu bảng (`\b7\d{6}\b` hoặc mã tổ hợp môn).
- [`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py):
  - Trong `build_studio_pages`: Bổ sung kiểm tra liên kết trang `prev_has_bottom_table`. Nếu trang trước có bảng ở đáy và khối đầu trang sau mang tín hiệu bảng $\rightarrow$ tự động giải cứu thành `box_type = "table"`, `block_label = "Bảng dữ liệu (tiếp nối)"`.
- [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx):
  - Cập nhật `classifyStudioRegion` và `mapVerificationDataToStudioDoc`: Bổ sung tham số `prevHasBottomTable`. Nhận diện hàng ngắt trang và chuyển sang `type: "table"`, `label: "Bảng dữ liệu (tiếp nối)"`.

### 3. Kết Quả Kiểm Thử (Verification)
- **Backend**:
  - `uv run ruff check .`: 0 errors.
- **Frontend**:
  - `npm run lint`: Checked 165 files in 176ms. 0 errors.
  - `npm run typecheck`: 0 errors.
  - `npm run build`: vite build thành công trong 6.76s.
