# Trang liên quan và đối chiếu tri thức

## Người dùng tài liệu

1. Mở nguồn trong kho tri thức, chọn đúng bản cần xem.
2. Trong **Nội dung → Trang tri thức**, chọn **Xem trang**.
3. Bấm **Xem nguồn** để đọc nguyên văn, gồm bảng, năm, điều kiện và ngoại lệ.
4. **Trang liên quan và liên kết ngược** dẫn tới các nguồn đang được phép phục vụ.
   Liên kết giữ đúng bản nguồn; xem năm dữ liệu và năm ban hành ở từng trích đoạn.

Các nguồn cùng nhắc một tên chưa chắc nói về cùng đối tượng. Đối chiếu mã, cơ
quan, năm và điều kiện trước khi dùng số liệu. Một ký hiệu chưa được định nghĩa
vẫn giữ nguyên, không tự đổi thành0.

Không có trang liên quan không có nghĩa bản nguồn mất dữ liệu. Tài liệu đã
chuẩn hóa và đạt chất lượng tiếp tục theo luồng nạp vector/phục vụ hiện có.
Người dùng phổ thông không cần duyệt từng gợi ý liên kết.

## Người quản trị có quyền đối chiếu

Chọn **Đối chiếu nâng cao** để xem kết quả kiểm tra của bản đang mở và bản đồ
đang phục vụ. Nút này chỉ xuất hiện khi tài khoản có quyền tương ứng.

| Thông báo | Cách xử lý |
|---|---|
| Cần xử lý | Đối chiếu tệp gốc, mã/số, span/hash hoặc liên kết nguồn; giữ chặn toàn vẹn hiện có. |
| Cần đối chiếu | Kiểm năm, đối tượng và điều kiện trong từng nguồn; chưa kết luận là mâu thuẫn. |
| Giới hạn nguồn | Giữ nguyên phần chưa biết; không diễn giải thành giá trị chắc chắn. |
| Gợi ý chưa xác minh | Chỉ là gợi ý tìm nguồn hoặc alias; không tự hợp nhất đối tượng/facts. |
| Lỗi biên soạn | Xem mã lỗi và cấu hình ModelOps/hạ tầng theo quy trình hiện có; không coi là thiếu dữ liệu. |
| Chưa sẵn sàng | Kiểm revision đang xem; không tự ghi đè bundle hoặc xuất bản lại. |

Các màn hình xem/đối chiếu không sửa dữ kiện hoặc quyền xuất bản và không gọi
model. Không cần ghi chú kỹ thuật để mở trang. Khi báo phạm vi đã thay đổi,
tải lại để nhận snapshot hiện hành, không dùng cache cũ như dữ liệu hợp lệ.

## Khi cập nhật tài liệu

Revision cũ giữ nguyên lịch sử. Bản mới không đổi nội dung và đủ điều kiện sẽ
tái dùng trang với căn cứ phiên bản mới. Nội dung đổi được biên soạn trong
pipeline của riêng nguồn đó. Nguồn bị gỡ/thu hồi không còn trong điều hướng được
phép phục vụ. Việc rollback phải theo quy trình có quyền hiện có.

Phiên600 chỉ thay mã và kiểm thử. Không biên soạn lại kho đang chạy, không nạp
lại vector hoặc xuất bản. Kho hiện đang staging có thể chưa có liên kết xuyên
nguồn ở map phục vụ; vẫn xem được trang và đối chiếu revision riêng có quyền.
