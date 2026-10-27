# Hướng dẫn chạy QNU AI Platform V1

Áp dụng cho `backendV1/` và `frontendV1/` trên Windows/PowerShell, đối chiếu mã ngày **27/10/2026**. Thư mục dự án trong các lệnh dưới đây là `D:\DuAnPhanMem\qnu-ai-platform`; thay đường dẫn nếu đặt ở nơi khác.

## 1. Chạy nhanh hằng ngày

Nếu đã cài thư viện, có cấu hình V1 và database đã migration, chỉ cần hạ tầng đang chạy cùng **ba cửa sổ PowerShell**: API, worker và giao diện. Máy mới làm phần 2–5 trước.

| Thành phần | Địa chỉ / vai trò |
| --- | --- |
| Giao diện V1 | <http://127.0.0.1:3001/dashboard> |
| API V1 | <http://127.0.0.1:8002> |
| Tài liệu API | <http://127.0.0.1:8002/docs> |
| Worker V1 | Chạy OCR, Compiler, review, indexing và các job vận hành; không có trang web riêng |

**Chọn một trong hai cách chạy backend dưới đây theo vị trí cấu hình đang dùng.** API và worker phải dùng cùng cách. Backend đọc `.env` theo **thư mục hiện tại**; không tự tìm `.env` ở thư mục cha.

### Cách A — cấu hình đang nằm ở `.env` tại gốc dự án

Giữ thư mục hiện tại ở gốc để giữ cả cách phân giải đường dẫn lưu trữ cũ. `--project` chỉ chọn môi trường Python của V1, không đổi thư mục hiện tại.

Cửa sổ 1 — API:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform
uv run --project .\backendV1 --frozen --extra dev uvicorn qnu.main:app --host 127.0.0.1 --port 8002
```

Cửa sổ 2 — worker:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform
uv run --project .\backendV1 --frozen --extra dev arq qnu.workers.settings.WorkerSettings
```

### Cách B — cấu hình riêng ở `backendV1/.env`

Cửa sổ 1 — API:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv run --frozen --extra dev uvicorn qnu.main:app --host 127.0.0.1 --port 8002
```

Cửa sổ 2 — worker:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv run --frozen --extra dev arq qnu.workers.settings.WorkerSettings
```

### Cửa sổ 3 — giao diện, dùng chung cho cả hai cách

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV1
npm run dev
```

Mở **<http://127.0.0.1:3001/dashboard>**, đăng nhập rồi chọn workspace. Có thể mở thẳng <http://127.0.0.1:3001/workspaces> để tạo hoặc chọn đơn vị.

`run.ps1 dev`, `dev1`, `dev2` và `be` ở gốc hiện vẫn chạy `backend/` và `frontend/` cũ. Dùng các lệnh V1 bên trên. File `backendV1/docker-compose.v1.yml` hiện chưa truyền đủ cấu hình và chia sẻ storage cho toàn luồng; hướng dẫn này dùng API/worker chạy trực tiếp trên máy.

## 2. Chuẩn bị lần đầu

| Cần có | Yêu cầu |
| --- | --- |
| Python và uv | Python **3.12.x**, uv dùng để cài/chạy backend theo `uv.lock` |
| Node.js và npm | Node.js **từ 22.12.0**; dùng `package-lock.json` của FE |
| PostgreSQL | Database và tài khoản đã được cấp; migration V1 tạo bảng trong database đó |
| Redis | Hàng đợi V1; mẫu cấu hình dùng cổng 6379, database Redis số 3 |
| Qdrant | Dùng cho lập chỉ mục và tìm kiếm; mẫu cấu hình dùng cổng 6333 |
| Lưu tệp | Chọn Local storage, hoặc S3/MinIO đã có bucket và quyền truy cập |
| Server AI | Truy cập được endpoint đã đăng ký trong ModelOps khi chạy OCR/Compiler/embedding/hỏi đáp |

Nếu dùng hạ tầng Docker của repo và các dịch vụ **chưa chạy**, mở Docker Desktop rồi chạy từ gốc:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform
docker compose -f .\docker-compose.infra.yml up -d postgres redis qdrant
docker compose -f .\docker-compose.infra.yml ps
```

