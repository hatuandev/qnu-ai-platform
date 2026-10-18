# Phiên 535 — Khép hai finding header DOCX và cell state GFM

Ngày: 2026-10-18. User giao sửa hai lỗi của [review534](./2026-10-18_phien_534_review_lai_chuan_docx_pdf.md). Chỉ xử lý mã và kiểm chứng; không coi đây là phê duyệt các tài liệu cũ hoặc cam kết toàn hệ thống không còn lỗi.

## Thay đổi và nguyên nhân

### Header có bằng chứng nguồn

- `docling_office_parser.py` đọc cờ `w:tblHeader` từ DOCX gốc bằng python-docx. Đối chiếu toàn bộ lưới ô đã mở rộng merge với lưới Docling, chỉ nhận khi source và đích khớp duy nhất. So khớp chỉ chuẩn hóa NFC/whitespace để liên kết, không ghi đè nội dung raw. Hai bảng trùng lưới hoặc không khớp giữ trạng thái chưa rõ.
- `ParsedContent.docx_header_evidence` là dữ liệu nội bộ; `source_extraction` chuyển nó tới builder. Cờ `column_header` mặc định của Docling vẫn nguyên trong raw document, không sửa thư viện trong `.venv`.
- `docling_structure.py` dùng số hàng header có căn cứ từ Word, không dùng proposal để loại data rows. Header không chắc → records giữ mọi hàng, header_path rỗng và `table_header_unresolved`. JSON giữ proof + proposed_header_rows + các cell engine gốc. Header số/năm/nhiều tầng hợp lệ và bảng chỉ có header có positive tests.
- Fixture cũ muốn kiểm header thật được bổ sung `w:tblHeader` rõ trong DOCX nguồn và truyền evidence qua helper. Không đổi assertion giá trị/trang chỉ để che lỗi; các fixture headerless riêng vẫn yêu cầu giữ đủ dòng.

### Trạng thái ô nhất quán giữa GFM và records

- Chuyển bộ phân loại marker bảo thủ đang có từ builder DOCX sang helper chung `qnu_markdown.cell_state`; không thêm từ điển tên cột hay từ khóa nghiệp vụ.
- `qnu_projection.py` tạo `tables.row_fields` cho mọi data row, gồm raw/state/normalized. Records giữ trạng thái đã khai báo; GFM phân biệt present/blank/ambiguous theo cùng quy tắc mặc định.
- Unresolved count và issues bao phủ cả GFM. Fact luôn có field_state và row-unit provenance; bỏ mặc định thiếu state thành present. GFM “–”/“-”/“/” chưa rõ nghĩa không còn thành fact và bị guard duyệt `QNU_UNRESOLVED_CELLS` chặn. 0 vẫn present, ô trống vẫn blank; trạng thái not_applicable đã khai báo với chú giải nguồn không bị classifier GFM ghi đè.
- Không tạo bbox/field origin giả cho GFM khi không có tọa độ ô; giữ source block/page và chỉ số dòng/cột.
- `EXTRACTION_VERSION` tăng từ v15 lên `layout-v16-qnu-evidence` để lần parse mới không reuse kết quả theo logic cũ. Tên giữ trong giới hạn cột normalizer_version 32 ký tự. Đây là fingerprint mã, không thay runtime config/model/provider, không tự reparse/index revision đang có.

## Kiểm chứng thực chạy

Cwd Python/Ruff: `backend`, dùng `.venv` hiện có, không cài dependency.

