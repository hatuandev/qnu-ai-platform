# Phiên 867 — Truy xuất danh sách theo tiêu đề nguồn

Lượt chat đầu bị đổi thành câu hỏi định nghĩa. Năm kết quả Dense đưa được bốn mục vào ngữ cảnh và bỏ sót hai mục trong cùng danh sách có trong PDF. Đánh giá của model tự yêu cầu thêm mã ngành.

- Router v3 giữ nguyên câu hỏi khi chưa có câu hỏi nghiệp vụ trước. Vẫn phân loại lời chào và làm rõ lượt nối tiếp.
- Kế hoạch cấu trúc v2 nhận danh sách gạch đầu dòng dưới tiêu đề nguồn đã ghim, giữ các dòng nối và giới hạn ở cùng mục. Tiếp tục kiểm quyền, phạm vi metadata, dẫn chứng và ngân sách.
- Prompt trả lời v18 đánh giá các yêu cầu thực tế của người dùng và chi tiết cần thiết để kết luận.

## Kiểm chứng

- Trong `backendV1`, pytest cho các nhóm unit coverage, routing, answer contract, clause context và projection đạt 49 ca. Ca mới ban đầu tái hiện lỗi. Ruff check và format check trên 8 tệp Python đạt. Từ root, harness DB cô lập chạy 2 ca hội thoại và `test_answer_coverage_861.py` đạt 6 ca, exit 0 và đã dọn DB.
- Phát lại gom dẫn chứng với năm kết quả đã lưu của lượt lỗi, trên chỉ mục hoạt động và nguồn đã phát hành. Cả hai ngân sách 16.000 và 32.768 byte chứa đủ sáu mục, với 15 block nội dung và gói dẫn chứng 10.749 byte. Đối chiếu không gọi model và transaction được rollback.
- Full backend qua `make.ps1 test-be` đang chạy lúc ghi nhận. Chưa nghiệm thu câu trả lời sinh từ model thật sau thay đổi.
