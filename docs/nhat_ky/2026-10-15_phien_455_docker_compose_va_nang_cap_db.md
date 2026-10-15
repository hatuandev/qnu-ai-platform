# Đánh giá Docker Compose và nâng cấp DB trên server

## Mục tiêu

Đối chiếu file triển khai hiện tại với Environment cũ trong ảnh, không suy diễn thành yêu cầu tạo demo riêng. Nâng cấp code không mặc nhiên cần reset DB. Chưa có Compose cũ hoặc Alembic revision của server để xác nhận toàn bộ đường nâng cấp.

## Kết luận kỹ thuật

- Giữ kiến trúc bootstrap, API, ARQ worker, frontend Nginx và hạ tầng Dokploy ngoài stack. Bootstrap thực hiện migration lên head rồi seed; backend/worker chờ bootstrap thành công. `AUTO_SEED=false` trong ảnh không điều khiển bước này.
- Dockerfile backend dùng Python 3.12, non-root UID 10001, đóng gói configs/migrations, có pg_dump/pg_restore PostgreSQL 16. Frontend build riêng rồi phục vụ qua Nginx, API proxy có timeout 300s và tắt buffering. Kiến trúc phù hợp, chưa xác nhận image build/chạy server.
- Trước deploy cần xử lý đăng nhập production so với mật khẩu dev cũ, origin chính xác, bỏ thông tin LLM tĩnh khỏi cấu hình triển khai để dùng ModelOps DB, và đổi địa chỉ 9router trong DB sang endpoint server có thể truy cập. Compose cần chuyển tiếp biến SSO khi sử dụng SSO.
- Để build lặp lại ổn định: sử dụng dependency lock và pin image/tool versions; frontend không nên tự fallback npm install khi npm ci lỗi. Backend có `apt-get ... && fc-cache ... || true` khiến lỗi phần cài đặt có thể bị che; nên tách điều kiện chỉ cho phép font cache thất bại nếu thực sự cần.
- Root `.dockerignore` loại `storage/...` nhưng không bao phủ rõ `backend/storage/...`; cần loại dữ liệu runtime, backup, log và tmp khỏi build context gốc để giảm dung lượng và tránh đưa dữ liệu không cần thiết tới builder. Dockerfile hiện không COPY storage vào image, nên không kết luận backup đã nằm trong image.
- Khi nâng cấp cùng stack, giữ nguyên DB, bucket, collection và volume dữ liệu; kiểm tra quyền ghi của volume cũ với UID 10001. Không tự đổi tên volume hoặc chạy down -v. Tách tên volume/alias chỉ cần khi chọn chạy hai stack riêng song song.

## Nâng cấp DB và chuyển dữ liệu

Không reset DB chỉ để cập nhật code. Trước deploy: sao lưu DB, MinIO/files, Qdrant và giữ khóa giải mã provider; kiểm tra revision DB, chạy thử migration trên bản sao khi server cách nhiều phiên bản; dừng API/worker cũ trong thời gian nâng schema nếu không tương thích.

Migration không đồng nghĩa tất cả thay đổi chỉ thêm bảng: `20261002_remove_local_models` xóa provider cũ theo ID/type và sửa routing, `20260919_facts_foreign_key_and_schema_sync` xóa facts mồ côi khi cần tạo FK. Những bước này chỉ áp dụng nếu còn pending; cần revision thực tế và kiểm tra dữ liệu trước khi nâng. Không tự stamp head hoặc reset khi migration lỗi.

Muốn dùng dữ liệu local mới nhất là tác vụ chuyển dữ liệu riêng, không phải kết quả tự động của migration. Phải đồng bộ DB, file/object storage, Qdrant và khóa provider, xử lý đường dẫn Windows nếu có. Không khôi phục DB local đè server mà thiếu kế hoạch và xác nhận.

## Kiểm tra và tệp thay đổi

Compose config --quiet với `.env.dokploy.example` đạt lại. Chỉ rà soát mã/config, không chạy migration, build image, Ruff/Pytest/Vite hay truy cập server. Không sửa Compose/Dockerfile/runtime, không đọc secrets thật, không reset DB hoặc thay đổi dịch vụ. Chỉ cập nhật nhật ký và ba tài liệu memory/index theo quy định.

Bài học: cần phân biệt nâng cấp ứng dụng, migration schema và thay thế bộ dữ liệu. Cả ba không thể gộp thành thao tác reset DB.
