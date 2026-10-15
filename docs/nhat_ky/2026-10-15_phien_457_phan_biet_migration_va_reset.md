# Phân biệt migration với reset dữ liệu

## Mục tiêu và kết luận

Người dùng nhớ app có chức năng xóa dữ liệu và tạo lại khi chuẩn bị triển khai. Kiểm tra theo hướng dẫn backend/clean code: có script reset riêng, nhưng migration và Compose bootstrap không tự gọi nó.

- `make migrate` gọi CLI db migrate; `make seed` và Compose bootstrap gọi CLI db bootstrap. Migration upgrade head, tạo DB nếu thiếu trong đường ensure, không drop DB hay truncate toàn bộ. Bootstrap migration rồi seed, không reset. Một số migration có thay đổi/dọn dữ liệu cụ thể, không đồng nghĩa mọi dữ liệu được giữ bất biến.
- `make reset-db` và alias `make reseed` gọi `backend/scripts/reset_and_reseed.py`. Script ngắt client connections trong DB đích, truncate tất cả bảng schema public trừ alembic_version, migration head, xóa tất cả collections ở Qdrant endpoint, seed và verify.
- Script không drop/create database, không xóa schema hoặc lịch sử Alembic, không dọn MinIO/files/Redis. Có thể ảnh hưởng bảng ngoài QNU nếu dùng chung database/public và collection ngoài QNU nếu dùng chung Qdrant. Script chưa có xác nhận target/confirmation phù hợp production và có warning/continue khi dọn Qdrant lỗi. Không khuyến nghị chạy nguyên bản trên hạ tầng dùng chung.
- Dockerfile production hiện không COPY `backend/scripts` hoặc Makefile; Make targets cũng dùng Python path Windows. Vì vậy không giả định có sẵn reset script/lệnh Make trong container Dokploy. Muốn reset server cần tác vụ một lần, scope/guard/backup cụ thể, không gắn tự động vào Deploy.

## Phạm vi thay đổi và kiểm chứng

Chỉ đọc Makefile, CLI, reset script, entrypoint, Alembic env và Docker/Compose; không import/chạy script, migration, seed hay truy cập DB/server. Không sửa runtime. Không Ruff/Pytest/Vite vì chỉ chẩn đoán và ghi docs. Nhật ký, snapshot, PROJECT_CONTEXT và hai mục lục được cập nhật. Bài học: tên reseed có thể che phạm vi phá hủy, luôn đọc call graph và targets trước khi hướng dẫn thực thi.
