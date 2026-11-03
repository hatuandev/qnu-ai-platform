# Phiên 844 — Khung PDF nhấp nháy

Tái hiện trên Chrome với app V1 local: 23 yêu cầu tải tệp gốc trong 12 giây,
PDF worker liên tục bị hủy. Tắt Suspense ở Document/Page để trạng thái tải
nằm trong khung PDF thay vì làm ẩn nội dung route.

Chrome sau sửa: 1 tải hoàn tất, 1 yêu cầu khởi động bị hủy, 0 cảnh báo worker
bị hủy, canvas hiển thị trong cả 30 mẫu đo. Vitest preview 9 PASS, Biome PASS.
