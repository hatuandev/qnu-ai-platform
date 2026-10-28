# Phiên 686 — Chẩn đoán khởi động V1 và database mới

## Yêu cầu và diễn biến có căn cứ

Người dùng gửi log `v1-dev`: ARQ timeout Redis, hai uv run cùng build môi trường,
API nghe8002 nhưng logPORT8001, FE báo auto-login tắt và npm.cmd hỏi kết thúc
batch khi dừng. Read-only lúc đầu xác nhận Docker daemon chưa chạy/không có
Redis listener. Người dùng tự mở Docker Desktop và chạy `v1-infra-up`; ba
container healthy nhưng preflight PostgreSQL FAIL.

Đối chiếu trực tiếp cho thấy DATABASE_URL kết nối được database local
`qnu_ai_platform`; trước khi ghi, đếm tất cả public base tables là0, chưa có
bảng version V1. Đây là DB mới từ volume vừa tạo. Trong phạm vi xử lý lỗi chạy
V1, áp dụng migration hiện có để khởi tạo schema sau khi xác nhận DB trống;
không reset/seed hoặc nhận các bảng hiện hữu làm sở hữu.

## Thay đổi tooling

- `scripts/check_v1_runtime.py`: kiểm tra đọc Redis PING, PostgreSQL/schema,
  Qdrant GET collections và Vite entry, không gọi model/DDL/seed. Thiếu bảng
  version được báo riêng là PostgreSQL đã kết nối nhưng schema chưa khởi tạo,
  hướng dẫn v1-migrate; không nhắc mở lại Docker nếu Redis/Qdrant đang tốt.
  Lỗi được giữ nghĩa thất bại và thông báo an toàn, không in URL/secret/raw exception.
- `scripts/run_v1.py`: v1-dev chạy check/chuẩn bị môi trường trước, chỉ mở ba
  tiến trình nếu đạt. API/worker dùng --no-sync, tránh build/sync đồng thời;
  PORT8002 chỉ đặt trong môi trường API con, không sửa root.env. FE chạy Node
  với Vite entry thay npm.cmd, tránh prompt kết thúc batch trên Windows.
- Thêm `v1-check` và `v1-infra-up` qua runner chung; Makefile/make.ps1 khai báo
  đủ16lệnh, Bash/CMD giữ dispatch prefix. Infra-up tường minh khởi động ba
  dịch vụ PostgreSQL/Redis/Qdrant với --wait; không tự mở Docker Desktop.
- Phát hiện và sửa lỗi uv --env-file trên Windows: đường dẫn backslash bị
  diễn giải mất dấu, lượt migrate đầu exit1 chưa chạy DDL. Chuyển riêng đối số
  env-file sang forward slash, kiểm tra nạp cấu hình thành công rồi migrate.
- Bổ sung regression ở scripts/tests và cập nhật hướng dẫn38; không sửa BE/FE
  application, migration source, runtime.env, ModelOps/auth/SSO hoặc native
  Vite warning không gây lỗi. Auto-login vẫn theo cấu hình đã có, không bật giả.

## Thao tác và kiểm chứng thực chạy

Cwd gốc repo; runtime backendV1/.venv và PowerShell/Git Bash có sẵn.

1. Docker compose ps và probe asyncpg read-only: ba container healthy, DB kết
   nối được; trước migration0bảng public. Không đọc corpus hoặc công bố secret.
2. `.\make.ps1 v1-migrate`: sau sửa đối số Windows, exit0; áp0001 →0002 →0003.
   Probe sau:44bảng public, head0003_rag_policy_metadata. Không tự tạo model,
   provider/key, workspace, quota hoặc tài liệu.
3. `.\make.ps1 v1-check`: exit0, Redis/PostgreSQL/schema/Qdrant/Vite đều OK.
   Đây là kiểm dependency, không phải ModelOps readiness hay quality benchmark.
4. Smoke thật mở đúng ba lệnh service sau preflight từ command_plan, xác nhận
   cổng8002/3001 chưa có listener trước khi mở. API /health/live và /health/ready
   trả200/statusok, FE /dashboard trả200, ARQ --check exit0. Các tiến trình do
   smoke tạo đã dừng bằng cơ chế cleanup; cổng được nhả, Docker người dùng mở
   vẫn chạy. Không gọi model, không gửi tài liệu, không xử lý job do người dùng tạo.
5. `python -m unittest discover -s scripts/tests -p test_*v1*.py -v`:
   **27PASS**, exit0; giữ12ca685 và thêm15ca. Trước sửa có12PASS/2FAIL/1ERROR
   cho preflight/onesync/port; checker trước thiếu-table probe2FAIL/6PASS.
   Lượt thêm output-test từng2ERROR do thiếu import fixture đã sửa và chạy lại
   cả27ca đạt; không bỏ test để xanh.
6. 54kiểm wrapper PowerShell/CMD/Bash bằng dry-run,16lệnh/loại +env +tham số sai:
   PASS. GNU Make binary không có, runtime NOT RUN; target/recipe kiểm tĩnh PASS.
7. Ruff check/format --check4tệp Python, parserPS/bash-n, UTF8khôngBOM/LF,
   link và diff phạm vi: PASS. Lượt đầu Ruff báo broad exceptions/unusedimport,
   đã thu hẹp exception và sửa trước gate cuối. Không sửa code BE/FE.

Bằng chứng ở `storage/artifacts/context686-v1-startup/`: baseline8tệp,
regression trước/sau, schema-receipt, smoke-receipt cùng log ba tiến trình,
preflight/worker heartbeat, wrapper-verification và receipt index. Không đưa
pasted log có dữ liệu người dùng hoặc giá trị secret vào docs/Git.

**NOT RUN:** fullsuite/build ứng dụng, login/SSO, inference/RAG/OCR live,
benchmark chất lượng, reindex, restore hoặc Git commit/push. Smoke không thay
thế nghiệm thu toàn luồng; DB mới còn cần cấu hình ModelOps/quota và dữ liệu
qua giao diện. Không coi4check startupOK là mọi chức năng đã sẵn sàng.

## Bàn giao

Người dùng chạy lại `.\make.ps1 v1-dev`, mở http://127.0.0.1:3001/dashboard.
Nếu dùng database khác, kiểm đúng cấu hình và revision trước khi migrate.
Hướng dẫn38 có cách kiểm/khởi tạo schema mới; chưa đẩy thay đổi tooling lên remote.

[Hướng dẫn38](../quy_trinh/38_huong_dan_chay_qnu_v1.md).
[Snapshot686](../memory/snapshots/2026-10-28_session_686.md).
