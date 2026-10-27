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
| Qdrant | collection chung | collection riêng (`QDRANT_COLLECTION`) |
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
