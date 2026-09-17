# NHẬT KÝ LÀM VIỆC — Khắc Phục Chuẩn Hóa Markdown & Scan Nhận Diện Bảng Biểu (Kế Thừa QNU AI Core)
**Ngày**: 2026-09-18 | **Thời gian**: 00:30 | **Phiên**: #75

---

## 1. Bối Cảnh & Vấn Đề (User Feedback)
- Khi người dùng tải tệp tin Word tuyển sinh (`Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`, 14 trang) lên hệ thống:
  1. **Markdown sinh ra bị lỗi nặng**: Các bảng biểu từ trang 2 đến trang 13 đều bị biến thành một dòng chuỗi giữ chỗ thô sơ `"Bảng biểu dữ liệu số hóa"`, làm mất hoàn toàn 53 ngành tuyển sinh, mã ngành, tổ hợp môn xét tuyển và số lượng chỉ tiêu.
  2. **Khung scan nhận diện layout không đúng**: Layout detector đánh dấu vùng bảng nhưng gán nhãn tĩnh và không bóc tách được dữ liệu dạng bảng Markdown, dẫn đến việc chuyển trang bị lệch và không có dữ liệu đối soát.

---

## 2. Nguyên Nhân Kỹ Thuật (Root Causes)
1. **`layout_detector.py`**:
   - Chứa dòng gán cứng `"text": "Bảng biểu dữ liệu số hóa"` khi phát hiện table qua PyMuPDF hoặc OpenCV.
   - Đồng thời loại trừ tất cả text blocks nằm trong bounding box của bảng, khiến text thật bị nuốt trọn và chỉ còn lại chuỗi placeholder.
2. **`office_parser.py` (`DocxParser`)**:
   - Tách rời danh sách paragraphs và danh sách tables, dồn toàn bộ bảng xuống cuối tệp Markdown thay vì xen kẽ theo đúng mạch văn bản gốc.
   - Gán cứng `page_count = 1`, khiến toàn bộ chunks bị dồn về trang 1 (`is_clumped = True`).
3. **`service.py` (`build_studio_pages`)**:
   - Khi phát hiện `is_clumped = True`, hệ thống tự động fallback sang `_synthesize_page_markdown_from_blocks`. Hàm này lấy `text` từ layout blocks của từng trang. Vì layout blocks chỉ có dòng `"Bảng biểu dữ liệu số hóa"`, toàn bộ trang 2-13 bị ghi đè bằng chuỗi giữ chỗ này.

---

## 3. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 3.1. Kế thừa Thuật toán DOCX từ `qnu-ai-core/docx_processor.py` sang `office_parser.py`
- Duyệt tuần tự `child in doc.element.body` (bảo toàn 100% thứ tự xen kẽ của đoạn văn và bảng biểu).
- Xử lý bảng chuyên sâu:
  - Header hàng đầu hoặc ô in đậm được định dạng thành tiêu đề bảng Markdown.
  - Xử lý ô gộp ngang (colspan) tự động nhân bản giá trị.
  - Ô chứa nhiều dòng được nối bằng `<br>` hoặc `; ` để bảo đảm cấu trúc hàng bảng không bị vỡ.
  - Tách hàng nhóm La Mã (ví dụ: `I. NHÓM NGÀNH ĐÀO TẠO GIÁO VIÊN`) thành tiêu đề cấp 3 `### ...`.
  - Cân bằng số cột giữa các hàng bảng.
- Chuẩn hóa Quốc hiệu, Tiêu ngữ, Số hiệu theo Nghị định 30 (chuyển thành blockquote `> `).

### 3.2. Chuẩn hóa Layout Detector (`layout_detector.py` & `blocks.py`)
- Bổ sung hàm `_format_table_markdown(rows)`.
- Trong `_detect_hybrid_pdf_regions`: Sử dụng `tab.extract()` từ PyMuPDF để lấy dữ liệu ô của bảng và render thành Markdown Table chuẩn.
- Gán bảng Markdown này vào `table["text"]` và `content_snippet`. Xóa bỏ hoàn toàn chuỗi placeholder `"Bảng biểu dữ liệu số hóa"`.
- Làm tương tự trong `extract_page_blocks` của `blocks.py` đối với vector tables.

### 3.3. Nâng cấp Bộ Làm Sạch Markdown (`cleaner.py`)
- `_normalize_markdown_table_block`: Chuẩn hóa số cột của header và separator, loại bỏ khoảng trắng dư thừa.
- `_stitch_table_continuations`: Nối các bảng bị chia cắt qua nhiều trang (ghép bảng khi trang tiếp theo bắt đầu bằng hàng dữ liệu của bảng trước mà không lặp lại header).
- Chuẩn hóa Unicode NFC (Zero Mojibake).

### 3.4. Cập nhật Service & Studio (`service.py`)
- `_synthesize_page_markdown_from_blocks`: Giữ nguyên khối Markdown table từ blocks thay vì biến thành bullet list.
- Thêm cờ phát hiện `has_placeholder` trong `_is_stale_raw_blocks`: Tự động re-extract các tài liệu cũ dính chuỗi `"Bảng biểu dữ liệu số hóa"`.

### 3.5. Dọn dẹp Frontend Fixtures (`verification-data.ts`)
- Loại bỏ sạch 12 vị trí chứa chuỗi `"Bảng biểu dữ liệu số hóa"` trong mock studio data.

---

## 4. Kết Quả Kiểm Thử (Verification)
1. **Trích xuất thực tế tệp `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`**:
   - Độ dài: **23.118 ký tự** (so với 3.967 ký tự bị cụt trước đó).
   - Bảng biểu: Trích xuất trọn vẹn **4 bảng lớn**, đầy đủ **53 ngành tuyển sinh**, mã ngành và tổ hợp môn.
   - Chuỗi `"Bảng biểu dữ liệu số hóa"`: **0 lần xuất hiện** (hoàn toàn triệt tiêu).
2. **Backend Test Suite**:
   - `uv run ruff check .`: 0 lỗi (All checks passed).
   - `uv run --extra dev pytest tests/test_knowledge_docx_tables.py tests/test_smart_layout.py tests/test_knowledge.py -v`: **32/32 passed**.
3. **Frontend Test Suite**:
   - `npm run lint`: **0 lỗi** (91 files checked).
   - `npm run typecheck`: **0 lỗi** (`tsc --noEmit`).
   - `npm run build`: Vite build thành công (17.15s).
4. **Kiểm tra Zero Mojibake**:
   - `python scripts/check_mojibake.py`: **225/225 files sạch**, 0 lỗi encoding.
