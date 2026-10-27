# Context633 — Kiểm thử upload, kho tri thức và Nemotron

Kết luận: **chưa đạt đầu-cuối**. OCR dịch vụ thật hoạt động, nhưng đường tích hợp DOCX và Quality Gate PDF còn lỗi/giới hạn. Đây là kiểm thử bằng API và worker, không phải nghiệm thu giao diện hay toàn bộ corpus.

## Kết quả thực chạy

| Ca | Kết quả | Bằng chứng |
|---|---|---|
| Upload DOCX, PDF native, PDF scan | PASS | 3 lần HTTP202/stored; kho tài liệu giữ file, không tự tạo tác vụ parse |
| Tải lại file gốc | PASS | 3 lần HTTP200, SHA256 khớp từng byte; storage thực tế S3StorageDriver |
| Lặp cùng Idempotency-Key | PASS | HTTP202, deduplicated=true, cùng document ID |
| Nạp DOCX/PDF native vào kho tri thức | PASS có giới hạn | Batch completed, 2 item succeeded, revision v1 ready; PDF giữ literal header chưa xác định |
| OCR ảnh PNG và PDF scan qua Nemotron | PASS trên mẫu | HTTP200, 1 trang mỗi ca; 16/16 ô bảng khớp, giữ tiếng Việt, năm, số 0 và dấu —; không fallback |
| Reparse PDF bằng Nemotron | NEEDS_ATTENTION | revision v2 review_required, TABLES_NOT_MATERIALIZED |
| Reparse DOCX bằng Nemotron | FAIL | revision v2 failed, DOCX_LAYOUT_ALIGNMENT_FAILED |
| Raw provenance PDF | PASS | Provider response, raw LaTeX, bbox, source span và map trang còn đủ; hash MD/JSON/evidence khớp S3 |
| Chặn tải nhầm artifact cũ của DOCX lỗi | PASS | API trả HTTP409; không trả tệp v1 như kết quả v2 |
| Giữ nguồn đang dùng và chưa index thử nghiệm | PASS | Active source vẫn là v1 của hai nguồn; active_index=null; 0 index revision trong collection thử |
| Regression adapter/runtime ngoại tuyến | PASS | 29 passed/3,20s/exit0; không thay thế bằng chứng dịch vụ thật |

## F633-01 — DOCX đối chiếu cả markup của OCR

Tác vụ thật thất bại với `DOCX_LAYOUT_ALIGNMENT_FAILED`. `align_office_markdown` token hóa bằng `\w+`, đòi tỷ lệ khớp ít nhất 0,9. Khi trang OCR chứa bảng HTML, tên thẻ chen giữa chữ trong ô. Replay trên đầu ra OCR thật đã lưu: bản native alignment được chấp nhận; bản HTML được ghép như đường runtime bị từ chối; phần chữ nhìn thấy sau khi đọc HTML được chấp nhận. Đo cùng fixture: bản HTML chỉ khớp khoảng 76,8%, chữ OCR khớp 100%. Chưa sửa parser, không hạ ngưỡng để làm xanh.

Nguồn: `backend/app/modules/knowledge/services/source_extraction.py`, hàm `align_office_markdown` và `extract_source`. Replay không gọi model thêm; không khẳng định nguyên nhân font chỉ từ thông báo lỗi chung.

## F633-02 — PDF có bảng nhưng Quality Gate đếm thiếu

Nemotron trả bảng HTML đủ 4 hàng × 4 cột, raw LaTeX/bbox/header còn nguyên. Raw evidence và structured JSON vẫn giữ đủ 16 ô. Tuy nhiên Quality Gate báo `detected_tables_count=1`, `markdown_tables_count=0`, `TABLES_NOT_MATERIALIZED`; revision mới dừng `review_required`. Canonical projection vẫn có bảng native kèm header rỗng/unknown và một phần text bị lặp. Vì vậy không kết luận bảng bị mất hoàn toàn hoặc đã đạt semantic/header.

Nguồn: `source_extraction.py`, `source_artifact.py`, `parsers/pdf_structure.py`. Đây là giới hạn tích hợp giữa HTML OCR, projection và phép kiểm bảng; không chứng minh dịch vụ Nemotron đọc sai ô.

