# Chuẩn hóa đóng gói Docker và cấu hình Dokploy

## Mục tiêu và phạm vi

Điều chỉnh Docker/Compose theo đề xuất đã được người dùng chấp thuận, giữ kiến trúc hiện tại và không reset DB. Không triển khai server, không migration hay chuyển dữ liệu thật, không sửa xác thực ứng dụng, RAG hoặc provider trong DB.

## Tệp thay đổi

| Tệp | Thay đổi |
| --- | --- |
| `backend/Dockerfile` | Cố định uv/base images bằng digest đã đối chiếu registry; Python 3.12 Bookworm khớp PostgreSQL tools; cài từ `uv.lock` bằng `uv sync --locked --no-dev`, project non-editable; bỏ PyTorch/torchvision ngoài dependency; lỗi apt/font không bị nuốt |
| `frontend/Dockerfile` | Cố định Node/Nginx digest; bắt buộc package-lock và npm ci, không fallback cài phiên bản khác; build args OIDC công khai |
| `.dockerignore`, `frontend/.dockerignore` | Loại storage/backup/tmp/tài liệu gốc và env khỏi build context tương ứng |
| `docker-compose.yml` | Không inject LLM model/API keys từ env; forward SSO cùng API/worker/bootstrap và FE build; dev auth mặc định false/password không bắt buộc; forward danh sách khóa cũ cho rotation có chủ đích; tag runtime khớp image |
| `.env.dokploy.example` | Bỏ biến LLM cũ, hướng dẫn giữ secret/dữ liệu, cấu hình SSO, warning không dùng local gateway URL; không cung cấp secret thật |
| `backend/tests/test_deployment_contract_456.py` | 17 ca contract Docker/Compose thật, gồm thiếu biến bắt buộc; CLI không có thì skip rõ ràng, không mock YAML hay gọi services |
| `docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md` | SOP đúng với stack dùng hạ tầng ngoài; nâng cấp không reset; migration/cửa sổ bảo trì/rollback/auth/network/data transfer |
| `docs/deployment.md` | Local dùng infra Compose, Python/Node/lock phù hợp, phân biệt với production |
| Memory, snapshot, hai mục lục nhật ký | Ghi nhận kết quả và các điều kiện triển khai còn thiếu |

## Cơ chế và quyết định

Build fail-fast khi lockfile không khớp, không âm thầm bỏ qua lỗi hoặc đổi dependency. Lock hiện tại có 109 packages, không yêu cầu torch/torchvision; ứng dụng gọi model qua API. Không sửa pyproject hoặc lock. Digest cố định giúp kiểm soát base image, vẫn cần cập nhật bản vá theo đợt có kiểm chứng. Build isolation của backend có thể lấy build backend theo pyproject, không tuyên bố image bit-for-bit reproducible hoặc toàn bộ supply chain bất biến.

Giữ volume `qnu_platform_storage`, alias `qnu-backend`, endpoint dữ liệu và bootstrap migration/seed. Không tạo reset/drop hoặc mount Docker socket. SSO được chuyển tiếp nhất quán, không đưa secret vào VITE build args. Chính sách production vẫn yêu cầu SSO và chặn mật khẩu dev; chưa có SSO là điều kiện còn thiếu, không phải đã xử lý bằng đổi môi trường development.

Nâng schema khác với chuyển dữ liệu local. Muốn dùng bộ tài liệu mới phải chuyển DB + files/object storage + Qdrant + khóa provider đồng bộ, kiểm tra path Windows sang Linux, và xác nhận thao tác trước. 9router trên PC cần endpoint mạng riêng truy cập được từ server; chưa sửa provider hoặc mở port.

## Kết quả kiểm chứng

- Regression ban đầu sau sửa môi trường tìm plugin Docker của test: **5 failed, 12 passed**, đúng các lỗi dev-default/SSO forwarding/LLM env/lockfile/context. Lần đầu harness thiếu biến hệ thống Windows làm CLI không tìm plugin; đó không phải bằng chứng lỗi ứng dụng và đã sửa trước khi xác nhận regression.
- Sau sửa: **17/17 contract tests đạt** bằng Compose CLI, gồm 11 ca thiếu biến bắt buộc. Không khởi động stack hoặc dùng credentials thật.
- `uv lock --check --offline`: **109 packages, đạt**, lock không thay đổi. Ruff toàn backend đạt, có warnings quyền truy cập thư mục test cũ.
- Build Docker BE và FE: **đạt trên Linux amd64** sau khi người dùng mở lại Docker Desktop. Lần build đầu bị ngắt giữa phiên, lần sau dùng cache và hoàn thành. Không tuyên bố đã kiểm chứng arm64/server Ubuntu thực tế.
- BE image `qnu-deployment-check:456-backend`: ID `sha256:0e2d3177d8d794d6807438d85aa3b856b4b268639f380c61ab7094ed8ded4feb`, size 1.349.836.607 bytes.
- FE image `qnu-deployment-check:456-frontend`: ID `sha256:0951b9572427374c95634181f3f36665d4386691c02af73d3fbdbf1195dab23f`, size 107.515.746 bytes. Size là số Docker inspect, không phải dung lượng tải nén.
- Smoke BE container dùng một lần, network none/no volumes: UID/GID10001, pg_dump/pg_restore16.15, writable storage, không có `.env`, import cv2/FastAPI/asyncpg/Docling/app/worker đạt, không cài torch. Import app có warning Qdrant compatibility do network bị chặn; không startup lifespan hoặc migration. Smoke Settings production với toàn placeholder, network none: dev login disabled và SSO authority được giữ đúng.
- Smoke FE: `nginx -t` đạt trong container không mạng/volume. `npm run build` local đạt Vite5115 modules và TypeScript exit0. FE Docker build cũng đạt.
- Full backend `pytest456_gate.xml`: **1344 passed, 13 failed, 15 skipped, 0 errors**, 257,33s. Đối chiếu tên với `pytest452_gate.xml`: 11 failures trùng baseline; thêm readiness API và versions API lỗi `CannotConnectNowError` lúc PostgreSQL đang startup/recovery sau Docker restart.
- Xác nhận sau DB ổn định: hai API tests trên cùng 17 contract tests đạt **19/19**, artifact `pytest456_confirm.xml`. Không gộp kết quả thành tuyên bố full suite 100% pass, không sửa test nền.
- Compose config --quiet với env mẫu đạt, `git diff --check` đạt. Không commit/push hoặc deploy server.

Các container smoke dùng `--rm` và đã kết thúc; image kiểm chứng giữ trong Docker local. Không dọn image/cache của người dùng.

## Điều kiện còn thiếu trước demo

Người dùng chưa có SSO nên cần quyết định cơ chế demo mật khẩu bắt buộc xác thực hoặc lớp bảo vệ truy cập đầy đủ; phiên này không thay đổi auth. Cần kiểm tra revision DB/server, permission volume cũ, kết nối hạ tầng và AI từ server, nguồn Git đủ bản sửa chưa commit. Chưa restore/copy dữ liệu local, chưa bật lịch backup hoặc đổi model, chưa nghiệm thu server readiness hay chatbot trên server.

## Bài học

Kiểm tra cú pháp Compose không đủ: phải build image, kiểm tra native dependencies và chính sách auth thật. Không dùng reset DB để chữa migration, kết nối AI hoặc đăng nhập. Các hướng dẫn clean code/backend/ModelOps giữ thay đổi ở tầng đóng gói và giữ cấu hình mô hình trong DB.
