# Phiên 525 — PDF → QNU RAG Markdown, đợt 1–3

## Phạm vi

Người dùng giao triển khai cả ba đợt: PDF văn bản và lớp bằng chứng, PDF scan/mixed,
bảng phức tạp/bố cục. Dùng PyMuPDF, PDF Inspector và OCR/ModelOps hiện có, không
thêm framework. Artifact chuẩn là dẫn xuất song song; không chuyển RAG sang đọc.
Không DB write thật, migration, OCR/inference thật, reparse/reindex/publication,
restart/deploy, commit/push; giữ nguyên thay đổi có sẵn của người dùng.

## Phương pháp và file

- `knowledge/parsers/pdf_evidence.py` (mới): native evidence trước legacy cleanup,
  uncapped layout, matrix/cell boxes, header, images và vector geometry; XY-cut.
- `knowledge/parsers/pdf_tables.py` (mới): HTML th/rowspan/colspan và GFM block
  adapters; native merged-cell bằng geometry, raw null còn nguyên trong sidecar;
  trường không rõ không đoán, không dùng bbox bảng làm bbox ô. Header suy luận,
  ô chưa rõ và spanning rows có cờ cần duyệt.
- `knowledge/parsers/pdf_structure.py` (mới): native/OCR region selection, chống
  trùng khi nội dung khớp, conflict giữ alternative; physical page/label/locator,
  heading typography có cờ, hình/công thức/footnotes, explicit context_refs.
  Bảng nối trang chỉ đề xuất liên kết cần duyệt, chưa gộp bằng cùng tên cột.
- `knowledge/services/source_extraction.py`: version `layout-v14-qnu-pdf-standard`,
  tạo model PDF từ evidence, giữ local→physical OCR map; DOCX preview không bị
  dựng nhầm thành artifact PDF. Capture/builder lỗi không phá serving extraction.
- `knowledge/services/qnu_docx_artifacts.py`: giữ đường import tương thích, dùng
  chung renderer cho PDF; raw JSON qua StorageDriver, MD/JSON/raw hashes; reuse
  kiểm raw sidecar trước khi ghi revision mới, artifact failed vẫn giữ raw.
- `knowledge/services/source_ingestion_service.py`: hook PDF ở import/reparse/reuse,
  tận dụng download endpoint và invalidation khi hiệu đính đã có.
- `ocr/schemas.py`, `ocr/service.py`, `ocr/adapters/paddleocr_adapter.py`: giữ raw
  provider/pre-clean pages bằng internal field exclude/repr=False, không log payload.
- `knowledge/services/header_rescue.py`: giữ raw crop OCR nội bộ; PDF builder nhận
  dòng số/ngày đề xuất cùng vùng crop và cờ cần duyệt, không tự xác nhận đúng.
- `tests/test_qnu_pdf_markdown.py` (mới): PDF tạo tại chỗ + OCR/DB/storage mocks,
  không gửi corpus ra dịch vụ; handler download kiểm luồng tải bằng mock.

Các đường file trên tương đối `backend/app/modules/`, ngoại trừ tests.
Raw OCR được copy trước cleaner và lưu ở snapshot sidecar khi dựng artifact;
không đưa raw payload vào API thông thường, Git hoặc nhật ký.

## Kiểm chứng

Cwd `backend`, dùng `.venv/Scripts/python.exe`:

- Ruff scoped trên 10 file app và `tests/test_qnu_pdf_markdown.py`: PASS.
- Nhóm 9 file: `test_qnu_pdf_markdown`, `test_qnu_docx_markdown`,
  `test_source_layout_extraction`, `test_ingestion_mixed_regressions`,
  `test_paddleocr_adapter`, `test_ocr_modelops_safety`,
  `test_knowledge_source_ingestion`, `test_native_table_review`,
  `test_source_page_provenance` với `-q -p no:cacheprovider`, basetemp
  `storage/pdf525-regression-verified`, loại hai ID hạ tầng dưới bằng `-k`:
  **150 passed, 2 deselected, 23 subtests passed**, exit 0, 56.73s.
- Trong lượt chạy trước có FAIL thực do thiếu hạ tầng, không đổi test để che:
  - `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page`:
    Redis capacity lease không kết nối được, `PROVIDER_CAPACITY_UNAVAILABLE`.
  - `tests/test_knowledge_source_ingestion.py::test_http_routes_source_management`:
    PostgreSQL connection refused từ middleware.
  Hai ID này vẫn chưa đạt trong môi trường hiện tại, không gọi toàn nhóm PASS.
- Test mới ban đầu dùng fixture có `page_count=0` bị validator chặn đúng; đã sửa
  fixture sang hai trang thật tương ứng (không nới validator). Bổ sung test crop,
  vector geometry và capture failure sau nhóm 150. Lượt cuối:
  `pytest tests/test_qnu_pdf_markdown.py tests/test_source_layout_extraction.py tests/test_source_context_stage2.py -q -p no:cacheprovider --basetemp=storage/pdf525-final-guards`
  → **68 passed**, exit 0, 40.18s (bao gồm **24 test PDF mới**; có trùng nhóm 150,
  không cộng hai nhóm thành tổng số ca độc lập). Ruff sau thay đổi cuối vẫn sạch.
- `docker ps` exit 1: Docker Desktop Linux engine pipe chưa tồn tại. Full suite,
  DB/API runtime có stack, S3 thật, UI đăng nhập, OCR/model thật và nghiệm thu 5 PDF
  thật (đợt 4) **NOT RUN**. Không suy 11 lỗi nền lịch sử là kết quả hiện tại.
- Có warning Qdrant version check do client được import trong test cũ; không có
  request gửi tài liệu/model thật trong các test mới.

## Giới hạn

Schema PASS/checksum chỉ chứng minh cấu trúc/toàn vẹn, không chứng minh OCR đúng.
Không sửa typo OCR, không gộp unknown-year, không tự sửa nguồn đang phục vụ.
Nested/multiple HTML tables cùng block, layout không đủ tọa độ, heading/footnote
mơ hồ, cross-page continuation chưa được xác nhận phải review. Header/caption
inference giữ cờ, không là căn cứ duyệt. Native legacy Markdown vẫn giữ nguyên
các heuristic cũ; QNU sidecar đọc raw evidence độc lập. Không có tuyên bố cải thiện
chất lượng chatbot hoặc hỗ trợ hoàn hảo mọi PDF.

Bước tiếp theo: bật stack, kiểm hai ID hạ tầng, đối chiếu 5 PDF đại diện trong
phạm vi được cho phép rồi mới bàn việc consumer RAG đọc MD chuẩn. Không reset DB
hoặc nạp lại toàn bộ tài liệu để thử tính năng này.
