# Context603 — Dùng compiler chủ đề qua API nâng cao

Đây là chức năng quản trị backend, chưa có giao diện frontend mới. Dùng session
đăng nhập và API prefix đang cấu hình trên server; không thêm key LLM vào request.
Nguồn đã upload/chuẩn hóa cần là revision mới nhất của binding, trạng thái ready,
raw hash/canonical/manifest còn khớp. Mỗi build chọn một revision cho mỗi binding.

## Tạo bản biên soạn

1. Gọi `GET /knowledge/collections/{collection}/compilations/preview` với query
   `source_revision_ids` lặp lại cho từng source. Cần quyền view và upload. Đọc
   `source_set_hash` và đối chiếu danh sách nguồn trước tạo build.
2. Gọi `POST /knowledge/collections/{collection}/compilations` với `topic`,
   `source_revision_ids`, `expected_source_set_hash` vừa preview và
   `idempotency_key` duy nhất cho thao tác. Không gửi provider/model/actor/status.
3. Request có thể xử lý lâu; intent được lưu trước inference. Nếu kết nối đóng,
   gọi GET danh sách/chi tiết, không tạo key mới để thử lại khi chưa biết kết quả.
   Gửi lại cùng payload/key chỉ lấy biên nhận; không tự chạy lại uncertain intent.

GET danh sách: `/knowledge/collections/{collection}/compilations`. Các trạng thái
trong danh sách là receipt, `snapshot_status=not_checked`; phải mở chi tiết để
kiểm lại nguồn trước quyết định. GET chi tiết:
`/knowledge/collections/{collection}/compilations/{job}`. Cần view + review;
GET không gọi LLM hoặc ghi dữ liệu.

## Đọc kết quả

- `ready_for_review`: đã có machine checks đầy đủ, vẫn là bản chưa xuất bản.
- `needs_attention`: còn semantic check chưa đủ; chưa cho approval.
- `running`: intent đang xử lý trong thời hạn.
- `uncertain`: xử lý gián đoạn/timeout/lỗi chưa hoàn thành; xem failure/audit,
  không coi là nội dung nguồn thiếu.
- `stale`: nguồn/pointer/epoch hoặc lineage thay đổi; không trả bundle cũ để dùng.
- `reviewed`, `rejected`, `revoked`: đã có hành động người dùng có quyền, còn audit.

Bundle có Markdown, proposal, source proof catalog, exact source offsets,
temporal context, topic coverage/review ledgers, dependencies và observed usage.
Đối chiếu condition/exception, year role, unknown và trạng thái draft của nguồn.
Reviewer model là bước kiểm tự động, không phải quyết định người dùng.

## Duyệt hoặc thu hồi

Gọi `POST /knowledge/collections/{collection}/compilations/{job}/decisions` với
`expected_version`, `expected_proposal_hash` từ chi tiết hiện tại,
`decision` (`approved`, `rejected`, `revoked`), `idempotency_key`, `comment` tùy
chọn. Server lấy actor từ auth; sai version/hash hoặc unresolved sẽ bị chặn.
Không gửi một loạt quyết định để thử làm xanh mọi issue.

Duyệt lưu quyết định cho dẫn xuất này, **không nạp vector hoặc xuất bản**. Nguồn
và facts cũ không đổi. Bản biên soạn hiện chưa được đưa vào context chatbot;
publication/serving vẫn qua cơ chế đã có, không có nút bỏ qua hoặc quyền mới.

Thu hồi giữ lịch sử và chặn reuse qua lineage. Nếu nguồn đổi, preview và tạo build
mới với key mới sau khi đã biết trạng thái build cũ. Chỉ packet nguồn/context
không đổi, có review đầy đủ và không bị thu hồi được tái sử dụng; phần tổng hợp
được kiểm lại. Không tự dùng upload mới như bằng chứng thay thế văn bản cũ.

Lỗi provider, budget, storage hoặc source integrity là lỗi thật; không tắt
validation, sửa registry metadata hoặc đổi source hash để vượt qua. Các kết quả
test và giới hạn: [VALIDATION_REPORT.md](./VALIDATION_REPORT.md).
