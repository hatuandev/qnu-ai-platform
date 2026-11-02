# Triển khai QNU V1

Ứng dụng mặc định: `backendV1/` và `frontendV1/`.

- [Chạy local V1](quy_trinh/38_huong_dan_chay_qnu_v1.md): API8002, frontend3001, worker riêng.
- [Docker và Dokploy](trien_khai/02_quy_trinh_trien_khai_dokploy.md): Compose ứng dụng V1, migration một lần và SSO.
- Root `.env.example`: template local; `.env.dokploy.example`: template production.

Không chép template đè khóa thật, reset DB hoặc tự chuyển dữ liệu legacy. Xóa mã cũ và chuyển dữ liệu là các thao tác riêng sau khi kiểm backup, dependencies và smoke test V1.
