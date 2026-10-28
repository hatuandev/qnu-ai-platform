# Workspace và ModelOps — API giai đoạn đầu

Prefix: `/platform/v1alpha1`. Nguồn OpenAPI là DTO/router thực tế; bản xuất tại [openapi-v1.json](openapi-v1.json).

## Luồng quản trị

1. Xác thực actor bằng SSO hoặc dev login đã cấu hình.
2. Platform admin tạo workspace và thêm SSO subject vào membership.
3. ModelOps admin đăng ký provider/model/capability và credential qua API; secret chỉ lưu mã hóa trong DB.
4. Platform admin cấp provider cho workspace và cấu hình quota tháng UTC.
5. Admin workspace chọn model mặc định theo capability trong danh sách được cấp.
6. Thành viên đọc catalog bằng workspace_id cụ thể; domain khác gọi public API ModelOps với actor + workspace + capability + preferred provider nếu có.

## API

| Nhóm | Endpoint |
|---|---|
| Workspace | POST/GET `/workspaces`; GET/PATCH `/workspaces/{id}` |
| Thành viên | GET/POST `/workspaces/{id}/members`; PATCH/DELETE `/workspaces/{id}/members/{member_id}` |
| Audit đơn vị | GET `/workspaces/{id}/events` |
| Provider | POST/GET `/modelops/providers`; GET/PATCH `/modelops/providers/{id}` |
| Diagnostics | GET `/modelops/providers/{id}/diagnostics`; POST `.../discover`; POST `.../probe` với capability; xem [contract](modelops-diagnostics.md) |
| Credential | POST/GET `/modelops/providers/{id}/keys`; POST `.../keys/{key_id}/rotate`; POST `.../keys/{key_id}/revoke` |
| Key audit | GET `/modelops/providers/{id}/key-events` |
| Audit cấu hình | GET `/modelops/events` |
| Default hệ thống | GET/PUT `/modelops/defaults` |
| Allowlist | GET/PUT `/workspaces/{id}/allowed-providers` |
| Default đơn vị | PUT `/workspaces/{id}/model-defaults` |
| Catalog cho đơn vị | GET `/modelops/catalog?workspace_id={id}` |
| Quota | GET/PUT `/workspaces/{id}/quota?period=YYYY-MM-01` |
| Usage | GET `/workspaces/{id}/usage` |

Các thao tác provider/key/default toàn cục yêu cầu `ai.models.manage`; tạo/sửa workspace yêu cầu `ai.workspaces.manage`. Membership role `admin` không tự tạo quyền nền tảng. Admin đơn vị chỉ thay defaults, không tự mở rộng allowlist hoặc tăng quota. Usage/audit đơn vị dành cho admin đơn vị và platform admin; catalog dành cho thành viên đang hoạt động.

## Quyền và trạng thái

- SSO subject phân biệt hoa/thường; không dùng email hoặc tên hiển thị làm membership key.
- Workspace mới có thể chưa có admin đơn vị. Platform admin bổ nhiệm/thu hồi để phục hồi quản trị. Admin đơn vị không tự hạ/thu hồi admin hoạt động cuối cùng; khóa workspace row tuần tự hóa các thay đổi đồng thời.
- Non-member/revoked membership nhận 404. Thành viên thiếu role hoặc workspace suspended nhận 403. Platform admin đọc metadata và phục hồi trạng thái suspended; runtime phân giải model vẫn từ chối suspended, kể cả platform admin.
- Catalog không trả endpoint hoặc key; provider bị tắt không được phân giải. Model mặc định theo capability phải thuộc grant, còn active và khớp capability. Không tự fallback sang default toàn cục chưa được cấp.
- Thu hồi key chỉ vô hiệu bản ghi tại QNU và ghi audit; không tuyên bố đã thu hồi credential ở dịch vụ upstream. Rotate nhận credential mới, vô hiệu bản cũ và thêm bản mới trong cùng transaction.

## Quota/usage nội bộ

`usage_service.reserve` nhận budget do inference tin cậy tính và request hash, kiểm quyền/grant/quota rồi giữ budget trong transaction. Request ID cùng workspace không bị tính hai lần; thay hash/actor/provider/budget trả 409. Caller phải tái dùng record đã có và không gửi lại inference đã thực thi.

`usage_service.settle` chỉ dành cho kết quả provider quan sát được, không có HTTP endpoint tự khai usage. NULL token giữ reservation và status unknown để đối soát; không coi timeout là miễn phí. NULL cost giữ nghĩa chưa biết. Settlement dùng tháng của reservation, không gán lại theo thời gian nhận kết quả. Giá/tariff và adapter tự đo usage chưa triển khai; chưa có inference thật trong batch này.

Reservation chỉ bảo vệ budget đã được caller tính; bước nối runtime phải tính và giới hạn budget đúng protocol/model, xử lý cancellation/reconciliation và ghi nhận usage thực. Không tuyên bố quota đầu-cuối với provider thật đã nghiệm thu.

## Dữ liệu và migration

V1 sở hữu các bảng được liệt kê trong `migration-ownership.yaml`; Alembic chỉ nhận allowlist tên bảng, dùng `alembic_version_backendv1` và migration lock chung. Baseline `0001_initial_schema` đã gộp toàn bộ schema đến15revision phát triển cũ, không stamp legacy. Bảng cùng tên có trước ngoài lịch sử v1 làm migration dừng, không tự nhận quyền sở hữu. Xem [hướng dẫn migration](migrations.md).

Không sửa migration backend cũ. Khi vận hành chung DB, cần giữ review riêng cho autogenerate của legacy để không tác động bảng v1. Ranh giới này không đổi nghiệp vụ dữ liệu chung của `backend/`.

## Capacity model — Context641

POST/PATCH provider nhận `token_limits` gồm context_window_tokens, max_input_tokens,
max_output_tokens tùy thông tin đã biết; số nguyên dương, không trần chung8K/32K.
Response thêm token_limits/capacity_status/capacity_basis. Cấu hình do quản trị khai
báo không được gắn nhãn đã kiểm định; đổi endpoint/model vô hiệu profile cũ.

Runtime dùng resolve_model_capacity/plan_model_request qua public API ModelOps;
input phải bao gồm token ảnh/framing theo protocol. Chưa biết hoặc vượt capacity
trả lỗi, không cắt nguồn. Xem [hợp đồng và điểm nối OCR](model-capacity.md).
