# NHẬT KÝ LÀM VIỆC — PHIÊN #194 (2026-09-22)
# Giải Pháp Bóc Tách Hoàn Chỉnh Toàn Diện: Chuẩn Hóa Bảng Đa Trang, Ghép Dòng Ngắt Đôi & Triệt Tiêu Số Trang Footer

---

## 1. Mục Tiêu & Bối Cảnh Phiên Làm Việc

- **Bối cảnh**: Người dùng thử nghiệm bóc tách tệp văn bản kế hoạch 22 trang (`KE HOACH TRIEN KHAI NHIỆM VỤ 2025-2026_update 16_9_2025.pdf`), đặt câu hỏi kiến trúc về sự phối hợp giữa `pdf-inspector` và `PyMuPDF`, đồng thời yêu cầu xây dựng một **giải pháp bóc tách hoàn chỉnh cho mọi trường hợp văn bản** bảo đảm tôn chỉ: **"1 dòng là 1 nội dung được phân theo cell và col"** và đạt chuẩn dữ liệu sản xuất (Production-Ready) nạp vào Vector DB (Qdrant).
- **Vấn đề phát hiện khi phân tích sâu**:
  1. *Lệch cột khi ghép dòng ngắt đôi (Column Misalignment)*: Hàng 4.10 (trang 11-12), 7.2 (trang 17-18), 8.1 (trang 18-19) bị rớt nửa nội dung sang trang sau. Trang sau có các cột spacer rỗng (`None`) khiến PyMuPDF phát hiện thành 9 hoặc 11 cột thay vì 7 cột. Khi ghép bảng trước khi chuẩn hóa cột, nội dung bị dồn sai cột (nhảy sang Cột 3 và Cột 6) và nuốt mất đơn vị chủ trì.
  2. *Gộp nhầm hàng dữ liệu thành subheader*: Hàm `_merge_second_header_row` hiểu nhầm hàng tiếp nối đầu trang 18 là hàng tiêu đề phụ cấp 2 do 3 ô đầu tiên bị trống (`None` spacer), dẫn đến nuốt luôn cả đoạn văn bản luật dài 200 ký tự vào tiêu đề cột Markdown.
  3. *Số La Mã bị ngắt dòng*: Trong văn bản gốc, tiêu đề mục La Mã `VIII` bị ngắt dòng thành `VII` trên dòng 1 và `I` trên dòng 2, tạo ra hai hàng bảng tách biệt `| VII | ... |` và `| I | | |...`.
  4. *Số trang rác ở chân trang*: Các số trang lẻ loi (`2`, `4`, `5`, ..., `22`) in ở đáy trang bị lọt vào luồng văn bản paragraph trước dấu phân trang `---`.

---

## 2. Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Căn Chỉnh Cột Tự Động & Hỗ Trợ `semantic_indices` Trong `_compact_task_row`
- Tệp tin: [`backend/app/modules/knowledge/normalization/table_reconstructor.py`](../../backend/app/modules/knowledge/normalization/table_reconstructor.py)
- Cập nhật hàm `_compact_task_row` tiếp nhận danh sách `semantic_indices`:
  - Khi hàng đầu trang tiếp nối là một hàng mồ côi (orphan continuation row) không có mã nhiệm vụ và không có số La Mã, hệ thống dùng `semantic_indices` để chiếu trực tiếp các ô dữ liệu về đúng vị trí danh nghĩa của schema 7 cột.
  - Cột 3 của trang 12 (`chương trình IUC-QNU giai đoạn 1...`) được ánh xạ chính xác về Cột 1 (`Nội dung nhiệm vụ`).
  - Khi ghép với hàng trước qua `merge_continuation`, hai hàng có cùng kích thước 7 cột, Cột 1 ghép vào Cột 1, Cột 2 (`Phòng KHCN&HTQT`) và Cột 3 (`PSU và các đơn vị liên quan`) được bảo toàn 100%.

### 2.2. Chống Nhầm Lẫn Hàng Dữ Liệu Dài Thành Subheader
- Tệp tin: [`backend/app/modules/knowledge/normalization/table_reconstructor.py`](../../backend/app/modules/knowledge/normalization/table_reconstructor.py)
- Thêm điều kiện phòng vệ trong `_merge_second_header_row`:
  ```python
  if any(len(v) > 50 or v.startswith("-") for v in first_values if v):
      return headers, rows
  ```
  Ngăn chặn tuyệt đối việc nuốt các đoạn văn bản nhiệm vụ/kết quả dài vào hàng tiêu đề bảng.

### 2.3. Tự Động Gộp Số La Mã Bị Tách Ngắt Dòng (`_merge_split_roman_rows`)
- Tệp tin: [`backend/app/modules/knowledge/normalization/table_reconstructor.py`](../../backend/app/modules/knowledge/normalization/table_reconstructor.py)
- Xây dựng thuật toán nhận diện: Nếu hàng $i$ có số La Mã (`VII`) và hàng $i+1$ có số La Mã tiếp nối (`I`) với tất cả các ô còn lại để trống:
  - Gộp thành chuỗi La Mã hợp lệ: `f"{curr}{nxt}"` $\rightarrow$ `VIII`.
  - Cập nhật ô đầu của hàng $i$ thành `VIII` và loại bỏ hoàn toàn hàng rỗng $i+1$.

