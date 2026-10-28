# Context701 — Cấu hình URL API tích hợp local

Người dùng yêu cầu thêm cấu hình nhanh, không chạy test.

- Runner V1 mặc định đọc .env tại root repo và chạy API cổng8002; backendV1/.env không tồn tại. Đã thêm duy nhất PUBLIC_BASE_URL=http://127.0.0.1:8002 vào .env root, giữ nguyên mọi dòng cấu hình khác.
- Phạm vi ngoại lệ: chỉ thêm PUBLIC_BASE_URL theo yêu cầu người dùng, không đổi credential hay endpoint/model upstream.
- Không chạy test/build, không gọi model, không restart, migrate, commit hoặc push. Cần người dùng khởi động lại backendV1 để tiến trình nạp cấu hình mới.
- Chỉ đọc runner/cấu hình liên quan để xác định đúng tệp; không in credential ra output.
