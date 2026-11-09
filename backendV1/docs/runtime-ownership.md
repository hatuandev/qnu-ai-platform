# Quyền sở hữu runtime

| Tài nguyên | Legacy (`backend`) | BackendV1 |
|---|---|---|
| Cổng HTTP | 8001 | 8002 |
| ARQ queue | queue mặc định | `qnu:v1:jobs` |
| Redis cache | namespace cũ | `qnu:v1:cache:` |
| Cron reconcile | có | chỉ chạy khi bật `OWN_RECONCILE=true` |
| S3/MinIO | bucket chung | bucket/prefix riêng |
| Blob kho tri thức | `documents/…` legacy | `v1/workspaces/{ws}/collections/{col}/blobs/…` |
| Blob bằng chứng OCR | `ocr/…` legacy | `v1/workspaces/{ws}/ocr/{run_id}/{kind}/p{page}-{sha256}.{ext}` |
| Job OCR | `ocr_process_source` (legacy) | `ocr_process_run`, `ocr_reconcile_queued` trên queue v1 |
| Qdrant | collection chung | collection riêng theo index run/embedding model |
| Migration | `alembic_version` | `alembic_version_backendv1` |

Nguyên tắc: **một job chỉ do một backend sở hữu**; v1 không bao giờ nhặt job của legacy.

## Job và cron của v1

| Tên | Loại | Việc |
|---|---|---|
| `ocr_process_run(run_id)` | job | claim run, render, OCR từng trang, dựng artifact |
| `ocr_reconcile_queued()` | cron 5 phút | enqueue lại run `queued` chưa dispatch (Redis mất job) |

`job_id` của v1 có dạng `qnu:v1:ocr:{run_id}:{attempt}` nên dispatch lặp là no-op.
ARQ đặt `retry_jobs=False`, `max_tries=1`: retry thuộc về bản ghi run, không có hai lớp
retry chồng nhau. Bật `OWN_RECONCILE` mới chạy cron, tránh hai backend cùng nhặt.

## Thời gian chạy tác vụ model

`ocr_process_run`, `compile_run`, `compiler_review_job` và `index_run` dùng
`WORKER_MODEL_JOB_TIMEOUT_SECONDS` (mặc định `86400`, tức 24 giờ), thay cho trần
30 phút chung của worker. Đây vẫn là giới hạn vận hành có thể cấu hình; không phải
chế độ chạy vô hạn. Các tác vụ bảo trì giữ trần 30 phút.

Giới hạn này độc lập với thời gian chờ phản hồi provider trong ModelOps và lease
của từng run. Lease tiếp tục được gia hạn theo cơ chế hiện có; quyền hủy, khóa
phiên bản, idempotency và quy tắc không gửi lại lời gọi uncertain vẫn giữ nguyên.
Worker cần được khởi động lại để nhận cấu hình/mã mới. Không tự khởi động lại
worker đang xử lý tài liệu chỉ để áp dụng thay đổi này.
