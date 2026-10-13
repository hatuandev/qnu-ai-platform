# Phiên #397 — Giữ kết quả công thức khi tạo PDF xem trước DOCX

## Mục tiêu và quyết định

Khắc phục Gotenberg/LibreOffice tính lại sai SUM(ABOVE) trên bảng có ô gộp. Giữ nguyên tệp gốc và dữ liệu Docling; chỉ chuyển một bản sao đã materialize kết quả công thức đã lưu sang PDF. Đã thông báo phương án trước khi triển khai, dùng skill Clean Code/Knowledge Ingestion và PDF để kiểm tra ảnh kết quả.

## Tệp thay đổi

- `backend/app/modules/knowledge/services/docx_preview_fields.py`: helper thuần biến đổi bytes ZIP/OOXML, field-stack cho complex field, unwrap fldSimple cho công thức bảng có instruction bắt đầu bằng dấu bằng. Giữ text/result run formatting, gridSpan, các archive part khác và ZIP metadata. Không sửa DOCX trên đĩa. Không hardcode SUM, tên file hoặc giá trị số.
- `backend/app/modules/knowledge/services/ingestion_service.py`: trước POST Gotenberg, DOCX đi qua helper trong asyncio.to_thread; không áp dụng cho định dạng khác.
- `backend/app/modules/knowledge/services/source_extraction.py`: tăng EXTRACTION_VERSION thành layout-v9-cached-docx-formulas để artifact key mới không tái sử dụng nguồn theo policy cũ. Giữ các thay đổi mixed-visuals có sẵn.
- `backend/tests/test_docx_preview_fields.py`:10 regression, công thức complex/simple, instruction chia run, ô gộp/formatting, bảo toàn PAGE/NUMPAGES, nested unsupported, thiếu cache, malformed/invalid DOCX, integration boundary Gotenberg.
- `backend/tests/test_knowledge.py`: test converter trả500 dùng DOCX ZIP thật thay cho b"xx", để thực sự đi đến HTTP error path sau validation mới.
- Cập nhật README nhật ký, PROJECT_CONTEXT, WORK_LOG.

## An toàn và giới hạn

Chỉ materialize field công thức trong bảng có cached text. PAGE/NUMPAGES/TOC và field không phải công thức giữ nguyên. Không tính toán công thức bằng AI, không đoán kết quả thiếu. Missing cache/malformed/nested unsupported/invalid container trả AppException422 rõ ràng; không gửi tài liệu không an toàn để converter tự suy diễn. Trường lồng nhau cần thêm xử lý có kiểm chứng sau này; hiện fail closed, không tuyên bố hỗ trợ mọi cấu trúc DOCX.

Cached result là giá trị đã lưu ở nguồn, không phải bảo đảm toán học cho mọi tài liệu; riêng tài liệu user đã đối chiếu25dòng trong phiên396. Chưa xây universal per-cell numeric parity guard hoặc sửa TABLE_HEADER_UNRESOLVED trang5–6. Cảnh báo cần duyệt có thể vẫn còn. Không tự duyệt/reparse/index/publish hoặc sửa source đang phục vụ.

## Kiểm chứng

- Regression đầu tiên fail đúng vì helper chưa tồn tại. Bộ trọng tâm Docling/layout/formula ban đầu37passed; bộ cuối formula10 + converter HTTP error1 =11passed.
- Ruff toàn backend đạt (có cảnh báo AccessDenied ở thư mục test cũ), git diff --check đạt. Không FE change nên không chạy FE build.
- Gotenberg thật với đúng file Phuong huong tuyen sinh 2024_DHQN_final.docx: PDF7trang, bốn số cuối trang7=1070/451/402/351. Render PNG trang7 và kiểm tra bằng mắt: hàng tổng đúng cột, không số quá lớn hoặc xuống dòng. SHA256 tệp DOCX trước/sau không đổi.
- Hai DOCX trong corpus: file Phuong huong được tạo bản sao công thức; báo cáo2025 không có formula thuộc phạm vi nên bytes giữ nguyên.
- Full lượt đầu984pass/12fail/3skip: một lỗi test mới do input giả b"xx"; sửa test và bổ sung invalid-input guard. Full cuối988passed/11failed/3skipped, các lỗi còn lại thuộc baseline dispatcher/export, legacy publish/GC/canary, reconciliation, auth role; không báo full suite sạch.

## Bàn giao

Chưa restart dev/worker, chưa chỉnh preview cache trong nguồn đã lưu, không reset DB hoặc thay đổi khóa/provider. Người dùng chạy make dev để worker nhận code rồi dùng Bóc tách lại cho nguồn này, kiểm tra/duyệt bản mới trước khi nạp/xuất bản nếu cần. Không phải xóa và upload lại DOCX. Bản PDF cũ đang lưu không tự biến thành PDF mới khi refresh đơn thuần.
