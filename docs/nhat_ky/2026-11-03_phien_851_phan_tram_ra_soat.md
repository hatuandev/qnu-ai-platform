# Phiên 851 — Phần trăm tiến độ rà soát

Thêm số phần trăm vào thanh tiến độ hiện có. Giao diện tính từ số nhóm hoàn tất chia cho tổng số nhóm do máy chủ trả về, làm tròn xuống để chỉ hiện 100% khi tất cả nhóm hoàn tất. Nếu chưa có tổng số nhóm, giao diện ẩn phần trăm.

Kiểm tra Biome hai tệp thay đổi và Vitest `tests/compilation-review-progress-850.test.tsx` trong `frontendV1` đều đạt, với 6/6 ca.
`npm run build` đạt. Còn cảnh báo kích thước bundle. Chưa kiểm tra trực quan trên trình duyệt.
