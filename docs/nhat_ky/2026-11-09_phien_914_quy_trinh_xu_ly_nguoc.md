# Phiên914 — Quy trình xử lý ngược cho QNU V1

## 1. Yêu cầu, phạm vi và giả định

Triển khai đợt sửa `backendV1` từ mốc `7c1cef65` trên nhánh `feat/v1-user-workflow` để hoàn tất
bốn nhóm hành vi ngược của luồng người dùng thường, đồng thời chốt hợp đồng API cho FE:

1. **Cập nhật tài liệu khi vẫn phục vụ bản cũ** — revision mới mặc định là ứng viên; chỉ chuyển
   serving/index sau khi duyệt, phát hành và lập chỉ mục khớp revision/hash/quyết định; lỗi giữ
   bản cũ; API phân biệt bản đang chuẩn bị, đã phát hành và thực sự phục vụ.
2. **Dừng xử lý an toàn** — đóng cuộc đua `PreparationIntent.cancel` với việc tạo/liên kết
   `CompilationRun`; fencing quyền/trạng thái ở mọi bước; giữ lượt dùng chung; reconciler theo
   lease; kết quả không xác định ghi `uncertain`; khởi động lại worker không làm sống lại lượt dừng.
3. **Thu hồi và xóa vĩnh viễn** — thu hồi ẩn ngay khỏi RAG/dẫn chứng và ghi trạng thái kho trống;
   xóa vĩnh viễn một preview + một xác nhận, thu hồi trong transaction, dọn nền theo checkpoint/
   lease, tiếp tục được sau lỗi, admin xem/tiếp quản lượt kẹt, giữ audit và dữ liệu ngoài phạm vi.
4. **Điểm liên quan và hợp đồng FE** — khôi phục thư mục kiểm kho/cha/tên; chặn xóa model còn
   tham chiếu; trả `actions` cho bốn nút **Dừng xử lý**, **Ngừng dùng cho trợ lý**, **Cập nhật tài
   liệu**, **Xóa vĩnh viễn**; tiến độ từ biên nhận backend; bỏ **Lưu trữ tài liệu** khỏi luồng thường.

Phạm vi là backend và tài liệu hợp đồng; FE tích hợp sau. Giữ nguyên: workspace là biên quyền và
mọi truy vấn qua `resolve_workspace_access`; nguồn/canonical OCR/bảng/ô/header/footnote/bbox/
revision/hash/bằng chứng; chuẩn bị xong không đồng nghĩa duyệt/phát hành; chỉ nội dung đủ điều kiện
vào chỉ mục phục vụ; idempotency, lease, audit, `uncertain` và lỗi provider/hạ tầng báo thật; model
giải quyết qua ModelOps; không hardcode từ điển/từ khóa để vá OCR hoặc retrieval.

Không clear/reset/seed/reindex, không upload lại, không thay publication, không restart phiên
người dùng, không deploy, không Git push. Không chạy test trên DB ứng dụng, không cài thêm
dependency. Không retry model để làm xanh, không nới assertion/bỏ guard; lỗi nền và F13 của phiên908
giữ nguyên. Kiểm chứng theo [verification](../../.agents/rules/verification.md), ghi nhận theo
[workflow/memory](../../.agents/rules/workflow-and-memory.md).

## 2. Kết quả theo phạm vi

### §1 — Ứng viên revision và read model ba bản

- `SourceService.upload` và `add_revision` đổi mặc định `staged=True`; router form cũng mặc định
  `True` khi FE không gửi trường. Revision mới tăng `current_revision_no`/`revision_count` nhưng
  không đổi `serving_revision_no`; bản cũ và tệp cũ giữ nguyên. `staged=false` tường minh vẫn giữ
  hành vi cũ cho tương thích.
- `GET /sources/{source_id}/summary` trả `serving` gồm `served_revision_no`,
  `preparing_revision_no`, `published_revision_no`, `served_version_id`, `served_document_id`;
  ba giá trị độc lập, không suy diễn lẫn nhau. Trả thêm `actions` (`can_stop`, `can_withdraw`,
  `can_update`, `can_delete`) và `preparation` (`intent_id`, `status`, `step`, `error_code`).
- `document/replace` giữ nguyên atomic switch: `pending` + `result.index_run_id`; chỉ `completed`
  sau khi generation mới sẵn sàng và transaction cuối chuyển serving revision, publication và
  active index. Lỗi bóc tách/biên soạn/phát hành/index giữ bản cũ phục vụ. Thu hồi bản cũ trong
  lúc chờ làm run/receipt `failed`, `/published` trả `404`, ứng viên vẫn `approved`, không chuyển
  serving và không có hit tìm kiếm.