Compose hạ tầng lấy cấu hình PostgreSQL từ `.env` ở gốc hoặc biến môi trường. Kiểm tra tài khoản/database được cấp thay vì đoán mật khẩu. Nếu dịch vụ đã chạy ở máy/server khác, dùng địa chỉ thực tế trong cấu hình backend và bỏ bước khởi động Docker.

Với `STORAGE_DRIVER=s3`, cần thêm MinIO hoặc S3 đang hoạt động. Nếu dùng MinIO của repo:

```powershell
docker compose -f .\docker-compose.infra.yml up -d minio
```

Chuẩn bị bucket đúng `S3_BUCKET` và credential có quyền đọc/ghi. Với `STORAGE_DRIVER=local` không cần MinIO. V1 hiện render PDF/DOCX bằng PyMuPDF; luồng này không cần Gotenberg.

Cài thư viện một lần, hoặc khi lockfile thay đổi:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv sync --extra dev --frozen

Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV1
npm ci --ignore-scripts --no-audit --no-fund
```

## 3. Cấu hình backend

**Môi trường đã có dữ liệu:** giữ database, khóa mã hóa và vị trí storage đang dùng. Không ghi đè `.env` hoặc đổi thư mục chạy tùy ý. Ví dụ `LOCAL_STORAGE_PATH=./storage` trỏ tới hai nơi khác nhau khi chạy từ gốc và từ `backendV1/`; nếu chuyển cách chạy, đặt đường dẫn tuyệt đối tới **đúng thư mục cũ** cho cả API và worker.

**Cài V1 mới với cấu hình riêng:** chỉ tạo tệp nếu chưa có:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Sửa `backendV1/.env` trên máy, thay các giá trị mẫu:

| Biến | Cách đặt |
| --- | --- |
| `ENVIRONMENT` | `development` khi chạy local |
| `DATABASE_URL` | Đúng database/tài khoản được cấp, dạng `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE`; URL-encode ký tự đặc biệt trong user/password |
| `REDIS_URL` | Ví dụ `redis://127.0.0.1:6379/3`; API và worker giống nhau |
| `QUEUE_NAME` | `qnu:v1:jobs`; giữ riêng với queue legacy |
| `CACHE_NAMESPACE` | `qnu:v1:cache:` |
| `STORAGE_DRIVER` | `local` để lưu trực tiếp; `s3` để dùng object storage |
| `LOCAL_STORAGE_PATH` | Thư mục bền vững, có quyền đọc/ghi; ưu tiên đường dẫn tuyệt đối khi nhiều cách chạy |
| `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_SECURE` | Điền theo hạ tầng nếu dùng `s3` |
| `QDRANT_URL` | Ví dụ `http://127.0.0.1:6333` |
| `SECRET_KEY` | Khóa ký ngẫu nhiên, tối thiểu **32 byte**; giữ ổn định giữa API/worker và các lần chạy |
| `PROVIDER_ENCRYPTION_KEY` | Khóa bảo vệ credential ModelOps; tạo ngẫu nhiên cho môi trường mới, giữ nguyên nếu DB đã có credential |
| `DEV_AUTH_ENABLED` | `true` để dùng admin dev local |
| `DEV_ACCESS_PASSWORD` | Mật khẩu truy cập dev do bạn đặt, không để trống |
| `SSO_ENABLED` | `false` nếu hiện dùng admin dev; bật và cấu hình SSO riêng khi chuyển sang đăng nhập thật |
| `API_PREFIX` | Giữ `/platform/v1alpha1` để khớp FE hiện tại |
| `ALLOWED_ORIGINS` | Nếu gọi API trực tiếp từ FE, gồm origin đang dùng, ví dụ `http://127.0.0.1:3001,http://localhost:3001` |
| `OCR_DISPATCH_ENABLED`, `OWN_RECONCILE` | `true` để giao job và phục hồi job V1 theo cấu hình hiện có |

