# Phiên #360 — Layout native, OCR theo trang và DOCX preview

## Mục tiêu và phạm vi

Triển khai phương án đã được người dùng đồng ý: giữ Docling DOCX, PyMuPDF/PDF Inspector cho PDF chữ và PaddleOCR-VL cho scan, cung cấp khung thật cho Studio hiện có. Không sửa Kho tài liệu, qnu-sso, provider/khóa hoặc RAG/DAG; không reset DB, không restart backend/worker, không bóc tách lại/xuất bản nguồn người dùng.

## Thay đổi

- `backend/app/modules/knowledge/services/source_extraction.py`: luồng chung cho import/reparse; layout contract left/top/width/height phần trăm, ID riêng từng trang, không confidence giả. PDF native giữ blocks; PDF hỗn hợp chỉ gửi các trang cần OCR rồi ánh xạ số trang về bản gốc. Thiếu/trùng số trang OCR, lỗi provider không được che bằng native text phần còn lại. Layout analysis/engine explicit bỏ native shortcut.
- `layout_text.py`: tái ghép glyph đa font bằng baseline, tọa độ x và khoảng cách tương đối median độ rộng; không từ điển. Dùng cho nội dung khung và đối chiếu DOCX khi font fallback tách chữ có dấu.
- `source_ingestion_service.py`: cả import và reparse dùng helper mới; lưu provenance engine thật/file_type/preview path. Artifact `layout-v3` tránh reuse manifest cũ mất khung. Giữ Markdown/hash, quy trình review/index/publish riêng. DOCX dùng Docling + Gotenberg có sẵn, sequence alignment token với coverage >=90%, lỗi mapping/converter báo rõ.
- `source_pages.py`: manifest giữ engine từng trang cùng dimensions/blocks.
- `backend/app/modules/ocr/schemas.py` và `service.py`: dimensions sống qua adapter → DTO → manifest. Regression DTO trước sửa đã fail đúng do dimensions bị bỏ.
- `source_purge.py`: dọn preview hash-content-addressed cùng snapshot, giữ object được nguồn khác tham chiếu. Reuse preview sao chép vào namespace nguồn nhận, không phụ thuộc object của nguồn khác.
- `tests/test_source_layout_extraction.py`: native/no OCR, hybrid/blank pages, explicit layout, missing/error OCR, DTO dimensions, Studio contract, Office alignment/mismatch/converter error, embedded scan-only pages, invalid coords, glyph reconstruction và preview hash.
- Cập nhật tests ingestion theo dependency boundary mới và tests purge cho preview/shared preview. Đồng bộ Quy trình 02, memory/snapshot/work log/mục lục nhật ký.

## Kiểm chứng

- **53 focused BE tests đạt**: source layout, ingestion, purge, page provenance, Paddle adapter, Studio revision safety và Docling Office.
- **Ruff toàn backend đạt**, có warning quyền đọc một số thư mục storage test cũ; không lỗi lint.
- **3 FE Studio mapper tests đạt**, không sửa FE source nên không chạy build/lint FE.
- File PDF thật người dùng cung cấp: native, 14 trang, 74 khối, Markdown 24689 ký tự; không gọi OCR hay thay đổi revision đang lưu.
- DOCX thử nghiệm thật qua Docling/Gotenberg: bản 1 trang/3 khung và 2 trang/2+2 khung đúng phân trang. DOCX tiếng Việt có bảng ban đầu tái hiện lỗi mapping vì renderer tách font; sau geometric reconstruction đạt 2 trang/4+2 khung, 1 bảng, giữ tiếng Việt và giá trị 150.
- PaddleOCR thật qua Tailscale (ngoài sandbox), fixture PDF hỗn hợp 2 trang: trang 1 native/1 khung/595x842; trang 2 PaddleOCR-VL/2 khung/1190x1684. Không tạo source/collection Knowledge từ fixture; OCR service ghi audit call như bình thường.
- Full suite cuối: **871 passed / 14 failed / 2 skipped**. 13 lỗi nền trùng danh sách phiên #357 (dispatch/facts, legacy publishing routes, reconciliation, auth); thêm một lỗi môi trường tạm thời `test_import_facts_from_excel_service` do openpyxl ghi file Temp Windows (`OSError 22 Invalid argument`). Chưa coi toàn bộ suite là đạt. Các lượt full trước đó có 13 lỗi nền; không sửa lan ngoài phạm vi.
- Chạy lại riêng test Excel vừa lỗi: **1 passed (3.95s)**, không sửa code Excel. Bộ source-layout cuối: **18 passed**; tối ưu không đưa dữ liệu ảnh vào rawdict chỉ lấy glyph cũng đã được kiểm tra.
- Chưa browser E2E hoặc chạy worker trên nguồn cũ. Kết quả Studio DTO + mapper được kiểm chứng độc lập, không coi là browser E2E.

## Lưu ý bàn giao

Không migration/reset. Backend và worker cần nhận code mới; sau đó Bóc tách lại nguồn cũ để tạo revision có layout. Không tự động sửa manifest/canonical text của revision đã xuất bản. DOCX cần Gotenberg và font phù hợp; mapping không chắc chắn sẽ fail thay vì gán số trang giả. Route scan là heuristic theo chữ/coverage ảnh/encoding, cần thêm corpus thực tế để tối ưu; không khẳng định nhận diện mọi tài liệu tuyệt đối.
