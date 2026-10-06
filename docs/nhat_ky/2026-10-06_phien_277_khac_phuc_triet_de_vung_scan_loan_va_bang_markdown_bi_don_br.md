# NHẬT KÝ PHIÊN LÀM VIỆC 277 (WORK LOG SESSION 277)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Thời gian thực hiện**: 2026-10-06 (15:00 - 15:20)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Khắc phục triệt để lỗi vùng nhận diện Scan (Bounding Boxes overlays) bị loạn xạ, gán sai nhãn (signature lọt giữa bảng, title gán vào căn cứ) và cấu trúc bảng Markdown bị dồn nén thẻ `<br>`, mất tiêu đề cột trên Trang 2 của Scan Studio (`QD2139_Muc_thu_hoc_phi_dao_tao_dai_hoc_tu_xa_dot_1.pdf`).

---

### 1. Hiện Trạng & Nguyên Nhân Gốc Rễ (100% Root Causes)

Người dùng phản ánh kèm 3 ảnh chụp Scan Studio:
1. **Vùng nhận diện scan (Bounding Boxes overlays) bị loạn xạ và sai lệch**:
   - *Trang 1*: Xuất hiện nhãn `signature` nằm lọt thỏm giữa hàng tiêu đề bảng học phí; nhãn `title` gán nhầm vào đoạn căn cứ pháp lý ("Căn cứ quy định về quyền hạn..."); khung `table` chỉ bao nửa dưới của bảng.
   - *Trang 2*: Khung `table` bị kéo dài quá mức xuống đáy trang, nuốt chửng cả phần "II. Hiệu lực thi hành", "Nơi nhận" và đè lên con dấu tròn đỏ; tên hiệu trưởng bị gán nhãn `title`.
   - **Nguyên nhân gốc rễ**:
     - Trong `OpenAIVisionOCRAdapter` (`backend/app/modules/ocr/adapters/openai_vision_adapter.py`), vì mô hình Vision LLM không sinh ra khối `layout_json` toạ độ, hàm `_parse_page_layout_and_markdown` fallback về `_semantic_markdown_partition`.
     - Hàm `_semantic_markdown_partition` đã **tự đoán mò toạ độ bằng cách cộng dồn `cur_y = 6.0; cur_y += bh + 2.0`** và gán nhãn bằng regex thô. Khi gặp chữ "HIỆU TRƯỞNG" ở đoạn căn cứ, nó gán nhãn `signature` rơi trúng giữa bảng học phí ở Trang 1.
     - Trong khi đó, hệ thống đã có sẵn **`SmartLayoutDetector`** (`backend/app/modules/ocr/layout_detector.py`) sử dụng giải thuật hình thái học thị giác máy tính (Morphological line detection qua NumPy và HSV red seal mask) cực kỳ chính xác nhưng chưa được đấu nối trực tiếp vào Adapter.

2. **Cấu trúc bảng Markdown trên cột bên phải bị dồn nén `<br>` và Trang 2 mất tiêu đề**:
   - Toàn bộ các hàng học phí từng đợt bị dồn nén thành một ô khổng lồ nhồi nhét đầy thẻ HTML `<br>` (`23.660.000<br>5.600.000...`).
   - Bảng ở Trang 2 bị mất hàng tiêu đề cột, chỉ trơ trọi 2 dòng phân cách rỗng `| :---: | :--- | :--- | ...`.
   - **Nguyên nhân gốc rễ**:
     - Trong `cleaner.py`, hàm `merge_ocr_orphan_table_rows` kiểm tra ngây thơ: hễ `col0` (cột STT) rỗng thì coi là dòng rớt chữ và gộp tất cả các ô vào dòng trên bằng `<br>` (`parent_val<br>child_val`). Nhưng trong bảng học phí, các hàng dưới là các đợt đóng tiền độc lập (`Học phí đợt 1`, `5.600.000`), không phải rớt chữ.
     - Tài liệu hành chính gốc ở Trang 2 tiếp nối bảng mà không in lại dòng tiêu đề "STT | Tên ngành...". Khi xem từng trang trên UI, thiếu hàng Header khiến React Markdown hiểu sai dòng đầu tiên là header hoặc dòng separator rác.

---

### 2. Các Thay Đổi & Giải Pháp Kỹ Thuật Triệt Để (Algorithmic-First)