Biến môi trường đã đặt trong cửa sổ PowerShell có ưu tiên hơn `.env`; nếu cấu hình không khớp, kiểm tra cả hai nơi mà không đưa giá trị bí mật vào log/chụp màn hình.

Credential LLM/server AI nhập tại **ModelOps → provider → credential**. Không đặt API key model vào `.env` hoặc biến `VITE_*`. `PROVIDER_ENCRYPTION_KEY` là khóa mã hóa của ứng dụng, khác API key provider; mất hoặc thay sai khóa này sẽ không đọc được credential đã lưu.

## 4. Chuẩn bị database và migration

Thực hiện lần đầu hoặc khi có migration mới, trước khi khởi động API/worker. Database phải tồn tại; Alembic tạo/cập nhật bảng, không tạo database PostgreSQL.

Nếu dùng database V1 mới, có thể tạo qua công cụ quản trị PostgreSQL. Ví dụ với `psql` đã cài và role `qnu` đã được cấp quyền tạo database:

```powershell
psql --host 127.0.0.1 --port 5432 --username qnu --dbname postgres --password --command 'CREATE DATABASE qnu_backend_v1;'
```

Đổi role/host theo môi trường và nhập mật khẩu khi được hỏi. Sau đó đặt `DATABASE_URL` trỏ tới database vừa tạo. Môi trường dùng chung database đã tồn tại thì bỏ bước tạo mới.

Với **cách B** ở phần 1:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv run --frozen --extra dev alembic current
uv run --frozen --extra dev alembic upgrade head
uv run --frozen --extra dev alembic current
```

Với **cách A** dùng `.env` ở gốc, migration vẫn chạy từ `backendV1/` để đúng `alembic.ini`, nhưng nạp tệp cấu hình ở gốc một cách tường minh:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv run --frozen --extra dev --env-file ..\.env alembic current
uv run --frozen --extra dev --env-file ..\.env alembic upgrade head
uv run --frozen --extra dev --env-file ..\.env alembic current
```

Chỉ chạy `upgrade` sau khi xác nhận đúng database cần nâng cấp và có bản sao lưu nếu đã có dữ liệu. Head hiện tại là **`0003_rag_policy_metadata`**, gồm baseline `0001_initial_schema` và `0002_operational_readiness`. Bảng quản lý revision V1 là `alembic_version_backendv1`.

Nếu báo không tìm thấy revision phát triển cũ, xem [hướng dẫn migration](../../backendV1/docs/migrations.md). Cần chuyển tiếp schema/dữ liệu theo hiện trạng; không dùng `stamp head`, xóa database hoặc `run.ps1 reset-db` để vượt lỗi. CLI `qnu.cli.main` hiện là khung, chưa thực hiện migrate/preflight; dùng Alembic như trên.

## 5. Cấu hình FE và tự đăng nhập admin local

