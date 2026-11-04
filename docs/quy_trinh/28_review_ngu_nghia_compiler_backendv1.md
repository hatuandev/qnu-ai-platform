# 28 — Review ngữ nghĩa sau Compiler backendV1

Compiler hoàn tất → gọi review → lưu báo cáo có căn cứ → người dùng đối chiếu →
quyết định sửa/biên soạn lại → duyệt/xuất bản theo luồng riêng.

Review kiểm hai chiều: nguồn có ý quan trọng thuộc chủ đề chưa được thể hiện và
bản biên soạn có ý thiếu/sai căn cứ. Ghim input snapshot, draft và bundle hashes;
giữ bảng/header/footnote/năm/đơn vị. Mỗi nhận xét đi với nguyên văn và vị trí nguồn
để màn hình sau này hiển thị văn bản thay cho mã.

Từ [quy trình29](29_noi_hau_ocr_review_va_sua_compiler_backendv1.md), Compiler mới
mặc định tạo intent review trong cùng transaction hoàn tất và giao worker v1.
Studio tạo lượt thủ công qua POST nền, mở tab tiến độ theo ID đã lưu và cho phép
dừng lượt đang chờ hoặc đang chạy. Phần hoàn tất được giữ lại. Nhóm đã gửi model
mà chưa rõ kết quả được đánh dấu chưa xác định. Model reviewer chọn qua ModelOps, có thể
khác model biên soạn. Một key/body chỉ tạo một lượt; failed/uncertain không auto retry.

Nguồn hoặc quyền/model thay đổi giữa HTTP khiến review bị chặn. Schema/ID/coverage
không hợp lệ giữ raw và báo lỗi; provider lỗi không giả thành không phát hiện vấn đề.
Kết quả chỉ có needs_attention hoặc no_issues_detected, không tự approved/publish.

Review dùng đúng nguồn Compiler đã dùng; bản
sửa hậu OCR được ghim bằng text version khi tạo Compiler; không trộn bản mới vào lượt cũ.

**Biên soạn nhanh** dùng toàn bộ nguồn đã chọn và lấy chủ đề làm tiêu đề.
Backend dựng bản nháp nguyên văn có dẫn chứng, giữ bảng và các cảnh báo nguồn.
Lượt này không tự tạo Review AI. Người dùng có thể yêu cầu Review thủ công
và tiếp tục qua quy trình xác nhận, duyệt và phát hành hiện hành.

Màn hình đọc của cả hai chế độ dùng cùng nhóm mở/đóng. Nhóm lấy tiêu đề từ
nguồn đã ghim hoặc dùng số trang khi thiếu tiêu đề rõ ràng. Đoạn tổng hợp
dẫn từ nhiều mục giữ tiêu đề biên soạn. Nhóm đọc là dữ liệu hiển thị riêng,
còn bản lưu, tệp tải xuống, dẫn chứng và vị trí chỉnh sửa lấy từ bản nháp gốc.

[API và cách tích hợp](../../backendV1/docs/compiler-review.md) ·
[Báo cáo652](../bao_cao/context652/REVIEW.md).