### §2 — Dừng xử lý an toàn

- Liên kết lượt con dùng conditional UPDATE chỉ khi intent còn `queued|waiting_ocr|compiling`;
  cancel không ghi đè bởi kết quả đến muộn. Lượt Compiler độc quyền đặt dưới khóa
  `prep:<intent_id>`; cancel chỉ hủy đúng lượt đó ở `queued|running`, không hủy lượt dùng chung/
  chạy độc lập.
- Worker claim bằng lease 180 giây; `_finish` chỉ ghi khi intent còn active; lỗi chung ghi
  `uncertain` với `preparation_advance_interrupted`, không tự nhận thành công. Reconciler chỉ
  phục hồi intent còn hiệu lực, lease hết hạn và `dispatched_at` cũ hơn 60 giây; restart không
  chạy lại intent `cancelled`. Quyền và trạng thái được đọc lại trước giao việc/nhận việc/lưu kết quả.

### §3 — Thu hồi, kho trống và xóa vĩnh viễn

- `withdraw` chỉ admin trên tài nguyên `active`: thu hồi mọi `CompiledVersion` `published` trong
  một transaction, tăng `state_version` và `change_sequence`, ghi audit, đánh thức outbox; RAG/
  tìm kiếm/dẫn chứng ẩn bản ngay request kế tiếp; giữ tệp/revision/lịch sử; `impact` trả
  `withdraw_keeps_originals=true`, `restore_available=true`.
- Thu hồi bản cuối: lần đồng bộ kế tiếp nhận `index_no_published_documents`, retire generation
  (xóa collection vector, xóa vector khỏi chunk DB, `is_active=false`, `vectors_retired_at`/
  `deactivated_at`), `kb_index_sync.status=empty`, phát `index.vectors_retired` +
  `index.collection_empty`; giữ manifest/chunk ID/citation lịch sử. `search-readiness` trả
  `empty`; đây không phải "Sẵn sàng cho trợ lý".
- `source/delete`: preview ghim đồ thị + hash tệp, `impact.permanent=true`; accept kiểm lại quyền,
  hạn/preview hash và phạm vi, tự thu hồi bản `published` trong cùng transaction, đánh dấu nguồn
  `deleted`, hủy job liên quan và giao `source_purge_job`. Phạm vi đổi sau preview trả
  `409 lifecycle_preview_stale`. Hỗ trợ nguồn `active|archived|deleted`; không cần restore trước.
- Biên nhận purge có `phase`/`progress`, `worker_id`, `lease_expires_at` (120 giây),
  `attempt_count`, `last_error_at`, `confirmed_by`, `takeover_by/at`. Worker chờ job đã hủy kết
  thúc (`waiting_for_workers`), rồi `deleting_vectors` (25), `deleting_objects` (55), `resealing`
  (80), `deleting_rows` (95), `completed` (100). Lỗi giữ `pending` + `error_code` + bước tiến độ,
  xóa lease; chạy lại worker/takeover tiếp tục trên cùng biên nhận. Chỉ `completed` mới là **Đã xóa**.
- Dọn đúng object key của nguồn (cả version/delete marker), xóa revision/OCR/Compiler/Review/
  draft liên quan/chunk/point vector; index dùng chung reseal manifest phần còn lại, không gọi
  model/re-embed tài liệu khác; object dùng chung trả `409 purge_shared_object`. Giữ audit,
  idempotency và bundle backup theo chính sách riêng.
- Admin workspace xem lượt kẹt qua `GET /source-deletions/active`, tiếp quản qua
  `POST /actions/{action_id}/takeover` khi không có lease hiệu lực; audit giữ `confirmed_by` và
  `takeover_by/at`; nguồn vẫn bị chặn sử dụng trong suốt quá trình.
- Upload phân biệt `duplicate_content`, `duplicate_content_deleted`, `source_purge_pending`,
  `revision_unchanged`; cho upload lại sau khi purge hoàn tất. Xóa kho chỉ nhận khi kho rỗng
  (`409 collection_not_empty`). `archive` vẫn có cho dữ liệu cũ nhưng bỏ khỏi hợp đồng thao tác thường.

### §4 — Khôi phục thư mục, ModelOps và hợp đồng FE

- `restore` thư mục kiểm theo thứ tự: kho còn khả dụng (`404 resource_unavailable`), thư mục đang
  xóa mềm (`409 folder_not_deleted`), cha tồn tại và hiển thị cùng kho
  (`409 folder_parent_unavailable`), tên không trùng anh-em cùng cấp không phân biệt hoa thường
  (`409 folder_name_exists`); xóa thư mục chỉ nhận khi rỗng (`409 folder_not_empty`).
