# NHẬT KÝ LÀM VIỆC — PHIÊN #202 (2026-09-23)

## 1. Tiêu Đề & Mục Tiêu Phiên Làm Việc
**Triệt tiêu 100% danh sách từ khóa hardcode (header_keywords) — Chuyển dịch toàn diện sang Thuật toán Nhận diện Header Bảng Dựa Trên Hình Thái & Cấu Trúc Đa Miền (Zero-Keyword Morphological Table Header Detection)**.

## 2. Bối Cảnh & Vấn Đề Kỹ Thuật Cốt Lõi
- Người dùng đặt câu hỏi sâu sắc về đoạn code tại [`backend/app/modules/knowledge/parsers/pdf_parser.py:L175-197`](backend/app/modules/knowledge/parsers/pdf_parser.py):
  > *"đoạn này phải hardcode sao, còn thuật toán hãy giải pháp nào tốt hơn để tối ưu hóa chức năng bóc tách không? sao tôi thấy mỗi lần đưa 1 file mới là có vấn đề, bạn có tiêu chuẩn bóc tách dữ liệu nào có thể áp dụng không?"*
- Phân tích nguyên nhân:
  1. Trước đây, cả `pdf_parser.py` và `table_reconstructor.py` đều dựa vào danh sách từ khóa tiếng Việt cố định (`header_keywords`: `stt, tt, nội dung, công việc, nhiệm vụ, chủ trì, thời gian, điểm, ngành...`).
  2. Bất kỳ tài liệu nào thuộc lĩnh vực khác (Tài chính - Kế toán: `Khoản mục, Dự toán, Quyết toán`, Thời khóa biểu: `Môn học, Tín chỉ, Phòng học`, hay tài liệu Tiếng Anh / Doanh nghiệp: `No., Task Description, Lead Unit, Status`) đều khiến thuật toán bị mù, không nhận diện được header và xé vụn bảng hoặc nhầm header thành data row.
  3. Lỗi false positive: Tên đơn vị như `Khoa CNTT` chứa substring `tt` từng bị nhận nhầm thành header `TT` nếu không có word boundary, làm vỡ quá trình nối tiếp đa trang.

## 3. Giải Pháp Kỹ Thuật Đạt Chuẩn Enterprise (Zero-Keyword Morphological Standard)
Hệ thống chuyển đổi triệt để sang 5 tiêu chuẩn phân tích hình thái học (Morphological Rules):
1. **Tiêu chuẩn Khóa Chuỗi (Sequence Key Check)**: Hàng header không bao giờ bắt đầu bằng khóa định danh dòng dữ liệu (số nguyên `^\d+$`, mã nhiệm vụ phân cấp `^\d+(\.\d+)+$`, chữ số La Mã `^[IVXLCDM]+$`, hoặc mã ngành 7 chữ số `^\d{7}[A-Za-z]*$`).
2. **Tiêu chuẩn Cột 0 Bắt Buộc (Primary Column 0 Integrity)**: Hàng tiêu đề bảng hợp thức bắt buộc phải định danh Cột 0. Nếu Cột 0 bị rỗng (`""`), đây là hàng dữ liệu mồ côi (orphan wrapped data cell) trôi từ trang trước sang chứ không phải header mới.
3. **Tiêu chuẩn Ngắn Gọn & Phi Mô Tả (Non-Descriptive & Length Boundary)**: Ô header là nhãn danh từ ngắn gọn (chiều dài $\le 45$ ký tự), không chứa gạch đầu dòng hành chính (`- `, `+ `, `• `, `* `) và không chứa dấu ngắt câu nhiều mệnh đề (`[\.;]\s+[A-ZÀ-Ỹ]`).
4. **Tiêu chuẩn Mật Độ Dữ Liệu Thấp (Low Data Density)**: Tiêu đề là danh từ/nhãn, không chứa giá trị định lượng. Mật độ ô chứa ngày tháng/tỷ lệ phần trăm (`\d+[/\-]\d+`, `\d+%`, `tháng \d`, `năm \d`) phải $\le 20\%$.
5. **Tiêu chuẩn Chữ Cái Bắt Buộc (Alphabetic Label Requirement)**: 100% ô header có nghĩa bắt buộc phải chứa ký tự chữ cái (`[a-zA-Zà-ỹÀ-Ỹ]`).

