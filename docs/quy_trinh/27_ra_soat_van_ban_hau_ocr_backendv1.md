# 27 — Rà soát văn bản hậu OCR backendV1

Đầu vào là OCR đã hoàn tất với bản gốc bất biến. Đầu ra là phiên bản văn bản
người dùng đã sửa, có Markdown/JSON đồng bộ và mapping về nguồn ban đầu.

Người dùng đọc đoạn → kiểm tra chính tả → xem gợi ý → sửa theo gợi ý hoặc tự sửa
→ lưu → đọc/tải bản sửa. Gợi ý không tự ghi dữ liệu. Màn hình sẽ trình bày văn bản
thay cho mã; theo xác nhận người dùng, giao diện làm sau, đợt này chỉ backendV1.

Backend kiểm quyền, version/hash và trước/sau; tạo cả JSON lẫn Markdown trên
BlobStore rồi xác minh trước khi commit. Lỗi một tệp giữ phiên bản hiện tại;
sửa đồng thời gây conflict thay vì ghi đè. Mỗi lần lưu có lịch sử, idempotency và audit.

ModelOps chat phát hiện ứng viên lỗi trong phạm vi người dùng chọn, có usage,
trace và trạng thái durable. Gợi ý sai schema/span/nguồn bị chặn; hạ tầng lỗi
được báo đúng. Cần giữ bản người dùng đang soạn khi lưu lỗi và không auto retry model.

Không ghi đè OCR gốc, không suy đã kiểm ảnh hoặc đã đúng chính tả, không thay
Compiler/publication/index đang ghim bằng chứng cũ. Từ [quy trình29](29_noi_hau_ocr_review_va_sua_compiler_backendv1.md),
Compiler chọn được số text version cụ thể; omission/0 dùng gốc, không tự lấy latest.

[Contract và quy tắc giao diện](../../backendV1/docs/ocr-text-review.md) ·
[Báo cáo651](../bao_cao/context651/REVIEW.md).

## Kiểm tra toàn tài liệu trên V1 (phiên831)

Nút **Kiểm tra chính tả** trên trang tài liệu mặc định chọn toàn bộ đoạn/ô có
chữ trong phiên bản đã lưu. Bấm **Bắt đầu kiểm tra** một lần; không cần mở từng
trang. Hệ thống tự chia theo trang, tối đa 20 đơn vị hoặc khoảng 8.000 ký tự
mỗi nhóm. Đây là quy tắc chia yêu cầu, không phải cam kết dung lượng token;
ModelOps và server vẫn kiểm tra giới hạn thực. Đơn vị dài được giữ nguyên,
không cắt bỏ chữ. Chỉ bỏ ảnh/figure và đơn vị không có chữ.

Mỗi nhóm dùng API hiện hữu với version/hash và khóa idempotency riêng. Không
tự retry model. Kết quả được tổng hợp thành báo cáo: nhóm hoàn tất, gợi ý sửa,
mục cần đối chiếu ảnh, trang gặp lỗi và nhóm chưa chạy. Lỗi riêng một nhóm
không xóa kết quả thành công. Lỗi quyền, quota, cấu hình/model, xung đột nguồn
hoặc phản hồi chưa xác định sẽ dừng gửi nhóm mới. Từ phiên832, mỗi lượt kiểm tra
chạy bất đồng bộ tối đa **2 nhóm đồng thời**; nhóm xong nhận nhóm tiếp theo,
không đợi nhóm kia. Giới hạn này thuộc từng lượt trong trình duyệt, không phải
giới hạn toàn server/nhiều tab. Có thể dừng sau các nhóm đang chạy; hệ thống chờ
và ghi nhận đủ các phản hồi đã gửi, không tự hủy rồi gửi lại. Không tuyên bố toàn
tài liệu đã kiểm tra nếu còn nhóm lỗi/chưa chạy.

Giữ màn hình mở khi chạy. Đây là điều phối tại trình duyệt, không phải tác vụ
nền tự tiếp tục sau khi đóng trang. Các lượt check riêng vẫn được backend lưu;
báo cáo tổng hợp trong màn hình hiện tại có thể tải JSON gồm trạng thái và mã
lượt check, không chứa nội dung văn bản hay khóa API. Đổi tài liệu/phiên bản/
phiên đăng nhập sẽ chặn kết quả cũ và không gửi các nhóm còn lại.

Muốn chỉ kiểm tra một phần, chọn **Chọn trang…** hoặc đánh dấu từng đoạn.
Từ phiên833, cả hai lựa chọn này dùng chung bộ chia nhóm và giới hạn hai nhóm
đồng thời. Yêu cầu kiểm tra chính tả chờ kết quả từ backend theo thời hạn gọi
model của ModelOps, thay vì dùng thời hạn mặc định 30 giây của API client.
Gợi ý vẫn phải đối chiếu ảnh, **Áp dụng vào nháp → Lưu thay đổi** để tạo phiên
bản mới. Nội dung OCR gốc không đổi; không tự compiler/publish/reindex.