- Xóa connection/model đang được tham chiếu trả `409 model_provider_in_use` kèm `detail` nêu loại
  tham chiếu (mặc định hệ thống/đơn vị, quyền sử dụng model, trợ lý, lịch sử lập chỉ mục/biên
  soạn/phản biện/sử dụng model). Lịch sử sử dụng model có FK chặn xóa và được giữ; gỡ allowlist
  không xóa lịch sử; mặc định không được trỏ model đã xóa (`409 allowlist_default_not_allowed`).
- Tài liệu hợp đồng: [resource-lifecycle](../../backendV1/docs/resource-lifecycle.md) bổ sung mục
  bốn nút, thu hồi/kho trống, API biên nhận/tiếp quản, purge checkpoint-lease, thay bản staged,
  khôi phục thư mục và xóa model.
  [47 — Hợp đồng luồng chính](../quy_trinh/47_hop_dong_luong_chinh_backend_v1.md) thêm §6 cho FE:
  ba bản serving, `actions`, `preparation`, bốn nút và quyền, tiến độ biên nhận, chi tiết kỹ thuật/
  tiếp quản chỉ admin, cùng lỗi thư mục/ModelOps. Bỏ archive khỏi thao tác thường.

### Schema và migration

- `alembic/versions/0020_reverse_flow.py`: thêm cột biên nhận vào `resource_lifecycle_actions`
  (`phase`, `progress` JSONB mặc định `{}`, `worker_id`, `lease_expires_at`, `attempt_count` mặc
  định 0, `last_error_at`, `confirmed_by`, `takeover_by`, `takeover_at`) và mở rộng
  `ck_index_sync_status` với `'empty'`. Downgrade trả ràng buộc cũ và bỏ cột.
- Model `IndexSync` cập nhật cùng ràng buộc; `LifecycleAction` thêm các cột trên. Không đổi bảng
  nguồn/revision/publication hiện có.

## 3. Tệp thay đổi

- `backendV1/qnu/domains/knowledge/sources/service.py`, `router.py`, `schemas.py`, `summary.py` —
  staged mặc định, read model `serving`/`actions`/`preparation`, cổng chặn mutation khi có
  preview xóa đang chờ.
- `backendV1/qnu/domains/knowledge/preparation/service.py`, `schemas.py` — fencing cancel/link,
  lease, `uncertain`, bước chuẩn bị trong summary.
- `backendV1/qnu/domains/knowledge/index/models.py`, `sync.py` — trạng thái `empty`, retire
  generation, đọc kho trống trung thực.
- `backendV1/qnu/domains/knowledge/folders/service.py` — thứ tự kiểm khôi phục thư mục.
- `backendV1/qnu/domains/lifecycle/models.py`, `schemas.py`, `router.py`, `service.py`,
  `effects.py`, `purge.py`, `purge_graph.py`, `targets.py` — biên nhận, withdraw/empty, purge
  auto-withdraw/checkpoint/lease/takeover, API admin, audit.
- `backendV1/qnu/domains/modelops/connections/service.py` — lỗi tham chiếu khi xóa model/provider,
  giữ lịch sử, chặn mặc định trỏ model đã xóa.
- `backendV1/alembic/versions/0020_reverse_flow.py` — migration mới.
- Test: `tests/integration/test_knowledge_summary_api.py`, `test_knowledge_actions_708.py`,
  `test_preparation_intents.py`, `test_lifecycle_659.py`, `test_lifecycle_runtime_659.py`,
  `test_source_purge_716.py`, `test_provider_connections_702.py`,
  `test_publication_index_sync_878.py`, `test_publication_646.py`, `test_index_api_647.py`,
  `test_compiler_edits_654.py`, `knowledge_support.py`; `tests/unit/test_source_purge_716.py`.
- Tài liệu: `backendV1/docs/resource-lifecycle.md`,
  `docs/quy_trinh/47_hop_dong_luong_chinh_backend_v1.md`, nhật ký/README/WORK_LOG/
  PROJECT_CONTEXT/snapshot phiên này.

## 4. Kiểm chứng

