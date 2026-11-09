# Phiên912 — Hợp đồng duyệt/phát hành và policy auto khi thiếu adapter chat

## 1. Yêu cầu, phạm vi và giả định

Hai phát hiện từ đợt review backend V1, với mục tiêu người dùng thường có thể **chuẩn bị nội dung,
xem lại và phát hành tài liệu** mà không phải cấu hình model hoặc tạo chỉ mục bằng tay:

1. **Hợp đồng Duyệt & Phát hành** trong
   [47 — Hợp đồng luồng chính backend V1](../quy_trinh/47_hop_dong_luong_chinh_backend_v1.md) phải
   khớp API thật: đăng ký tạo `draft`; duyệt bằng preview `approve` + cam kết riêng; phát hành bằng
   **preview mới** `publish` + cam kết riêng với khóa idempotency khác; mô tả `review_ack`/
   `review_skip`, quyền, phục hồi khi lỗi mạng và cách FE báo sẵn sàng cho trợ lý.
2. **Chuẩn bị `auto`** không được trả `422` khi workspace có provider Chat mặc định được cấp nhưng
   loại provider không có adapter; policy phải chuyển source-only an toàn và vẫn tạo draft có
   bằng chứng, không gọi model.

Batch này **chỉ backend và tài liệu hợp đồng**, không xây frontend mới. Giữ nguyên: nguồn/canonical
OCR/bảng/ô/header/footnote/bbox/revision/hash/bằng chứng; quyền workspace và kiểm nguồn ở server;
chuẩn bị xong không đồng nghĩa đã duyệt/phát hành; chỉ nội dung đủ điều kiện mới vào chỉ mục phục
vụ; giữ idempotency, lease, hủy, audit và `uncertain`; lỗi provider/hạ tầng báo thật; model giải
quyết qua ModelOps; không thêm trần output cố định; không khôi phục quota tháng; không hardcode
ngành/năm/tài liệu/đáp án benchmark.

Không clear/reset/seed/reindex, không upload lại, không thay publication, không restart phiên người
dùng, không deploy, không Git push. Không chạy test trên DB ứng dụng, không cài thêm dependency.
Kiểm chứng theo [verification](../../.agents/rules/verification.md) và ghi nhận theo
[workflow/memory](../../.agents/rules/workflow-and-memory.md).

## 2. Kết quả theo phạm vi

### A — Hợp đồng Duyệt & Phát hành cho FE mới

- Hợp đồng cũ bỏ qua bước duyệt và đặt `review_skip` ở bước phát hành, trái với API: `review_skip`
  chỉ dùng cho `approve` (gửi ở `publish` bị `422`), và phát hành trực tiếp từ `draft` bị
  `409 publication_transition_invalid`. Đã viết lại §4 theo đúng mã hiện hành, gồm sáu bước:
  1. Đăng ký `POST /compiled-documents` (hoặc `.../versions`) với `Idempotency-Key`; phiên bản
     `draft`; lưu `version.id`, `bundle_sha256`, `state_version`.
  2. Đọc `GET .../review-gate`: `200` chỉ khi có review hoàn tất khớp phiên bản; thiếu review trả
     `409 publication_review_required`.
  3. Tạo preview `approve` với đúng **một trong hai** xác nhận: `review_ack` (review thật, đủ
     `review_id`, `report_sha256`, `confirmed_reviewed: true`, `resolutions` phủ đúng một lần mọi
     `finding_id`) hoặc `review_skip` (`confirmed_skip: true`, đúng `version_id` + `bundle_sha256`,
     `reason` ≥ 10 ký tự); thêm `retrieval_metadata_sha256` khi phiên bản có metadata.
  4. Cam kết duyệt bằng `POST .../decisions` với `{preview_id, preview_sha256}` và khóa riêng;
     retry mạng dùng đúng khóa/body, khóa cũ nội dung khác trả `409 idempotency_conflict`.
  5. Tạo **preview phát hành mới** `publish` không kèm trường review; server tự kiểm biên nhận duyệt
     khớp bundle và trạng thái (`409 publication_approval_required` khi thiếu).
  6. Cam kết phát hành bằng khóa **khác** khóa duyệt; phiên bản sang `published`, quyết định vào
     `history`, backend tự đánh thức đồng bộ chỉ mục — FE không gọi index thủ công.
- Ghi rõ quyền backend: `approve` cho admin/reviewer từ `draft`/`superseded`/`withdrawn`;
  `publish`/`withdraw` chỉ admin; đăng ký cho admin/editor; đọc `summary`/`published`/`history`/
  `review-gate` cho admin/editor/reviewer/member.
