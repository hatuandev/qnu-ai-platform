# Hướng dẫn chạy QNU AI Platform V1

Hướng dẫn các lệnh `v1-*`/`v2-*` cho Backend V1 và Frontend V2 trên Windows. `dev` và `dev2` chạy Backend V1, worker V1 và Frontend V2 ở cổng 3002; `v1-dev` chỉ chạy API và worker. FrontendV1 đã được gỡ khỏi checkout. Thư mục dự án trong các lệnh dưới đây là `D:\DuAnPhanMem\qnu-ai-platform`.

## 1. Chạy nhanh hằng ngày

**Cập nhật 29/10/2026:** worker hiện có nhận thêm `source_purge_job` để xóa vĩnh
viễn tài liệu nguồn đã xác nhận và không còn bản phát hành. Không cần migration
riêng cho thay đổi này; sau khi cập nhật mã, dừng/chạy lại `v1-dev` để API/worker
nạp hàm mới. Không có thao tác tự xóa dữ liệu khi khởi động. Tác vụ lỗi giữ biên
nhận chờ và được reconciler gửi lại; MinIO/S3 cần quyền xóa cả object version.

Nếu đã cài thư viện, có cấu hình V1 và database đã migration, chỉ cần hạ tầng đang chạy cùng **ba cửa sổ PowerShell**: API, worker và giao diện. Máy mới làm phần 2–5 trước.

### Chạy bằng Make — cách gọn nhất

Từ gốc dự án, dùng GNU Make hoặc `make.bat` trên CMD:

```text
make v1-help          # Xem các lệnh V1
make v1-infra-up      # PostgreSQL + Redis + Qdrant + MinIO + Gotenberg; chuẩn bị bucket local
make v1-check         # Kiểm tra kết nối, schema và dependency FE V2
make v1-dev           # Chạy API + worker trong cùng phiên (không FE)
make v1-be            # Hoặc chạy riêng API
make v1-worker        # Hoặc chạy riêng worker
make v2-fe            # Hoặc chạy riêng Frontend V2
```

