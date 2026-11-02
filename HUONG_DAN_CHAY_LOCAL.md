# Chạy QNU V1 trên laptop

Lệnh mặc định đã chuyển sang V1: API8002, frontend3001 và worker riêng.

```powershell
Set-Location D:\DuAnPhanMem\qnu-ai-platform
.\make.ps1 check
.\make.ps1 dev
```

Giữ cấu hình `.env` đang dùng và hạ tầng Docker hiện có. Nếu hạ tầng đang dừng, dùng `.\make.ps1 infra-up` sau khi kiểm cấu hình; không reset DB/volume.

Máy mới, cấu hình SSO/ModelOps, migration và xử lý lỗi: [hướng dẫn đầy đủ V1](docs/quy_trinh/38_huong_dan_chay_qnu_v1.md).

`dev` không mở cửa sổ ẩn, không tự dừng app đang có và không tự migrate/seed. Ctrl+C dừng các thành phần của phiên vừa mở. Có thể chạy `be`, `worker`, `fe` ở ba cửa sổ nếu cần log riêng. Tên `v1-*` vẫn dùng được.

Đã chuyển các runner root, nhưng chưa xóa thư mục legacy hoặc dữ liệu. Đường triển khai server khác local: xem [Docker/Dokploy V1](docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md).
