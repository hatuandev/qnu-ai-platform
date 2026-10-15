# Review mẫu Environment Dokploy

## Mục tiêu và kết quả

Rà soát `.env.dokploy.example` theo yêu cầu xem sai/thiếu, đối chiếu Compose, Settings, frontend OIDC build args, storage và auth. Không sửa template, Compose hoặc Environment thật.

- Compose config --quiet đạt. Mẫu đủ các biến bắt buộc `:?`, không trùng key và các biến đang khai báo đều được Compose tham chiếu. Đây là kiểm tra contract/cú pháp, chưa xác nhận mạng, secret hoặc SSO thực tế.
- Phần lớn endpoint/user/password là placeholder; không dán nguyên file lên server. Các URL internal chỉ đúng nếu hostname tồn tại trên network và quyền truy cập hợp lệ. DB phải trỏ đúng `qnu_ai_platform`; ảnh người dùng đã xác nhận Alembic revision server `20260926_reconcile_core_schema`, trùng mốc thử nâng thành công phiên458, nhưng chưa có schema/data dump thực tế.
- Dòng3 “Copy toàn bộ” chưa phù hợp nâng cấp: các dòng5/58 đã cảnh báo giữ khóa, nhưng chỉ dẫn đầu có thể khiến ghi đè secret. Kiến nghị sửa lời hướng dẫn để cập nhật từng biến, không thay bằng placeholder. Không tự sửa khi người dùng chỉ yêu cầu review.
- `ENVIRONMENT=production`, dev=false/password rỗng, SSO=true là cấu hình khớp chính sách code hiện tại. Không phải cấu hình demo đăng nhập mật khẩu. Người dùng chưa SSO: cần đăng ký client/redirect/quyền thực hoặc triển khai phương án demo auth an toàn riêng; không đổi development hay dev=true để né bảo mật.
- Origin phải là domain ứng dụng thật, không phải domain dashboard Dokploy. S3 endpoint/secure và Gotenberg credentials phải tương ứng dịch vụ thật. Không đổi bucket/collection để chữa lỗi nếu muốn giữ dữ liệu cũ.
- API key/model LLM không thiếu: đã chủ động quản lý qua DB ModelOps. 9router localhost trong DB phải đổi endpoint truy cập được từ server, không thêm biến LLM vào env.
- `BACKEND_WORKERS=4` không sai nhưng chưa được chọn theo tài nguyên/server DB dùng chung. Pool mặc định15+overflow10 mỗi process; bốn API process có thể lên100 connections, chưa kể worker và app khác. DB_POOL_SIZE/DB_MAX_OVERFLOW/WORKER_MAX_JOBS/S3_REGION có Settings nhưng chưa được forward trong Compose; muốn tùy chỉnh cần cập nhật cả hai, không chỉ thêm env. MinIO mặc định us-east-1 thường không cần S3_REGION riêng. Không tự chỉnh số kết nối/concurrency khi chưa có số liệu tải.
- Backup nâng cao/secret mount/drill không phải yêu cầu bắt buộc để app chạy; mặc định drill tắt và không tự bật lịch. Không thêm secret file path khi chưa mount thật.

## Kiểm chứng và phạm vi

Chỉ đọc mã và env mẫu; không đọc file env thật, không gọi DB/provider/network server, không migration/reset/seed/deploy. Không Ruff/Pytest/Vite vì không sửa code/runtime. Cập nhật nhật ký, snapshot, memory và hai mục lục theo quy định. Bài học: env mẫu hợp lệ cú pháp không đồng nghĩa đủ cấu hình cho môi trường cụ thể, nhất là xác thực và khóa giải mã khi nâng cấp.
