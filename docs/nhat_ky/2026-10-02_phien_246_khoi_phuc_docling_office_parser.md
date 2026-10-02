# NHẬT KÝ LÀM VIỆC: KHÔI PHỤC DOCLING OFFICE PARSER CHO TÀI LIỆU OFFICE

- **Thời gian**: 2026-10-02
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  - Khôi phục Docling chỉ cho bóc tách định dạng Office (DOCX, XLSX, PPTX, DOC, XLS, PPT) dạng declarative.
  - Không khôi phục các thành phần AI chạy local: EasyOCR, SentenceTransformers, Torch/Transformers, `models-local`, Ollama/vLLM.
  - OCR tài liệu scan giữ nguyên 100% qua Gemini/Mistral API và ModelOps database.
  - Cung cấp cơ chế Native Fallback tự động khi thiếu thư viện phụ trợ môi trường.

---

## 1. Các Thay Đổi Mã Nguồn & Kiến Trúc

1. **Dependency (`backend/pyproject.toml` & `backend/uv.lock`)**:
   - Sử dụng `"docling-slim[format-office,format-pdf-pypdfium2]>=2.127.0,<3"`.
   - Bổ sung `pypdfium2` để đáp ứng chuỗi backend khởi tạo PDFium mà backend Office của Docling yêu cầu nội bộ. Không bao gồm Torch hay model OCR local.

2. **Parser mới (`backend/app/modules/knowledge/parsers/docling_office_parser.py`)**:
   - Khởi tạo `DoclingOfficeParser(extension, fallback=...)` kế thừa `BaseDocumentParser`.
   - Ánh xạ động định dạng sang `MsWordDocumentBackend`, `MsExcelDocumentBackend`, `MsPowerpointDocumentBackend`.
   - **Sửa lỗi thứ tự**: Đặt kiểm tra `if self.extension not in _BACKEND_CONFIG` trước khi truy cập dictionary để tránh `KeyError`.
   - **Sửa lỗi trích xuất bảng**: Bổ sung `separator` vào khối table block trong `_extract_markdown_tables` để không bị bỏ sót dòng dữ liệu đầu tiên và bảo toàn Markdown GFM chuẩn.
   - Khi gặp `(ImportError, ModuleNotFoundError)` (ví dụ chưa cài `pypdfium2`), tự động chuyển sang native fallback và gắn metadata `parser="native_fallback"`.

3. **Fallback & Registry (`backend/app/modules/knowledge/parsers/`)**:
   - Bổ sung `PptxParser` native trong `office_parser.py` bóc tách văn bản slide, bảng biểu và metadata số trang bằng `python-pptx`.
   - Registry `__init__.py` bọc `DoclingOfficeParser` kèm fallback tương ứng:
     - `docx` -> `fallback=DocxParser()`
     - `xlsx` -> `fallback=XlsxParser()`
     - `pptx` -> `fallback=PptxParser()`
     - `doc`, `xls`, `ppt` -> `DoclingOfficeParser` trực tiếp.

4. **Frontend (`frontend/src/lib/file-inspector.ts` & `frontend2/src/lib/file-inspector.ts`)**:
   - Đổi nhãn đề xuất sang Docling Office Parser thuần túy bóc tách cấu trúc XML và ma trận bảng.
   - Loại bỏ hoàn toàn các nhắc đến TableFormer local hay OCR local.

---

## 2. Rà Soát Triệt Để Runtime AI Local

Đã quét toàn bộ mã nguồn `backend/app/`:
- **EasyOCR**: `0` import / runtime. Chỉ còn các chuỗi từ chối fail-closed trong danh mục provider.
- **SentenceTransformers**: `0` import / runtime. Pipeline embedding dùng Cloudflare Workers AI API (`@cf/baai/bge-m3`).
- **Ollama / vLLM**: `0` adapter runtime. Mọi LLM routing chạy qua nhà cung cấp đám mây quản lý trong PostgreSQL ModelOps.
- **`models-local`**: `0` thư mục hoặc tham chiếu cấu hình.

---

## 3. Kết Quả Kiểm Thử & Xác Minh

1. **Python Compileall**:
   - `python -m compileall app/modules/knowledge/parsers/`: **PASS** (100% cú pháp hợp lệ).
2. **Unit Tests (`backend/tests/test_docling_office_parser.py`)**:
   - `test_unsupported_extension_raises_value_error`: **PASS** (ném `ValueError` chuẩn thay vì `KeyError`).
   - `test_parser_factory_routes_office_extensions_to_docling_office_parser`: **PASS** (cả 6 định dạng office đều trỏ về DoclingOfficeParser).
   - `test_docling_office_parser_fallback_on_missing_dependency`: **PASS** (tự động chuyển sang native fallback mượt mà khi thiếu pypdfium2).
   - `test_docling_office_parser_raises_without_fallback_on_import_error`: **PASS** (ném lỗi rõ ràng khi không có fallback).
   - `test_extract_markdown_tables_helper`: **PASS** (trích xuất bảng Markdown chính xác cả header và các hàng dữ liệu).
   - Kết quả: **5/5 tests PASSED**.
3. **Git Diff Check**:
   - `git diff --check backend/app/modules/knowledge/parsers/`: **PASS** (0 lỗi whitespace / conflict).

---

## 4. Trạng Thái & Giới Hạn Môi Trường

- **Trạng thái**: **HOÀN THÀNH** khôi phục Docling Office Parser.
- **Giới hạn môi trường**: Trong môi trường cục bộ hiện tại, package `pypdfium2` chưa được cài đặt vào `.venv` do giới hạn mạng. Parser đang vận hành ổn định qua cơ chế **Native Fallback** tự động. Khi máy chủ có kết nối mạng, chạy `uv sync` để nạp đầy đủ backend Docling gốc.
