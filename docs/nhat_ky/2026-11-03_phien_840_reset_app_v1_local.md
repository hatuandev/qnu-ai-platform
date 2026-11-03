# Phiên 840 — Reset app V1 local

Thêm `make clear` / `.\make.ps1 clear` cho app V1 local. Cờ `--confirm-local-reset` xác nhận xóa volume, Docker endpoint từ xa bị từ chối. Quy trình tiếp theo: `infra-up`, `migrate`, `dev`.

Kiểm chứng: 23 test runner PASS, Ruff PASS, dry-run root/backend đúng compose và tệp môi trường. Reset thật và E2E: NOT RUN. Dịch vụ lưu trữ ngoài Docker nằm ngoài phạm vi reset.
