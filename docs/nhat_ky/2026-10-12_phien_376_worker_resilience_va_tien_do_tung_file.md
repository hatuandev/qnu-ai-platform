# Phiên #376 — Worker resilience và tiến độ từng file

- Ngày: 2026-10-12.
- Yêu cầu: Triển khai ưu tiên limiter/recovery/retry cho nhiều người nạp và % xử lý độc lập từng tài liệu.
- Skills: backend, clean-code, ingestion, ModelOps, frontend/admin-design. Đề xuất trước: milestone thực, không nội suy timer hoặc giả số trang Paddle.

## Thay đổi

- `app/core/provider_capacity.py`: Lua Redis cross-process capacity lease, renew/cleanup/fail-closed; client riêng tránh tái dùng pool khác event loop. Paddle adapter bọc mọi extract, VectorIndexer bọc embedding các nhánh runtime hiện có; cùng endpoint dùng cùng resource hash.
- `app/workers/leased_execution.py`: job/resource locks, heartbeat, attempt context, phân loại cause chain transient, retry_after; timeout/mất lease chuyển sang recovery DB thay vì ARQ chạy lại ngay item processing.
- `app/modules/jobs/ingestion_recovery.py`: reclaim ingestion và index jobs theo lease + heartbeat quá hạn; giữ source đã xong/hủy, scope index theo binding/tenant/workspace/revision, bỏ staging bị gián đoạn và không đổi active. Limit3/backoff và pending dispatch IDs mới. Chưa bao phủ reparse/export/purge recovery mới.
- `ingestion_admission.py`: PostgreSQL tenant advisory lock + backlog limit429; `ingestion_progress.py`: progress DB độc lập, attempt/status fence, monotonic.
- Settings defaults: worker10 jobs/process, timeout900s/max_tries3, OCR2/embedding4 per endpoint/category, queue wait120s, ingestion backlog1000/tenant. Không seed khóa/model hoặc sửa ModelOps credentials; limits là hạ tầng có thể cấu hình.
- `source_ingestion_service`, import_batch_service/schemas và worker tasks: progress milestone20/65/75/85/90/99, succeeded100; hydrate per-item response từ job mới nhất, retry0. Không cần migration.
- FE import-batch-modal + import-progress helper/types: %/thanh riêng mỗi item, batch average, Cần duyệt riêng, bảng overflow; không biến failed thành100. Chưa tiến độ trang/chunk thật vì adapter trả cả tệp.
- Compose worker healthcheck ARQ, cron mỗi15s. Đã cập nhật quy trình01/02/06 và tài liệu phiên.

## Kiểm chứng

- Test-first: worker max_tries chưa truyền vào ARQ, progress module chưa có — 2 ca fail trước triển khai.
- 76 targeted BE đạt; 7 ca resilience trong đó Redis thật20 requests giữ giới hạn, Redisdown fail-closed, DB/savepoint fixture recovery tránh lease còn sống, giữ item completed, đổiattempt, progress độc lập0/65/100, không lùi và chặn attempt cũ. Fixture tenant riêng/rollback; không recover user jobs.
- FE 2 progress tests đạt; scoped Biome/Vite build/TypeScript typecheck cuối đạt (exit code0); full FE lint14 lỗi nền ngoài phạm vi.
- Ruff toàn BE đạt. Full BE cuối gồm guard CancelledError: 924 passed, 11 failed cũ, 2 skipped (35,47s); cùng nhóm lỗi #374/#375 (consulting export, publishing auth/canary/GC, reconciliation/facts/sessionrole). 26 regression worker/resilience/vectorload cuối đạt.
- Docker compose config --quiet đạt. Không chạy broker/worker production mới, không benchmark GPU/Paddle/vLLM thật, không kill/restart/crash worker thật, chưa browser E2E.
- Không reset/migrate/nạp/xóa/ngừng tài liệu user/qnu-sso hay thay credentials; backend/worker hiện chạy cần restart/drain để nhận code mới.

## Giới hạn vận hành

- Khôi phục mặc định có thể chờ tối đa khoảng timeout+120s sau heartbeat cũ để tránh giành job còn sống. Redis TTL/lease không thay thế khả năng hủy inference trên server AI.
- Capacity chia theo endpoint/category, không có budget GPU tổng giữa các port/model alias; cần benchmark5/10/20 người và điều chỉnh limit trước khi cam kết production capacity.
- Chưa crash E2E/browser, chưa recovery mới cho reparse/export/purge; fairness theo user chưa bổ sung. Tổng backlog tenant đã có, không phải cam kết SLA.
