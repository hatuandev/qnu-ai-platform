# Triển khai QNU V1 trên Docker / Dokploy

Root `docker-compose.yml` đã chuyển sang `backendV1`; Compose hiện chỉ có backend/worker (chưa có service frontend vì `frontendV2` chưa có SSO production). File `backendV1/docker-compose.v1.yml` là entrypoint tương thích, include cùng cấu hình root; không duy trì hai stack ứng dụng khác nhau.

## Dịch vụ

| Service | Thực hiện | Điều kiện |
| --- | --- | --- |
| storage-init | Tạo bucket S3/MinIO nếu chưa tồn tại | Object store truy cập được |
| bootstrap | `alembic upgrade head`, chỉ migration V1 | Kết nối DB đã được cấu hình và storage-init xong |
| backend | `qnu.main:app`, nội bộ8002 | Bootstrap thành công |
| worker | `qnu.workers.settings.WorkerSettings` | Backend healthy |

Compose không có service frontend: website trên server vẫn là bản cũ có SSO cho tới khi `frontendV2` được bổ sung đăng nhập production. Worker có trần vận hành `WORKER_MODEL_JOB_TIMEOUT_SECONDS` mặc định86400; thời gian chờ provider vẫn do ModelOps.

## Chuẩn bị

1. Đối chiếu commit, backup PostgreSQL, object store và Qdrant; lưu riêng khóa ModelOps hiện tại. Mã V1 không tự nhập dữ liệu legacy.
2. Giữ đúng DATABASE_URL, bucket, collection, volume và PROVIDER_ENCRYPTION_KEY. Bootstrap chỉ sở hữu bảng/version `alembic_version_backendv1`, không stamp hay chạy migration backend cũ. Kiểm các revision pending trên bản sao nếu server chưa từng chạy V1.
3. Hạ tầng PostgreSQL/Redis/Qdrant/MinIO/Gotenberg phải truy cập được từ container qua `dokploy-network`. URL localhost ở trong container không trỏ về laptop hay container hạ tầng khác. Không chạy infra local để thay hạ tầng production.
4. Điền mẫu `.env.dokploy.example` bằng secret store/Dokploy Environment. Không copy placeholder đè khóa thật; không đưa key AI vào file này. ModelOps DB quyết định provider/model/key/grant/default.
5. `ALLOWED_ORIGINS` là chuỗi origin ngăn cách bằng dấu phẩy, không phải JSON array. `PUBLIC_BASE_URL` là URL mà browser truy cập được cho API cùng origin. Giữ queue/cache V1 riêng, không dùng hàng đợi legacy.
6. Production V1 yêu cầu DEV_AUTH_ENABLED=false, SSO_ENABLED=true và cấu hình OpenIddict thật. Các cờ demo legacy cho dev login trong production không có hiệu lực ở V1. API xác thực token Bearer theo SSO; chưa có bundle frontend production trong Compose.
7. Volume `qnu_platform_storage` vẫn được giữ cùng tên, mount `/app/storage`. UID10001 phải có quyền ghi khi dùng local storage; không đổi quyền hàng loạt trên dữ liệu chưa kiểm. Nếu S3, cấu hình cùng bucket đã chứa dữ liệu V1. `storage-init` tự tạo bucket khi thiếu; với AWS S3 hoặc khóa không có quyền `CreateBucket`, tạo bucket trước bằng công cụ quản trị.

## Kiểm cấu hình và build trước triển khai

Các lệnh dưới đây giả định file secret đã điền trên server tên `.env.production`. Không in toàn bộ `docker compose config` ra log vì có thể chứa secret.

```bash
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production build backend
```

Backend image cài Python3.12 theo uv.lock bằng `uv sync --frozen --no-dev`. `.dockerignore` theo từng build context loại .env, venv, node_modules và dữ liệu runtime. Không copy thư mục backend/frontend legacy vào image.

Khi đã được phép triển khai trên đúng server:

```bash
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
docker compose --env-file .env.production logs --tail=100 bootstrap backend worker
```

Dokploy: chọn repository/branch đã kiểm, dùng root Compose, nhập Environment, rồi Deploy. Khi `frontendV2` có SSO, thêm domain HTTPS vào service frontend mới; hiện tại chỉ triển khai backend/worker và giữ website cũ trên server.

Bootstrap không seed, không tạo provider/key mặc định và không OCR/reindex lại tài liệu. API/worker không tự migrate. Sau deploy kiểm đúng V1 UI, SSO, workspace membership, ModelOps MinerU và các chức năng upload/OCR/compiler/publication/chat trên kho thử trước demo. Build và health không thay thế bài test chất lượng RAG/OCR.

## Ổn định vận hành

- `storage-init` chạy một lần trước `bootstrap`. Nếu log báo `AccessDenied`, sửa quyền khóa S3 hoặc tạo bucket thủ công rồi deploy lại; không bỏ qua bước này vì upload sẽ lỗi `NoSuchBucket`.
- Backend healthy theo `/health/ready` (PostgreSQL + Redis), không chỉ theo tiến trình. Migration lỗi hoặc thiếu dependency thì stack dừng thay vì chạy nửa vời.
- Log mỗi container giới hạn 20 MB × 5 tệp để tránh đầy đĩa server; log lâu dài vẫn thu qua Dokploy/nhật ký tập trung nếu cần.
- `stop_grace_period` 30 giây cho backend và 60 giây cho worker để deploy/restart không cắt ngang xử lý.
- Chỉ một replica backend đặt `OWN_RECONCILE=true`; replica bổ sung đặt `false` để không tranh việc quét hàng đợi.
- `frontendV2` chưa có luồng đăng nhập production (chỉ có cầu nối dev của Vite và tự tắt trong bản build). Trên server tiếp tục dùng website cũ có SSO; chỉ đưa V2 lên Compose sau khi bổ sung SSO và kiểm thử đăng nhập thật.

## Giữ dữ liệu và quay lại bản trước

Không dùng `down -v`, volume prune hoặc reset DB để sửa lỗi deploy. Dừng đúng app container khi cần; giữ named volumes và các bản backup. Image tag V1 tách riêng `qnu-ai-platform-v1`; lưu commit/tag trước khi nâng. Rollback image không tự rollback schema; nếu migration đã chuyển dữ liệu, dùng kế hoạch khôi phục đã kiểm trên bản sao.

Hai thư mục backend/frontend cũ và `frontendV1/` đã được gỡ khỏi checkout sau khi lưu riêng toàn bộ mã và tệp ignored. Lịch sử Git chỉ khôi phục được tệp đã commit; giữ bản lưu riêng cho cấu hình cá nhân, storage và dữ liệu test cũ. [Local V1](../quy_trinh/38_huong_dan_chay_qnu_v1.md) dùng API8002/FE V2 3002 với runner foreground, khác Compose server.