| Phạm vi | Lệnh | Kết quả | Receipt |
| :--- | :--- | :--- | :--- |
| Ruff | `uv run ruff check <32 tệp Python thay đổi>` | **All checks passed** | — |
| Chuẩn bị, phát hành, index sync, provider, capacity, auto-extraction | `uv run python scripts/test_database.py tests/integration/test_publication_index_sync_878.py tests/integration/test_provider_connections_702.py tests/integration/test_capacity_discovery_733.py tests/integration/test_preparation_intents.py tests/integration/test_preparation_publication_chain.py tests/integration/test_auto_extraction_710.py -q` | **72 passed** (243,79s) | `qnu_v1_test_546830b743e249d8`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 253,22s |
| Dừng xử lý an toàn | `uv run python scripts/test_database.py tests/integration/test_preparation_intents.py -k "cancel or shared_compilation or restart_and_reconcile or interrupted_advance" -q` | **8 passed** (24,34s) | `qnu_v1_test_dd5e011d155f46fc`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0` |
| Xóa vĩnh viễn nguồn | `uv run python scripts/test_database.py tests/integration/test_source_purge_716.py -q` | **8 passed** (56,02s) | `qnu_v1_test_e067f0fe705d4d1c`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 64,31s |
| Summary, thư mục, preparation | `uv run python scripts/test_database.py tests/integration/test_knowledge_summary_api.py tests/integration/test_knowledge_actions_708.py::test_folder_restore_requires_visible_parent_and_free_name tests/integration/test_knowledge_actions_708.py::test_folder_restore_rejects_case_insensitive_sibling tests/integration/test_knowledge_actions_708.py::test_folder_restore_in_archived_collection_is_not_available tests/integration/test_preparation_intents.py::test_source_summary_reports_preparation_step_and_stop_action -q` | **15 passed** (104,85s) | `qnu_v1_test_a81e5906f947443d`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 113,30s |
| Thay thế/thu hồi và xóa model | `uv run python scripts/test_database.py tests/integration/test_lifecycle_runtime_659.py::test_withdrawn_old_version_while_replacement_waits_never_activates_candidate tests/integration/test_provider_connections_702.py::test_delete_referenced_model_reports_reference_type_and_keeps_defaults tests/integration/test_provider_connections_702.py::test_model_usage_history_blocks_deletion_and_is_retained -q` | **3 passed** (19,13s) | `qnu_v1_test_99be33bdfcc646e6`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 27,47s |
| Full backend suite | `uv run python scripts/test_database.py tests -q` | **ĐANG CHẠY — cập nhật sau khi hoàn tất** | — |

- Tái hiện trước khi sửa: các ca `test_shared_index_generation_survives_purge_of_one_document`,
  `test_cancel_does_not_cancel_a_shared_compilation_linked_by_reuse`,
  `test_withdrawal_while_building_keeps_newer_intent_and_never_activates_stale_content` và các ca
  khôi phục thư mục từng FAIL trong lượt chạy trung gian trên DB cô lập, sau đó PASS ở các nhóm trên.
- Test chạy trên DB test do harness tạo và drop; không dùng DB ứng dụng. Storage là thư mục cô lập
  dưới `storage/context636/<db>/objects`; vector store và queue dùng cấu hình test.
- **Lỗi nền giữ nguyên:** `test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access`
  (fixture RAG đã ghi ở phiên911) nếu xuất hiện trong full suite vẫn là FAIL nền, không sửa trong batch.
- **F13 của phiên908 vẫn là vấn đề chất lượng riêng**, chưa sửa; test mock/refactor không chứng
  minh F13 đạt.
- **NOT RUN:** model/OCR thật, benchmark RAG, kiểm tải, trình duyệt/FE; không áp migration 0020 lên
  DB ứng dụng, không restart ứng dụng, không reindex dữ liệu thật.

## 5. Rủi ro, giới hạn

- Hợp đồng FE §6 là nguồn chuẩn cho đợt tích hợp sau; FE chưa được xây/kiểm trong batch này.
- Migration `0020_reverse_flow` phải áp trước khi chạy API/worker mới trên môi trường ứng dụng;
  batch này chỉ chạy trên DB cô lập.
- Purge đã kiểm bằng fixture tổng hợp và adapter test; chưa chứng minh trên MinIO/S3 thật với
  version/delete marker, Qdrant thật quy mô lớn hoặc backup thật.
- Lease/checkpoint và takeover đã kiểm bằng DB cô lập; vận hành thật cần theo dõi
  `GET /source-deletions/active` và audit `source.purge_takeover`.
- `empty` là trạng thái thật của kho không còn bản phát hành; FE không được hiển thị thành
  "Sẵn sàng cho trợ lý".

## 6. Việc tiếp theo

- FE mới dùng §6 của hợp đồng 47: đọc `serving`/`actions`/`preparation`, poll biên nhận lifecycle
  thay vì giữ tiến độ cục bộ, chỉ báo **Đã xóa** khi `status=completed` và `impact.permanent=true`.
- Áp migration `0020_reverse_flow` theo quy trình release trước khi khởi động API/worker mới; batch
  này không tự migrate, không restart.
- Kiểm chứng thật trên môi trường ứng dụng cho withdraw/xóa/replace sau khi có phê duyệt; giữ lỗi
  nền RAG và F13 cho việc riêng.
