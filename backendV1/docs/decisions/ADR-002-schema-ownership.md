# ADR-002 — Sở hữu schema

**Quyết định:** backendV1 dùng version table riêng `alembic_version_backendv1`;
`0001_initial_schema` tạo toàn bộ bảng v1 bằng DDL cố định, không stamp chuỗi legacy.

**Hệ quả:** hai chuỗi migration cùng tồn tại trên một DB; v1 chỉ tạo bảng của mình.

Ngày2026-10-27, theo yêu cầu người dùng,15revision phát triển0001–0015 được gộp
thành baseline khởi tạo. Schema được đối chiếu với DB thử chạy toàn bộ chuỗi cũ;
nguồn cũ giữ nguyên bytes trong `alembic/archive/0001-0015_20261027.zip`.
Baseline từ chối nhận bảng v1 đã có ngoài lịch sử. Không tự stamp/chuyển đổi DB
đang ở revision cũ. Xem [quy trình migration](../migrations.md).

Context666 thêm `0002_operational_readiness` theo cách tăng dần bình thường;
không sửa lại DDL baseline. Review ack mở rộng bảng preview v1; biên nhận dọn tệp
dùng bảng v1 mới, có trong ownership manifest. Recovery chỉ sao lưu/khôi phục các
bảng do backendV1 sở hữu vào DB mới; legacy và version table của legacy không bị
đổi. Workspace v1 vẫn là biên quyền, gồm các thao tác GC và đọc readiness.