Tạo tệp riêng nếu chưa có:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV1
if (-not (Test-Path -LiteralPath .env.local)) {
    Copy-Item -LiteralPath .env.example -Destination .env.local
}
```

Trong `frontendV1/.env.local`, đặt:

```dotenv
FRONTEND_PORT=3001
QNU_API_PROXY_TARGET=http://127.0.0.1:8002
VITE_QNU_API_BASE_URL=
VITE_DEV_AUTH_ENABLED=true
QNU_DEV_AUTO_LOGIN=true
QNU_DEV_ACCESS_KEY=<điền đúng DEV_ACCESS_PASSWORD của backend V1>
```

Dòng `<...>` là chỗ điền giá trị riêng trên máy, không để nguyên dấu ngoặc. Giữ `VITE_QNU_API_BASE_URL` trống để FE gọi API qua proxy Vite. Các lệnh ở phần 1 cố định cổng API là 8002; muốn đổi cổng cần đổi cả lệnh API và `QNU_API_PROXY_TARGET`.

Khi mở trang V1, cầu nối local lấy token admin **`dev.admin`**, quyền `AI.Admin`; không cần tạo tài khoản hay seed admin trong database. Access key do tiến trình Vite đọc, không nhúng vào bundle; token vẫn được backend xác minh.

Nếu không muốn tự đăng nhập, đặt `QNU_DEV_AUTO_LOGIN=false`, mở <http://127.0.0.1:3001/sign-in> rồi nhập access key dev. Sau khi bấm đăng xuất, tự đăng nhập bị chặn trong phiên tab; dùng nút **Tự đăng nhập bằng cấu hình local** / **Thử lại** để bật lại rõ ràng.

Cơ chế này chỉ dùng cho local development, API đích và trình duyệt phải qua loopback. Build/preview không có cầu nối tự đăng nhập. Khi đổi tệp môi trường, nạp lại đúng tiến trình API/worker/FE liên quan. Production cần tắt dev auth và cấu hình SSO; hướng dẫn này chưa phải quy trình triển khai production.

## 6. Kiểm tra sau khi mở ứng dụng

Mở cửa sổ PowerShell khác:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8002/health/live
Invoke-RestMethod -Uri http://127.0.0.1:8002/health/ready
```

`/health/live` xác nhận API còn phản hồi; `/health/ready` kiểm kết nối PostgreSQL và Redis, trả 503 nếu thiếu một trong hai. Hai kết quả này chưa chứng minh migration, worker, Qdrant hay model hoạt động đầy đủ.

Sau đăng nhập, mở workspace → **Vận hành** → kiểm tra sẵn sàng bằng tài khoản admin. Màn này kiểm thêm schema, queue/worker, Qdrant, cấu hình model/quota và đọc tệp nguồn. Workspace mới chưa có nguồn có thể báo `no_source_to_probe`; upload một tài liệu rồi kiểm tra lại. Readiness không tự chạy inference model và không chứng nhận chất lượng câu trả lời.

## 7. Thiết lập ModelOps cho workspace mới

Bỏ qua các bước đã cấu hình đúng; không tạo lại provider/key khi chỉ khởi động lại ứng dụng.

1. Vào **Workspaces**, tạo/chọn đơn vị. Workspace là biên giới quyền trong V1; mọi yêu cầu vẫn được server kiểm quyền.
2. Vào **ModelOps → Providers**, thêm provider theo endpoint/model thực tế, capability và credential. Hiện một bản ghi provider gắn một `model_name`; nếu server phục vụ nhiều model, tạo các bản ghi tương ứng.
3. Khai báo capacity/input/output theo model và server đang dùng. Embedding cần `embedding_dimension`; OCR cần accounting ảnh/trang phù hợp. Không suy capacity từ tên model hoặc điền số giả để vượt kiểm tra. Xem [capacity ModelOps](../../backendV1/docs/model-capacity.md).
4. Tại workspace, cấp danh sách provider được phép, rồi chọn default **OCR**, **chat**, **embedding**, và **rerank** nếu dùng. Default toàn hệ thống không thay thế bước cấp quyền cho workspace.
5. Cấu hình **quota tháng hiện tại theo UTC** cho workspace. Thiếu bản ghi quota sẽ chặn inference; unlimited chỉ có hiệu lực khi được lưu tường minh, không phải khi bỏ qua cấu hình. Sang tháng cần cấu hình kỳ mới.

Các vai trò model trong luồng hiện tại:

| Vai trò | Dùng ở đâu | Model đã tham khảo trong phiên làm việc |
| --- | --- | --- |
| OCR | Đọc ảnh trang PDF/DOCX | `nemotron-parse` |
| Chat | Compiler, review, gợi ý chính tả, trả lời | `qwen3.5-9b` hoặc model chat được cấp qua ModelOps |
| Embedding | Lập chỉ mục và tìm kiếm | `bge-m3` |
| Rerank | Xếp lại ứng viên khi bật rerank | `bge-reranker-v2-m3` |

