# 19 — Workspace và ModelOps của backendV1

Chỉ áp dụng backendV1 theo ngoại lệ workspace trong AGENTS.md. Backend cũ giữ phạm vi dữ liệu chung. Workspace là biên giới quyền bằng membership/role, không yêu cầu phân vùng vật lý PostgreSQL.

1. Xác thực actor qua SSO hoặc dev login cấu hình tường minh.
2. Platform admin tạo workspace và gán thành viên theo SSO subject phân biệt hoa/thường.
3. ModelOps admin đăng ký provider/model/capability, lưu credential qua API vào DB mã hóa.
4. Platform cấp allowlist và quota tháng UTC cho workspace.
5. Admin đơn vị chọn default theo capability trong grant; thành viên đọc catalog gắn workspace cụ thể.
6. Khi nối inference, runtime phải resolve quyền/provider rồi reserve budget trước thực thi; settle bằng usage quan sát thật. Unknown giữ unknown và reservation chờ đối soát.

Nguồn file sẽ upload trực tiếp vào collection trong batch tiếp theo. Chưa có Repository, Knowledge ingestion/RAG/provider inference thật trong batch636. Không coi capability khai báo là verified hoặc tổng token không biết là0.

[Hợp đồng API và vai trò](../../backendV1/docs/workspaces-modelops.md). [Kiểm chứng636](../bao_cao/context636/REVIEW.md).

Context641 bổ sung capacity khi tạo/sửa model: token_limits theo endpoint/model,
context/input/output riêng, unknown giữ null, không trần chung8K/32K. Thay đích vô
hiệu profile cũ; runtime gọi budget guard có kiểm quyền trước HTTP. Ngân sách
workflow OCR mặc định8192 là cấu hình tác vụ, không phải context model.
[Hợp đồng và điểm nối runtime](../../backendV1/docs/model-capacity.md).
