# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Studio-View & Page-Image Thật — BBoxes Từ Engine, Xóa 6MB Ảnh Thừa (Việc 2/5)

### 1. Bối cảnh
Việc 2 trong kế hoạch 30% còn lại: thay ảnh JPG commit cứng và bboxes viết tay bằng dữ liệu thật từ backend, theo đúng mẫu `studio-view` của qnu-ai-core.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
**Backend:**
1. `knowledge/parsers/blocks.py` (mới): helper dùng chung đổi tọa độ PDF points sang % (0–100), trích text blocks + table bboxes thật từ PyMuPDF.
2. `parsers/base.py` + `pdf_parser.py`: `ParsedContent` thêm trường `blocks`, parser điền geometry thật theo từng trang.
3. OCR adapters: `pymupdf_adapter` gắn blocks thật mỗi trang; `docling_adapter` gom layout boxes từ provenance (page_no + bbox → %, phân loại table/header/text); `easyocr` giữ trung thực không boxes.
4. `ocr/schemas.py`: `OCRPageResult` thêm `blocks`; ingest lưu `page_blocks` vào `doc_metadata`.
5. Endpoints mới: `GET /documents/{id}/studio-view` (markdown + boxes + regions dẫn xuất + image_url theo trang) và `GET /documents/{id}/pages/{n}/image` (render PNG dpi=150 từ file gốc MinIO/local, cache tại `previews/{id}/`, docx trả 404 rõ ràng).
6. Confidence boxes dùng default theo loại đã documents hóa (engine không expose per-block confidence) — hình học 100% thật, không bịa nội dung.

**Frontend:**
7. `api-client.getDocumentVerification`: ưu tiên `studio-view` (boxes + ảnh thật), fallback mapping chunks, giữ fixture demo.
8. Xóa `frontend/public/ocr-cache/qd2699` (29 ảnh, ~6MB, không chỗ nào tham chiếu) khỏi git; giữ 14 ảnh `doc_ts_2026` làm fixture Sample Mode hợp lệ theo AGENTS 8.9.

### 3. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi (sửa S112 blocks.py, I001 router).
- `uv run --extra dev pytest -q`: **88/88 passed** (+5 tests: tọa độ %, parser sinh blocks thật, builder studio gộp chunks+boxes, studio-view 404, page-image docx 404).
- FE: biome lint 0, typecheck 0, build ✓ (6.09s); Playwright Suite 09: **4/4 passed**.