Tên trên dùng để nhận diện cấu hình từng trao đổi, không phải cấu hình tự nạp hoặc cam kết model hiện đang sẵn sàng. Endpoint/credential/capacity lấy từ cấu hình ModelOps thực tế; danh sách `/v1/models` chưa đủ chứng minh các API OCR/embedding/rerank hoạt động.

## 8. Dùng thử một tài liệu từ đầu đến hỏi đáp

1. Trong workspace, tạo **kho tri thức**, tải một PDF/DOCX nhỏ. Xác nhận có revision và tải lại được nguồn.
2. Yêu cầu **OCR/xử lý** và theo dõi job; worker phải đang chạy. Đọc kết quả Markdown/JSON và trang nguồn sau khi hoàn tất.
3. Nếu cần, chọn đoạn/ô để kiểm tra chính tả, xem gợi ý rồi áp dụng hoặc sửa tay và lưu. Bản sửa cập nhật Markdown/JSON dẫn xuất theo phiên bản; nguồn và raw OCR vẫn giữ.
4. Chạy **Compiler**, chọn đúng revision/bản văn bản cần dùng. Chờ biên soạn và review; xem finding, đối chiếu nguồn và sửa nếu cần.
5. Con người xác nhận review, giải trình các finding cần xử lý, duyệt rồi xuất bản. Job completed chưa đồng nghĩa đã được duyệt/xuất bản.
6. Tạo **index** cho bản đang xuất bản và chờ hoàn tất. Có thể xem snapshot/generation tại phần lập chỉ mục.
7. Mở **Tìm kiếm** hoặc **Hỏi đáp thử** trong kho, đặt phạm vi năm/tài liệu khi cần; xem nguồn trích dẫn để đối chiếu.
8. Muốn trò chuyện có lịch sử: tạo **trợ lý**, gắn kho/model phù hợp và mở hội thoại. Hỏi đáp thử theo kho là một yêu cầu độc lập, không tự lưu lịch sử hội thoại.

Để thay/xóa dữ liệu hoặc tạm dừng trợ lý, dùng thao tác vòng đời có preview/xác nhận trong giao diện. Xem [vòng đời ngược](31_vong_doi_nguoc_backendv1.md) và [hướng dẫn FE vận hành](34_frontend_vong_doi_thay_the_va_van_hanh.md). `/reference-dashboard` và các màn KTX còn lại là giao diện mẫu, không dùng để đánh giá chức năng QNU V1.

## 9. Lỗi thường gặp