| Gate | Kết quả |
|---|---|
| TDD trước sửa | `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_header_and_cell_states.py --basetemp=storage/fix535-red` → **11 failed, 1 passed**, exit 1; đúng header role và GFM states/fact provenance |
| Regression mới sau sửa | 15 ca cuối trong `test_qnu_header_and_cell_states.py`; gồm headerless text/số, header nhiều tầng/năm, explicit false, header-only, duplicate-table abstention, marker/0/blank, guard duyệt bằng đối tượng giả trong RAM và độ dài phiên bản khớp schema lưu trữ |
| Focused cuối | `.venv/Scripts/python.exe -m pytest -q tests/test_qnu_header_and_cell_states.py tests/test_qnu_standard_regressions.py tests/test_qnu_docx_markdown.py tests/test_qnu_pdf_markdown.py tests/test_qnu_serving.py tests/test_qnu_standard_integration.py tests/test_pdf_review_regressions.py tests/test_studio_revision_safety.py tests/test_document_revisions_lifecycle.py tests/test_docling_office_parser.py tests/test_knowledge_source_ingestion.py tests/test_source_context_review.py::test_real_db_context_revision_keeps_serving_pointer_and_rejects_stale_edit tests/test_source_pause.py::test_live_pause_excludes_source_changes_cache_key_and_preserves_artifacts --basetemp=storage/fix535-focused-final --junitxml=storage/fix535-focused-final.xml` → **201 passed, 23 subtests passed**, exit 0, 13.47s |
| Ruff | 9 file mã/test thuộc diff, `ruff check` → **PASS**, exit 0 |
| Tương thích tệp cũ | Script `review-standard-532-stored.py` chạy lại từ root bằng Python backend, READ ONLY DB + chỉ đọc storage → **6/6 pair valid**, exit 0; năm PDF vẫn review_required. Ba dòng PDF raw rebuild trong RAM giữ đúng một row, không ghi artifact |
| Full đầu | **FAIL 15 failed, 2112 passed, 17 skipped, 23 subtests passed**, exit 1, 208.24s. Ngoài13baseline có2regression do tên fingerprint mới dài35ký tự vượt cột normalizer_version String(32); đã sửa thành tên23ký tự và thêm test contract, hai integration bị ảnh hưởng đã PASS trong focused cuối |
| Full cuối sau sửa regression | `.venv/Scripts/python.exe -m pytest -q --basetemp=storage/fix535-full-final --junitxml=storage/fix535-full-final.xml` → **FAIL: 13 failed, 2115 passed, 17 skipped, 23 subtests passed**, exit 1, 202.33s |

Ruff chạy trên `parsers/base.py`, `parsers/docling_office_parser.py`, `parsers/docling_structure.py`, `normalization/qnu_markdown.py`, `normalization/qnu_projection.py`, `services/source_extraction.py` dưới `app/modules/knowledge/`, và ba test `test_qnu_header_and_cell_states.py`, `test_qnu_standard_regressions.py`, `test_qnu_docx_markdown.py`.

Log local bị ignore: `backend/storage/fix535-red.log`, `fix535-focused-final.log`, `fix535-focused-final.xml`, `fix535-stored.log`, `fix535-full.log`, `fix535-full.xml`, `fix535-full-final.log`, `fix535-full-final.xml`.

Hai regression phát hiện ở full đầu (không gọi chúng là baseline): `tests/test_source_context_review.py::test_real_db_context_revision_keeps_serving_pointer_and_rejects_stale_edit` và `tests/test_source_pause.py::test_live_pause_excludes_source_changes_cache_key_and_preserves_artifacts`. Integration dùng fixture trong transaction/savepoint và rollback, không đổi schema hay ghi giữ dữ liệu nguồn của người dùng.

Đối chiếu tự động exact IDs trong XML cuối với baseline phiên529: **13/13 khớp**, `new_failures=[]`, `missing_baseline=[]`, exit 0. Hai regression độ dài ở full đầu đã hết trong full cuối. Danh sách13ID còn lỗi được giữ trong [nhật ký533](./2026-10-18_phien_533_sua_bon_loi_chuan_docx_pdf.md); backend tổng thể vẫn FAIL, không gọi là PASS toàn hệ thống.

Tự review diff và 15 regression mới: không còn finding đang mở trong hai hành vi được giao. UTF-8 không BOM/LF, liên kết mới và diff whitespace đạt. Kết luận này có phạm vi, không thay duyệt nội dung nguồn.

## Giới hạn và bàn giao

Chưa visual QA tất cả nguồn, chưa live OCR/Word render mới/retrieval/chat. Word preview trong test được mock; parse DOCX, đọc Word XML, builder/projection và guard nghiệp vụ là thật. Fixture giả không chứng minh mọi layout hoặc provider thật đều đạt.

Header DOCX chỉ trình bày đẹp nhưng không có annotation/bằng chứng nguồn có thể cần đối soát thêm; parser bảo toàn hàng. Header của bảng trùng nội dung được giữ chưa rõ khi không xác minh được association. Không suy tên cột bằng từ điển.

Không commit/push/stage/reset/dọn tracked, không thao tác nghiệp vụ ghi lên dữ liệu người dùng hay artifact nguồn/reparse/approve/index/publish/restart/deploy/config/model changes. Sáu tệp nguồn vẫn giữ revision hiện có, năm PDF cũ chưa được duyệt. Monitor Gemini vẫn paused.
