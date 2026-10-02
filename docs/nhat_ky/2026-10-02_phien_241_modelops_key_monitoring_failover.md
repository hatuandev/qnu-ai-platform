# Phiên #241 — Giám sát khóa API và lịch sử Failover

- Ngày: 2026-10-02 (UTC+7)
- Phạm vi: giai đoạn 3 được người dùng phê duyệt.

## Triển khai

1. Bảng sự kiện theo provider, index cho truy vấn lịch sử; ghi chọn/chuyển khóa, kết quả thành công và lỗi chuẩn hóa trong cùng giao dịch cập nhật khóa.
2. API lịch sử giới hạn 1–100 sự kiện; mặc định 30. API mô phỏng chỉ đọc dữ liệu, không gọi provider, không ghi quota.
3. Giao diện Khóa API thêm lịch sử, trạng thái đang dùng, cooldown và lỗi liên tiếp; tự cập nhật 10 giây, hiển thị lỗi tải dữ liệu và hỗ trợ thử lại.
4. Endpoint mô phỏng cũ vẫn tương thích, được đánh dấu deprecated và không còn thay đổi dữ liệu thật.
5. Migration khóa giai đoạn 2 và lịch sử giai đoạn 3 đã chạy thành công trên CSDL local.

## Kết quả kiểm tra

- Build frontend và TypeScript: thành công. Biome trên file frontend thay đổi: không lỗi.
- Ruff trên file backend thay đổi: không lỗi. Nhóm kiểm thử ModelOps/resolver/monitoring: 34 passed.
- Kiểm tra PostgreSQL thật: khóa 1 → 2 → 3 khi hai khóa đầu gặp 429, 6 sự kiện và 42 token được ghi đúng. Dữ liệu thử được rollback hoàn toàn, không gửi request ra provider.
- API local mới: HTTP 200, mô phỏng có `dry_run=true`.
- Full pytest: 495 passed, 5 failed. Tên lỗi trùng phiên #240 ở admissions/facts/artifact; chưa sửa trong phạm vi giai đoạn 3. Full Ruff còn 32 lỗi ở script/scratch ngoài phạm vi.

## Giới hạn và vận hành

- Thử Failover trên UI là dự đoán thứ tự chọn khóa tại thời điểm kiểm tra; không phải kiểm tra 429 thật từ provider. Lease, quota và trạng thái có thể thay đổi khi các request khác chạy đồng thời.
- Lịch sử bắt đầu từ khi migration và mã mới được sử dụng, không tạo dữ liệu lịch sử giả cho các request cũ.
- Môi trường triển khai khác cần áp dụng migration tới `20261002_provider_key_events`.
- Lịch sử hiển thị 30 sự kiện mới nhất; chưa bổ sung chính sách tự xóa sự kiện cũ.