## F633-03 — Import batch chưa mang lựa chọn OCR

`KnowledgeImportBatchCreateRequest` không có `ocr_engine`; `import_batch_service.py` tạo job chỉ có item_id/batch_id. Worker đọc ocr_engine nhưng nhận null; `extract_pdf` dùng paddleocr cho scan khi không có engine cụ thể. Collection thử có cấu hình Nemotron riêng nhưng chưa đủ để chứng minh đường initial import chọn đúng Nemotron. Ca scan đã upload và OCR trực tiếp thành công; **scan → initial knowledge import bằng Nemotron: NOT RUN**, không giả nhận đã đạt.

Đã kiểm tra đường reparse từng nguồn vì API này có `ocr_engine`; không đổi job bằng SQL, không sửa default toàn hệ thống để ép ca thử.

## Metadata artifact của bản thất bại

Revision DOCX v2 kế thừa snapshot_metadata với artifact ready thuộc v1, dù canonical mới null và status failed. API tải artifact kiểm danh tính và trả409 đúng. Đây là metadata dễ gây hiểu nhầm trên UI; không phải bằng chứng dữ liệu v1 đã được xuất bản dưới v2. Không chép tệp cũ thành kết quả OCR mới.

## Phạm vi và trạng thái để lại

- Collection `col_929f275c6229`, nhãn CTX633 — Kiểm thử DOCX PDF Nemotron; metadata đánh dấu thử nghiệm, không dùng nghiệp vụ. Group `doc_grp_77dcea5a41db`; 3 file mẫu còn để kiểm tra.
- Hai v1 ready được luồng import tự đặt active; hai v2 lỗi/cần duyệt không thay active v1. Không duyệt/publish, không vector index, Compiler hay retrieval.
- Tạo provider Nemotron qua ModelOps, model alias `nemotron-parse`, endpoint theo người dùng, key đi qua key pool được bảo vệ. Không ghi credential vào source/log/.env; model alias không xác minh độc lập phiên bản trọng số upstream.
- System defaults trước/sau giữ nguyên. Automatic approval đã chặn PUT đổi OCR mặc định toàn cục trước khi chạy vì vượt phạm vi kiểm thử; tiếp tục bằng request riêng từng nguồn, không bypass.
- Không sửa app logic, không restart API/worker. Giữ các sửa đổi chưa commit đồng thời. Không commit/push.
- NOT RUN: UI trình duyệt, tài liệu thực tế phức tạp/nhiều trang, publish/vector/RAG, full Pytest (phiên này không đổi mã ứng dụng).

## Lệnh và bằng chứng

Cwd backend; các script fixture/API tại `backend/storage/context633` (gitignored, không có key). `prepare_and_probe.py`, `e2e_upload_import.py`, `e2e_nemotron_reparse.py`, `verify_results.py`, `final_checks.py` thực chạy exit0. Probe, upload, reparse và kiểm tra S3 dùng quyền mạng đã được phê duyệt. `final-checks.json` được bổ sung kiểm tra cấu trúc DOCX cells riêng, không coi nó có cùng shape PDF grid.

`.venv\Scripts\python.exe -m pytest tests/test_nemotron_ocr_631.py -vv -o faulthandler_timeout=30`: 29 PASS/0 FAIL, exit0. Lần đầu chạy trong môi trường hạn chế treo Redis đã dừng đúng hai tiến trình test; chỉ kết quả chạy lại có quyền mạng được ghi PASS. Các cảnh báo PDF Inspector được giữ, không diễn giải thành bảo đảm parsing toàn diện.

Bằng chứng đã rút gọn, không secret/Base64: [result.json](result.json). Nội dung fixture tổng hợp gồm header Chương trình/Năm dữ liệu/Chỉ tiêu/Học phí, 3 dòng dữ liệu 2025/2026 và chú thích; không gửi corpus nghiệp vụ ra provider.

Bước tiếp theo phù hợp: sửa ba ranh giới trên với regression dựa vào cấu trúc tổng quát rồi chạy lại đúng fixture và tài liệu thật được chỉ định. Chưa triển khai sửa trong yêu cầu kiểm thử này.
