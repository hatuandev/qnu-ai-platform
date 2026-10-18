# Phiên 522 — Triển khai chuẩn Markdown RAG vào đường nạp DOCX

## Yêu cầu và phạm vi

Tiếp phiên 521 (đã chốt [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md)),
triển khai đường sinh bản chuẩn cho DOCX từ cấu trúc DoclingDocument, nối vào
đường nạp thật và có cách tải artifact. Giữ nguyên luồng PDF/OCR, MD cũ và mọi
thứ đang phục vụ; không thêm framework/thư viện mới; không reset DB, reindex,
xuất bản, restart, deploy hay Git. Không tuyên bố cải thiện chất lượng trả lời
chỉ từ việc sinh MD đúng schema.

## Kết quả

- `normalization/qnu_markdown.py`: models + emitter YAML/`rag:block` + parser +
  validator + renderer; bảng `records` phải có con `table_row`/`note`
  (`table_records_missing`), figure rỗng thiếu cờ là `block_body_empty`.
- `parsers/docling_structure.py`: builder từ DoclingDocument — heading/đoạn/list/
  bảng/hình/công thức/code, ô gộp giữ origin, `parent_id` cho mọi khối, page
  mapping theo projection (gap được chứa số thứ tự list "1."), title fallback từ
  item `title` rồi tên file.
- `parsers/base.py`, `parsers/docling_office_parser.py`: giữ DoclingDocument
  trong bộ nhớ (`ParsedContent.docling_document`), không persist vào document
  metadata và không log nội dung.
- `services/source_extraction.py`: `EXTRACTION_VERSION` →
  `layout-v13-qnu-docx-standard`; `SourceExtraction.qnu_document`;
  `align_office_markdown` trả thêm page ranges (tương thích ngược).
- `services/qnu_docx_artifacts.py` (mới): `build_qnu_markdown_artifact` render →
  validate → lưu content-addressed `{snapshot}.{sha}.qnu-rag-v1.md` +
  `{snapshot}.{sha}.qnu-doc-v1.json`; trạng thái `ready`/`failed`
  (`validation_failed`/`build_error`)/`unavailable` (`docling_document_unavailable`);
  fallback native không tạo artifact giả; không raise vì lỗi nội dung.
- `services/source_ingestion_service.py`: sinh artifact cho DOCX ở nhập mới lẫn
  reparse; `source_rev_id`/revision mới tạo sớm để gắn đúng; metadata vào
  `snapshot_metadata["qnu_markdown"]` + `parse_provenance["qnu_markdown"]`; nhánh
  reuse copy nguyên trạng; reparse non-docx xóa key cũ; thêm
  `get_qnu_markdown_artifact` (kiểm quyền qua `get_source`).
- `router.py`: `GET .../sources/{source_id}/revisions/{revision_id}/qnu-markdown`
  (`format=md|json`, quyền `ai.knowledge.view`); 404 `SOURCE_REVISION_NOT_FOUND`/
  `QNU_MARKDOWN_NOT_AVAILABLE`/`QNU_MARKDOWN_FILE_MISSING`, 409/404
  `QNU_MARKDOWN_NOT_READY`.
- Frontend: nút "Tải Markdown chuẩn" trong menu nguồn (chỉ bật khi có revision
  đang phục vụ) + `downloadSourceQnuMarkdown` (blob, toast lỗi/ thành công).
- `backend/tests/test_qnu_docx_markdown.py` (mới, 10 test): 4 nhóm fixture —
  cấu trúc/list lồng; bảng gộp/ô trống/số 0/mã 0 đầu/ghi chú; ký tự Markdown đặc
  biệt + marker giả + placeholder + escape; fallback không DoclingDocument, lỗi
  validate, mapping trang và wiring extraction.
- Docs: cập nhật trạng thái triển khai ở đầu và mục 11 của
  [chuẩn v1.0](../quy_trinh/13_chuan_markdown_rag_v1.md); đồng bộ nhật ký/README/
  WORK_LOG/PROJECT_CONTEXT.

## Kiểm chứng

- `ruff check` 9 file backend đã sửa → All checks passed! (sửa S112 nhỏ trong
  `_caption_text`, RUF100, I001).
- Focused: `pytest` 5 file (qnu_docx_markdown, docling_office_parser,
  source_layout_extraction, knowledge_docx_tables, ingestion_mixed_regressions)
  `-q -p no:cacheprovider` → **57 passed** (50.50s).
- Full suite (Docker đã bật lại, container healthy):
  `pytest backend/tests -q -p no:cacheprovider --basetemp=...` →
  **11 failed, 1954 passed, 17 skipped** (214.63s). 11 FAIL đúng danh sách
  baseline cũ (2 consulting, 6 publishing v2, 1 rag_data_truth, 1 trust_boundary,
  1 universal_tools); 1954 = 1944 cũ + 10 test mới, không phát sinh lỗi mới.
- Ghi chú trung thực: lần chạy full đầu tiên (không `--basetemp`) có 60 ERROR do
  `PermissionError [WinError 5]` tại `%TEMP%\pytest-of-AnhTuan` — thư mục cũ thuộc
  tiến trình elevated, không xóa được nếu thiếu quyền admin; không phải lỗi mã.
  Chạy lại với basetemp riêng → 0 error. Người dùng có thể xóa thư mục temp đó
  bằng quyền admin để các lần chạy mặc định sạch.
- Frontend: `npx biome check` 3 file → clean; `npm run build` và
  `npm run typecheck` PASS (exit 0). Phát hiện công cụ ghi LF vào file cần CRLF
  theo `biome.json` (`knowledge-api.ts`, nút mới) và mixed-ending ở `base.py`,
  đã sửa đúng quy ước (backend/docs UTF-8 LF, frontend CRLF); `git diff --check`
  exit 0.
- NOT RUN: chat/benchmark câu hỏi trên artifact chuẩn, reindex/publish, PDF/OCR
  áp chuẩn, UI đăng nhập thực. Artifact chuẩn hiện là **dẫn xuất song song**,
  chưa được consumer RAG đọc.

## Giới hạn và bước tiếp theo

- Chất lượng trả lời không được suy ra từ việc sinh MD đúng schema; cần batch
  kiểm chứng bằng câu hỏi đại diện khi được giao đọc artifact chuẩn.
- Nhánh reuse copy nguyên metadata nên frontmatter MD giữ `revision_id` gốc —
  trung thực nhưng cần lưu ý khi đọc; endpoint không đổi tham chiếu.
- Mapping trang DOCX dựa trên projection render, không phải phân trang thật.
- Chỉ khi được giao: cho pipeline chunk/RAG đọc artifact chuẩn, hoặc mở rộng
  chuẩn cho PDF/OCR; vẫn không tự reindex/publish/commit.
