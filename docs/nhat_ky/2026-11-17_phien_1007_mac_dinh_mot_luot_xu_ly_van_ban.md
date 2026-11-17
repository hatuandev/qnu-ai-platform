# Phiên 1007 — Mặc định xử lý một phần tại một thời điểm

Các lượt biên soạn và rà soát mới ghim mức đồng thời mặc định là 1. Bộ lập lịch biên soạn cũng dùng mức 1 khi lượt thiếu giá trị đã ghim. Lượt có giá trị đã ghim tiếp tục dùng giá trị đó trong giới hạn vận hành hiện hành. Mức mặc định của tác vụ tài liệu và giới hạn ModelOps dùng chung là hai thiết lập riêng.

Phần cấu hình UI đang được triển khai ở đợt riêng. Khi nối UI, lấy model theo từng bước và mức đồng thời của model đã chọn từ cấu hình toàn hệ thống. Dùng mức 1 khi chưa có cấu hình phù hợp. Mức có hiệu lực vẫn chịu các trần vận hành, quyền và quota hiện hành. Giữ thông số đã ghim khi tiếp tục một lượt cũ.

## Kiểm chứng

- Ruff theo phạm vi và ba nhóm unit test lập lịch, chia phần rà soát và ngân sách đã đạt 41 ca.
- Hai ca tích hợp về rà soát nhiều phần và model chỉ định riêng đã đạt trên cơ sở dữ liệu cô lập. Chạy lại ca rà soát nhiều phần với assertion mới xác nhận trace ghim mức 1 và báo cáo kiểm đủ nội dung. Hai cơ sở dữ liệu thử đều được dọn.
- Bộ đầy đủ và luồng cấu hình qua UI sẽ được kiểm ở cuối đợt triển khai chung.