- Quy ước FE: không gộp hai bước; hiện **Duyệt** cho người có quyền duyệt, trạng thái **Đã duyệt**
  sau khi duyệt, chỉ admin thấy **Phát hành**; hộp xác nhận nêu phiên bản/hash và chế độ review,
  không lộ ID kỹ thuật.
- Phục hồi: lỗi cam kết duyệt thì đọc lại phiên bản và retry đúng khóa/body; đã duyệt nhưng phát
  hành lỗi thì giữ **Đã duyệt** và tiếp tục bằng preview `publish` mới với khóa phát hành mới;
  phát hành thành công nhưng mất phản hồi thì không gửi lại, đọc `summary`/`published`.
- Chỉ báo **Sẵn sàng cho trợ lý** khi `summary.readiness.status == "ready"` và
  `serving_matches_published == true` (đúng `version.id`, `state_version`, `bundle_sha256`,
  `publication_decision_id`); `not_indexed`/`outdated`/`unavailable` hiển thị trung thực. §5 ghi
  đúng các trường của `GET .../index-readiness`.
- Test chuỗi mới `test_explicit_skip_approval_publishes_and_only_then_serves_the_exact_version`:
  nguồn thật → chuẩn bị `auto` tối giản (không có provider Chat) → đăng ký `draft` → gate `409`
  → publish trực tiếp `409 publication_transition_invalid` → `review_skip` ở publish `422`
  → reviewer tạo preview `approve` chế độ bỏ qua, cam kết và replay đúng khóa trả cùng quyết định
  → admin tạo preview `publish` mới, cam kết khóa khác → `published` và `/published` đúng phiên bản
  → trước đồng bộ `not_indexed`/`serving_matches_published=false` → chạy lượt chỉ mục → `ready` và
  serving khớp đúng phiên bản đã phát hành.
- Các test cũ `test_fast_publication_779.py`, `test_publication_646.py`, `test_review_gate_666.py`
  đã phủ chuyển trạng thái và từ chối; được chạy lại trong nhóm kiểm chứng.

### B — Policy `auto` khi provider Chat không có adapter

- Nguyên nhân: `resolve_chat_runtime()` kiểm protocol của `transport_for(provider_type)` trước khi
  đọc khóa và ném `AppException` 422 `chat_provider_type_unsupported`; `_resolve_auto_policy()` chỉ
  bắt `DependencyUnavailable`, nên yêu cầu `auto` trả `422` dù Chat là bước tùy chọn.
- Sửa `_resolve_auto_policy()` bắt `AppException` và chỉ hạ cấp khi mã thuộc
  `OPTIONAL_CHAT_UNAVAILABLE_CODES`; mã khác (quyền/hạ tầng) được ném lại. Danh sách dùng chung
  được áp ở cả bước chọn provider mặc định (`auto_policy`) và bước phân giải runtime khi tạo policy.
- Khi hạ cấp: policy ghim `supplement="disabled"` với `reason` an toàn
  (`chat_provider_type_unsupported`), intent vẫn ghim `provider_id` để giải thích; run biên soạn
  source-only có `provider_id=null` và không gọi model. Draft giữ nguyên bằng chứng nguồn.
- Lựa chọn `mode="ai"` hoặc `provider_id` tường minh không đổi: lỗi cấu hình/provider vẫn hiện đúng
  mã (`chat_provider_type_unsupported`). Quyền workspace, idempotency, ghim nguồn/revision và kiểm
  trôi sau ghim (`preparation_policy_changed`) giữ nguyên.
- Test mới `test_auto_mode_degrades_when_granted_chat_adapter_is_missing`: provider `gemini` (không
  có adapter) được cấp và đặt mặc định Chat; intent `auto` tối giản `201`, policy đúng
  `disabled`/lý do; chạy hết pipeline tới `ready`; run `source_first=true`, cờ AI false,
  `provider_id=null`; draft có `sections` và `source_binding=confirmed_by_source`; intent `ai`
  tường minh cùng provider thất bại với `error_code=chat_provider_type_unsupported`.

## 3. Tệp thay đổi

- `backendV1/qnu/domains/knowledge/preparation/plan.py` — bắt `AppException` và dùng danh sách mã
  tùy chọn dùng chung khi tạo policy `auto` (tệp mới từ phiên911, tiếp tục chỉnh trong batch này).
