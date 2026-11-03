# Phiên 842 — Trang tài liệu và thống kê sử dụng V1

Giữ URL rút gọn khi cập nhật tham số trang, phiên bản và lượt OCR để tránh điều
hướng lặp. Kiểm tra với router bộ nhớ và các ca preview hiện có.

Gỡ yêu cầu cấu hình quota tháng khỏi thực thi ModelOps và readiness. Kỳ sử dụng
tự tạo khi reserve. Giữ thống kê, idempotency, quyền và giới hạn vật lý của model.
API PUT quota cũ được đánh dấu deprecated và chỉ khởi tạo kỳ thống kê tương thích.
Màn Mức sử dụng chỉ đọc. Không cần migration.

Ruff và Biome có phạm vi đạt. Vitest 46 ca trọng tâm đạt, trong đó hai ca router
được mở rộng để kiểm tra URL không dao động và đã chạy lại đạt. Không gửi tài liệu
đến provider thật trong phiên sửa.

Harness DB cô lập: 4 ca MinerU/đổi tháng/ghi nhận đồng thời/readiness đạt,
2 ca compiler review/indexing với giới hạn cũ đạt. Full backend được khởi chạy
trong DB cô lập, chưa có kết quả tổng tại thời điểm bàn giao.
