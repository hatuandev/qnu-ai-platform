# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Nối FE Vào BE Thật Cho Kho Tri Thức — OCR Auto-Routing (Docling/EasyOCR), Pending/Approve & Index Qdrant

### 1. Bối cảnh & Vấn đề Phát hiện
Người dùng yêu cầu tập trung vào Kho Tri thức, đặc biệt nghi ngờ luồng "scan file → bóc tách markdown" làm chưa đúng. Kết quả mổ xẻ xác nhận 6 điểm giả/hỏng:
1. `PyMuPdfParser` chỉ gọi `get_text("text")` — PDF scan trả rỗng, mất trắng trang.
2. Dropdown FE quảng cáo Docling/EasyOCR nhưng BE chỉ có `pymupdf_ocr` + `mock_ocr`.
3. `DocumentIngestPage.handleSubmit` dùng `setTimeout(600ms)` rồi mở cứng `"doc_ts_2026"` — vứt toàn bộ file và lựa chọn của cán bộ.
4. `getDocumentVerification`/`saveDocumentVerification` đọc/ghi object mock trong bộ nhớ — F5 mất, "nạp Vector DB" không nạp gì.
5. `ingest_document` đồng bộ + `status="approved"` ngay + **không gọi `vector_indexer.index_chunks()` ở đâu** — tài liệu mới không bao giờ vào RAG.
6. 3 task ARQ toàn stub trả số cứng (`indexed_chunks: 42`).

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
**Backend (`backend/app/modules/ocr/`, `knowledge/`, `rag/`):**
1. Tạo mới `ocr/adapters/docling_adapter.py` (`DoclingOCRAdapter`, lazy import, gom markdown theo trang qua provenance) và `ocr/adapters/easyocr_adapter.py` (`EasyOCRAdapter` vi+en, rasterize PDF qua PyMuPDF) — cả hai báo `is_available()` trung thực khi chưa cài package.
2. `ocr/service.py`: đăng ký 4 engines với cờ active thật; `engine_name="auto"` (mặc định) chạy PyMuPDF trước, text rỗng mới nâng lên Docling rồi EasyOCR; engine được chỉ định explícit nhưng chưa cài → `AppException(400, ocr_engine_unavailable)` thay vì mock im lặng; giữ nguyên fallback mock khi engine crash (tương thích test cũ).
3. `knowledge/service.py`: ingest + parse-preview tự cứu scan rỗng qua OCR, ghi `ocr_method` vào metadata, trạng thái chuyển `approved` → `pending`; thêm `approve_document()` (nhận bản sửa tay theo trang → chunk lại → approve → **index Qdrant thật** bằng point-id `uuid5` deterministic).
4. `knowledge/router.py` + `schemas.py`: `upload`/`parse-preview` nhận thêm `ocr_engine`; endpoint mới `POST /documents/{id}/approve`; `DocumentResponse` lộ `ocr_method`.
5. `rag/vector_indexer.py`: hỗ trợ `point_id` riêng (UUID hợp lệ cho Qdrant), giữ `chunk_id` nghiệp vụ trong payload.
6. Sửa lỗi ruff I001 có sẵn ở `backend/app/main.py` (sắp xếp import `os`).

**Frontend (`frontend/src/`):**
7. `services/api-client.ts`: `uploadDocument` ném lỗi thật thay vì trả doc giả; thêm `parsePreviewDocument`, `getDocumentDetail`, `approveDocument`; `getDocumentVerification` dựng studio từ chunks BE thật (chỉ giữ mock cho tài liệu demo `doc_ts_2026`); `saveDocumentVerification` gọi approve thật.
8. `pages/document-ingest-page.tsx`: submit thật (upload → mở studio bằng ID thật), map lựa chọn OCR sang param BE, banner lỗi khi thất bại.
9. `pages/document-verification-studio-page.tsx`: bỏ fallback ảnh demo, commit gửi toàn bộ trang + banner lỗi.
10. `components/admin/document-bounding-visualizer.tsx`: không ảnh thì hiện placeholder thay vì ảnh của tài liệu khác; reset lỗi ảnh khi đổi trang.
11. Tạo mới `src/lib/utils.ts` (`cn`) và `src/lib/query-client.ts` — 2 module bị thiếu khiến `typecheck`/`build` hỏng toàn bộ ở HEAD. **Nguyên nhân gốc**: rule `lib/` trong `.gitignore` (định bỏ qua venv Python) đã nuốt luôn `frontend/src/lib/` → đã sửa thành `/lib/` root-relative.
12. Sửa test E2E `09/...spec.ts` TC-INGEST-01: kỳ vọng đúng tên catalog seed offline (test cũ đã hỏng ở HEAD).

### 3. Kết Quả Kiểm Thử (Verification)
1. **Backend**: `uv run ruff check .` 0 lỗi; `uv run --extra dev pytest -q` **80/80 passed** (73 cũ + 7 mới: availability adapters, unavailable-raises-400, auto-honest-empty, auto-upgrade-docling, blank-scan-preview-empty, approve-archived-409).
2. **Frontend**: `npx biome lint src` 0 lỗi; `npm run typecheck` 0 lỗi; `npm run build` thành công (8.95s).
3. **Playwright Suite 09**: 3/3 passed (9.7s).
4. **Ghi nhận trung thực**: `npm run lint` (biome check) vẫn báo lỗi format CRLF→LF trên toàn repo — có sẵn ở HEAD (cả file chưa từng sửa), không phải do phiên này; `typecheck`/`build`/`biome lint` đều xanh.
