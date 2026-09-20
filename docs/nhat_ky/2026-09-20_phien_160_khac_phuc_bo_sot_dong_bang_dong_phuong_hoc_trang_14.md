# NHẬT KÝ LÀM VIỆC — Phiên 160: Khắc Phục Bỏ Sót Hàng Bảng "Đông phương học" Ở Đầu Trang 14 Do Hiện Tượng Bảng Ngắt Trang Mở Đỉnh (Open-Top Table Continuation)
**Ngày thực hiện**: 2026-09-20  
**Người thực hiện**: AI Senior Full-Stack Architect  
**Mục tiêu**: Phân tích chi tiết tọa độ hình học và khắc phục dứt điểm hiện tượng Scan Studio bỏ sót hàng dữ liệu đầu tiên `Đông phương học | 7310608` ở đỉnh trang 14 của tài liệu tuyển sinh, chỉ đóng khung cam cho hàng thứ hai `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204`.

---

## 1. Bối Cảnh & Phân Tích Nguyên Nhân Gốc Rễ (Root Cause)

Người dùng phát hiện trên trang 14 của tài liệu tuyển sinh (`Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).pdf`), hệ thống nhận diện scan trong Scan Studio bỏ sót 1 dòng ở trên là `Đông phương học`, chỉ đóng khung cam `[table]` cho dòng dưới `Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204`.

Qua điều tra sâu tọa độ hình học (PDF drawings, vector text blocks và PyMuPDF table finder):
1. **Hiện tượng bảng ngắt trang mở đỉnh (Open-Top Continuation Table)**:
   - Bảng môn thi `Tiếng Anh` ở đáy trang 13 kéo dài sang trang 14 với 2 hàng:
     * Hàng 1: `| | Đông phương học | 7310608 |` (tọa độ `y = 49.68` đến `66.12`, tương ứng `y = 5.9%`)
     * Hàng 2: `| Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204 |` (tọa độ `y = 66.36` đến `83.42`, tương ứng `y = 7.88%`)
   - Vì bảng bị ngắt trang từ trang 13 sang trang 14, **ở đỉnh trang 14 KHÔNG CÓ ĐƯỜNG KẺ NGANG TRÊN CÙNG** (`y = 49.68`), mà chỉ có 4 đường kẻ dọc bắt đầu từ `y = 49.68` kéo dài xuống đường kẻ ngang giữa `y = 66.12`.
2. **Hạn chế của thuật toán `page.find_tables()` mặc định**:
   - Thuật toán `find_tables()` của PyMuPDF yêu cầu bảng phải có viền khép kín, nên nó đã **bỏ qua hoàn toàn hàng 1** và chỉ phát hiện bảng từ đường kẻ ngang giữa (hàng 2 `Tiếng Trung`, `y = 66.36` đến `83.42`).
3. **Hiện tượng triệt tiêu text block (Text Block Suppression Over-eagerness)**:
   - `page.get_text("blocks")` gom cả 2 dòng trên thành `Block 0` (`y0 = 51.52, y1 = 82.88`).
   - Hàm `extract_page_blocks` thấy `Block 0` giao cắt > 40% với `Table 0` (hàng 2 `Tiếng Trung`), nên đã loại bỏ `Block 0` để tránh trùng lặp chữ.
   - Hậu quả: Hàng 1 (`Đông phương học`) vừa không được `find_tables()` đưa vào bảng, vừa bị loại bỏ khỏi text blocks, dẫn đến biến mất hoàn toàn khỏi khung nhận diện scan!

---

## 2. Giải Pháp Kỹ Thuật Toàn Diện (Dual-Layer Rescue)

### 2.1. Tầng 1: Nhận Diện Đường Kẻ Ngang Ảo Cho Bảng Mở Đỉnh (`detect_open_top_lines` & `find_page_tables`)
- Trong [`backend/app/modules/knowledge/parsers/blocks.py`](../../backend/app/modules/knowledge/parsers/blocks.py):
  * Xây dựng hàm `detect_open_top_lines(page)`: Quét các đường kẻ dọc (`drawings`) ở đỉnh trang (`y0 < page_height * 0.35`). Nếu có $\ge 2$ đường kẻ dọc xuất phát từ cùng một tọa độ `min_y0` với độ rộng $\ge 100$pt mà không có đường kẻ ngang thực sự ở `min_y0`, hàm tạo đường kẻ ngang ảo `add_lines = [((min_x, min_y0), (max_x, min_y0))]`.
  * Xây dựng hàm `find_page_tables(page, **kwargs)`: Tự động kích hoạt `detect_open_top_lines` và truyền vào `page.find_tables(add_lines=...)`.
  * PyMuPDF kết nối đường kẻ ngang ảo với các đường kẻ dọc có sẵn, nhận diện trọn vẹn 100% cả 2 hàng:
    ```markdown
    |  | Đông phương học | 7310608 |
    | :--- | :--- | :--- |
    | Tiếng Trung | Ngôn ngữ Trung Quốc | 7220204 |
    ```
  * Tọa độ bảng tự động bắt đầu từ `y = 5.9%` (thay vì `7.88%`), chiều cao tăng từ `2.03%` lên `4.01%`, bao phủ hoàn hảo cả 2 hàng.
  * Đồng bộ `find_page_tables` sang [`pdf_parser.py`](../../backend/app/modules/knowledge/parsers/pdf_parser.py) và [`layout_detector.py`](../../backend/app/modules/ocr/layout_detector.py).

