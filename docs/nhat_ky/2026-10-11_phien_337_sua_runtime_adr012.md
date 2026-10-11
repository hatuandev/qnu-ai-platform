# Phiên #337 — Sửa runtime ADR-012

## Mục tiêu và ranh giới

Sửa các lỗi chặn quy trình Kho tài liệu thuần lưu trữ → snapshot độc lập trong Kho tri thức → parse/OCR → normalize/review → chunks/facts → embedding → parity → publish. Không sửa qnu-sso, không reset DB, không commit/push. Giữ nguyên thay đổi sẵn có của người dùng.

## Thay đổi chính

- `source_ingestion_service.py`: lưu/flush source revision trước chunking; gọi đúng OCRService và raw_text; kiểm tra SHA-256 của tệp đã chọn; lưu snapshot riêng; gọi build đúng tham số, không nuốt lỗi; sửa Markdown tạo revision mới thay vì sửa artifact cache cũ; kiểm tra hủy; cập nhật item/batch.
- `import_batch_service.py`, `import_state_service.py`: idempotency hash theo yêu cầu chuẩn hóa; tạo durable JobRecord cùng transaction với batch/items trước dispatch; counters được đối soát từ item, không phục hồi batch đã hủy.
- `models.py`, `schemas.py`, migration `20261011_independent_index.py`: gỡ FK provenance legacy của index, cho phép nguồn độc lập không có repository revision/document. Migration chưa áp dụng trên DB thật.
- `vector_generation_service.py`: namespace theo cấu hình embedding; tạo KnowledgeChunk/Fact đúng FK và revision; đồng nhất chunk ID giữa PostgreSQL/Qdrant; metadata trích dẫn lấy từ snapshot; có counts tái sử dụng; giữ trạng thái generation đang active.
- `generation_publish_service.py`: kích hoạt toàn bộ revision trước khi khóa collection và kiểm tra CAS epoch/source membership. Chỉ đổi pointer khi đủ điều kiện; không deactive điểm cũ vì truy vấn đã pin snapshot và rollback còn cần chúng. Retention/GC phải quản lý việc xóa sau này.
- `vector_indexer.py`, `retriever.py`, `binding_service.py`: dùng namespace/model/provider của generation đã pin; đọc nguồn độc lập; ID và title cho sparse/dense không còn bắt buộc tài liệu gốc.
- FE: tab nguồn dùng API nhập mới và quản lý generation (tạo/build/publish/rollback); model để trống phân giải ModelOps; nullable IDs và lịch sử source đúng DTO; kiểm tra lint có phạm vi. Dùng primitives sẵn có theo skill frontend/admin, không thêm thư viện UI.
- `.gitignore`: bỏ qua snapshot runtime, không xóa tệp người dùng.

## Kiểm chứng

- Regression ban đầu tái hiện lỗi nullable/provenance và thứ tự lưu source; sau sửa bộ trọng tâm ADR-012/Knowledge/retrieval: **61 passed**.
- Kiểm tra lại source ingestion và vector generation sau sửa tên tệp/ID payload: **12 passed**.
- Test fault injection: activation nguồn thứ hai lỗi thì pointer/epoch cũ nguyên vẹn, không deactive chỉ mục cũ; cancelled batch giữ cancelled và tính lại counters.
- Ruff toàn backend: đạt, có cảnh báo Access denied khi duyệt thư mục test cũ.
- Frontend: Vite build + TypeScript đạt sau sửa nullable navigation; Biome kiểm tra có phạm vi các tệp sửa và sửa liên kết label/control. Đây không phải kiểm tra thao tác trên trình duyệt.
- Alembic heads: một head `20261011_independent_index`; chưa kiểm thử migration trên PostgreSQL thật.
- Full pytest: **760 passed, 15 failed, 2 skipped**. Lỗi còn lại: các test consulting/tools cần DB (connection refused); API legacy GC/canary/upload nhận 403; fixture auth mong `admin` thay vì `AI.Admin`; reconciliation legacy; worker count mong 6 nhưng có 7 task. Chưa xác nhận baseline nên không kết luận tất cả là lỗi có sẵn hoặc do môi trường.
- Docker ps thất bại vì pipe Docker Desktop Linux engine không tồn tại. Chưa chạy E2E FE+BE, Qdrant/Redis/worker/OCR/provider thật.

## Bài học và bước tiếp theo

Mock tests không thay thế nghiệm thu ứng dụng thật. Không tuyên bố production-ready từ các kết quả trên. Sau khi dịch vụ sẵn sàng: áp dụng migration không reset DB; kiểm thử upload 100 tài liệu, nhập snapshot, scan OCR/review, build/publish, embedding model thứ hai không OCR lại, lỗi build giữ chỉ mục cũ, hủy/retry, xóa tài liệu gốc vẫn truy vấn nguồn đã nhập. Tiếp tục xử lý các test full-suite chưa sạch trước nghiệm thu toàn dự án.
