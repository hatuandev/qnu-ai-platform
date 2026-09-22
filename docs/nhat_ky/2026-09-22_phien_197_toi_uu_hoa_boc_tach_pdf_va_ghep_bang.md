# NHẬT KÝ LÀM VIỆC — PHIÊN #197
# Ngày: 2026-09-22 | Thời gian: 20:15 (UTC+7)
# Người thực hiện: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
# Mục tiêu: Tối Ưu Hóa Toàn Diện Bộ Bóc Tách PDF, Phân Mảnh Bảng Đa Trang & Triệt Tiêu Lặp Text Chân Trang

---

## 1. Bối Cảnh & Vấn Đề Cần Giải Quyết

Trong quá trình kiểm thử thực tế chức năng bóc tách kho tri thức bằng tệp PDF chính thức *Thông tin tuyển sinh đại học năm 2026 (cập nhật)* (`Thong tin tuyen sinh dai hoc 2026_Lan2-1.pdf`, 14 trang) của Trường Đại học Quy Nhơn, hệ thống bóc tách phát sinh 5 sai lệch cấu trúc:
1. **Đảo lộn thứ tự Trang 2**: Khối bảng (5 ngành đầu tiên) bị đẩy lên đỉnh trang, trong khi các đoạn văn mô tả 5 phương thức tuyển sinh và Mục 4 bị đẩy xuống dưới bảng.
2. **Bảng đa trang dồn cục (Trang 3..8)**: Thuật toán `render_canonical_document_markdown` dồn toàn bộ 53 ngành vào Trang 2 (`min(source_pages)`), khiến Trang 3..8 bị trống trong `page_markdowns`. Khi xem theo trang trong Scan Studio, hệ thống fallback về các khối rời rạc gây rách hàng mồ côi (`| | | | | |`).
3. **Lặp text ngành 51 & 52 ở chân Trang 12**: Một khối text lớn cắt ngang biên giới đáy bảng chứa cả 2 ngành cuối bảng lẫn cụm `Nơi nhận: ... HIỆU TRƯỞNG`, khiến ngành 51 và 52 xuất hiện 2 lần.
4. **Tiêu đề Phụ lục 1 bị đảo lộn (Trang 13)**: Tiêu đề `PHỤ LỤC 1` bị đẩy xuống dưới bảng môn thi.
5. **Khuyết môn thi hoặc gộp sai ngành độc lập (Trang 14)**: Ngành *Đông phương học* (mã `7310608`) có cột 0 bị trống trong PDF gốc nên bị gộp sai vào ngành *Ngôn ngữ Anh*.
6. **Lỗi Serialization `page_markdowns`**: `page_number in page_markdowns` thất bại vì `page_number` là số nguyên (`int`), còn PostgreSQL JSONB lưu khóa dạng chuỗi (`str`).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Backend Ingestion & Layout Normalization
- [`markdown_renderer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/markdown_renderer.py):
  - Phân bổ hàng của bảng đa trang theo `pnum in sorted(tbl.source_pages)`.
  - Sinh bảng Markdown độc lập kèm header cho từng trang, bảo đảm thứ tự và ngữ cảnh bảng toàn vẹn.
- [`table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/table_reconstructor.py):
  - `is_orphan_continuation_row`: Thêm chốt chặn bảo vệ mã ngành 7 chữ số (`_PROGRAM_CODE_RE`) không bị coi là hàng mồ côi.
  - `reconstruct_multi_page_tables`: Kế thừa tên nhóm môn (`active_group`) vào ô đầu trang trống của trang tiếp nối.
- [`blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py):
  - Thêm line-level clipping cho các khối văn bản giao cắt một phần với bảng.
  - Sắp xếp toàn bộ `blocks` theo tọa độ đọc tự nhiên `(y, x)` giải quyết lỗi đảo lộn thứ tự Trang 2 và 13.
- [`pdf_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/pdf_parser.py):
  - Bổ sung line-level clipping cho `canonical_blocks`.
  - Phân loại `BlockType.HEADING` cho các dòng tiêu đề phụ lục.
- [`ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py):
  - `build_studio_pages`: Tra cứu `page_markdowns.get(page_number) or page_markdowns.get(str(page_number))`.
  - Đưa toàn bộ các trang có trong `page_markdowns` vào danh sách trang.
  - `_synthesize_page_markdown_from_blocks`: Sắp xếp các khối theo tọa độ `y` trước khi render fallback.

### 2.2. Unit Testing Mới
- [`test_table_stitching_and_page_partition.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_table_stitching_and_page_partition.py):
  - 5 ca kiểm thử bao phủ toàn bộ các cơ chế mới: bảo vệ mã ngành, kế thừa header, phân bổ trang, xử lý khóa chuỗi studio pages, và sắp xếp theo tọa độ.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Unit Test Suite Mới**:
   - `uv run --extra dev pytest tests/test_table_stitching_and_page_partition.py`: **5/5 passed** (100% trong 0.91s).
2. **Kiểm Thử Hồi Quy Domain & Doc Types**:
   - `uv run --extra dev pytest tests/test_domain_records_and_quality_gate.py tests/test_document_types.py`: **22/22 passed** (100% trong 2.65s).
3. **Kiểm Tra Mã Nguồn Backend (Ruff)**:
   - `uv run ruff check .`: **All checks passed! (0 lỗi)**.
4. **Kiểm Tra Giao Diện Frontend**:
   - `npm run lint`: **170 files checked, 0 lỗi**.
   - `npm run typecheck`: **0 lỗi**.
   - `npm run build`: **Vite build thành công (11.27s)**.
5. **Kiểm Thử Thực Tế Trực Tiếp Tệp PDF Tuyển Sinh 14 Trang**:
   - Trang 2: Mô tả 5 phương thức tuyển sinh nằm TRÊN bảng.
   - Trang 2..8: Bảng đa trang phân bổ đều với đầy đủ tiêu đề cột cho từng trang.
   - Trang 12: Biến mất 100% text lặp ngành 51 & 52 trước khối "Nơi nhận:".
   - Trang 13: Tiêu đề `PHỤ LỤC 1` nằm TRÊN bảng.
   - Trang 14: Ngành *Đông phương học* kế thừa đầy đủ môn xét tuyển *Tiếng Anh*.
   - Studio Pages: Toàn bộ 14 trang hiển thị mượt mà.
