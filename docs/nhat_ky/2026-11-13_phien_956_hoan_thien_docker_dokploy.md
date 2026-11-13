# Phiên 956 — Hoàn thiện Docker cho Dokploy: tạo bucket tự động, healthcheck readiness, log xoay vòng

## 1. Yêu cầu và phạm vi

- Người dùng cho biết server triển khai bằng **Dokploy** và yêu cầu hoàn thiện cấu hình Docker để chạy ổn định trên server.
- Phạm vi đã thực hiện: root `docker-compose.yml`, `.env.dokploy.example`, một module bootstrap mới `backendV1/qnu/platform/storage_init.py` cùng unit test, và tài liệu quy trình Dokploy. Không sửa cấu hình đang chạy local, không đổi mã nghiệp vụ, không migration, không re-index.
- Nguyên tắc giữ nguyên: không commit/push/deploy khi chưa được duyệt; không in secret ra log; không thêm dependency mới; không đổi frontend V2 khi chưa có SSO.

## 2. Vấn đề tìm được khi rà cấu hình hiện có

1. **Bucket S3/MinIO chưa được tạo khi server mới.** Adapter `qnu/adapters/storage/s3.py` chỉ đọc/ghi object, không tạo bucket; stack infra (`docker-compose.infra.yml`) dựng MinIO trống. Lần upload đầu trên server mới sẽ lỗi `NoSuchBucket` giữa chừng OCR.
2. **Healthcheck chỉ kiểm tra tiến trình.** Dockerfile kiểm tra `/health/live`; backend có thể "healthy" khi mất PostgreSQL/Redis và stack không dừng lại đúng lúc.
3. **Log container không giới hạn** → nguy cơ đầy đĩa server sau nhiều tuần chạy OCR/worker.
4. **Không có thời gian chờ tắt máy** → deploy/restart có thể cắt ngang job dài (OCR, indexing, model).
5. **`frontendV2` chưa có luồng đăng nhập production** (chỉ có cầu nối auto-login của Vite, tự tắt trong bản build). Build production không có token → mọi API trả 401. Do đó server tiếp tục dùng `frontendV1` có SSO; ghi rõ chặn thay vì dùng mẹo `DEV_AUTH` trên Internet.

## 3. Thay đổi

### 3.1 `backendV1/qnu/platform/storage_init.py` (mới)

- Lệnh một lần `python -m qnu.platform.storage_init`: nếu `STORAGE_DRIVER` không phải `s3` thì thoát 0; nếu bucket tồn tại (`head_bucket`) thì thoát 0; nếu thiếu (`404`/`NoSuchBucket`/`NotFound`) thì `create_bucket`; mọi lỗi khác (`AccessDenied`, lỗi kết nối) in mã lỗi **không kèm secret** và thoát 1 để compose retry/không chạy tiếp.
- Không in access key/secret/URL có thông tin đăng nhập.

### 3.2 `docker-compose.yml`

- Thêm anchor `x-logging` (json-file, 20 MB × 5 tệp) áp cho cả 4 service chạy của backend image và frontend.
- Thêm `init: true` cho container Python để xử lý zombie process.
- **`storage-init`** chạy trước `bootstrap` (`condition: service_completed_successfully`), `restart: "on-failure:5"`, tắt healthcheck.
- **Backend** healthcheck chuyển sang `/health/ready` (PostgreSQL + Redis), `start_period` 30 s; thêm `stop_grace_period: 30s`.
- **Worker** thêm healthcheck `arq --check qnu.workers.settings.WorkerSettings`, `stop_grace_period: 60s`, chờ backend healthy như trước.
- Frontend giữ `expose: 80` cho Dokploy gắn domain, thêm log rotation.

### 3.3 `.env.dokploy.example`

- Ghi chú quyền khóa S3 phải có `HeadBucket`/`CreateBucket` cho `storage-init`.
- Ghi chú chỉ một replica đặt `OWN_RECONCILE=true`.
- Thêm `ANSWER_CACHE_TTL_SECONDS=0` (cache câu trả lời chính xác vẫn tắt trên production).

### 3.4 `docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md`

