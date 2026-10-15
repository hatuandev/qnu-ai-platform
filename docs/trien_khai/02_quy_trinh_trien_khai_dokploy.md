# Triển khai và nâng cấp trên Dokploy

Stack hiện tại triển khai ứng dụng lên hạ tầng Dokploy đã có. Nâng cấp code không yêu cầu reset DB. Việc đưa dữ liệu mới nhất từ máy cá nhân lên server là một tác vụ chuyển dữ liệu riêng, không diễn ra tự động khi build hoặc migration.

## 1. Kiến trúc và điều kiện triển khai

`docker-compose.yml` ở gốc repository có bốn dịch vụ:

| Dịch vụ | Chức năng | Điều kiện khởi động |
| --- | --- | --- |
| `bootstrap` | Chờ PostgreSQL, khóa bootstrap, migration lên head, seed và kiểm tra | Hạ tầng có sẵn và credential hợp lệ |
| `backend` | API cổng nội bộ 8001 | Bootstrap kết thúc thành công |
| `worker` | Xử lý ARQ | Bootstrap kết thúc thành công |
| `frontend` | React đã build, Nginx cổng nội bộ 80, proxy API | Backend healthy |

PostgreSQL, Redis, Qdrant, MinIO và Gotenberg **không được tạo bởi Compose ứng dụng**. Chuẩn bị các dịch vụ này trước và bảo đảm container ứng dụng kết nối được qua `dokploy-network` hoặc tuyến mạng được cấp quyền. Không dùng `docker-compose.infra.yml` để thay hạ tầng server đang có; file đó phục vụ local development.

Compose cần chế độ Docker Compose hỗ trợ build và `service_completed_successfully`, không phải Docker Stack/Swarm. Nguồn Git phải có đủ Dockerfile, lockfile, `backend/app`, migrations, `configs` và mã FE. Dán riêng Raw Compose mà không có build context không đủ để build ứng dụng.

## 2. Chuẩn bị trước khi nâng cấp

1. Ghi lại commit đang chạy, phiên bản PostgreSQL/Qdrant và Alembic revision của DB server. Có thể đọc `alembic_version` trên DB hoặc chạy `alembic current` trong container hiện tại nếu container có cấu hình tương ứng.
2. Sao lưu đồng bộ PostgreSQL, MinIO/files và Qdrant; giữ khóa `PROVIDER_ENCRYPTION_KEY` tương ứng ở nơi riêng an toàn. Không dán khóa vào báo cáo hoặc chat.
3. Giữ nguyên các đích dữ liệu: `DATABASE_URL`, bucket, collection và named volume `qnu_platform_storage`. Kiểm tra volume cũ cho phép UID/GID `10001:10001` ghi tại `/app/storage`; không đổi quyền đệ quy trên thư mục chưa xác minh.
4. Nếu server cách nhiều phiên bản, kiểm tra các migration pending trên bản sao trước. Có migration dọn provider local đã ngừng hỗ trợ và facts mồ côi, không phải mọi migration chỉ thêm bảng. Chỉ migration chưa áp dụng mới chạy.
5. Đặt cửa sổ bảo trì khi nâng schema không tương thích: ngừng nhận yêu cầu và dừng API/worker cũ trước khi bootstrap mới thay đổi schema. `depends_on` chỉ bảo đảm thứ tự khởi động, không tự drain bản cũ.
6. Gán `APP_IMAGE_TAG` theo bản phát hành để nhận diện image và rollback. Không ghi đè image đang chạy nếu cần giữ khả năng quay lại bản cũ.

Không reset DB, không `down -v`, không xóa bucket/Qdrant, không `alembic stamp head` để bỏ qua migration lỗi. Rollback image sau khi schema đã thay đổi cần kiểm tra tương thích; không giả định chỉ chạy image cũ là đủ.

## 3. Cấu hình Environment

Dùng [mẫu Environment](../../.env.dokploy.example) làm danh sách biến cần kiểm tra. Với bản đang chạy, cập nhật từng mục, **không chép placeholder đè lên secret hoặc địa chỉ dữ liệu thật**.

- Khai báo `DATABASE_URL` chuẩn asyncpg, URL-encode phần username/password nếu cần. Compose yêu cầu biến này; chỉ đặt `CONNECTION_STRING` không đáp ứng điều kiện Compose hiện tại.
- Điền Redis, Qdrant, MinIO, Gotenberg theo kết nối server thực tế; `S3_SECURE` phù hợp HTTP/HTTPS.
- `ALLOWED_ORIGINS` là danh sách origin HTTPS được phép, không dùng wildcard cho bản public có xác thực.
- Giữ nguyên `SECRET_KEY`, `PROVIDER_ENCRYPTION_KEY`, `INTERNAL_API_KEY` của bản cài đặt khi nâng cấp. Rotation là quy trình riêng; `OLD_PROVIDER_ENCRYPTION_KEYS` mặc định `[]`.
- Chat/OCR/embedding/reranker, endpoint và API key được quản lý qua `/models` trong PostgreSQL, không qua biến LLM trong Environment. Compose không chuyển tiếp các biến model/key LLM cũ.
- `AUTO_SEED=false` không tắt bootstrap. Bootstrap vẫn migration và seed idempotent; kiểm tra log và dữ liệu trên bản sao khi nâng từ bản cũ.

### Đăng nhập

Production dùng SSO: `DEV_AUTH_ENABLED=false`, `SSO_ENABLED=true`, cùng authority/client/audience thực tế. Đăng ký redirect URI đầy đủ tại SSO, ví dụ `https://TEN_MIEN_DEMO/signin-oidc` và logout `https://TEN_MIEN_DEMO/sign-in`.

