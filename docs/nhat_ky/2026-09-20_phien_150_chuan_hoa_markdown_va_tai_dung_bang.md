# NHẬT KÝ LÀM VIỆC — PHIÊN #150
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Triển Khai Chặng 1 Chuẩn Hóa Markdown: Canonical Models, Loại Trùng Text Bảng & Tái Dựng Bảng Đa Trang

---

## 1. Bối Cảnh & Mục Tiêu

Theo bản kế hoạch [`docs/ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md`](../ke_hoach/10_ke_hoach_chuan_hoa_markdown_qdrant_va_chat_luong_rag.md), hệ thống bóc tách PDF trước đây gặp các vấn đề nghiêm trọng ảnh hưởng trực tiếp tới chất lượng RAG:
1. **Dữ liệu bảng bị nhân đôi**: Văn bản thô của ô bảng bị lấy từ `page.get_text("text")` rồi tiếp tục nối khối bảng Markdown ở dưới, khiến nội dung xuất hiện 2 lần trên cùng 1 trang.
2. **Cột rác `Cột N`**: Ô gộp tiêu đề nhóm sinh ra các cột rỗng `Cột 2, 3, 5, 11`.
3. **Vỡ hàng trong ô bảng**: Ký tự ngắt dòng `\n` trong ô không được xử lý khiến cú pháp bảng Markdown bị đứt gãy.
4. **Bảng ngắt trang bị chia cắt**: Bảng 53 ngành tuyển sinh bị xé lẻ thành 7 bảng nhỏ, hàng tiếp nối ở trang sau bị rớt thành hàng mồ côi.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Triển Khai (Chặng 1 — P0.1 & P0.2)

### 2.1. Khởi Tạo Package Canonical Normalization (`app/modules/knowledge/normalization/`)
- [`models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/models.py): Khai báo các typed models chuẩn Pydantic:
  * `BlockType` (HEADING, PARAGRAPH, TABLE, LIST, SIGNATURE,...).
  * `SourceSpan`: Lưu chính xác số trang và bounding box gốc `(x0, y0, x1, y1)`.
  * `CanonicalCell`: Tách bạch `raw_value` (bất biến) và `normalized_value` (đã làm sạch).
  * `CanonicalRow`: Định danh hàng, danh sách ô, cờ `is_continuation`.
  * `CanonicalTable`: Schema fingerprint, headers, rows, danh sách trang nguồn `source_pages`.
  * `CanonicalBlock`: Khối văn bản ngoài bảng.
  * `CanonicalDocument`: Mô hình tài liệu chuẩn hóa chứa blocks, tables, issues và metadata.

### 2.2. Thuật Toán Tái Dựng Bảng Đa Trang (`table_reconstructor.py`)
- [`table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/table_reconstructor.py):
  * `table_schema_key()`: Tạo mã băm SHA-256 xác định cấu trúc cột của bảng độc lập với khoảng trắng/dấu câu.
  * `is_repeated_header()`: Nhận diện và tự động xóa bỏ các dòng tiêu đề lặp lại ở đầu trang tiếp theo.
  * `merge_continuation()`: Giải cứu hàng mồ côi (như `Tiếng Trung | Ngôn ngữ Trung Quốc` ở trang 14 của tài liệu tuyển sinh) bằng cách gộp vào hàng cuối cùng của trang trước.
  * `clean_table_columns()`: Quét và loại bỏ triệt để các cột rác `Cột N` có tỷ lệ ô trống $> 85\%$.
  * `reconstruct_multi_page_tables()`: Nối liền mạch các bảng liên tiếp có cùng schema thành 1 bảng logic duy nhất.

### 2.3. Trình Render Markdown Chuẩn Dòng Đơn (`markdown_renderer.py`)
- [`markdown_renderer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/markdown_renderer.py):
  * Đảm bảo mỗi hàng bảng là **đúng 1 dòng Markdown duy nhất**.
  * Chuyển các ký tự xuống dòng `\n` bên trong ô thành `<br>`, escape ký tự `|` thành `\|`.
  * Căn lề thông minh (`:---:` cho STT/Mã/Điểm, `:---` cho nội dung văn bản).
  * Chèn chú thích ranh giới trang `<!-- Page X -->` tự nhiên mà không làm vỡ thân bảng.

### 2.4. Nâng Cấp `PyMuPdfParser` Chống Trùng Lặp (`pdf_parser.py`)
- [`pdf_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/pdf_parser.py):
  * Tích hợp hàm hình học `_is_table_text()`: Tính tỷ lệ giao cắt diện tích giữa text block và bbox của bảng (`intersection_ratio >= 0.50` hoặc tâm text nằm trong bảng).
  * **Loại bỏ hoàn toàn các khối chữ thuộc về bảng ra khỏi paragraph stream**.
  * Chấm dứt triệt để việc nối cả văn bản phẳng và bảng Markdown vào `raw_text`.

---

## 3. Các Tệp Đã Tạo & Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`normalization/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/__init__.py) | `NEW` | Export các model canonical. |
| [`normalization/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/models.py) | `NEW` | Định nghĩa `CanonicalCell`, `CanonicalRow`, `CanonicalTable`, `CanonicalDocument`. |
| [`normalization/table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/table_reconstructor.py) | `NEW` | Tái dựng bảng nhiều trang, schema fingerprint, xóa header lặp, cứu hàng mồ côi, xóa cột rác. |
| [`normalization/markdown_renderer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/markdown_renderer.py) | `NEW` | Render Markdown chuẩn 1 hàng/dòng, reflow ô nhiều dòng thành `<br>`. |
| [`parsers/pdf_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/pdf_parser.py) | `MODIFY` | Loại bỏ text trong bảng khỏi luồng văn bản, kết nối pipeline tái dựng bảng canonical. |
| [`parsers/blocks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/parsers/blocks.py) | `MODIFY` | Không tự sinh các cột placeholder `Cột N` rác. |
| [`tests/test_table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_table_reconstructor.py) | `NEW` | Bộ 8 unit tests kiểm tra toàn diện schema key, nối trang, cứu orphan row, render Markdown và chống trùng lặp. |

---

## 4. Kết Quả Kiểm Thử (Verification)

- **Backend**:
  * `uv run ruff check .` $\rightarrow$ **All checks passed! (0 lỗi)**.
  * `pytest tests/test_table_reconstructor.py` $\rightarrow$ **8 passed in 0.84s (100%)**.
  * `pytest tests/test_knowledge.py` $\rightarrow$ **31 passed in 56.26s (100%)**.
- **Frontend**:
  * `npm run lint` $\rightarrow$ **Checked 165 files. No fixes applied. (0 lỗi)**.
  * `npm run typecheck` $\rightarrow$ **0 lỗi**.
