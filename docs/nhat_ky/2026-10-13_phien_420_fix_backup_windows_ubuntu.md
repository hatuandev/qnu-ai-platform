# Phiên 420 — Sửa khởi chạy sao lưu trên Windows và Ubuntu

## Mục tiêu và phạm vi

Người dùng đồng ý sửa lỗi POST backup 503, yêu cầu tương thích Windows và Ubuntu. Sửa boundary khởi chạy tiến trình độc lập; không đổi event-loop policy toàn app, không bỏ `--reload`, không chỉnh DB/Redis/ModelOps, không restart dịch vụ và không tạo hay khôi phục backup dữ liệu thật.

Áp dụng hướng dẫn backend và clean-code: regression tái hiện trước khi sửa, thay đổi gọn trong module backups, kiểm chứng bằng tiến trình và dữ liệu mẫu thật thay vì giả lập kết quả thành công.

## Nguyên nhân và thuật toán

1. Windows/Uvicorn reload dùng SelectorEventLoop, không hỗ trợ `asyncio.create_subprocess_exec` trong request. Phép thử đối chứng vẫn xác nhận `NotImplementedError` của API cũ.
2. Mật khẩu truyền UTF-8 qua pipe nhưng runner đọc `sys.stdin.readline()` theo encoding mặc định Windows, làm sai mật khẩu có dấu. Regression dùng mật khẩu tiếng Việt của fixture phát hiện lỗi này độc lập với lỗi Selector.
3. Launcher dùng `subprocess.Popen` trong `asyncio.to_thread`: Windows áp dụng `CREATE_NO_WINDOW`, POSIX áp dụng `start_new_session`. Không shell, không mật khẩu argv/env/catalogue/log. Mật khẩu giới hạn kích thước, pipe được flush/đóng; runner giải mã byte stdin bằng UTF-8 rõ ràng.
4. Reap tiến trình qua thread, không dùng subprocess transport của request loop. Giữ tracking waiter; khi request bị hủy trong lúc spawn, chờ launcher bàn giao và đăng ký reap rồi truyền tiếp cancellation.
5. Nếu spawn lỗi: catalogue/history chuyển failed, HTTP 503 `BACKUP_LAUNCH_FAILED`; chỉ ghi loại lỗi đã làm sạch, không ghi raw exception có thể chứa bí mật. Nếu gửi pipe lỗi, kill/reap đúng child vừa tạo.

## Tệp thay đổi

- `backend/app/modules/backups/launcher.py`: launcher portable mới.
- `backend/app/modules/backups/service.py`: offload spawn/reap, lifecycle và sanitized diagnostics.
- `backend/app/modules/backups/runner.py`: đọc mật khẩu UTF-8 từ binary stdin.
- `backend/tests/test_backup_launcher.py`: real runner/HTTP 202 trên default loop và Windows Selector; lỗi executable thiếu, đối chứng API cũ.
- `backend/tests/docker/backup_launcher.Dockerfile`: harness Ubuntu 24.04, chỉ source và thư viện cần cho phạm vi backup; không `.env`/volume dữ liệu thật.
- Runbook backup, nhật ký README, memory và WORK_LOG.

## Kiểm thử

| Kiểm tra | Kết quả |
|---|---|
| Regression trước sửa | 2 failed / 1 passed: Selector launch fail và mật khẩu Unicode sai; đối chứng API cũ đúng lỗi |
| Windows, launcher + unit/security backup | **30 passed**, 11.84 giây |
| Ubuntu 24.04 container, cùng bộ test | **27 passed / 3 skipped**, 4.31 giây; chỉ skip 3 ca riêng Windows |
| Integration PG16 + MinIO + Qdrant mẫu | **1 passed**, 42.45 giây: child tạo archive, verify, isolated drill, đối soát Unicode/review/key pool/vector và khóa |
| Ruff toàn backend | Đạt; có cảnh báo quyền đọc một số thư mục test cũ, không có lỗi lint |
| Ruff format 4 tệp Python thay đổi | Đạt |
| Pytest toàn backend | **1101 passed / 11 failed / 10 skipped**, 132.05 giây; cùng 11 lỗi baseline của phiên 418 |
| Frontend / Vite build | Không chạy: không sửa frontend trong phiên này |

Harness Ubuntu ban đầu thiếu extras `sqlalchemy[asyncio]`, bcrypt và ARQ; đã bổ sung, import runner và lượt test cuối đạt. Đây không phải build image production đầy đủ hay chạy toàn bộ backend suite trên Ubuntu.

11 baseline còn lại: 2 consulting export, 6 publishing API/permission, 1 reconciliation, 1 auth role expectation, 1 universal export; không có lỗi backup mới. Không sửa lan sang các module này.

Lệnh tái lập (từ workspace, Docker phải có sẵn):

```text
docker build -f backend/tests/docker/backup_launcher.Dockerfile -t qnu-backup-compat:420 .
docker run --rm --network none --label qnu.backup.compat=420 qnu-backup-compat:420
```

Windows: từ backend dùng `.venv/Scripts/python.exe -m pytest tests/test_backup_launcher.py tests/test_backups.py -q` và `QNU_TEST_BACKUP_DOCKER=1` cho suite integration opt-in. Test thật dùng archive synthetic và container có nhãn ownership, không backup DB hiện hành; các container mẫu đã kết thúc/dọn. Image kiểm thử giữ local để tái lập; fixture encrypted/catalogue giữ trong thư mục test.

## Bàn giao và giới hạn

- Khởi động lại backend để chắc chắn nạp mã mới rồi F5 trang Sao lưu, tạo thao tác mới. Không reset DB hoặc xóa Redis; các bản failed trước đây được giữ làm lịch sử, không tự biến thành thành công.
- Nếu chưa nạp thay đổi đợt 1 ở mọi BE replica/worker, làm theo điều kiện restart toàn bộ trong runbook. Phiên này không sửa worker hay frontend.
- Mật khẩu thực vẫn do người dùng giữ riêng. Không có lưu/replay mật khẩu, không tự chạy lại các backup failed.
- Tương thích launcher đã kiểm chứng trên Windows và Ubuntu 24.04; vẫn cần pg_dump đúng major, quyền thư mục, storage/network/Docker tương ứng. Chưa chạy backup corpus thật, UI authenticated E2E, Docker production build hay cam kết RPO/RTO.

## Bài học

Phải kiểm thử boundary HTTP ở chính loại event loop của chế độ phát triển, không chỉ loop mặc định pytest. Pipe chứa bí mật phải có encoding đối xứng rõ ràng giữa parent/child; không dựa trên locale hệ điều hành. Thành công launch/HTTP 202 không đồng nghĩa backup hoàn tất: cần đối soát trạng thái terminal và toàn vẹn archive.