- Bảng service thêm dòng `storage-init`; bootstrap phụ thuộc nó.
- Mục 7 nêu rõ auto-create bucket và trường hợp AWS S3/khóa bị hạn chế quyền phải tạo bucket trước.
- Thêm mục **Ổn định vận hành**: hướng dẫn khi `storage-init` báo `AccessDenied`, healthcheck readiness, log 20 MB × 5, grace period 30/60 s, một replica `OWN_RECONCILE`, và chặn `frontendV2` chưa có SSO.

### 3.5 `backendV1/Dockerfile`

- Thêm `UV_HTTP_TIMEOUT=120` vào `ENV`. Nguyên nhân trực tiếp: lượt build đầu tiên thất bại tại `uv sync` với `Failed to download docling-core==2.105.0 ... Failed to download distribution due to network timeout. Try increasing UV_HTTP_TIMEOUT (current value: 30s)` — mạng tải gói chậm, không phải lỗi mã. Tăng hạn mức chờ giúp build chịu được mạng chậm của registry/PyPI; không ảnh hưởng runtime.

### 3.6 `backendV1/tests/unit/test_storage_init_957.py` (mới)

- 4 ca: bucket có sẵn không bị tạo lại; bucket thiếu (`NoSuchBucket`) được tạo; `AccessDenied` trả mã 1 và không gọi tạo; `STORAGE_DRIVER=local` bỏ qua boto3 hoàn toàn.
- Dùng `SimpleNamespace`/`monkeypatch`, không gọi mạng thật.

## 4. Kiểm chứng (chỉ ghi kết quả thực chạy)

- `uv run --frozen ruff check` + `ruff format --check` cho 2 tệp mới: **All checks passed / already formatted**.
- `uv run --frozen pytest tests/unit/test_storage_init_957.py -q`: **4 passed** (0,73 s).
- `docker compose --env-file .env.dokploy.example config --quiet`: **OK** (cú pháp/anchor/điều kiện hợp lệ).
- Chạy `storage_init` thật với MinIO local: **`storage-init: bucket ready (qnu-ai-documents)`** (bucket đã có, không tạo lại).
- Xác minh lệnh healthcheck worker: worker local đang chạy với Redis logical DB 0; `arq --check ...` với `REDIS_URL` DB 0 trả **exit 0** kèm sentinel `qnu:v1:jobs:health-check`. Lượt đầu trả exit 1 vì CLI đọc `backendV1/.env` (DB 3) khác môi trường worker local — sai lệch môi trường của máy dev, không phải lỗi lệnh; trong container worker và healthcheck dùng chung `REDIS_URL`.
- **Build image backend+frontend:** lượt đầu **FAIL** tại `uv sync` — `docling-core` tải quá hạn 30 s của uv (`Failed to download distribution due to network timeout`); đã thêm `UV_HTTP_TIMEOUT=120` vào Dockerfile và chạy lại: **FAIL lần 2 do mạng Docker Desktop không phân giải được `auth.docker.io`** (`dial tcp: lookup auth.docker.io: getaddrinfow: This is usually a temporary error during hostname resolution`), base image chưa có cache local nên không thể build offline. **Build trên máy này: NOT RUN được trọn vẹn — không tuyên bố PASS.** Cần chạy lại trên server/mạng ổn định.
- Full backend test suite, E2E live, deploy thật lên Dokploy: **NOT RUN** (`NOT RUN ≠ PASS`).

## 5. Giới hạn và bước tiếp

- `storage-init` chỉ tạo bucket, không tạo policy/user; MinIO phải chạy và khóa phải có quyền tương ứng trước khi deploy.
- Không tự chạy migration/seed: `bootstrap` chỉ `alembic upgrade head`; provider/key/workspace vẫn cấu hình trong ModelOps sau deploy.
- Server cần điền `.env.production` từ mẫu, tạo `dokploy-network`, gắn domain vào service `frontend` cổng 80, đăng ký SSO callback `/signin-oidc` và logout `/sign-in` trước khi demo.
- Chưa commit/push; working tree gồm 6 tệp mã/cấu hình của phiên (compose, env mẫu, Dockerfile, storage_init, test, tài liệu quy trình) cùng 5 tệp tài liệu phiên chờ duyệt.
