# Context558 — Hướng dẫn nạp tài liệu

1. Tải DOCX hoặc PDF lên kho tài liệu/kho tri thức theo quyền hiện có.
2. Hệ thống tự chuẩn hóa và kiểm tra nội dung. Bạn không phải đọc 18 issue hay xác nhận từng assertion.
3. Xem trạng thái:
   - **Sẵn sàng nạp vector:** nội dung đạt kiểm tra.
   - **Sẵn sàng, có giới hạn dữ liệu:** một số ô được giữ nguyên vì chưa đủ căn cứ sử dụng giá trị; hệ thống không tự điền số.
   - **Nội dung cần kiểm tra:** mở danh sách ngắn để biết lỗi thực sự cần xử lý.
4. Nhấn **Xem Markdown** nếu muốn kiểm tra kết quả, rồi **Nạp vector** và chọn chỉ mục/model embedding đang được phép sử dụng.
5. Nạp xong là **Đã nạp · Chờ xuất bản**. Chỉ khi người có quyền thực hiện xuất bản và hệ thống kiểm tra đạt, chatbot mới dùng bản này.

## Khi nào cần đối chiếu nâng cao?

Quản trị dùng **Đối chiếu nâng cao** khi cần xem bằng chứng, xác định quan hệ có điều kiện hoặc sửa nội dung. Smart Approval và quyết định ngữ nghĩa ở đây không phải bước bắt buộc của nội dung mới đã đạt kiểm tra tự động. Áp dụng diễn giải vẫn phải tuân thủ revision nháp, quyền và hash.

## Dữ liệu cũ

Nguồn Context557 và checkpoint Context552–557 được giữ nguyên. Luồng mới không tự chuyển bản cũ sang ready hoặc tự duyệt proposal đang yêu cầu sửa. Muốn chuyển bản cũ qua pipeline mới phải có thao tác tạo/reparse revision phù hợp; phiên này không tự chạy lại tài liệu thật.

## Giới hạn nghiệm thu

Các ca tích hợp dùng DOCX/PDF thực tạo trong test, PostgreSQL riêng và Storage tạm. Adapter embedding/Qdrant được thay tại ranh giới test; chưa nghiệm thu embedding provider thật hoặc hội thoại LLM thật. Giao diện thật chỉ được mở để quan sát, không gửi quyết định/nạp vector/xuất bản nguồn của bạn.
