# Nhật Ký Làm Việc — Phiên #196: Khắc Phục Triệt Để 6 Vấn Đề Cấu Trúc Trong Bộ Bóc Tách Tài Liệu (PDF, OCR, Table Reconstructor & Cleaner)

- **Thời gian**: 2026-09-22 14:25 (UTC+7)
- **Phiên số**: #196
- **Kỹ sư**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý triệt để tại gốc 6 vấn đề nghiêm trọng trong bộ mã nguồn bóc tách tài liệu tuyển sinh ĐH Quy Nhơn 2026 từ file PDF 14 trang sang Markdown đạt chuẩn GFM và sẵn sàng nạp Vector DB.

---

## 1. Bối Cảnh & Vấn Đề
Khi kiểm thử tính năng bóc tách PDF tuyển sinh ĐH Quy Nhơn 2026 14 trang thành file Markdown, hệ thống gặp 6 vấn đề cấu trúc:
1. Đảo lộn trật tự đọc (Table hoisted above headings): Bảng ngành đặt trước các phương thức tuyển sinh.
2. Hàng mồ côi ngắt trang (Orphan rows): Các ngành STT 5, 23, 30, 39, 48 bị ngắt trang biến thành hàng mồ côi mất mã và tên ngành.
3. Bảng IELTS/VSTEP bị xé nhỏ: Hai bảng đặt ngang bị cắt thành hai bảng 2 cột thiếu thông tin.
4. Header đa tầng rớt vào dòng dữ liệu: Header cấp 2 của bảng điểm chuẩn 2024-2025 bị gộp nhầm vào hàng 32.
5. Rò rỉ rác OCR đáy trang 12: Dữ liệu ngành 51-52 bị rò rỉ dưới dạng văn bản thô ngoài bảng.
6. Thiếu hàng phân cách GFM Table `|---|---|` và mã ngành ngắt dòng (`7340301\nAC`).

---

## 2. Các Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. `pdf_parser.py` ([`backend/app/modules/knowledge/parsers/pdf_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/pdf_parser.py))
- **Hợp nhất bảng song song (`_fuse_side_by_side_tables`)**: Tự động phát hiện các bảng nằm ngang nhau có độ phủ trục $Y \ge 70\%$, ghép thành 1 bảng 4 cột duy nhất kèm phân biệt tên cột trùng lặp (`Điểm quy đổi IELTS` và `Điểm quy đổi VSTEP`).
- **Mở rộng Margin Buffer & Triệt Tiêu Rác OCR**: Mở rộng bbox đệm quanh bảng thêm 6pt ngang và 10pt dọc (`_is_table_text`), kết hợp `is_heading` guard để bảo vệ các dòng tiêu đề/mục văn bản không bị lọc nhầm.

### 2.2. `table_reconstructor.py` ([`backend/app/modules/knowledge/normalization/table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/table_reconstructor.py))
- **Nhận diện & Khử Sub-header lặp lại (`is_sub_header_row`)**: Nhận diện hàng header cấp 2 (Chỉ tiêu, Điểm trúng tuyển) lặp lại ở đầu trang tiếp theo (Page 12) và loại bỏ, bảo vệ hàng dữ liệu số 32 không bị gộp bậy.
- **Bảo vệ hàng có mã ngành 7 ký tự (`_PROGRAM_CODE_RE = r"^\d{7}[A-Za-z]*$"`)**: Ngăn chặn `is_orphan_continuation_row` nhận nhầm các hàng dữ liệu độc lập (như Đông phương học trong Phụ lục 1).
- **Chuẩn hóa ô chứa mã ngành ngắt dòng (`_normalize_program_code_cells`)**: Tự động hợp nhất các mã ngành bị bẻ dòng (`7340301\nAC` $\to$ `7340301AC`).
- **Điền tiến giá trị danh mục phân cấp (`_forward_fill_hierarchical_columns`)**: Tự động điền tên môn ở cột 1 cho các hàng rowspan trong Phụ lục 1 (đủ 38/38 ngành).

### 2.3. `cleaner.py` ([`backend/app/modules/knowledge/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py))
- **Sửa lỗi nuốt delimiter hàng phân cách bảng trong `_stitch_table_continuations`**: Bổ sung điều kiện `has_page_boundary`, chỉ thực hiện khâu nối khi thực sự có ranh giới trang (`<!-- Page N -->` hoặc `---`), bảo toàn 100% dòng phân cách GFM table `|---|---|` của mọi bảng.

### 2.4. `markdown_renderer.py` ([`backend/app/modules/knowledge/normalization/markdown_renderer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/markdown_renderer.py))
- **Sắp xếp dòng văn bản và bảng theo trật tự đọc tự nhiên (`top_y`)**: Bảng và text block trên mỗi trang được neo chuẩn xác theo thứ tự xuất hiện trên trang PDF.
- **Căn lề thông minh cho bảng GFM**: Tự động sinh `:---:` cho cột chỉ số/mã/năm/điểm và `:---` cho cột văn bản.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Kiểm tra tự động với tệp bóc tách thực tế (`scripts/validate_admission_markdown.py`)**:
   - `python scripts/validate_admission_markdown.py "Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach (1).md"`: **100% Passed (0 lỗi)**!
   - `python scripts/validate_admission_markdown.py "Thong tin tuyen sinh dai hoc 2026_Lan2-1_boc_tach.md"`: **100% Passed (0 lỗi)**!
   - Đạt trọn vẹn cả 9 tiêu chí: UTF-8 sạch, trật tự đọc 100% tuyến tính, 53/53 ngành tuyển sinh, bảng 4 cột VSTEP/IELTS, 52/52 ngành điểm chuẩn, 38/38 ngành Phụ lục 1, zero orphan rows, zero OCR leakage.

2. **Kiểm toán Zero Mojibake (`scripts/check_mojibake.py`)**:
   - Quét 414 tệp trong toàn bộ dự án: **0 lỗi Mojibake / ký tự rác**.

3. **Backend Suite (Pytest & Ruff)**:
   - `uv run ruff check .`: **All checks passed! (0 lỗi)**
   - `uv run --extra dev pytest tests/test_table_reconstructor.py tests/test_knowledge.py -v`: **51/51 passed (100%)**

4. **Frontend Suite**:
   - `npm run lint`: **170 files checked, 0 errors**
   - `npm run typecheck`: **tsc --noEmit, 0 errors**
