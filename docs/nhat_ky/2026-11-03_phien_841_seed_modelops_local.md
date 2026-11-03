# Phiên 841 — Seed ModelOps local

Dừng phiên dev. Thêm lệnh seed sau migration cho DB development local, tái dùng
kết nối, khóa dùng chung và model theo cấu hình QNU. Khóa nhập ẩn khi thiếu,
lưu qua ModelOps. Lệnh cập nhật bốn default hệ thống.

Ruff, import CLI, dry-run và 24 test runner PASS. Seed ghi DB và gọi nhà cung cấp
thật NOT RUN. Workspace vẫn cần cấp quyền model và quota theo quy trình hiện có.
