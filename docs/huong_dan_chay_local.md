# Hướng dẫn local — V1

Lệnh root đã chuyển sang `backendV1` và `frontendV1`. Xem [hướng dẫn V1 hiện hành](quy_trinh/38_huong_dan_chay_qnu_v1.md) để thiết lập, migration và chạy API8002/frontend3001/worker.

```powershell
.\make.ps1 check
.\make.ps1 dev
```

Không chạy hướng dẫn legacy để bootstrap hoặc reset dữ liệu. Giữ DB, bucket, provider encryption key và nguồn tài liệu hiện có. Production dùng [quy trình Dokploy](trien_khai/02_quy_trinh_trien_khai_dokploy.md).
