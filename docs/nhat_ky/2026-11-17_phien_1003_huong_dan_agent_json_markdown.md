# Phiên 1003 — Cập nhật hướng dẫn agent về JSON và Markdown

Người dùng yêu cầu ghi lại kết luận về hiệu quả của hai tệp liên kết để các phiên sau nắm đúng luồng.

- `AGENTS.md` ghi nguyên tắc giữ hai tệp cùng phiên bản, giữ ánh xạ dẫn chứng và dùng ngân sách model cho phần cần rà soát. Vai trò xử lý tài liệu có thêm cách kiểm hash, độ phủ và nguồn lập chỉ mục khi phát hành.
- Số đo tham chiếu trên cùng bản nháp DOCX phức tạp và cùng cấu hình Qwen ở phiên 1000 là 5 → 1 lượt, 102.050 → 10.094 token, 118,55 → 56,72 giây. Đây là kết quả kết hợp liên kết theo khối với cách backend đối chiếu nguyên văn và chọn ngữ cảnh trên mẫu đó. [Kết quả gốc](2026-11-17_phien_1000_lien_ket_json_markdown.md)
- Ba lượt thật ở phiên 1002 đều hoàn tất rà soát trong một lượt Qwen. Thời gian hai PDF tăng trong lượt đo có thời gian chạy chồng nhau. Cơ chế chia khối dài đã kiểm trên văn bản giả lập 45.000 ký tự. [Phiên 1002](2026-11-17_phien_1002_khoi_phuc_ngay_va_lich.md) · [Phiên 995](2026-11-17_phien_995_ra_soat_khoi_van_ban_dai.md)

Kiểm chứng phiên này gồm `git diff --check`, đọc lại UTF-8, kiểm LF của dòng mới, kiểm đích liên kết và đối chiếu các trường hợp xử lý với quy trình hiện hành. Kiểm thử ứng dụng và gọi model thuộc các phiên được dẫn ở trên.
