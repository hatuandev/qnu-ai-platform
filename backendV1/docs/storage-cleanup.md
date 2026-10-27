# Dọn tệp dẫn xuất mồ côi — backendV1

Prefix: `/platform/v1alpha1/workspaces/{workspace_id}/operations/storage-cleanups`.
Chỉ admin của workspace hoặc quản trị nền tảng; mọi truy vấn qua resolver v1.

1. `POST /previews` với `{"reason":"...","min_age_hours":24}`.
2. Xem số tệp, ID tệp, dung lượng, thời gian sửa và preview hash/hạn dùng.
3. `POST /actions` với preview ID/hash và header `Idempotency-Key`.
4. `GET /actions/{id}` đọc biên nhận do chính người gọi tạo. Lỗi I/O có thể giữ
   pending; dùng lại cùng body/key. Không đổi key để thực hiện lại ngầm.

Server chỉ chọn tệp dẫn xuất của job v1 đã kết thúc, cũ ít nhất 24 giờ và không
còn được bất kỳ hàng dữ liệu được giữ trong workspace tham chiếu. Phạm vi gồm
Markdown/JSON/manifest, ảnh trang dẫn xuất, snapshot Compiler/review và phiên bản
text dẫn xuất. Không có cron tự xóa; không dọn một phần inventory bị giới hạn.

Luôn giữ bản gốc, raw model response, backup, namespace lạ, owner chưa xác định
và mọi tệp còn được tham chiếu, kể cả tài nguyên đang trong thùng rác. Khi còn job
queued/running/deleting, server từ chối vì chưa chứng minh được tệp mồ côi.
Tệp tạm chỉ được xét khi nằm trong namespace dẫn xuất/owner hợp lệ như trên.

Preview ghim actor, đích lưu trữ, lý do, tuổi, danh sách, checksum và phiên bản
object. Trước khi xóa server kiểm lại quyền/references; việc xóa có điều kiện
theo version/hash. Local dùng khóa ghi cùng ranh giới storage; S3/MinIO dùng
ETag và conditional delete. Tệp thay đổi sẽ được giữ, thao tác trả conflict.
Adapter không hỗ trợ điều kiện xóa phải báo lỗi, không hạ xuống xóa vô điều kiện.

Giới hạn: inventory 10.000 object mỗi prefix, tối đa 500 ứng viên/256 MiB; vượt
giới hạn trả lỗi. Audit ghi ID thao tác/số tệp, không ghi nội dung tài liệu.
Intent pending được commit trước I/O nên retry sau lỗi không cần phê duyệt mới;
tệp đã vắng được ghi `absent`, không giả là vừa xóa. Không dùng API này để purge
nguồn gốc hoặc xóa vĩnh viễn tài liệu nghiệp vụ.

Local và MinIO đã kiểm tra việc giữ nội dung mới khi object đổi sau preview.
Xem [vòng đời tài nguyên](resource-lifecycle.md) để dọn generation vector cũ.
