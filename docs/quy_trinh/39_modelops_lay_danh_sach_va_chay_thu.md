# ModelOps V1 — Lấy danh sách và chạy thử model

Chức năng dành cho quản trị ModelOps. “Lấy danh sách” là hỏi server có những
model nào; không tải weights hoặc cài model vào máy.

1. Vào **ModelOps → Providers**, thêm/chọn provider và lưu khóa tại API keys.
   Mỗi bản ghi gắn với một model và những chức năng đã khai báo.
2. Tại **Kiểm tra provider**, bấm **Lấy danh sách model**. Có tên trong danh
   sách chưa có nghĩa model chạy được.
3. Chọn tên rồi bấm **Sửa cấu hình** nếu muốn đổi. Xem lại model, chức năng và
   capacity rồi **Lưu thay đổi**. Hủy không đổi dữ liệu.
4. Bấm **Thử Chat/Embedding/Rerank/OCR** theo chức năng đã khai báo. QNU dùng
   mẫu nhỏ tự tạo, không lấy tài liệu của bạn. Server có thể tính phí lượt gọi.
5. Đọc kết quả: ngày/giờ, thành công/thất bại/chưa hỗ trợ, độ trễ, lỗi/HTTP,
   model server báo và dimension/token nếu đo được.
6. Đổi endpoint/model/khóa khiến kết quả cũ hiện **Cần thử lại**. Đây là lịch
   sử kiểm tra, không phải giám sát liên tục.

| Kết quả | Cách xử lý |
| --- | --- |
| Thiếu khóa | Thêm/xoay khóa qua ModelOps |
| HTTP401/403 | Kiểm tra credential và quyền tại đúng server |
| HTTP429 | Chờ theo thời điểm server đề nghị thử lại, nếu có |
| Không kết nối được/hết thời gian | Kiểm tra server/mạng/timeout; hệ thống không tự gửi lại |
| Phản hồi sai hợp đồng | Kiểm tra đúng model, chức năng và endpoint |
| Cần thử lại | Chạy lại cho cấu hình/khóa mới |
| Chưa hỗ trợ | Adapter kiểm tra cho loại provider/chức năng này chưa triển khai |

Server QNU được người dùng cung cấp có base URL
`http://100.105.13.53:8000/v1`; discovery gọi `/models`. Ngày28/10/2026 server
liệt kê `bge-m3`, `bge-reranker-v2-m3`, `qwen3.8-27b-q4`, `nemotron-parse`.
Danh sách có thể đổi; dùng nút lấy lại để xem hiện trạng. Khóa lưu mã hóa trong
ModelOps DB, không đưa vào tài liệu hoặc cấu hình FE.

Chạy thử không tự cấp model cho workspace hoặc thay mặc định. Sau đó vẫn khai
báo capacity, cấp provider, chọn default và quota theo [hướng dẫn V1](38_huong_dan_chay_qnu_v1.md).
Không suy context tối đa hay độ chính xác OCR/RAG từ một mẫu thử.
[Hợp đồng BE](../../backendV1/docs/modelops-diagnostics.md).
