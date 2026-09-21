# NHẬT KÝ LÀM VIỆC — PHIÊN #169
**Thời gian**: 2026-09-21 09:45 (UTC+7)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Cài đặt & tích hợp thư viện mã nguồn mở Firecrawl `pdf-inspector` (Rust Core v1.22.1) vào pipeline Kho Tri Thức và OCR của QNU AI Platform, thay thế cơ chế đếm ký tự thủ công (`len < 40`) bằng hệ thống phân loại cấu trúc thông minh (`text_based`, `scanned`, `mixed`), tăng tốc bóc tách văn bản số hóa lên 10-30ms.

---

## 1. Bối Cảnh Kỹ Thuật & Lý Do Thay Đổi
- Trước đây, khi cán bộ nạp tệp PDF, hệ thống kiểm tra phân nhánh OCR bằng các câu lệnh Python thủ công:
  - `ingestion_service.py`: `if len(parsed.raw_text.strip()) < 40:` thì gọi OCR rescue.
  - `ocr/service.py`: `if len(result_dict.get("raw_text", "")) > 80:` thì skip OCR.
- **Hạn chế**:
  - Không nhận diện được tệp lai (`mixed`) có trang văn bản số hóa và trang scan con dấu/chữ ký.
  - Xử lý đơn luồng trong Python chậm hơn so với native binary.
  - Chưa tận dụng được khả năng xuất Markdown có cấu trúc chuẩn GitHub Flavored Markdown (GFM) trực tiếp từ bộ đọc PDF.
- **Giải pháp**: Tích hợp thư viện Rust mã nguồn mở chính thức của Firecrawl: `pdf-inspector` (v1.22.1), kết hợp theo mô hình kiến trúc song mã với `PyMuPDF`.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Cài Đặt Gói & Adapter `PDFInspector`
1. [`backend/pyproject.toml`](../../backend/pyproject.toml):
   - Chạy lệnh `uv add pdf-inspector` thêm gói `pdf-inspector>=1.22.1`.
2. [`backend/app/modules/knowledge/parsers/pdf_inspector.py`](../../backend/app/modules/knowledge/parsers/pdf_inspector.py):
   - Xây dựng lớp DTO `PDFInspectionResult` với các thuộc tính: `pdf_type`, `confidence`, `page_count`, `pages_needing_ocr`, `has_encoding_issues`, `is_complex_layout`, `pages_with_tables`, `markdown`, `page_markdowns`, `pages_detail`, `processing_time_ms`.
   - Cung cấp các cờ tiện ích: `is_text_based`, `is_scanned`, `is_mixed`, `can_skip_ocr`.
   - Trang bị cơ chế Graceful Fallback: tự động trả về `unknown` và ghi log nếu gặp nhị phân PDF hỏng.
3. [`backend/app/modules/knowledge/parsers/__init__.py`](../../backend/app/modules/knowledge/parsers/__init__.py):
   - Xuất khẩu `PDFInspector` và `PDFInspectionResult`.

### 2.2. Tích Hợp Song Mã Vào PyMuPdfParser, Ingestion & OCR
1. [`backend/app/modules/knowledge/parsers/pdf_parser.py`](../../backend/app/modules/knowledge/parsers/pdf_parser.py):
   - Gọi `PDFInspector.inspect_bytes(file_bytes)` để đính kèm metadata phân loại thông minh (`pdf_type`, `pages_needing_ocr`, `confidence`, `inspector_engine`, `inspection_time_ms`).
   - Ưu tiên sử dụng Markdown có cấu trúc do Rust trích xuất; đồng thời bảo tồn 100% `extract_page_blocks` từ PyMuPDF cho Bounding Boxes trên Scan Studio.
2. [`backend/app/modules/knowledge/services/ingestion_service.py`](../../backend/app/modules/knowledge/services/ingestion_service.py):
   - Thay thế toàn bộ logic thủ công `len < 40` bằng kiểm tra phân loại `pdf_type in ("scanned", "image_based")` và `(pdf_type == "mixed" and pages_needing_ocr)`.
3. [`backend/app/modules/ocr/service.py`](../../backend/app/modules/ocr/service.py):
   - Trong `_extract_auto()`: Sử dụng `PDFInspector.inspect_bytes(content)` trước khi route. Nếu là `text_based`, trả về kết quả Fast-Path ngay trong 10-30ms mà không tốn chi phí gọi OCR.

### 2.3. Đồng Bộ Tài Liệu Quy Trình & Sơ Đồ Kiến Trúc
1. [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](../quy_trinh/02_nap_tri_thuc_minio.md):
   - Cập nhật Bước 3 và Mermaid diagram làm rõ vai trò Firecrawl PDF Inspector kết hợp PyMuPDF.
2. [`docs/diagrams/kho_tri_thuc_architecture.html`](../diagrams/kho_tri_thuc_architecture.html):
   - Cập nhật node `Firecrawl PDF Inspector` (Rust Core) trong Phân Vùng 2 và thẻ giải thích Card 1.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Bộ Test Chuyên Biệt Mới** ([`backend/tests/test_pdf_inspector.py`](../../backend/tests/test_pdf_inspector.py)):
   - `test_pdf_inspector_text_based`: PASS (~9ms, `can_skip_ocr = True`).
   - `test_pdf_inspector_scanned_image`: PASS (`is_scanned = True`).
   - `test_pdf_inspector_multi_page`: PASS (trích xuất `page_markdowns` và `pages_detail`).
   - `test_pdf_inspector_malformed_bytes_graceful_fallback`: PASS (xử lý an toàn byte hỏng).
   - `test_pdf_inspector_empty_bytes`: PASS (xử lý byte rỗng).
   - **Kết quả: 5/5 passed (100%) trong 0.90s**.

2. **Kiểm Thử Hồi Quy Toàn Bộ Hệ Thống**:
   - `uv run --extra dev pytest tests/test_knowledge.py tests/test_ocr.py tests/test_smart_layout.py tests/test_table_reconstructor.py -v`:
     - **63/63 passed (100%) trong 54s**.
   - `uv run ruff check .`:
     - **All checks passed! (0 lỗi linter)**.
   - `npm run lint` & `npm run typecheck`:
     - **Checked 167 files in 394ms (0 lỗi Biome), tsc --noEmit (0 lỗi TypeScript)**.
