# ADR-008 — ModelOps quản trị và quyền model theo workspace

Trạng thái: triển khai batch636, 2026-10-26; cập nhật batch957, 2026-11-13 (bãi bỏ allowlist/defaults theo đơn vị). Phạm vi chỉ backendV1.

## Quyết định

1. Provider/model/key là catalog quản trị tập trung. Vai trò admin trong membership không tự tạo quyền nền tảng. Chỉ actor có quyền quản trị ModelOps được tạo provider/key, thay default hệ thống và sửa quota.
2. `model_defaults` giữ một bản ghi mặc định hệ thống duy nhất theo chat/embedding/rerank/OCR. Không còn `workspace_allowed_providers` hay `workspace_model_defaults`: quyền dùng model không cấp theo đơn vị.
3. Catalog và public API phân giải model nhận workspace cụ thể và gọi resolve_workspace_access để kiểm quyền thành viên; model mặc định lấy từ bản ghi hệ thống. Suspended/revoked/disabled/wrong capability phải trả lỗi.
4. V1 dùng bảng providers/provider_keys/model_defaults và modelops_events riêng, không sửa hoặc sao chép bảng/key/defaults legacy. Đây là ánh xạ vật lý mới của ERD nghiệp vụ, không phải port nguyên schema backend.
5. Credential lưu mã hóa, đọc dạng che; rotate vô hiệu local record cũ và thêm record mới trong cùng transaction. Audit không chứa secret. Thao tác này không thu hồi key ở upstream.
6. Quota theo tháng UTC. Không có cấu hình tháng thì reservation bị chặn; NULL limit chỉ mang nghĩa unlimited khi quản trị cấu hình tường minh. Row lock và request hash bảo vệ reservation/idempotency. NULL token/cost giữ nghĩa chưa biết; reservation của timeout chưa rõ billing được giữ chờ đối soát.
7. Metering chỉ có giao diện nội bộ cho runtime tin cậy. HTTP chỉ đọc usage, không cho người dùng tự khai usage hoặc sửa counters. Cần quan sát provider thật và budget đúng model/protocol khi nối inference.

## Kiểm chứng và giới hạn

API/PostgreSQL, race quota/admin, JWT/JWKS có kiểm thử; xem báo cáo636. Chưa live QNU SSO, discovery/probe/provider inference/OCR, streaming hoặc key lease/cooldown/fallback runtime. Đăng ký capability không được coi là đã verify model. Các adapter placeholder vẫn báo lỗi tường minh.

## Cập nhật batch957 — bãi bỏ cấu hình model theo đơn vị

Người dùng chốt 2026-11-13: model là chính sách toàn hệ thống; workspace chỉ còn là biên giới quyền, không mang cấu hình model riêng. Đã bỏ endpoint `GET/PUT /workspaces/{id}/allowed-providers` và `PUT /workspaces/{id}/model-defaults`, model/schema tương ứng, enforcement trong phân giải, UI frontendV1/frontendV2 và test liên quan. Migration `0027_drop_ws_model_policy` drop hai bảng; `SCHEMA_HEAD` tương ứng. Sau thay đổi, mọi workspace phân giải cùng bản ghi `model_defaults` hệ thống; membership/suspended vẫn bị kiểm trước khi trả model.
