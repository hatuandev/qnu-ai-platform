# Migration Backend V1

Revision hiện tại là `0033_document_model_group`. Từ thư mục gốc trên Windows, dùng:

```powershell
.\make.ps1 v1-db-check
.\make.ps1 v1-migrate
.\make.ps1 v1-db-check
```

`v1-db-check` đọc revision trong giao dịch PostgreSQL chỉ đọc. Database mới chưa
có revision sẽ trả về kết quả trống. `v1-migrate` áp dụng thay đổi schema cho
database đã được chọn. Khi kiểm tra thấy `0033_document_model_group (head)`, có thể
chạy `.\make.ps1 dev` để mở Backend V1, worker và Frontend V2.

## Khởi tạo và nâng cấp

- **Database chưa có schema V1.** Với schema mặc định `public` và bản gộp nằm
  trong chuỗi hiện hành, `v1-migrate` tạo schema trực tiếp từ
  [bản SQL 0031](../alembic/baselines/0031_spelling_defaults.sql) và ghi
  `alembic_version_backendv1` trong cùng một giao dịch, rồi chạy các revision
  còn thiếu. Nếu phát hiện bảng V1
  đã tồn tại ngoài lịch sử, lệnh dừng. Bảng và revision của backend legacy
  được giữ nguyên.
- **Database đã có revision V1.** Alembic chạy đúng các revision còn thiếu,
  gồm các bước chuyển dữ liệu. Nếu revision không có trong chuỗi hiện hành,
  cần kiểm tra lịch sử trước khi nâng cấp. Giữ bản sao lưu cho database đã
  có dữ liệu.
- **Kiểm tra chuỗi đầy đủ.** Từ `backendV1`, chạy `uv run alembic upgrade head`
  trên database thử đã cấu hình. Khi gọi Alembic trực tiếp và cần đường
  khởi tạo nhanh, dùng `uv run alembic upgrade head --tag qnu-bootstrap`.
  `alembic upgrade head --sql` dùng để xem
  DDL lịch sử, vì một số bước chuyển dữ liệu chỉ chạy online.

Bản gộp là DDL đóng băng từ `pg_dump --schema-only --schema=public --no-owner
--no-privileges --exclude-table=public.alembic_version_backendv1` trên database
cô lập đã chạy toàn bộ chuỗi đến 0031. Khi tạo bản gộp mới, bỏ phần cấu hình
phiên dump và lệnh tạo schema `public`, sau đó so sánh schema của hai đường khởi
tạo trên PostgreSQL thử nghiệm. Kiểm tra nâng cấp với dữ liệu mẫu, bảo toàn bảng
legacy, rollback khi xung đột và chạy lại ở head. Database test có tiền tố
`qnu_v1_test_`.

## Lịch sử revision

Chuỗi hiện hành giữ nguyên `0001_initial_schema` và các revision đã phát hành.
Bản gộp chỉ bổ sung đường khởi tạo, các thay đổi schema tiếp theo dùng revision mới.
Các migration phát triển trước khi đóng băng `0001_initial_schema` ngày
2026-10-27 nằm trong [ZIP lưu trữ](../alembic/archive/0001-0015_20261027.zip).
Nếu database còn trỏ đến một revision phát triển đã lưu trữ, cần lập đường
chuyển tiếp theo schema và dữ liệu thực tế. Chuyển revision bằng tay không thực
hiện các bước chuyển dữ liệu.
