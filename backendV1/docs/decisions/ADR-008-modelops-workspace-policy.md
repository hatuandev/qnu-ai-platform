# ADR-008 — ModelOps quản trị và quyền model theo workspace

Trạng thái: triển khai batch636, 2026-10-26. Phạm vi chỉ backendV1.

## Quyết định

1. Provider/model/key là catalog quản trị tập trung. Vai trò admin trong membership không tự tạo quyền nền tảng. Chỉ actor có quyền quản trị ModelOps được tạo provider/key, thay default hệ thống, cấp allowlist và sửa quota.
2. `workspace_allowed_providers` là quyền được cấp. `workspace_model_defaults` chỉ chọn trong quyền đó theo chat/embedding/rerank/OCR; khóa ngoại ghép chặn default ngoài grant. Admin đơn vị được đổi defaults, không tự thêm grant. Cờ is_default cũ chỉ phản chiếu default chat.
3. Catalog và public API phân giải model nhận workspace cụ thể và gọi resolve_workspace_access. Không hợp allowlist của nhiều workspace, không tự lấy default hệ thống khi đơn vị chưa được cấp. Suspended/revoked/disabled/wrong capability phải trả lỗi.
4. V1 dùng bảng providers/provider_keys/model_defaults và modelops_events riêng, không sửa hoặc sao chép bảng/key/defaults legacy. Đây là ánh xạ vật lý mới của ERD nghiệp vụ, không phải port nguyên schema backend.
5. Credential lưu mã hóa, đọc dạng che; rotate vô hiệu local record cũ và thêm record mới trong cùng transaction. Audit không chứa secret. Thao tác này không thu hồi key ở upstream.
6. Quota theo tháng UTC. Không có cấu hình tháng thì reservation bị chặn; NULL limit chỉ mang nghĩa unlimited khi quản trị cấu hình tường minh. Row lock và request hash bảo vệ reservation/idempotency. NULL token/cost giữ nghĩa chưa biết; reservation của timeout chưa rõ billing được giữ chờ đối soát.
7. Metering chỉ có giao diện nội bộ cho runtime tin cậy. HTTP chỉ đọc usage, không cho người dùng tự khai usage hoặc sửa counters. Cần quan sát provider thật và budget đúng model/protocol khi nối inference.

## Kiểm chứng và giới hạn

API/PostgreSQL, race quota/admin, JWT/JWKS có kiểm thử; xem báo cáo636. Chưa live QNU SSO, discovery/probe/provider inference/OCR, streaming hoặc key lease/cooldown/fallback runtime. Đăng ký capability không được coi là đã verify model. Các adapter placeholder vẫn báo lỗi tường minh.
