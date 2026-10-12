# Phiên #375 — Đánh giá tải nhiều người nạp tài liệu

- Ngày: 2026-10-12; read-only code/config/thư viện ARQ cài tại repo, chưa load test hay sửa runtime.
- Skill backend dùng để kiểm tra queue, persistence, concurrency và recovery.

## Có sẵn

- ARQ/Redis tách việc nạp khỏi API, PostgreSQL lưu job/batch/item, deterministic broker IDs/idempotency, collection/item locks, cron reconcile pending dispatches.
- Worker max_jobs=10 mỗi process, timeout 300s, heartbeat worker 15s. Docker worker restart unless-stopped; container healthcheck đang disable.
- Batch nguồn tối đa 500 tài liệu, phân chia thành job cho từng item. Chỉ mục serving không phụ thuộc staging publish mới.

## Chưa đủ để cam kết production đa người dùng

1. Không thấy limiter chung theo provider PaddleOCR/embedding trong các đường đã rà. 10 jobs mỗi process không phải giới hạn toàn cụm; thêm worker tăng tải AI. Chưa đo sức chịu của server AI.
2. process_import_item commit processing trước OCR, lần nhận lại thấy processing trả IMPORT_ITEM_IN_PROGRESS. Cron chỉ tìm queued+dispatch pending, chưa có cơ chế lease/timeout reclaim item/job đang chạy bị bỏ lại khi worker chết. Cần recovery bảo đảm idempotency, không OCR trùng.
3. WorkerSettings dùng max_retries=3 nhưng ARQ đang cài nhận max_tries (default5), get_kwargs chỉ lấy tham số Worker.__init__. retry_jobs chỉ xử lý Retry/CancelledError/RetryJob trong mã thư viện, không tự retry mọi exception HTTP/OCR. Cần phân loại lỗi tạm thời và backoff thật.
4. timeout job 300s cần đối chiếu PDF dài/dịch vụ chậm; nhiều tệp Base64 cùng lúc tăng RAM. Chưa có benchmark dung lượng/số trang/job latency.
5. Queue chung cho OCR/index/export/purge/GC; chưa chứng minh fairness/hạn mức user/tenant, chưa kiểm thử overload và crash/restart. Container worker healthcheck disable dù ARQ có heartbeat.

## Ưu tiên đề xuất

Limiter toàn cụm theo provider + quota backlog → reclaim stale jobs/items và retry đúng ARQ → health/queue age/latency/memory metrics → bài kiểm thử đồng thời 5/10/20 người, scan lớn/native/DOCX, cùng tài liệu/cùng kho, OCR lỗi/worker chết/Redis gián đoạn. Đây là kịch bản đo, không cam kết sức chứa hay đề xuất con số concurrency an toàn khi chưa benchmark.

## Giới hạn

Ảnh 0%/parse chỉ thể hiện giai đoạn hiện tại, không chứng minh treo hoặc năng lực chịu tải. Không chạy request OCR/embedding/userbatch mới; không kiểm định server triển khai hay load E2E; chưa sửa code. Ruff/Pytest/build không chạy cho chẩn đoán read-only. Chỉ cập nhật nhật ký/snapshot/context/worklog/index, không đổi quy trình vận hành.
