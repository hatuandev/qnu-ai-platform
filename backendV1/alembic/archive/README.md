# Bản lưu migration phát triển trước baseline

`0001-0015_20261027.zip` chứa nguyên bytes15file migration cũ, từ `0001_baseline`
đến `0015_resource_lifecycle`. Alembic không nạp thư mục này.

SHA-256 của ZIP:
`8e7ead7f15b3c485f3a551859bba691339abd4e1f0d4d73c1ba3e1e492050639`.

Baseline hiện hành là `../versions/0001_initial_schema.py`. Không giải nén ZIP
vào `versions` rồi chạy trên DB mới: hai chuỗi dùng revision khác nhau và sẽ tạo
cùng schema. Archive chỉ phục vụ đối chiếu/khôi phục nguồn hoặc lập kế hoạch
chuyển tiếp cho một DB thật còn ở revision cũ. Không chứa dữ liệu hay credential.

Xem [hướng dẫn migration](../../docs/migrations.md).
