# Phiên 1008 — Khởi tạo gọn migration Backend V1

## Phạm vi

Tinh gọn `v1-migrate` cho database chưa có schema V1. Giữ chuỗi Alembic đã phát
hành để nâng cấp database có revision và để đối chiếu. `v1-db-check` thực hiện
giao dịch chỉ đọc.

Bản SQL đóng băng từ PostgreSQL 16.16 ở revision `0031_spelling_defaults`. Khi
head khớp bản gộp và schema hiện tại là `public`, lệnh áp dụng SQL và ghi revision
trong cùng một giao dịch có khóa. Nếu đã có revision, Alembic chạy đúng các bước
còn thiếu. Khi head đổi, lệnh dùng chuỗi migration cho đến khi có bản gộp mới.

## Kiểm chứng

- Từ root, `python -m unittest discover -s scripts/tests -p test_run_v1.py` đạt
  25 ca. `make.ps1 dev --dry-run` trỏ đúng API V1, worker V1 và Vite FE V2.
- Từ `backendV1`, Ruff trên các file Python thay đổi đạt. Bộ kiểm tra migration
  qua `scripts/run_isolated_tests.py` đạt 6 ca. Thử `current` trên DB trống và
  bảng version VARCHAR(32), khởi tạo lặp, giữ bảng legacy, rollback khi trùng
  index, nâng cấp từ 0004 kèm chuyển khóa và giữ ciphertext mẫu.
- Hai database thử tạo bằng chuỗi và bằng bản gộp có 63 bảng ứng dụng. DDL
  `pg_dump --schema-only` khớp sau khi chuẩn hóa biểu diễn tương đương của ép
  kiểu mảng literal. Lần đo có khởi động tiến trình gần 6 giây ở cả hai đường.
- Kiểm tra ban đầu phát hiện test offline cấm mọi `DROP TABLE` dù revision 0027
  chủ đích gỡ hai bảng cấu hình model theo đơn vị. Đã kiểm đúng danh sách hai
  bảng. Test ORM riêng cũng thiếu đăng ký model công khai và mặc định chính tả.
- `make.ps1 v1-db-check` báo `0031_spelling_defaults (head)`. Kiểm tra hạ tầng
  của `dev` đạt. DDL chỉ chạy trên DB thử, phiên này chỉ đọc DB đang cấu hình.
- Full suite backend được khởi chạy cô lập. Kết quả chưa có tại thời điểm ghi.

Xem [hướng dẫn migration](../../backendV1/docs/migrations.md).