Compose chuyển cấu hình SSO vào bootstrap/BE/worker và chuyển cấu hình OIDC công khai vào bước build FE. Đổi cấu hình OIDC yêu cầu build lại FE; không truyền password, client secret hoặc API key vào `VITE_*`.

**Chưa có SSO thì chưa thể nghiệm thu đăng nhập production bằng bản cấu hình này.** Mật khẩu Dev Access Gate cũ không dùng được ở production. Không đổi `ENVIRONMENT=development` rồi mở Internet để né điều kiện này: chế độ development có nhánh default actor dành cho local. Muốn demo mật khẩu cần thiết kế xác thực bắt buộc riêng hoặc bảo vệ toàn bộ truy cập qua lớp kiểm soát bên ngoài đã được xác nhận; phiên chỉnh Docker không thay đổi cơ chế đăng nhập ứng dụng.

### Kết nối 9router và server AI

`localhost:20128` trong container là chính container, không phải máy cá nhân. Nếu 9router tiếp tục chạy trên máy cá nhân, dùng địa chỉ mạng riêng mà server có thể truy cập, ví dụ Tailscale, kiểm tra listener/firewall/API key rồi sửa base URL trong `/models`. Không công khai gateway không bảo vệ ra Internet.

Tương tự, kiểm tra kết nối từ BE và worker tới embedding/reranker/OCR trên server AI. Không đổi model embedding của kho chỉ để thay địa chỉ mạng.

## 4. Build và routing

Trong Dokploy chọn repository và commit đã kiểm tra, build context gốc repository, đường dẫn `docker-compose.yml`. Trước Deploy, kiểm tra Preview Compose và cấu hình Environment.

Lệnh kiểm tra tương đương ở checkout server:

```bash
docker compose --env-file /DUONG_DAN_ENV_RIENG -f docker-compose.yml config --quiet
docker compose --env-file /DUONG_DAN_ENV_RIENG -f docker-compose.yml build bootstrap backend worker frontend
```

`config --quiet` chỉ kiểm tra cú pháp và biến bắt buộc; không chứng minh credential hoặc mạng hợp lệ. Không xuất toàn bộ `docker compose config` vào log vì có thể chứa secret.

BE dùng Python 3.12 và uv cố định, `uv sync --locked --no-dev`, không cài runtime model local/PyTorch ngoài lock. FE dùng `npm ci` và build/typecheck. Base images cố định bằng digest; cập nhật digest có kiểm chứng để nhận bản vá bảo mật, không giữ bất biến vô thời hạn. Root build context loại `backend/storage`, backup, tmp, tài liệu gốc và `.env*`; dữ liệu không được chuyển theo image.

Trong tab Domains, trỏ tên miền HTTPS tới service **`frontend`**, container port **`80`**. Nginx tự proxy `/platform/` và health tới backend nội bộ; không cần mở cổng DB, 8001 hoặc Redis ra Internet. Xác nhận các dịch vụ ngoài ở đúng network trước khi Deploy.

Volume `qnu_platform_storage` và alias `qnu-backend` giữ tương thích bản hiện tại. Nếu chủ động tạo hai stack song song trên cùng network thì phải thiết kế tách image tag/volume/alias và proxy đích; không copy nguyên stack rồi mặc định hai bản độc lập.

## 5. Deploy và kiểm tra

Sau bảo trì và sao lưu, Deploy trên Dokploy, theo dõi theo thứ tự:

1. Bootstrap kết thúc với exit 0 và log `Production bootstrap completed successfully`. Bootstrap là tác vụ một lần, trạng thái exited thành công là bình thường.
2. Backend healthy; `python -m app.cli db check` trong backend xác nhận schema. Không chạy migration song song với bootstrap.
3. Worker healthcheck thành công, không có lỗi credential/decrypt/bucket hoặc kết nối broker.
4. Frontend HTTPS trả giao diện; deep link vẫn mở được khi F5. Kiểm tra `/health/live` và `/health/ready` qua cùng tên miền; health chưa chứng minh chất lượng RAG.
5. Kiểm tra chưa đăng nhập bị từ chối trên API được bảo vệ, đăng nhập SSO thành công, quyền tài khoản đúng.
6. Kiểm tra `/models`, nguồn đã xuất bản, citation mở được tài liệu, hỏi một câu có nguồn và một câu thiếu nguồn. Xem model thực tế/fallback và lỗi timeout, không chỉ dựa vào HTTP 200.

Nếu bootstrap lỗi, giữ log đã loại secrets và xác định migration cụ thể; không reset DB để vượt lỗi. Nếu mạng AI lỗi, sửa tuyến mạng/cấu hình provider, không đổi schema hay xóa vector.

## 6. Chuyển dữ liệu local để demo

Migration chỉ nâng cấu trúc DB server, không lấy dữ liệu từ máy cá nhân. Muốn tái hiện dữ liệu local cần kế hoạch chuyển đồng bộ DB, file/object storage, Qdrant và khóa provider; đối soát snapshot và đường dẫn Windows khi sang Linux. Không restore riêng DB đè lên server rồi dùng bucket/vector cũ không tương ứng. Việc restore dữ liệu server cần được xác nhận riêng trước khi thực hiện.

## Tham khảo

[Dokploy Compose](https://docs.dokploy.com/docs/core/docker-compose), [Dokploy Domains](https://docs.dokploy.com/docs/core/docker-compose/domains), [uv Docker](https://docs.astral.sh/uv/guides/integration/docker/).