## 4. Các Tệp Mã Nguồn Đã Chỉnh Sửa & Bổ Sung
1. [`backend/app/modules/knowledge/parsers/pdf_parser.py`](backend/app/modules/knowledge/parsers/pdf_parser.py):
   - Xóa bỏ hoàn toàn tuple 21 từ khóa `header_keywords`.
   - Viết lại hàm `_is_hdr(r_cells, is_first_header)` tuân thủ 5 tiêu chuẩn hình thái học, hỗ trợ tham số `is_first_header` cho phép sub-header 1 ô ở cấp 2.
2. [`backend/app/modules/knowledge/normalization/table_reconstructor.py`](backend/app/modules/knowledge/normalization/table_reconstructor.py):
   - Xóa bỏ regex tìm từ khóa `stt|tt|mã|tên...` trong `_has_semantic_headers`.
   - Áp dụng 5 quy tắc hình thái học zero-keyword đồng bộ.
3. [`backend/tests/test_table_stitching_and_page_partition.py`](backend/tests/test_table_stitching_and_page_partition.py):
   - Bổ sung test suite `test_morphological_header_detection_multilingual_and_financial` kiểm thử khả năng tự động nhận diện bảng Tiếng Anh doanh nghiệp, Bảng Tài chính - Kế toán, và Thời khóa biểu mà không cần bất kỳ từ khóa nào.

## 5. Kết Quả Kiểm Thử Toàn Diện (Verification)
1. **Kiểm tra 3 tệp PDF nghiệp vụ thực tế**:
   - `File 1: Kế hoạch Bán dẫn, AI & ANM (2214/KH-ĐHQN)` (12 trang): Ghép nối hoàn hảo bảng Phụ lục 8 trang (Trang 5-12) thành 1 Master Table duy nhất gồm 339 dòng. 0 số trang rò rỉ.
   - `File 2: Kế hoạch Học liệu E-learning (2781/KH-ĐHQN)` (3 trang): Bóc tách 8 dòng bảng 4 cột chuẩn chỉnh, 0 số trang rò rỉ.
   - `File 3: Kế hoạch BĐCLGD (4053/KH-ĐHQN)` (7 trang): Bóc tách 26 dòng bảng, 0 số trang rò rỉ.
3. **Kiểm tra 2 tệp PDF theo yêu cầu trực tiếp của người dùng**:
   - `Tệp 1: Kế hoạch triển khai nhiệm vụ trọng tâm 2025-2026 (22 trang)`:
     - Bóc tách và ghép nối toàn bộ 20 trang Phụ lục (Trang 3 đến 22) thành **1 Master Table duy nhất gồm 87 dòng**.
     - Hoàn thiện nối câu bị ngắt đôi qua trang cho các nhiệm vụ trọng yếu: Row 8.1 (Trang 18 $\to$ 19: "...mức lương cơ sở và chế độ tiền thưởng đối với cán bộ, công chức, viên chức và lực lượng vũ trang"), Row 9.3 (Trang 19 $\to$ 20: "...quản lý tài sản công; xây dựng định mức kinh tế kỹ thuật"), Row 11.3 (Trang 21 $\to$ 22: "...Đại hội Hội Sinh viên Trường ĐHQN lần thứ XVI, nhiệm kỳ 2025 - 2028").
     - 0 số trang rò rỉ, 100% cột và định dạng bảng đạt chuẩn.
   - `Tệp 2: Thông tin tuyển sinh đại học 2026 (14 trang)`:
     - Bóc tách đầy đủ và chính xác **4 bảng dữ liệu**:
       - Bảng 1 (Trang 2-8): Đầy đủ 53/53 ngành & tổ hợp môn xét tuyển.
       - Bảng 2 (Trang 9): Bảng 4 cột quy đổi điểm chứng chỉ IELTS và VSTEP.
       - Bảng 3 (Trang 11-12): Đầy đủ 52/52 ngành với chỉ tiêu, số trúng tuyển và điểm chuẩn 2 năm 2024 & 2025.
       - Bảng 4 (Trang 13-14): Đầy đủ 38/38 ngành xét tuyển thẳng và ưu tiên xét tuyển theo môn thi HSG quốc gia.
     - 0 số trang rò rỉ, 100% dữ liệu nguyên vẹn.
4. **Backend**:
   - `uv run ruff check .`: 0 lỗi (All checks passed).
   - `uv run --extra dev pytest`: **413/413 passed (100%)**.
5. **Frontend**:
   - `npm run lint`: 170 files checked, 0 lỗi.
   - `npm run typecheck`: 0 lỗi.
   - `npm run build`: Thành công trong 14.42s.
