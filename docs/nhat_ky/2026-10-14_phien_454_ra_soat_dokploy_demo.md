# Rà soát triển khai demo trên Dokploy

## Mục tiêu và lựa chọn

Người dùng muốn demo trên server web đang có bản cũ. Bản demo cần dữ liệu mới nhất từ máy local, đăng nhập bằng mật khẩu (chưa có SSO), và kết nối 9router vẫn chạy trên máy cá nhân. Phiên này chỉ rà soát và đề xuất; chưa thay đổi cấu hình hay triển khai.

## Kết quả rà soát

- `docker-compose.yml` có bootstrap, backend, worker, frontend; PostgreSQL, Redis, Qdrant, MinIO và Gotenberg là dịch vụ ngoài trên `dokploy-network`. Bootstrap migration và seed trước API/worker; `AUTO_SEED=false` trong ảnh không vô hiệu hóa bootstrap.
- Production không cho phép Dev Access Gate. Validator có thể tự tắt cờ dev với SSO authority mặc định, hoặc báo lỗi khi authority đã cấu hình; endpoint login bằng mật khẩu luôn bị chặn ở production. Compose chưa chuyển tiếp các biến SSO từ Environment vào backend/worker/bootstrap.
- Không mở công khai bằng cách đổi ENVIRONMENT sang development: `get_current_actor` có nhánh trả default admin khi không có token và không có header enforce auth. Cần cơ chế demo bắt buộc xác thực hoặc lớp bảo vệ truy cập bên ngoài; không nới chính sách production.
- `.env.dokploy.example` và SOP Dokploy còn biến LLM/model cũ và chỉ dẫn không khớp stack hiện tại. Credential/model phải do ModelOps DB quản lý; cần cấu hình origin chính xác thay wildcard.
- Dữ liệu local không tự đi theo image. Muốn tái hiện chatbot cần chuyển đồng bộ PostgreSQL, file/object storage, Qdrant và khóa giải mã provider tương ứng, kiểm tra đường dẫn local Windows trước khi chuyển Linux. Chỉ chuyển DB là không đủ. Chưa thực hiện restore hoặc di chuyển dữ liệu.
- `localhost:20128` trong container không phải máy cá nhân. Đề xuất kết nối 9router qua mạng riêng như Tailscale, kiểm tra bind/firewall/API key và khả năng truy cập từ container; không mở gateway không bảo vệ ra Internet. Embedding/reranker trên AI server cũng cần tuyến truy cập.
- Nếu tạo demo song song, volume cố định `qnu_platform_storage`, alias `qnu-backend` và backend image tag cần tách để tránh trùng bản cũ. Không dùng nguyên Compose để tạo hai stack độc lập mà chưa xử lý các tên này.
- Có thay đổi runtime chưa commit và file hierarchy/historical chưa được Git theo dõi ở thời điểm rà soát. Deploy từ repository phải có đầy đủ bản code đã kiểm tra; không tự commit/push.
- Dockerfile backend cài dependency bằng `uv pip ... -r pyproject.toml`, chưa dùng lock để cố định toàn bộ dependency. Build server có thể lệch bản local; cần kiểm chứng image trước demo.

## Kiểm tra và giới hạn

`docker compose --env-file .env.dokploy.example -f docker-compose.yml config --quiet` đạt trên Compose v5.5.1. Đây chỉ là kiểm tra cú pháp/interpolation với placeholder, không xác nhận credential, build image, mạng hay đăng nhập server. Không chạy Ruff/Pytest/Vite vì không sửa runtime. Không đọc secrets thật, không thay đổi DB, model, publication, dịch vụ, backup hoặc server Dokploy.

Dokploy có thể cấu hình domain tại tab Domains và tự thêm routing; với frontend Nginx hiện tại chọn service `frontend`, container port `80`, HTTPS. Nguồn: [Dokploy Domains](https://docs.dokploy.com/docs/core/docker-compose/domains). Cần xác nhận thực tế tên miền demo và tài nguyên server.

## Hướng xử lý đề xuất

Chuẩn bị bản demo tách biệt với dữ liệu cũ; chọn cơ chế xác thực an toàn cho mật khẩu demo; chuẩn hóa Compose/environment/build; kết nối riêng tới 9router/AI server; lập kế hoạch chuyển dữ liệu đầy đủ và đối soát trước khi demo. Chưa có xác nhận triển khai các thay đổi này.

## Tệp thay đổi và bài học

Chỉ thêm nhật ký này và cập nhật ba mục lục/bộ nhớ bắt buộc. Không sửa Compose/Dockerfile/runtime. Một Compose hợp lệ không chứng minh ứng dụng đã sẵn sàng demo; xác thực, dữ liệu và kết nối AI cần được kiểm tra riêng.
