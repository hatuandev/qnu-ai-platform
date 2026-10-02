# Phiên #242 — Rà soát xoay khóa API từ giai đoạn 1 đến 3

- Ngày: 2026-10-02 (UTC+7)
- Yêu cầu: rà soát lại toàn bộ ba giai đoạn và xử lý lỗi phát hiện.

## Phát hiện và sửa

1. SQLAlchemyError/StopAsyncIteration trước đây có thể bị xem là chưa migration, rồi rollback session và fallback JSONB. Đã bỏ việc che lỗi CSDL và điều kiện dành riêng cho mock trong production; cập nhật fixtures phản ánh COUNT đúng kiểu.
2. Dự toán token quá lớn từng làm hết quota vĩnh viễn dù còn số dư. Đã tách điều kiện đủ quota cho request khỏi trạng thái quota thực tế ở cả relational và JSONB.
3. Khóa primary do migration tạo không có JSONB nên API sửa/kiểm tra có thể không tìm thấy. CRUD đọc snapshot relational trước; xóa và kiểm tra cùng dùng nguồn khóa đó.
4. Import chỉ ghi JSONB, runtime có thể tiếp tục dùng khóa cũ. Đã bổ sung đồng bộ relational, bảo toàn usage/cooldown của khóa không đổi và xóa lease/reset state khi thay credential.
5. Hủy chat/embedding/reranker/OCR không giải phóng khóa ngay. Đã bổ sung xử lý cancellation. Streaming chat gia hạn ownership khi tiếp tục nhận token; lease có thêm khoảng đệm timeout.
6. Hard quota nhận diện theo mã cấu trúc cho 402/403/429; UI kết quả thử được ghi đúng là mô phỏng, bỏ emoji.

## Bằng chứng kiểm tra

- 80 kiểm thử trọng điểm passed, gồm lỗi DB, phân loại quota, lease renewal/cancellation và streaming không tự chạy lại sau khi đã phát token.
- Kiểm tra PostgreSQL với provider riêng: request lớn/nhỏ theo quota; 3 session đồng thời không nhận trùng khóa; request thứ tư không lấy khóa bận; 1 → 2 → 3 khi hai khóa đầu gặp 429; history và quota ghi đúng; sửa primary không có JSONB; import đồng bộ secret và giữ state khóa khác.
- Dữ liệu provider thử được xóa theo ID ngẫu nhiên của riêng phép thử, cascade xóa keys/events. Không gọi API provider bên ngoài.
- Frontend build và TypeScript: đạt. Biome trên file UI sửa: đạt. Ruff trên các file sửa: đạt.
- Full suite cuối: 504 passed, 5 failed. Tên lỗi trùng lần chạy trước ở admissions agentic, consulting dispatcher, hai fact lookup và universal tools. Không sửa các lỗi nghiệp vụ này trong phạm vi xoay khóa.
- Full Ruff: 32 lỗi ở script/scratch hiện hữu. Lỗi quyền thư mục tạm ở lần chạy pytest đầu được khắc phục bằng basetemp mới trong workspace.

## Giới hạn cần giữ rõ

- Thử Failover là mô phỏng; chưa gửi request để gây 429 thật tới provider.
- Token streaming hiện ước lượng theo độ dài ký tự.
- Chưa có chính sách tự xóa history. Batch embedding/OCR rất dài vẫn cần heartbeat lease độc lập; kiểm tra lần này không chứng nhận tải dài đó.
