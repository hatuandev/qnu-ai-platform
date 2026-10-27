# 31 — Dừng, thu hồi, thay thế và khôi phục backendV1

Áp dụng riêng cho backendV1. Workspace là biên quyền membership/role của đơn vị;
không thay chính sách dữ liệu chung của backend cũ.

## Tài liệu cũ không còn được sử dụng

1. Chọn tài liệu nguồn, văn bản biên soạn hoặc cả kho.
2. Xem trước ảnh hưởng đến publication, tác vụ và phạm vi chatbot/hội thoại.
3. Xác nhận lưu trữ hoặc đưa vào thùng rác bằng actor có quyền.
4. BE hủy tác vụ liên quan đang chờ/chạy và chặn nội dung ở API, retrieval/citation.
   File gốc, raw OCR, Markdown/JSON và lịch sử vẫn được giữ.
5. Nếu cần thu hồi publication theo nghiệp vụ, dùng luồng quyết định `withdraw`.
6. Có thể dọn vector/chunk của generation không còn phục vụ. Chỉ mục active còn
   nội dung hợp lệ được bảo vệ; chỉ mục không còn tài liệu khả dụng được retire
   trước khi dọn. Lỗi bên ngoài giữ thao tác chờ để gửi lại cùng key.

## Nạp bản mới và chuyển sang sử dụng

Nạp revision với `staged=true` → OCR → sửa hậu OCR nếu cần → Compiler → review →
đăng ký và duyệt phiên bản → xem trước/xác nhận thay thế → tạo index mới → chuyển
publication, serving revision và active index trong transaction cuối.

Bản cũ vẫn phục vụ đến khi chuyển thành công. Nếu xử lý thất bại, bản cũ còn
hiệu lực. Nguồn dùng chung nhiều văn bản có kiểm tra xung đột, chưa hỗ trợ thay
đồng loạt nhiều compiled document trong một action.

## Chatbot và hội thoại

- Dừng/bật chatbot không đổi revision cấu hình; hội thoại cũ có thể tiếp tục sau
  khi bật lại. Thay persona/model/cấu hình thực sự vẫn yêu cầu hội thoại mới.
- Lưu trữ/xóa chatbot làm chatbot và hội thoại liên quan không truy cập theo luồng
  bình thường. Khôi phục giữ chatbot tắt, cần bật riêng.
- Chủ hội thoại lưu trữ/xóa/khôi phục hội thoại của mình. Quản trị không thay thế
  quyền sở hữu để xem hoặc xóa hội thoại của người khác.
- Hủy có trạng thái bền vững và chặn kết quả muộn. Server AI có thể tiếp tục tính
  toán request đã nhận; token có số đo vẫn ghi nhận, phần chưa rõ không thành 0.

## Khôi phục

Xem trước và xác nhận khôi phục bằng quyền phù hợp. Kiểm tra kho cha, trạng thái
nguồn và chỉ mục. Nếu generation đã bị dọn hoặc không chứa đủ phiên bản được
khôi phục, tạo generation mới. Tác vụ đã hủy không tự chạy lại.

Hợp đồng endpoint, trường dữ liệu, role, idempotency và giới hạn:
[API vòng đời ngược](../../backendV1/docs/resource-lifecycle.md).

Migration và việc khởi động API/worker mới là bước vận hành riêng. Thay đổi mã
không tự xóa tài liệu hay dọn corpus đang phục vụ.
