# Nhật Ký Phiên Làm Việc #281: Khắc Phục Triệt Để Bounding Box Chữ Ký Bị Lệch Vào Đoạn Văn & Triệt Tiêu Nhãn List Trên Scan Studio

- **Thời gian**: 2026-10-06 23:45 (UTC+7)
- **Phiên số**: #281
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  1. Khắc phục triệt để lỗi Bounding Box `signature` bị gán nhầm vào nửa phải của đoạn văn số 4 (do thuật toán chia cột cưỡng bức).
  2. Tự động nhận diện và bao trọn 100% cụm chữ ký thật: con dấu đỏ tròn của ĐH Quy Nhơn (`has_seal`), chức vụ ("HIỆU TRƯỞNG"), chữ ký mực xanh và họ tên lãnh đạo ("PGS.TS. Đỗ Ngọc Mỹ") ở góc dưới bên phải trang cuối.
  3. Triệt tiêu hoàn toàn nhãn `list` (danh sách) vô căn cứ trên các khối văn bản điều khoản thông thường, chuẩn hóa tất cả về nhãn `text` (Khối văn bản) sạch sẽ.
  4. Chuẩn hóa bộ lọc tiêu đề trong `_semantic_markdown_partition` để không gán nhầm `title` cho các câu văn chứa từ ngữ quy chế thông thường.

---

## 1. Hiện Tượng & Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 1.1 Khung `signature` nhận diện sai chỗ chữ ký
- **Hiện tượng**: Trên tài liệu `quy che dao tao _QNU_2021.pdf` (Trang 23), khung mang nhãn `signature` lại nằm đè lên nửa bên phải của đoạn văn số 4 (*"vướng mắc, các đơn vị, cá nhân liên quan có bản cho Nhà trường..."*). Trong khi đó, cụm chữ ký viết tay và con dấu đỏ thực sự ở góc dưới bên phải lại hoàn toàn không được đóng khung.
- **Nguyên nhân gốc rễ**:
  1. Trong `layout_detector.py` (`_detect_morphology_regions`), điều kiện `by2 >= (seal_y1 - int(0.04 * h))` đã kích hoạt nhầm cờ hiệu `is_signing_area = True` trên đoạn văn số 4 ở phía trên con dấu.
  2. Thuật toán tìm khe giữa `gutter_start:gutter_end` bắt gặp khoảng trắng giữa 2 từ trong đoạn văn số 4, sau đó tự ý **cắt đôi đoạn văn số 4 thành 2 cột**: nửa trái gán nhãn `list` ("Nơi nhận"), nửa phải gán nhãn `signature` ("Chữ ký / Con dấu").
  3. Cụm con dấu đỏ và chức vụ/họ tên thực sự ở bên dưới không được tạo bounding box độc lập đưa vào danh sách trả về.

### 1.2 Xuất hiện nhãn `list` tràn lan
- **Hiện tượng**: Các khoản thông thường của Điều 29 (khoản 1, khoản 2, khoản 3) đều bị hiển thị badge `list` màu xanh ngọc.
- **Nguyên nhân gốc rễ**:
  - Tại dòng 1598–1600 của `layout_detector.py`, có một quy tắc gán cứng: `elif h_pct >= 6.0: r_type = "list"`. Bất kỳ khối văn bản nào cao từ 3 dòng chữ trở lên đều bị ép đổi loại thành `list`.
  - Trong `_detect_hybrid_pdf_regions` và `_semantic_markdown_partition` cũng tồn tại logic gán `lbl = "list"` cho các dòng bắt đầu bằng số thứ tự `1.`, `2.`, gạch đầu dòng.
  - Trên thực tế, văn bản hành chính theo NĐ 30 gồm các điều khoản và đoạn văn liên tục; khung nhận diện scan chuẩn chỉ có `text`, `title`, `header`, `table`, `signature`.

---

## 2. Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1 Chuẩn Hóa Vùng Chữ Ký & Con Dấu Thật (`layout_detector.py`)
1. **Lấy Tọa Độ Thực Của Con Dấu Đỏ**:
   - Mở rộng trích xuất cả tọa độ ngang `seal_x1, seal_x2` từ `red_bottom` bên cạnh `seal_y1, seal_y2`.