Trong PowerShell, không cần cài GNU Make, dùng runner có sẵn:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform
.\make.ps1 v1-dev
```

`v1-dev` giữ tiến trình ở cửa sổ hiện tại, log API và worker hiển thị cùng nhau;
**Ctrl+C** dừng các tiến trình con của phiên này. Một thành phần thoát thì thành
phần còn lại cũng dừng và trả mã lỗi. Lệnh không tự restart phiên cũ; nếu đang
có dịch vụ V1 thì dùng lại hoặc dừng đúng phiên đó trước khi mở mới. Muốn có
giao diện, chạy `dev` (API + worker + FE V2) hoặc `v2-fe` ở cửa sổ riêng.

Trước khi mở ba thành phần, `v1-dev` kiểm tra Redis PING, kết nối PostgreSQL và
revision V1, Qdrant, storage cùng Vite đã cài. Với S3, kiểm tra endpoint, credential
và bucket bằng request chỉ đọc; với local, kiểm tra đường dẫn/quyền truy cập.
Có lỗi thì báo từng mục và dừng ngay;
kiểm tra không gọi model hoặc tự migration. Môi trường Python được chuẩn bị
một lần ở bước này; API/worker dùng `--no-sync` để tránh hai tiến trình cùng
cập nhật `.venv`. FE gọi trực tiếp Vite qua Node, tránh câu hỏi kết thúc batch
của `npm.cmd` khi dừng trên Windows. Khi chạy riêng API/worker, cài dependency
bằng `v1-install-be` trước nếu chưa có môi trường.

Nếu Docker vừa tạo volume PostgreSQL mới, container healthy chưa có nghĩa đã
có bảng V1. Sau khi xác nhận đúng database cần khởi tạo, chạy:

```powershell
.\make.ps1 v1-migrate
.\make.ps1 v1-check
.\make.ps1 v1-dev
```

`v1-migrate` nâng schema và thực hiện các chuyển dữ liệu của revision tương ứng.
Revision0005 gom model cũ vào nhà cung cấp theo endpoint, giữ ID và phạm vi khóa;
không tự cấp credential mới, quota hoặc tài liệu. Các cấu hình ModelOps thực hiện
theo phần 7 và [quy trình42](42_modelops_nha_cung_cap_va_model.md). Nếu database cũ có
revision phát triển đã gộp, xem phần 4 thay vì stamp/reset để vượt lỗi.

Mặc định API/worker đọc `.env` tại **gốc repo**, giữ cách phân giải storage
của cách A bên dưới. Nếu dùng `backendV1/.env` (cách B), chọn rõ trong cùng phiên:

```powershell
$env:QNU_V1_ENV_DIR = "backend"
.\make.ps1 v1-dev
```

Chuyển lại cách A bằng `$env:QNU_V1_ENV_DIR = "root"`. Không tự dò tệp để đổi
môi trường hoặc sao chép `.env`. Có thể xem lệnh/thư mục mà không chạy dịch vụ:

```powershell
.\make.ps1 v1-dev --dry-run
.\make.ps1 v1-migrate --dry-run --env-dir backend
```

Với GNU Make, dùng `make v1-dev V1_ARGS=--dry-run`; với Bash dùng
`./make v1-dev --dry-run`; CMD dùng `make.bat v1-dev --dry-run`.

Các lệnh thiết lập và kiểm tra bổ sung:

| Lệnh | Thực hiện |
| --- | --- |
| `make v1-install-be` / `make v2-install-fe` | Cài thư viện theo lockfile; không tạo/ghi đè cấu hình |
| `make v1-infra-up` | Khởi động PostgreSQL, Redis, Qdrant, MinIO, Gotenberg và chờ health; chuẩn bị storage local, kiểm tra ghi/đọc/xóa tệp thử; không mở API/worker/FE hoặc migrate DB |
| `make v1-check` | Đọc trạng thái Redis/PostgreSQL schema/Qdrant/storage/Vite, không ghi DB/storage hoặc gọi model |
| `make v1-db-check` | Đọc Alembic revision hiện tại, không seed hoặc migration |
| `make v1-migrate` | **Chủ động nâng schema** bằng Alembic; kiểm tra database và backup theo phần 4 trước |
| `make v1-test-be` | Harness tạo DB thử riêng trên loopback, chạy test rồi dọn đúng DB đó; cần quyền tạo DB |
| `make v1-lint` | Ruff BE rồi Biome FE V2, dừng nếu có lỗi, không tự sửa |
| `make v2-typecheck` / `make v2-build` | TypeScript / build FE V2; clone mới cần dev/build để sinh route tree trước khi typecheck riêng |

PowerShell thay `make` bằng `.\make.ps1` cho mọi lệnh trên. `check` và `db-ready` kiểm Vite trong `frontendV2`. Nếu chưa có thư viện FE V2, chạy `v2-install-fe`. `fe2` chạy riêng Frontend V2. Frontend V2 không có bộ test riêng. Các lệnh legacy `seed/reset-db/reseed/reconcile/reindex` đã ngừng hỗ trợ.

Để thử lại app V1 trên dữ liệu trắng, dừng `dev` bằng Ctrl+C rồi chạy:

```powershell
.\make.ps1 clear --confirm-local-reset
.\make.ps1 infra-up
.\make.ps1 migrate
.\make.ps1 seed-modelops
.\make.ps1 dev
```

Dừng nếu có lệnh báo lỗi. Mở <http://127.0.0.1:3002/> sau khi `dev` khởi động.
`clear` xóa volume PostgreSQL, Redis, Qdrant và MinIO của Docker local. Workspace,
ModelOps và tài liệu lưu trong các volume này cần được tạo lại. Dữ liệu trên
dịch vụ ngoài Docker hoặc thư mục lưu trữ riêng nằm ngoài phạm vi reset. Giữ cùng
lựa chọn `QNU_V1_ENV_DIR` cho toàn bộ các lệnh. Xem trước bằng
`.\make.ps1 clear --dry-run`. Với GNU Make, dùng `make clear ARGS=--confirm-local-reset`.

`seed-modelops` là bước tùy chọn cho DB development local. Lệnh thêm 9router Luna
(`cx/gpt-6-luna`) và dùng `E2E_9ROUTER_API_KEY` trong `.env` gốc nếu chưa có
khóa dùng chung đang hoạt động trên ModelOps. Seed đặt Qwen tắt suy luận cho
chat, biên soạn, rà soát bản biên soạn và kiểm tra chính tả. Lệnh thiết lập Qwen,
BGE Embedding, BGE Rerank và MinerU làm model mặc định hệ thống. Nếu chưa có khóa
dùng chung đang hoạt động, lệnh yêu cầu nhập ẩn khóa QNU dùng cho gateway QNU và
MinerU. Chạy lại sẽ tái dùng kết nối, khóa và model phù hợp. Thiết lập quyền
model cho từng workspace sau khi đăng nhập.
`db-ready` chỉ tương đương kiểm tra `check`, không tự tạo schema/seed. Runner chung là
[`scripts/run_v1.py`](../../scripts/run_v1.py), cần Python có sẵn trên máy hoặc
môi trường `.venv` V1 đã cài. Lệnh khởi động không tự migration/seed/reset DB.

### Chạy thủ công từng thành phần

| Thành phần | Địa chỉ / vai trò |
| --- | --- |
| Giao diện V2 | <http://127.0.0.1:3002/> |
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
Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV2
npm run dev
```