| Hiện tượng | Kiểm tra / cách xử lý |
| --- | --- |
| Không mở được cổng 8002 hoặc FE báo không kết nối | Xem cửa sổ API có chạy `qnu.main:app` hay không; kiểm tra cổng và `QNU_API_PROXY_TARGET` |
| Vite báo cổng 3001 đã dùng | Dừng đúng tiến trình đang chiếm cổng nếu không còn dùng, hoặc đổi `FRONTEND_PORT`; Vite hiện không tự nhảy cổng |
| PostgreSQL báo sai mật khẩu hoặc dùng tên tài khoản Windows | Kiểm tra thư mục chạy, `.env` thực sự được nạp và `DATABASE_URL`; không lấy mặc định làm cấu hình môi trường |
| Thiếu bảng/revision hoặc readiness báo schema sai | Chạy `alembic current` đúng môi trường; đối chiếu phần 4 trước khi nâng cấp |
| `SIGNING_KEY_MISSING`, `invalid_credentials`, `dev_gate_disabled` | Kiểm tra khóa ký ≥32 byte, dev gate, môi trường development và hai giá trị mật khẩu dev khớp nhau |
| Tự đăng nhập không hoạt động | Dùng `npm run dev`, URL loopback và kiểm tra `.env.local`; build/preview không có cầu nối; sau logout dùng nút đăng nhập lại |
| `ENCRYPTION_KEY_MISSING` / `DECRYPT_FAILED` | Kiểm tra API và worker dùng đúng khóa mã hóa đã bảo vệ credential trong DB; không thay khóa tùy ý |
| OCR/Compiler/index đứng `queued` | Xem cửa sổ worker, Redis URL, queue `qnu:v1:jobs`, database và cờ dispatch/reconcile của API/worker có khớp; xem chi tiết job ở Vận hành |
| `quota_not_configured` / `quota_exceeded` | Cấu hình quota đúng tháng UTC hoặc kiểm tra usage/reservation; không giả định tháng trước còn hiệu lực |
| Capacity thiếu/stale, `model_input_budget_unknown` | Kiểm tra lại capacity và OCR image accounting sau khi đổi endpoint/model; không tăng token môi trường để bỏ qua kiểm tra |
| Provider trả 401/403, ví dụ `embedding_auth_failed` | Kiểm tra credential đang active ở ModelOps và quyền trên server AI; không biến lỗi provider thành “không có dữ liệu” |
| Upload đọc được ở API nhưng worker báo thiếu tệp | Hai tiến trình phải dùng cùng storage driver và cùng đường dẫn tuyệt đối/bucket; kiểm tra khác thư mục hiện tại |
| Tìm kiếm/hỏi đáp chưa có nguồn | Kiểm tra tài liệu đã duyệt, xuất bản, index hoàn tất và scope đang chọn; upload/OCR xong chưa tự đưa dữ liệu vào trả lời |
| Bấm tác vụ xong mất kết nối, trạng thái `uncertain` | Mở lại chi tiết job/biên nhận để đối soát trước khi gửi mới; không bấm lặp để ép chạy lại |

## 10. Dừng và chạy lại

Chờ các job đang xử lý kết thúc nếu có thể, rồi nhấn **Ctrl+C** tại từng cửa sổ FE/API/worker đã mở. Việc dừng tiến trình không xóa dữ liệu; trạng thái job gián đoạn cần kiểm lại ở Vận hành khi chạy tiếp. Không tự gửi lại inference chưa rõ kết quả.

PostgreSQL, Redis, Qdrant, MinIO có thể đang dùng chung với bản cũ: giữ chúng chạy nếu còn ứng dụng sử dụng. Lần sau dùng lại phần 1; không cần seed/reset database, migration lại hằng ngày hoặc nạp lại tài liệu.

Nếu cần phục hồi toàn bộ từ backup, dùng [runbook recovery](../../backendV1/docs/recovery.md) vào đích mới. Hiện thao tác full restore chưa có giao diện web.

## Nguồn đối chiếu và phạm vi kiểm tra

- [Backend README](../../backendV1/README.md), [pyproject](../../backendV1/pyproject.toml), [Settings](../../backendV1/qnu/platform/config.py), [worker](../../backendV1/qnu/workers/settings.py), [health](../../backendV1/qnu/api/health.py).
- [FE package](../../frontendV1/package.json), [Vite config](../../frontendV1/vite.config.ts), [môi trường mẫu FE](../../frontendV1/.env.example), [cầu nối admin local](../../frontendV1/dev/dev-auto-login.ts).
- [Môi trường mẫu BE](../../backendV1/.env.example), [migration](../../backendV1/docs/migrations.md), [quyền workspace/ModelOps](../../backendV1/docs/workspaces-modelops.md), [readiness](../../backendV1/docs/readiness.md).

Tài liệu được kiểm tra tĩnh với mã/cấu hình hiện tại và liên kết nội bộ. Lượt viết hướng dẫn này không khởi động dịch vụ, áp migration hay gọi model thật; các lệnh thiết lập/chạy ở trên dành cho người vận hành thực hiện trên môi trường đã chọn.
