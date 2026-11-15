# Triển khai QNU V1

Ứng dụng hiện hành: `backendV1/` và `frontendV2/`.

- [Chạy local V1](quy_trinh/38_huong_dan_chay_qnu_v1.md): API8002, Frontend V2 ở 3002, worker riêng.
- [Docker và Dokploy](trien_khai/02_quy_trinh_trien_khai_dokploy.md): Compose backend/worker V1, migration một lần và SSO; service frontend đóng gói sẵn nhưng nằm sau profile `frontend` (chưa bật vì thiếu SSO production).
- [Kênh chatbot công khai](trien_khai/06_kenh_chatbot_cong_khai.md): checklist bật `/chatbot/{slug}`, domain/TLS, kiểm chứng header nhúng và test iframe thật.
- Root `.env.example`: template local; `.env.dokploy.example`: template production.

Không chép template đè khóa thật, reset DB hoặc tự chuyển dữ liệu legacy. Xóa mã cũ và chuyển dữ liệu là các thao tác riêng sau khi kiểm backup, dependencies và smoke test V1.
