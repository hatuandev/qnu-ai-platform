# Phiên 913 — Chốt mốc backend và rà vòng đời ngược

Người dùng yêu cầu chốt mã hiện có trên Git trước khi dùng prompt triển khai vòng đời ngược. Phạm vi mốc là các thay đổi Context909–912 trên nhánh `feat/v1-user-workflow`, từ commit `3f4f6fb7`. Hai tệp Python được dọn dòng trống cuối tệp.

- Kiểm tra toàn bộ danh sách tệp chờ commit. Quét theo mẫu bí mật trên phần thêm và tệp mới, không phát hiện ứng viên. Môi trường thật, tệp nguồn và dữ liệu chạy thử nằm ngoài danh sách commit.
- Từ `backendV1`, chạy `.venv\Scripts\ruff.exe check <các tệp Python backend thay đổi>` và `.venv\Scripts\python.exe -m alembic heads`. Cả hai exit 0, schema có một head `0019_source_only_compilation`.
- Đối chiếu biên nhận của Context912. Nhóm chuẩn bị/phát hành/readiness đạt 61 ca và nhóm đồng bộ chỉ mục đạt 11 ca. Full suite, model thật và migration trên DB ứng dụng chưa chạy ở mốc này.
- Rà vòng đời ngược trên DB cô lập. Đã tái hiện gián đoạn bản cũ khi thay tệp, tác vụ con tiếp tục sau khi dừng lượt chuẩn bị, xóa bị kẹt do bản phát hành hoặc thu quyền, chỉ mục còn active sau lần thu hồi cuối, lỗi khôi phục thư mục và mặc định ModelOps trỏ vào model đã xóa. Kiểm thử recovery cần tách khỏi chế độ Selector của Windows và đạt 4/4 khi chạy riêng.

Đích Git là nhánh hiện tại trên Gitea. GitHub chưa có nhánh này và lịch sử cần gửi chứa một PDF 162,41 MiB. Việc xử lý lịch sử GitHub thuộc đợt riêng theo lựa chọn trước đó của người dùng.

Đợt sau triển khai Dừng xử lý, Ngừng dùng cho trợ lý, Cập nhật tài liệu và Xóa vĩnh viễn. Mốc này ghi nhận hiện trạng để làm baseline, chưa thay đổi các thao tác ngược.