- `backendV1/tests/integration/test_preparation_intents.py` — thêm test hạ cấp khi thiếu adapter.
- `backendV1/tests/integration/test_preparation_publication_chain.py` — thêm test chuỗi
  nguồn → chuẩn bị → duyệt bỏ qua có xác nhận → phát hành → chỉ mục sẵn sàng.
- `docs/quy_trinh/47_hop_dong_luong_chinh_backend_v1.md` — viết lại §4; cập nhật §2 (thiếu chat tùy
  chọn kể cả không adapter) và §5 (trường `index-readiness`).
- `docs/nhat_ky/2026-11-09_phien_911_lam_sach_backend_v1.md`,
  `docs/memory/snapshots/2026-11-09_session_911.md`, `docs/memory/PROJECT_CONTEXT.md` — sửa trạng
  thái full suite phiên911 thành **NOT RUN** (đã dừng trước khi hoàn tất), không dùng kết quả dở
  dang.
- `docs/nhat_ky/README.md`, `docs/WORK_LOG.md` — thêm mục phiên912.
- `docs/memory/snapshots/2026-11-09_session_912.md` — snapshot phiên này.

## 4. Kiểm chứng

| Phạm vi | Lệnh | Kết quả | Receipt |
| :--- | :--- | :--- | :--- |
| Ruff | `uv run ruff check qnu/domains/knowledge/preparation/plan.py tests/integration/test_preparation_intents.py tests/integration/test_preparation_publication_chain.py` | **All checks passed** | — |
| Chuẩn bị, duyệt/phát hành, readiness | `uv run python scripts/test_database.py tests/integration/test_preparation_intents.py tests/integration/test_preparation_publication_chain.py tests/integration/test_fast_publication_779.py tests/integration/test_publication_646.py tests/integration/test_review_gate_666.py tests/integration/test_index_readiness_819.py tests/integration/test_readiness_666.py` | **61 passed** (283,60s) | `qnu_v1_test_4a667836aaac42aa`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 293,27s |
| Đồng bộ chỉ mục sau phát hành | `uv run python scripts/test_database.py tests/integration/test_publication_index_sync_878.py` | **11 passed** (74,06s) | `qnu_v1_test_d256135f07ed44da`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 93,42s |

- Test chạy trên DB test cô lập do harness tạo và drop; không dùng DB ứng dụng.
- **Lỗi nền giữ nguyên:** `test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access`
  vẫn là lỗi fixture RAG đã ghi ở phiên911 (fake chat đọc `tables` và hòa điểm RRF theo `chunk_id`
  ngẫu nhiên); batch này không chạy lại nhóm RAG, không nới assertion và không nhận là đã sửa.
- **F13 của phiên908 vẫn là vấn đề chất lượng riêng**, chưa sửa; test mock/refactor không chứng
  minh F13 đạt.
- **NOT RUN:** full backend suite, model/OCR thật, benchmark RAG, kiểm tải, trình duyệt/FE; không
  áp migration lên DB ứng dụng, không restart ứng dụng, không reindex dữ liệu thật.

## 5. Rủi ro, giới hạn

- Hợp đồng §4 là nguồn chuẩn cho FE mới nhưng FE chưa được xây/kiểm trong batch này; mọi suy diễn
  ngoài mã API hiện hành phải đối chiếu lại backend.
- `review_skip` là lựa chọn **con người xác nhận** cho đúng phiên bản/hash, chỉ dành cho `approve`;
  FE không được tự động bỏ qua review. Backend vẫn kiểm quyền, chuyển trạng thái và biên nhận.
- `auto` chỉ hạ cấp với các mã thiếu cấu hình tùy chọn trong danh sách dùng chung; lỗi quyền, xác
  thực hoặc hạ tầng khác vẫn báo lỗi thật. Sau khi ghim policy, thay đổi model/cấu hình trả
  `preparation_policy_changed`, không âm thầm đổi model.
- Migration `0019_source_only_compilation` (cho `provider_id=null` của run source-only) **chưa áp**
  lên DB ứng dụng; cần áp trước khi chạy API/worker mới trên môi trường dev.

## 6. Việc tiếp theo

- FE mới dùng đúng §4: hai quyết định riêng, hai khóa riêng, preview mới cho `publish`, poll
  `summary`/`index-readiness` trước khi báo **Sẵn sàng cho trợ lý**.
- Trước khi khởi động backend mới trên DB ứng dụng, áp migration `0019_source_only_compilation`
  theo quy trình release; batch này không tự migrate.
- Lỗi nền RAG fixture và F13 cần việc riêng; không gộp vào kết quả batch này.