### 2.2. Tầng 2: Cơ Chế Safeguard Cứu Bảng Nối Trang Ở Cả Backend và Frontend
1. **Backend (`build_studio_pages` trong `ingestion_service.py`)**:
   - Khi gặp bảng ở đầu trang tiếp nối từ bảng đáy trang trước (`prev_has_bottom_table` và `bx_y <= 12.0`):
   - Đánh dấu nhãn chuẩn `"Bảng dữ liệu (tiếp nối)"` và căn chỉnh độ rộng với bảng trang trước (`prev_table_coords`).
   - Nếu dữ liệu cũ bị ngắt ở `bx_y > 6.5%`, tự động mở rộng `bx_y` lên `5.0% - 5.8%` để bao trọn hàng mồ côi phía trên.
2. **Frontend (`scan-studio-page.tsx`)**:
   - Cập nhật `classifyStudioRegion` và `mapVerificationDataToStudioDoc`:
   - Khi bảng tiếp nối ở đỉnh trang có `top > 6.5%` và `height <= 3.5%`:
   - Tự động mở rộng `finalTop = Math.max(5.0, top - 2.1)` và bù đắp chiều cao `finalHeight = height + (top - finalTop)`.
   - Giúp khung cam `[table]` ngay lập tức ôm trọn cả hàng `Đông phương học` và `Tiếng Trung` trên giao diện người dùng.

---

## 3. Danh Sách Tệp Thay Đổi

| Tệp | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :---: | :--- |
| [`backend/app/modules/knowledge/parsers/blocks.py`](../../backend/app/modules/knowledge/parsers/blocks.py) | Sửa đổi | Bổ sung `detect_open_top_lines`, `find_page_tables` và `_rescue_open_top_table`. |
| [`backend/app/modules/knowledge/parsers/pdf_parser.py`](../../backend/app/modules/knowledge/parsers/pdf_parser.py) | Sửa đổi | Áp dụng `find_page_tables` để không bỏ qua các hàng bảng ngắt trang. |
| [`backend/app/modules/ocr/layout_detector.py`](../../backend/app/modules/ocr/layout_detector.py) | Sửa đổi | Áp dụng `find_page_tables` trong `detect_layout_regions`, hạ ngưỡng `t_h >= 1.5%`. |
| [`backend/app/modules/knowledge/services/ingestion_service.py`](../../backend/app/modules/knowledge/services/ingestion_service.py) | Sửa đổi | Cập nhật `build_studio_pages` căn chỉnh và mở rộng BBox bảng tiếp nối. |
| [`frontend/src/pages/scan-studio-page.tsx`](../../frontend/src/pages/scan-studio-page.tsx) | Sửa đổi | Tự động mở rộng `finalTop` và `finalHeight` cho bảng tiếp nối bị cắt đỉnh. |
| [`backend/tests/test_table_reconstructor.py`](../../backend/tests/test_table_reconstructor.py) | Sửa đổi | Bổ sung unit test `test_detect_open_top_lines_and_rescue_table`. |

---

## 4. Kết Quả Kiểm Thử (Verification)

1. **Backend Linter & Formatter**:
   - `uv run ruff check .` $\rightarrow$ **All checks passed (0 lỗi)**.
2. **Backend Unit Tests**:
   - `uv run --extra dev pytest tests/test_table_reconstructor.py` $\rightarrow$ **13/13 passed (100%)**.
   - `uv run --extra dev pytest tests/test_knowledge.py` $\rightarrow$ **31/31 passed (100%)**.
3. **Frontend Linter & Typecheck & Build**:
   - `npm run lint` $\rightarrow$ **166 files checked, 0 errors**.
   - `npm run typecheck` $\rightarrow$ **0 errors**.
   - `npm run build` $\rightarrow$ **Build production thành công trong 12.34s**.
