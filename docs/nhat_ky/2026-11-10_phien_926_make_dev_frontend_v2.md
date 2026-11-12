# Phiên 926 — Chạy Frontend V2 bằng make dev

- `dev` và `dev2` dùng chung kế hoạch API V1 cổng 8002, worker V1 và Frontend V2 cổng 3002. Vite dùng `--strictPort`. `check` và `db-ready` kiểm thư viện của Frontend V2. `fe2` mở riêng Frontend V2.
- `dev1` và `v1-dev` giữ lối chạy Frontend V1. Phạm vi đổi mặc định là launcher dev local. Docker triển khai, test và công cụ build Frontend V1 dùng lệnh riêng hiện có.
- Từ root, `python -m unittest discover -s scripts/tests -p 'test_run_v1.py'` đạt 25 ca và mẫu `test_check_v1_runtime.py` đạt 10 ca. Ruff trên bốn tệp runner/test và `git diff --check` thoát 0.
- `make.ps1 dev --dry-run` xác nhận lệnh và thư mục của từng tiến trình. `make.ps1 check` đạt với hạ tầng local, schema hiện hành và Vite Frontend V2. Chạy Vite theo kế hoạch `dev` trả HTTP 200 ở cổng 3002 và chuyển tiếp đúng prefix tới API giả lập. Phiên Vite kiểm thử đã dừng. Chưa chạy đồng thời ba dịch vụ trên DB ứng dụng.