Mở **<http://127.0.0.1:3002/>**. V2 tự đăng nhập qua cầu nối dev khi `QNU_DEV_AUTO_LOGIN=true` và tự định tuyến đơn vị theo `QNU_DEV_WORKSPACE_CODE`; xem phần 5.

`run.ps1` ở gốc là entrypoint tương thích, gọi lại `make.ps1` nên chạy đúng các lệnh V1 bên trên; `dev`/`dev2` chạy kèm Frontend V2, `v1-dev` chỉ chạy API/worker. `backendV1/docker-compose.v1.yml` là entrypoint tương thích include cấu hình root, không phải một stack thứ hai; hướng dẫn này dùng API/worker chạy trực tiếp trên máy. Nếu máy cũ còn thư mục `backend/` hoặc `frontend/` untracked, đó là tàn dư đã bị gỡ khỏi Git — không chạy và không dùng làm căn cứ.

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
.\make.ps1 v1-infra-up
docker compose -f .\docker-compose.infra.yml ps
```

Runner truyền tệp `.env` đã chọn cho Compose; biến môi trường của phiên có thể ghi đè giá trị tệp. Cấu hình `POSTGRES_*` của Compose phải khớp database local trong `DATABASE_URL`; lệnh không thay tài khoản/database trong volume đã có. Nếu dịch vụ đã chạy ở máy/server khác, dùng địa chỉ thực tế trong cấu hình backend và bỏ bước khởi động Docker.

`v1-infra-up` đọc đúng `.env` đã chọn bằng `QNU_V1_ENV_DIR`/`--env-dir`,
kiểm tra cấu hình storage trước khi chạy Docker, khởi động đủ năm dịch vụ
và chỉ báo thành công khi bước chuẩn bị storage cuối cùng đạt. MinIO dùng đúng
image `pgsty/minio:RELEASE.2026-06-18T00-00-00Z`, dữ liệu nằm trong volume
`qnu_minio_data`. Không cần chạy MinIO riêng sau lệnh này:

```powershell
.\make.ps1 v1-infra-up
.\make.ps1 v1-check
```

Với `STORAGE_DRIVER=s3` và endpoint MinIO local `http://127.0.0.1:9000`
(hoặc `localhost`/`[::1]` cùng cổng), lệnh tạo bucket `S3_BUCKET` nếu còn thiếu.
Credential phải có quyền tạo bucket khi cần, ghi, đọc và xóa. Lệnh giữ nguyên
bucket/tệp cũ, thử bằng một object có tên ngẫu nhiên rồi xóa đúng object thử;
nếu lỗi xác thực, thao tác hoặc dọn tệp thử thì trả mã lỗi. Có thể chạy lại lệnh.
Console ở [MinIO local](http://127.0.0.1:9001); tài khoản lấy từ cấu hình S3 đã chọn.

Với S3 bên ngoài hoặc endpoint local tùy chỉnh, lệnh chỉ kiểm tra bucket đã có,
không tạo bucket hay ghi object lên endpoint đó. Quản trị storage phải chuẩn bị
bucket và quyền đọc/ghi. Với `STORAGE_DRIVER=local`, lệnh chuẩn bị đúng thư mục
đang cấu hình và thử ghi/đọc tệp tạm; `v1-check` chỉ đọc, không tạo thư mục/tệp.
MinIO vẫn được bật như một thành phần của bộ hạ tầng local.

`v1-check` chỉ xác nhận S3 truy cập được bucket; đây không phải bằng chứng quyền
ghi/đọc object. Phép thử ghi/đọc/xóa thực hiện trong `v1-infra-up` cho storage local.
Gotenberg được khởi động cùng bộ hạ tầng từ Context711, dùng image
`gotenberg/gotenberg:8`. Từ máy host truy cập `http://127.0.0.1:3005`, kiểm tra
`GET /health`; container trong cùng mạng Compose dùng `http://gotenberg:3000`.
Cổng3005 chỉ bind loopback. Có thể bật riêng mà không chạy lại các dịch vụ khác:

```powershell
docker compose -f .\docker-compose.infra.yml --env-file .\.env up -d --no-deps --wait gotenberg
```

DOCX mới dùng Gotenberg LibreOffice theo `DOCX_CONVERTER=gotenberg-libreoffice`;
`GOTENBERG_URL` được đọc từ Settings của `.env` đã chọn. Có thể chọn rõ
`DOCX_CONVERTER=docx-story` để dùng Story cho các job mới. Job ghim lựa chọn,
endpoint, `DOCX_RENDERER_REVISION` và phiên bản PyMuPDF; lỗi Gotenberg báo lỗi,
không tự đổi converter. PDF trực tiếp vẫn dùng PyMuPDF.

Ở nhánh Gotenberg, Docling đọc cấu trúc bảng từ DOCX gốc. Chỉ ghép cấu trúc
vào bảng PDF khi nội dung và số cột khớp duy nhất. Đầu trang, chân trang,
ảnh trang và tọa độ nội dung lấy từ PDF đã dàn trang.

Khi đổi image/font/tùy chọn chuyển đổi, đổi `DOCX_RENDERER_REVISION` để phân biệt
generation mới. Đây là revision triển khai do quản trị đặt, không phải phiên bản
Gotenberg được đo tự động. Giá trị mặc định là `qnu-docx/v2`. Khi phục hồi DOCX,
job dùng lại `render_pdf` đã lưu và kiểm hash thay vì gọi converter lần nữa.
Job cũ chưa có profile mới giữ Story; nếu đã có PDF thì giữ PDF đó và ghi rõ
metadata converter cũ không xác định. Không tự xử lý lại tài liệu đã xuất bản.
Thời gian chờ Gotenberg không giữ khóa MuPDF dùng chung; chỉ bước xử lý PDF/ảnh
giữ khóa. Log chuyển đổi chỉ ghi sự kiện, status hoặc loại lỗi, không ghi body
phản hồi, nội dung tài liệu hoặc exception thô. Unit test render/native có chốt
chặn client HTTP thật; ca kiểm Gotenberg phải cung cấp client giả tường minh.
Model AI vẫn được cấu hình riêng qua ModelOps; lệnh này không tải/chạy model.

Cài thư viện một lần, hoặc khi lockfile thay đổi:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\backendV1
uv sync --extra dev --frozen

Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV2
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
| `ALLOWED_ORIGINS` | Nếu gọi API trực tiếp từ FE, gồm origin đang dùng, ví dụ `http://127.0.0.1:3002,http://localhost:3002` |
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

Chỉ chạy `upgrade` sau khi xác nhận đúng database cần nâng cấp và có bản sao lưu nếu đã có dữ liệu. Head hiện tại là **`0005_provider_connections`**, nối sau `0004_application_api_keys`; giữ baseline `0001_initial_schema` và các revision đã phát hành. Bảng quản lý revision V1 là `alembic_version_backendv1`.

Nếu báo không tìm thấy revision phát triển cũ, xem [hướng dẫn migration](../../backendV1/docs/migrations.md). Cần chuyển tiếp schema/dữ liệu theo hiện trạng; không dùng `stamp head`, xóa database hoặc `run.ps1 reset-db` để vượt lỗi. CLI `qnu.cli.main` hiện là khung, chưa thực hiện migrate/preflight; dùng Alembic như trên.

## 5. Cấu hình FE và tự đăng nhập admin local

Tạo tệp riêng nếu chưa có:

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform\frontendV2
if (-not (Test-Path -LiteralPath .env.local)) {
    Copy-Item -LiteralPath .env.example -Destination .env.local
}
```

Trong `frontendV2/.env.local`, đặt:

```dotenv
FRONTEND_V2_PORT=3002
QNU_API_PROXY_TARGET=http://127.0.0.1:8002
QNU_DEV_AUTO_LOGIN=true
QNU_DEV_ACCESS_KEY=<điền đúng DEV_ACCESS_PASSWORD của backend V1>
QNU_DEV_WORKSPACE_CODE=<mã đơn vị đã seed, ví dụ shl>
```

Dòng `<...>` là chỗ điền giá trị riêng trên máy, không để nguyên dấu ngoặc. FE gọi API qua proxy Vite `/platform/v1alpha1`. Các lệnh ở phần 1 cố định cổng API là 8002; muốn đổi cổng cần đổi cả lệnh API và `QNU_API_PROXY_TARGET`.

Khi mở trang V2, cầu nối dev lấy token admin **`dev.admin`**, quyền `AI.Admin`; không cần tạo tài khoản hay seed admin trong database. Access key do tiến trình Vite đọc, không nhúng vào bundle; token vẫn được backend xác minh. V2 không tự chọn đơn vị mẫu: thiếu `QNU_DEV_WORKSPACE_CODE`/`VITE_DEV_WORKSPACE_CODE` thì màn hình báo lỗi cấu hình.

Nếu không bật tự đăng nhập, V2 báo lỗi cầu nối dev; hiện chưa có màn hình nhập access key. Đặt `QNU_DEV_AUTO_LOGIN=true` và chạy bằng `npm run dev` để làm việc local.

Cơ chế này chỉ dùng cho local development, API đích và trình duyệt phải qua loopback. Build/preview không có cầu nối tự đăng nhập. Khi đổi tệp môi trường, nạp lại đúng tiến trình API/worker/FE liên quan. Production cần tắt dev auth và cấu hình SSO; hướng dẫn này chưa phải quy trình triển khai production.

## 6. Kiểm tra sau khi mở ứng dụng

Mở cửa sổ PowerShell khác:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8002/health/live
Invoke-RestMethod -Uri http://127.0.0.1:8002/health/ready
```

`/health/live` xác nhận API còn phản hồi; `/health/ready` kiểm kết nối PostgreSQL và Redis, trả 503 nếu thiếu một trong hai. Hai kết quả này chưa chứng minh migration, worker, Qdrant hay model hoạt động đầy đủ.

Sau đăng nhập, mở workspace → **Vận hành** → kiểm tra sẵn sàng bằng tài khoản admin. Màn này kiểm thêm schema, queue/worker, Qdrant, cấu hình model và đọc tệp nguồn. Workspace mới chưa có nguồn có thể báo `no_source_to_probe`; upload một tài liệu rồi kiểm tra lại. Readiness không tự chạy inference model và không chứng nhận chất lượng câu trả lời.

### Mở chức năng từ sidebar

Sidebar chia thành **Tri thức, Trợ lý, Quản trị, Vận hành**. Khi chưa chọn
workspace/kho, bấm chức năng sẽ mở màn chọn tương ứng. Lựa chọn đang dùng hiện
ở mục **Đang làm việc**; dùng **Đổi workspace/Đổi kho** để chuyển. Trong cùng
phiên, chuyển qua ModelOps hay đóng menu điện thoại vẫn giữ lựa chọn này.
Tải lại trang lấy lựa chọn từ URL; đăng xuất không lưu lựa chọn sang phiên khác.

Các mục tài liệu cần chọn kho. Nếu workspace mới chưa có kho, quản trị/editor
có thể bấm **Tạo kho đầu tiên** ngay trên màn chọn. OCR cần chọn tiếp nguồn;
Biên soạn, Xuất bản, Tìm kiếm, Hỏi đáp và Đánh giá RAG mở đúng tab hoặc trang
của kho đã chọn. Các mục Tác vụ, Sao lưu, Dọn dữ liệu mở từng phần riêng của
trang vận hành. **Ctrl+K** dùng cùng danh mục và lựa chọn với sidebar.
Quyền thực hiện thao tác vẫn được backend kiểm tra.

## 7. Thiết lập ModelOps cho workspace mới

Bỏ qua các bước đã cấu hình đúng; không tạo lại provider/key khi chỉ khởi động lại ứng dụng.

1. Vào **Workspaces**, tạo/chọn đơn vị. Workspace là biên giới quyền trong V1; mọi yêu cầu vẫn được server kiểm quyền.
2. Vào **ModelOps → Nhà cung cấp**, tạo kết nối theo tên/loại/endpoint. Trong chi tiết: thêm API key → thử kết nối → thêm các model và capability. Một server AI là một nhà cung cấp chứa nhiều model; xem [hướng dẫn42](42_modelops_nha_cung_cap_va_model.md).
3. Khai báo capacity/input/output theo model và server đang dùng. Embedding cần `embedding_dimension`; OCR cần accounting ảnh/trang phù hợp. Không suy capacity từ tên model hoặc điền số giả để vượt kiểm tra. Xem [capacity ModelOps](../../backendV1/docs/model-capacity.md).
4. Tại workspace, cấp danh sách provider được phép, rồi chọn default **OCR**, **chat**, **embedding**, và **rerank** nếu dùng. Default toàn hệ thống không thay thế bước cấp quyền cho workspace.
5. Mở **Mức sử dụng** để theo dõi token. Hệ thống tự tạo kỳ thống kê UTC khi có lượt gọi đầu tiên.

Các vai trò model trong luồng hiện tại:

| Vai trò | Dùng ở đâu | Model đã tham khảo trong phiên làm việc |
| --- | --- | --- |
| OCR | Đọc ảnh trang PDF/DOCX | `nemotron-parse` |
| Chat | Compiler, review, gợi ý chính tả, trả lời | `qwen3.5-9b` hoặc model chat được cấp qua ModelOps |
| Embedding | Lập chỉ mục và tìm kiếm | `bge-m3` |
| Rerank | Xếp lại ứng viên khi bật rerank | `bge-reranker-v2-m3` |

Tên trên dùng để nhận diện cấu hình từng trao đổi, không phải cấu hình tự nạp hoặc cam kết model hiện đang sẵn sàng. Endpoint/credential/capacity lấy từ cấu hình ModelOps thực tế; danh sách `/v1/models` chưa đủ chứng minh các API OCR/embedding/rerank hoạt động.

Trên trang nhà cung cấp, dùng **Thử kết nối** để lấy danh sách; trong chi tiết
model, dùng **Thử** theo chức năng để đọc kết quả/độ trễ/lỗi. Kết quả thử không tự sửa capacity hay cấp quyền
workspace. Xem [hướng dẫn ModelOps](39_modelops_lay_danh_sach_va_chay_thu.md).

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
| Vite báo cổng 3002 đã dùng | Dừng đúng tiến trình đang chiếm cổng nếu không còn dùng, hoặc đổi `FRONTEND_V2_PORT`; runner chạy V2 với `--strictPort` nên không tự nhảy cổng |
| PostgreSQL báo sai mật khẩu hoặc dùng tên tài khoản Windows | Kiểm tra thư mục chạy, `.env` thực sự được nạp và `DATABASE_URL`; không lấy mặc định làm cấu hình môi trường |
| PostgreSQL connected nhưng V1 schema not initialized | Database đã kết nối nhưng chưa có bảng V1; xác nhận đúng database rồi chạy `v1-migrate`, kiểm lại bằng `v1-check` |
| Thiếu bảng/revision hoặc readiness báo schema sai | Chạy `alembic current` đúng môi trường; đối chiếu phần 4 trước khi nâng cấp |
| `SIGNING_KEY_MISSING`, `invalid_credentials`, `dev_gate_disabled` | Kiểm tra khóa ký ≥32 byte, dev gate, môi trường development và hai giá trị mật khẩu dev khớp nhau |
| Tự đăng nhập không hoạt động | Dùng `npm run dev`, URL loopback và kiểm tra `.env.local`; build/preview không có cầu nối; sau logout dùng nút đăng nhập lại |
| `ENCRYPTION_KEY_MISSING` / `DECRYPT_FAILED` | Kiểm tra API và worker dùng đúng khóa mã hóa đã bảo vệ credential trong DB; không thay khóa tùy ý |
| OCR/Compiler/index đứng `queued` | Xem cửa sổ worker, Redis URL, queue `qnu:v1:jobs`, database và cờ dispatch/reconcile của API/worker có khớp; xem chi tiết job ở Vận hành |
| Capacity thiếu/stale, `model_input_budget_unknown` | Kiểm tra lại capacity và OCR image accounting sau khi đổi endpoint/model; không tăng token môi trường để bỏ qua kiểm tra |
| Provider trả 401/403, ví dụ `embedding_auth_failed` | Kiểm tra credential đang active ở ModelOps và quyền trên server AI; không biến lỗi provider thành “không có dữ liệu” |
| Upload đọc được ở API nhưng worker báo thiếu tệp | Hai tiến trình phải dùng cùng storage driver và cùng đường dẫn tuyệt đối/bucket; kiểm tra khác thư mục hiện tại |
| Upload báo không ghi được tệp vào kho lưu trữ | Chạy `v1-check`; với MinIO local chạy `v1-infra-up` để bật dịch vụ, chuẩn bị bucket và thử quyền ghi/đọc/xóa. Với S3 khác kiểm tra endpoint, credential và quyền bucket |
| Tìm kiếm/hỏi đáp chưa có nguồn | Kiểm tra tài liệu đã duyệt, xuất bản, index hoàn tất và scope đang chọn; upload/OCR xong chưa tự đưa dữ liệu vào trả lời |
| Bấm tác vụ xong mất kết nối, trạng thái `uncertain` | Mở lại chi tiết job/biên nhận để đối soát trước khi gửi mới; không bấm lặp để ép chạy lại |

## 10. Dừng và chạy lại

Chờ các job đang xử lý kết thúc nếu có thể, rồi nhấn **Ctrl+C** tại từng cửa sổ FE/API/worker đã mở. Việc dừng tiến trình không xóa dữ liệu; trạng thái job gián đoạn cần kiểm lại ở Vận hành khi chạy tiếp. Không tự gửi lại inference chưa rõ kết quả.

PostgreSQL, Redis, Qdrant, MinIO có thể đang dùng chung với bản cũ: giữ chúng chạy nếu còn ứng dụng sử dụng. Lần sau dùng lại phần 1; không cần seed/reset database, migration lại hằng ngày hoặc nạp lại tài liệu.

Nếu cần phục hồi toàn bộ từ backup, dùng [runbook recovery](../../backendV1/docs/recovery.md) vào đích mới. Hiện thao tác full restore chưa có giao diện web.

## Nguồn đối chiếu và phạm vi kiểm tra

- [Backend README](../../backendV1/README.md), [pyproject](../../backendV1/pyproject.toml), [Settings](../../backendV1/qnu/platform/config.py), [worker](../../backendV1/qnu/workers/settings.py), [health](../../backendV1/qnu/api/health.py).
- [FE package](../../frontendV2/package.json), [Vite config](../../frontendV2/vite.config.ts), [môi trường mẫu FE](../../frontendV2/.env.example), [cầu nối admin local](../../frontendV2/dev/dev-auto-login.ts).
- [Môi trường mẫu BE](../../backendV1/.env.example), [migration](../../backendV1/docs/migrations.md), [quyền workspace/ModelOps](../../backendV1/docs/workspaces-modelops.md), [readiness](../../backendV1/docs/readiness.md).

Hướng dẫn ban đầu được kiểm tra tĩnh ở phiên683. Khi xử lý log khởi động ở
phiên686, đã xác nhận database local mới trống, áp dụng migration đến
`0003_rag_policy_metadata` và kiểm tra thật API live/ready, FE cùng heartbeat
worker, sau đó dừng đúng tiến trình thử. Không chạy inference hoặc nghiệm thu
chất lượng câu trả lời; cấu hình và trạng thái môi trường khác cần kiểm lại.
