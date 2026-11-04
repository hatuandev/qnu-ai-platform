# Phiên 862 — Đối chiếu biên soạn nhanh

- Tạo một lượt nháp mới trên app V1 local bằng POST compilation-runs với `source_first=true` và `auto_review=false`. Ghim lại đúng bản bóc tách gốc của lượt AI, kiểm tra cả revision và hash qua GET draft.
- PASS qua API thật. Lượt nhanh hoàn tất sau 0,85 giây tính từ lúc nhận yêu cầu, xử lý worker 0,39 giây, không gọi model. Lượt AI đã có dùng 145.578 token và xử lý 130,44 giây.
- PASS đối chiếu 171/171 khối chữ và 13/13 bảng theo cùng bản bóc tách. Hai bảng quy đổi được giữ riêng, phụ lục có trong bản nháp, số và ngày ban hành vẫn nằm ở các khối chữ riêng.
- Phạm vi kiểm là tạo bản nháp và đối chiếu dữ liệu. Review AI, phát hành, lập chỉ mục và kiểm thử RAG chưa chạy.
