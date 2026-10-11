# Phiên #340 — Sửa OCR/ModelOps và bảo toàn nguồn trang sau review E2E

## Mục tiêu và ranh giới

Xử lý findings #339 theo yêu cầu người dùng. Không sửa qnu-sso; không reset/migrate DB, reseed DB thật, sửa khóa thật hoặc tự động thay chỉ mục đang phục vụ. Giữ nguyên thay đổi có sẵn trong worktree. Skills clean-code, backend, ingestion, ModelOps và RAG định hướng sửa có phạm vi, giữ chứng cứ trang và không nhận test giả lập là E2E.

## Thay đổi runtime

- `backend/app/modules/ocr/adapters/paddleocr_adapter.py`: bỏ endpoint mặc định gắn cứng; chưa cấu hình thì unavailable/fail-fast. Kiểm tra JSON/result/list/trang/text; lỗi protocol và nội dung rỗng trả AppException. Giữ trang trắng và marker số trang. Bỏ confidence 0.98 tự đặt; giá trị tương thích 0 có `confidence_source=unavailable`, không phải độ tin cậy đo được.
- `backend/app/modules/ocr/service.py`, `schemas.py`: provider thiếu/inactive không gọi adapter mặc định; dùng endpoint/model/timeout DB; chặn response rỗng success=True; chuyển tiếp nguồn confidence.
- `backend/app/modules/modelops/services/provider_service.py`: seed chỉ thêm presets thiếu. Kể cả tham số legacy overwrite=True cũng không xóa provider Ollama, ghi đè khóa/key pool/endpoint/timeout/cấu hình người dùng hoặc system defaults. Muốn đổi cấu hình dùng API cập nhật tường minh.
- `backend/app/modules/knowledge/services/source_pages.py` (mới): ranh giới từ structured OCR hoặc marker có sẵn; chuẩn hóa từng trang; đếm ký tự thật. Không chia đều văn bản để đoán trang; thiếu mapping thì page=null. Facts tách theo trang; chunks không vượt ranh giới trang dù chunker nào.
- `source_ingestion_service.py`: giữ structured OCR pages; manifest thật; hiệu đính tạo manifest mới và version v2. Artifact fingerprint v2 tránh tái dùng bản bóc tách cũ mất mapping.
- `chunk_set_service.py`: tạo chunks theo từng trang và version fingerprint page-boundaries-v2, không tự gán trang 1; cache cũ không được coi tương đương với cách chia mới.
- `vector_generation_service.py`: payload/chunks giữ page=null khi chưa biết; facts đọc từng trang canonical thay vì toàn văn đặt trang 1.

Không tự sửa các artifacts/chỉ mục đang active. Với nguồn cũ không có ranh giới trang, phải bóc tách lại ở Kho tri thức rồi build/publish revision mới để có trích dẫn trang chính xác; không thể khôi phục mapping chỉ từ văn bản đã bị ghép phẳng.

## Kiểm thử và bằng chứng

- Regression mới `test_ocr_modelops_safety.py`: 7 ca ban đầu FAIL trước sửa, chứng minh lỗi endpoint/disabled provider/malformed/seed. Bổ sung endpoint-model-timeout từ DB, JSON không hợp lệ, trang trắng, confidence không đo được.
- `test_source_page_provenance.py`: bảng chỉ ở trang 2 cho facts/chunks, manifest ký tự thật, trang đầu trắng, hiệu đính marker, không đoán trang khi thiếu mapping. Test đầu tiên phát hiện chunker gộp trang; sửa tại tầng điều phối chunk set.
- Đồng bộ `test_ocr.py` với engine Paddle và hợp đồng rỗng phải báo lỗi; test orchestration failover cô lập bước gọi adapter, không dùng session giả để giả vờ provider thật. `test_modelops.py` kiểm tra defaults đọc đúng cấu hình seed thay vì tên OCR cũ.
- Bộ liên quan: **83 passed**, gồm OCR, ModelOps, source/chunk/vector và regressions ADR-012. Dùng fixture/mocks tại biên phụ thuộc, không phải xác nhận inference thật.
- Full backend lần cuối: **787 passed, 9 failed, 2 skipped** (31.36s). 6 lỗi API legacy publishing nhận 403; 1 reconciliation legacy_payload_schema; 1 assertion auth AI.Admin/admin; 1 assertion workers 7/6. Các nhóm này cũng có trong các lần full suite trước, không nới quyền hoặc sửa qnu-sso để làm xanh tests.
- Ruff toàn backend: exit 0, All checks passed; có cảnh báo Access denied khi duyệt một số thư mục môi trường nên không tuyên bố quét được mọi thư mục.
- `npm run build`: exit 0 (Vite và TypeScript); Vite build 6.27s. Không có thay đổi FE trong phiên này.

## Ma trận nghiệm thu thực tế

| Hạng mục | Trạng thái sau sửa | Căn cứ / phần còn thiếu |
| --- | --- | --- |
| Provider tắt/thiếu không gửi OCR; seed giữ cấu hình | PASS (regression) | Test lỗi và bảo toàn khóa cấu hình; không reseed DB thật |
| JSON sai/rỗng/trang trắng; trang 2 trong chunks/facts | PASS (regression) | Fixtures có nội dung khác trang; không gọi Paddle thật |
| Browser FE → BE → ARQ → Paddle/vLLM → Qdrant → RAG sau sửa | NOT RUN | #338 chỉ báo cáo bộ mẫu nhỏ trước sửa; cần chạy lại với request/job/artifact traces |
| 100 tài liệu khác hash, huỷ/retry/idempotency ở dịch vụ thật | NOT RUN | Không suy ra từ unit tests |
| Embedding model thứ hai, không OCR lại, vector space độc lập | NOT RUN | Chưa có bằng chứng server cung cấp embedding thứ hai; reranker không phải embedding |
| Reranker down, activation giữa chừng/CAS, xóa tài liệu gốc | NOT RUN (E2E) | Có tests phạm vi ở các phiên nhưng chưa tái chứng minh toàn luồng thật |
| Migration trên DB có dữ liệu cũ | NOT RUN | Không reset hoặc migrate DB của người dùng |
| Full backend | FAIL | 9 tests còn lỗi, liệt kê phía trên |
| Frontend build / kiểm tra mã | PASS có giới hạn | Không thay thế browser E2E |

## Bài học

Chứng cứ trang phải xuất phát từ kết quả parser/OCR, không từ độ dài văn bản. Seed không phải thao tác reset cấu hình. Thay đổi thuật toán tạo artifact phải có version fingerprint để tránh dùng cache cũ sai nghĩa. Báo cáo test cần phân biệt bộ giả lập, tích hợp DB và E2E dịch vụ thật; chưa nghiệm thu toàn diện.