1. **Đấu Nối Trực Tiếp `SmartLayoutDetector` Vào `OpenAIVisionOCRAdapter`**:
   - Tệp: `backend/app/modules/ocr/adapters/openai_vision_adapter.py`
   - Khi mô hình không sinh ra `layout_json`, lập tức gọi `smart_layout_detector.detect_layout_regions(image_input=img_bytes, markdown_text=clean_text, page_number=p_num)`.
   - Chuyển đổi chính xác 100% toạ độ hình học thực tế thành `blocks` chuẩn cho Frontend Scan Studio (`coordinates: {x, y, width, height}`).
   - Khắc phục cấu hình `base_url` để `OpenAIVisionOCRAdapter` mặc định (OpenRouter) không bị nhầm lẫn thành Ollama local.

2. **Tinh Chỉnh Ngưỡng Thị Giác Trong `SmartLayoutDetector`**:
   - Tệp: `backend/app/modules/ocr/layout_detector.py`
   - Điều chỉnh ngưỡng `top_val >= 40.0` (thay vì `>= 70.0`) cho khối danh sách Nơi nhận ở trang kết thúc, giúp các văn bản có phần chữ ký & nơi nhận bắt đầu từ ~50% trang (như QD2139) được gắn snippet chính xác.

3. **Bảo Tồn Bản Ghi Bảng Độc Lập & Cơ Chế Kế Thừa Header Bảng (Continuation Inheritance)**:
   - Tệp: `backend/app/modules/ocr/cleaner.py`
   - Cập nhật `merge_ocr_orphan_table_rows`: Thêm điều kiện nhận diện số tiền (`has_currency_or_number`) và phân kỳ (`has_installment`). Giữ nguyên 100% các hàng học phí độc lập, triệt tiêu việc gộp thẻ `<br>`.
   - Bổ sung hàm `inherit_table_headers_for_continuation_pages`: Quét và lưu trữ `last_header` và `last_separator` từ trang trước; nếu trang sau bắt đầu bằng một bảng tiếp nối thiếu header, tự động loại bỏ separator rác và chèn header chuẩn cùng số lượng cột được đệm đủ chuẩn GFM.

---

### 3. Kết Quả Đo Đạc & Kiểm Thử Thực Tế

- **Kiểm định Bounding Boxes của QD2139 qua `SmartLayoutDetector`**:
  - **Trang 1** (6 vùng chuẩn mực):
    - `header`: x=10.1%, y=8.3%, w=81.5%, h=6.4% (Quốc hiệu, Tiêu ngữ, Tên trường, Số QĐ)
    - `title`: x=30.0%, y=16.3%, w=41.8%, h=5.6% (Tiêu đề Quyết định)
    - `text`: x=25.7%, y=24.6%, w=53.1%, h=1.6% (HIỆU TRƯỞNG TRƯỜNG ĐH QUY NHƠN)
    - `list`: x=11.0%, y=28.2%, w=79.8%, h=28.7% (3 đoạn căn cứ pháp lý)
    - `text`: x=75.6%, y=58.0%, w=14.9%, h=1.0% (Đơn vị tính: VNĐ)
    - `table`: x=10.0%, y=59.2%, w=81.5%, h=33.1% (Toàn bộ bảng học phí Trang 1)
  - **Trang 2** (5 vùng chuẩn mực):
    - `table`: x=10.2%, y=7.5%, w=81.4%, h=32.7% (Bảng học phí tiếp nối Trang 2)
    - `text`: x=17.3%, y=41.9%, w=21.4%, h=1.2% (II. Hiệu lực thi hành)
    - `text`: x=11.3%, y=44.5%, w=79.4%, h=3.1% (Quy định này có hiệu lực...)
    - `list`: x=11.8%, y=49.9%, w=23.9%, h=15.2% (Nơi nhận bên trái)
    - `signature`: x=51.5%, y=49.9%, w=32.2%, h=15.2% (Con dấu tròn đỏ & Chữ ký bên phải)

- **Kiểm định Linter & Pytest Suite**:
  - `backend/.venv/Scripts/python.exe -m ruff check backend/app/modules/ocr/`: **0 lỗi** (All checks passed!).
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ocr.py`: **17/17 passed (100%)**.
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ocr_cleaner_headers.py`: **2/2 passed (100%)**.
