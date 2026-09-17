# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Cài Đặt Docling Thật & Kiểm Chứng Bóc Tách Đề Án Tuyển Sinh 2026 (Việc 1/5)

### 1. Bối cảnh
Phiên #36 để lại adapters Docling/EasyOCR ở dạng lazy (chưa cài package nên chưa chạy thật). Máy dev: RAM 16GB, không GPU, 5 container infra healthy — đủ chạy Docling CPU. Mục tiêu: `uv add docling` + kiểm chứng bóc thật file Đề án 2026.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Cài đặt** (`backend/pyproject.toml`, `uv.lock`): `uv add docling` → docling 2.128.0 + 77 packages (torch 2.14 CPU, transformers, opencv, pypdfium2...). Lợi ích kèm theo: `rapidocr 3.9.2` về cùng bundle Docling.
2. **Kiểm chứng thật** bằng file `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx` (67KB) từ `qnu-ai-core` qua `DoclingOCRAdapter.extract()`:
   - Kết quả: **48.050 ký tự markdown, 307 dòng, phát hiện bảng biểu, confidence 0.97**, tiếng Việt đầy đủ dấu, bảng ngành/mã/chỉ tiêu/tổ hợp render đúng.
   - Lưu ý: thiếu LibreOffice nên phần tử DrawingML trong DOCX bị bỏ qua (log cảnh báo, không crash) — chấp nhận được cho văn bản tuyển sinh.
3. **Sửa tests phụ thuộc môi trường** (`backend/tests/test_ocr.py`): các test availability/unavailable-engine chuyển sang đối chiếu `find_spec` thực tế + nhánh mô phỏng khi cả hai engine đã cài; sửa ruff SIM117 (gộp `with`).

### 3. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -q`: **80/80 passed** (155s — Docling thật đã chạy trên PDF scan trắng trong 2 tests, tải model layout lần đầu, trả rỗng trung thực).
- Từ nay auto-routing `auto` trên scan thật sẽ nâng lên Docling thay vì dừng ở PyMuPDF rỗng.