### 2.4. Tiền Chuẩn Hóa Schema Trước Khi Ghép Nối Bảng Đa Trang
- Tệp tin: [`backend/app/modules/knowledge/normalization/table_reconstructor.py`](../../backend/app/modules/knowledge/normalization/table_reconstructor.py)
- Trong `reconstruct_multi_page_tables`: Áp dụng `clean_table_columns` trên toàn bộ danh sách `raw_tables` đầu vào trước khi tiến hành kiểm tra `schema_matches` và `merge_continuation`.
- Nhờ đó, tất cả các trang con (dù ban đầu bị PyMuPDF nhận nhầm 9 hay 11 cột) đều được chuẩn hóa về 7 cột danh nghĩa đồng nhất, loại bỏ hoàn toàn hiện tượng lệch cột khi ghép nối.

### 2.5. Triệt Tiêu Số Trang Đơn Độc Ở Chân Trang (Pagination Sanitization)
- Tệp tin:
  - [`backend/app/modules/knowledge/parsers/blocks.py`](../../backend/app/modules/knowledge/parsers/blocks.py): Phân loại khối có `top_percent >= 88.0` và khớp `^\d{1,3}$` hoặc `Trang \d+` thành loại `footer` ("Số trang").
  - [`backend/app/modules/knowledge/parsers/pdf_parser.py`](../../backend/app/modules/knowledge/parsers/pdf_parser.py): Lọc bỏ các khối ở tọa độ `y0 > height * 0.88` khớp mẫu số trang, không đưa vào danh sách văn bản canonical.
  - [`backend/app/modules/knowledge/services/ingestion_service.py`](../../backend/app/modules/knowledge/services/ingestion_service.py): Bỏ qua khối `footer` trong hàm tổng hợp Markdown từng trang.

---

## 3. Kết Quả Kiểm Thử Thực Tế

### 3.1. Thẩm Định Trực Tiếp Trên Tệp Kế Hoạch 22 Trang
- **Hàng 4.10 (Trang 11-12)**:
  ```markdown
  | 4.10 | Triển khai hiệu quả, đúng tiến độ<br>các đề tài, dự án phi chính phủ<br>đang thực hiện, đặc biệt là chương trình IUC-QNU giai đoạn<br>1, dự án ECO-WIND và các dự án<br>được phê duyệt trong năm 2025. | Phòng<br>KHCN&HTQT | PSU và các đơn<br>vị liên quan |  |  | Báo cáo tiến độ, kết quả thực<br>hiện các dự án |
  ```
  $\rightarrow$ Chuẩn xác 7 cột, Cột 2 là `Phòng KHCN&HTQT`, Cột 3 là `PSU và các đơn vị liên quan`, không bị mất hay lệch cột.
- **Hàng 7.2 (Trang 17-18)**:
  $\rightarrow$ Nội dung Luật Nhà giáo trọn vẹn ở Cột 1; Cột 6 chứa đầy đủ 3 sản phẩm kết quả, không còn hiện tượng lặp lại văn bản luật ở cột sản phẩm.
- **Mục La Mã VIII (Trang 18)**:
  ```markdown
  | VIII | Công tác thi đua, khen thưởng |  |  |  |  |  |
  ```
  $\rightarrow$ Gộp thành công thành `VIII`, triệt tiêu hàng rác `| I | | |...`.
- **Hàng 8.1 (Trang 18-19)**:
  $\rightarrow$ Ghép nối liền mạch qua trang 18-19, Cột 2 là `Phòng TC-NS`, Cột 6 là `Quy định về công tác thi đua...`.
- **Khử số trang chân trang**:
  $\rightarrow$ `Stray number lines count: 0` (100% số trang đơn độc bị triệt tiêu).
- **Quy tắc 1 dòng = 1 bản ghi**:
  $\rightarrow$ 100% các hàng trong bảng đều nằm trên đúng một dòng vật lý duy nhất, nội bộ ô dùng `<br>` chuẩn Markdown GFM.

### 3.2. Kiểm Thử Hệ Thống (Quality Gates)
- **Unit Tests**: 8/8 tests trong `test_table_stitching_and_page_partition.py` passed (100%).
- **Knowledge Test Suite**: 55/55 passed trong 44.92s.
- **Ruff Check**: `All checks passed!` (0 lỗi).
- **Frontend Biome**: `Checked 170 files in 200ms. No fixes applied.` (0 lỗi).
- **Frontend Typecheck**: `tsc --noEmit` (0 lỗi).
- **Frontend Build**: `built in 9.00s` thành công.
