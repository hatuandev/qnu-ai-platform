# 20 — Upload kho tri thức backendV1

Chỉ áp dụng `backendV1/`; workspace là biên giới quyền theo membership/role.
File được upload trực tiếp vào collection. Nguồn hiện dừng ở `stored`.

1. Xác thực actor và kiểm tra quyền bằng `resolve_workspace_access` trước khi gọi service.
2. Kiểm tra collection/source trong workspace, giới hạn kích thước, định dạng thật,
   tên hiển thị và SHA-256 từ bytes gốc.
3. Với `Idempotency-Key`, so fingerprint gồm title hiệu lực; cùng yêu cầu replay200,
   khác yêu cầu trả409. Sổ cũ được đối chiếu thêm title đã lưu, không sửa lịch sử.
4. Ghi blob theo khóa nội dung. Driver local ghi file tạm cùng thư mục rồi xuất bản
   nguyên vẹn; writer lỗi không cắt file mà revision đã commit đang tham chiếu.
   Trên Windows, lỗi đổi tên chỉ được coi là thành công khi bytes đích khớp hoàn toàn.
5. Commit nguồn, revision bất biến, sổ idempotency và audit. Unique constraint xử lý
   đua ghi; rollback DB không xóa blob dùng chung với writer thắng.
6. Thêm revision chỉ nhận file; trường title bị từ chối422. Tải file kiểm lại quyền,
   chuỗi workspace/collection/source/revision và checksum trước khi trả bytes gốc.

Migration0005 từ chối downgrade để giữ chứng cứ và giữ version nhất quán. Cần kế
hoạch rollback riêng nếu thay đổi triển khai. Chưa có parse/OCR/worker/index/RAG
trong luồng này.

[Hợp đồng chi tiết](../../backendV1/docs/knowledge-collections.md).
[Kiểm chứng bản sửa639](../bao_cao/context639/REVIEW.md).
