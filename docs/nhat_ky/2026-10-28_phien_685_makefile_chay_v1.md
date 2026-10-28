# Phiên 685 — Makefile và runner chạy V1

## Yêu cầu và phạm vi

Người dùng thường dùng Makefile, yêu cầu xem và điều chỉnh để chạy V1.
Áp dụng skill qnu-clean-code-architect cho thay đổi gọn và kiểm chứng theo rủi ro.
Chỉ sửa tooling chạy local và hướng dẫn; không sửa ứng dụng BE/FE, cấu hình
môi trường hoặc hành vi RAG. Giữ lệnh legacy và `run.ps1` hiện có.

## Thay đổi

- `Makefile`, `make` (Bash), `make.bat` (CMD), `make.ps1` (PowerShell) có chung
  14 lệnh `v1-*`; help nhắc V1, default GNU Make vẫn hiển thị help.
- `scripts/run_v1.py` là runner dùng thư viện chuẩn: API8002, worker đúng queue
  moduleV1, FE qua npm; mặc định cwd gốc để giữ `.env`/storage. Có lựa chọn
  `QNU_V1_ENV_DIR=backend` hoặc `--env-dir backend`, không tự dò/chép cấu hình.
- `v1-dev` giám sát ba tiến trình trong foreground, Ctrl+C dọn nhóm tiến trình
  do phiên tạo; một thành phần thoát thì dừng các thành phần còn lại và báo lỗi.
  Không tự restart dịch vụ có sẵn, không tìm/kill tiến trình theo cổng/tên.
- Lệnh riêng cài dependency, migrate, current, test BE bằng DB harness cô lập,
  test FE, lint, typecheck, build; mã lỗi truyền về, chuỗi lint dừng khi lỗi.
  Migrate chỉ chạy khi gọi lệnh tường minh, không ghép vào dev/seed/reset.
- `--dry-run` chỉ xuất argv/cwd, không đọc giá trị secret hay chạy lệnh.
  Kiểm `.env` và resolve đủ công cụ trước khi mở dịch vụ.
- Bổ sung [hướng dẫn38](../quy_trinh/38_huong_dan_chay_qnu_v1.md) với bảng lệnh
  và cách dùng PowerShell khi không cài GNU Make. Lệnh không có tiền tố `v1-`
  giữ nghĩa legacy, kể cả `make dev`.

## Kiểm chứng thực chạy

Cwd gốc repo, Python trong `backendV1/.venv`, PowerShell/Git Bash sẵn có:

- `python -m unittest discover -s scripts/tests -p test_run_v1.py -v`:
  **12PASS**, exit0. Bao gồm ghim cwd/env/argv, không auto-migrate, backend
  test harness, thiếu env/tool chặn launch, trả lỗi/dừng chuỗi, cleanup khi
  spawn lỗi/child thoát/Ctrl+C và nhóm tiến trình thử thật giữ tiến trình khác.
- Lượt đầu9PASS/1FAIL do test kiểm suffix đường dẫn Unix trên Windows;
  sửa kiểm tra Path đúng đường dẫn, không đổi logic runner để làm xanh.
- 48 kiểm tra wrapper: mỗi PowerShell/CMD/Bash gọi đủ14lệnh bằng dry-run,
  lựa chọn env backend và tham số sai trả lỗi. Chạy từ cwd artifact khác repo
  vẫn định vị đúng gốc dự án. Không chạy nội dung lệnh migration/test ứng dụng.
- Ruff check và format --check trên đúng2tệp Python mới: PASS, exit0.
  Parser PowerShell và `bash -n ./make`: PASS.
- GNU Make binary không có trên máy: runtime **NOT RUN**. Kiểm tra tĩnh14target,
  recipe chung và default help: PASS; không tuyên bố đã chạy GNU Make thật.
- UTF-8 không BOM/LF,19link local trong hướng dẫn, `git diff --check`: PASS.
  Diff legacy bodies chỉ thêm dispatch/help và mở rộng tham số PS; không đổi
  recipe cũ. `run.ps1` giữ đúng bytes trước task, không ghi đè thay đổi sẵn có.

Bằng chứng ở `storage/artifacts/context685-v1-make/` (Git ignore): before6tệp,
runner-tests/ruff logs, wrapper-verification.json, source-verification.json và
receipt các index memory chèn có phạm vi/kiểm hash, giữ lịch sử.

**NOT RUN:** full test/build BE/FE, cài dependency, chạy API/ARQ/FE thật, DB
migration, inference, reindex, restart, deploy hoặc Git commit/push. Worker thật
có thể xử lý job còn chờ khi người dùng chủ động chạy; nên kiểm tra đúng môi
trường và chỉ mở một phiên dev, không coi help/dry-run là readiness toàn luồng.

## Bàn giao

Từ gốc repo dùng `.\make.ps1 v1-dev` trên PowerShell hoặc `make v1-dev` khi
GNU Make/CMD runner có sẵn; xem `v1-help`. Mặc định root.env; chọn backend mode
nếu cấu hình nằm trong backendV1. Chưa tự push thay đổi tooling lên Gitea.

[Snapshot685](../memory/snapshots/2026-10-28_session_685.md).
