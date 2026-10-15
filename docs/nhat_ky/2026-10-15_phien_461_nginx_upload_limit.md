# Phiên 461 — Giới hạn upload Nginx

## Mục tiêu và thay đổi

Người dùng báo upload PDF 16,7 MB nhận HTTP 413 dù UI ghi tối đa 50 MB và yêu cầu thêm cấu hình Nginx. Thêm `client_max_body_size 60m;` trong khối server của `frontend/nginx.conf`, chừa dung lượng multipart cho tệp 50 MiB. Không đổi giới hạn từng tệp, Backend, dữ liệu hay cơ chế xác thực. Cập nhật runbook triển khai và bộ nhớ/nhật ký.

## Kiểm chứng và bàn giao

Chỉ kiểm tra diff có phạm vi, không chạy Pytest/Vite/Docker theo yêu cầu người dùng đang cần xử lý gấp. Không truy cập, reload hoặc deploy server; không commit/push. Dockerfile COPY nginx.conf vào image nên cần đưa thay đổi lên Git và build/deploy lại Frontend. Chưa cam kết mọi HTTP 413 được giải quyết nếu proxy ngoài container còn có giới hạn riêng.

## Phương pháp

Áp dụng skill qnu-clean-code-architect: thay đổi cấu hình tối thiểu, không mở upload vô hạn hoặc sửa lan ra luồng ingestion. Không reset DB/nạp vector.