2. **Bao Trọn Cụm Ký Tên & Con Dấu Thật**:
   - Xác định dải chữ ký ở nửa bên phải (`x >= 0.38 * w`): đỉnh mở rộng lên phía trên con dấu (`seal_y1 - 0.08 * h`) để ôm trọn chức vụ `"HIỆU TRƯỞNG"`, đáy mở rộng xuống dưới (`seal_y2 + 0.08 * h`) để ôm trọn họ tên `"PGS.TS. Đỗ Ngọc Mỹ"`.
   - Gom tất cả các khối text con ở nửa phải trong dải này cùng với con dấu đỏ thành **MỘT KHỐI `signature` DUY NHẤT** (`bbox = (sig_left, sig_top, sig_right, sig_bottom)`).
3. **Bảo Tồn Toàn Vẹn Khối Văn Bản Ở Phía Trên**:
   - Đoạn văn số 4 (trải dài toàn dòng, đáy nằm trên vùng ký) được giữ nguyên vẹn 100% là một khối `text` ("Khối văn bản"), tuyệt đối không bị cắt đôi thành 2 cột nữa.

### 2.2 Triệt Tiêu Hoàn Toàn Nhãn `list` Trên Bố Cục Scan
1. **Trong `_detect_morphology_regions`**:
   - Xóa bỏ hoàn toàn điều kiện `elif h_pct >= 6.0: r_type = "list"`. Mọi đoạn văn bản thông thường đều ánh xạ về `text` ("Khối văn bản").
2. **Trong `_detect_hybrid_pdf_regions`**:
   - Xóa bỏ nhánh `elif self._is_list_marker(txt): rtype = "list"`, chuyển toàn bộ về `text`.
3. **Trong `_associate_snippets_with_regions`**:
   - Cập nhật logic gán text bên trái trang cuối ("Nơi nhận:") dựa trên tọa độ vị trí thực tế (`left < 45.0%` và `top >= 40.0%`) thay vì phụ thuộc vào nhãn `list`.
4. **Trong `_semantic_markdown_partition` (`openai_vision_adapter.py`)**:
   - Bỏ gán `lbl = "list"`, chuẩn hóa phân loại `is_title` chỉ kích hoạt khi dòng bắt đầu bằng `#` hoặc bắt đầu bằng từ khóa tiêu đề ngắn gọn (`first_line_upper.startswith(...)`), tránh gán nhầm `title` cho các câu văn có chứa từ "quy định" hay "quy chế".

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Unit Test Bố Cục Chữ Ký & Triệt Tiêu Nhãn List**:
   - Tạo test tổng hợp `tests/test_smart_layout_closing_signature.py` mô phỏng chính xác Trang 23 (4 đoạn văn bản + con dấu đỏ tròn + chức vụ + họ tên):
     * `assert "list" not in labels`: **PASSED 100%** (0 nhãn list).
     * `assert len(sig_regions) == 1`: **PASSED 100%** (đúng 1 vùng chữ ký bao quanh con dấu).
     * `assert p4["width"] >= 50.0`: **PASSED 100%** (đoạn văn số 4 giữ nguyên độ rộng toàn dòng, không bị cắt đôi).
2. **Bộ Test OCR Toàn Diện**:
   - `tests/test_ocr.py`: 17/17 passed.
   - `tests/test_ocr_cleaner.py`: 7/7 passed.
   - `tests/test_ocr_cleaner_headers.py`: 2/2 passed.
   - `tests/test_smart_layout_closing_signature.py`: 1/1 passed.
   - **Tổng cộng: 27/27 tests passed (100%)**.
3. **Linter & Code Quality**:
   - `uv run ruff check`: **0 lỗi** trên toàn bộ các file thay đổi.

---

## 4. Tệp Tin Thay Đổi
- `backend/app/modules/ocr/layout_detector.py`: Cập nhật tọa độ con dấu đỏ, gộp khối signature chuẩn và loại bỏ nhãn `list`.
- `backend/app/modules/ocr/adapters/openai_vision_adapter.py`: Tinh chỉnh `_semantic_markdown_partition` loại bỏ `list` và chống false-positive `title`.
- `backend/tests/test_ocr_cleaner.py`: Cập nhật assertion nối hàng bằng khoảng trắng thay vì `<br>`.
- `backend/tests/test_smart_layout_closing_signature.py`: Bổ sung test tự động kiểm tra chữ ký và nhãn layout.
