# Phiên916 — Hoàn tất các lỗi còn lại của luồng xử lý ngược

## 1. Yêu cầu, phạm vi và giả định

Tiếp nối phiên 914/915 trên nhánh `feat/v1-user-workflow`, hoàn tất năm nhóm lỗi còn lại của
`backendV1` trong luồng xử lý ngược, giữ nguyên migration `0020_reverse_flow` đã đồng bộ:

1. **P1 — Xóa nền và tiếp quản.** Ghi nhận tác vụ còn khả năng ghi trước khi đổi trạng thái hủy;
   chỉ dọn khi tác vụ đã dừng hoặc có cơ chế chặn ghi muộn; chặn cả nhánh thành công và lỗi của
   soát chính tả; kiểm quyền sở hữu lease ở mọi bước dọn/tiến độ/lỗi/hoàn tất; worker cũ không
   thể xóa lease của worker mới; giữ cùng biên nhận khi phục hồi sau lỗi.
2. **P1 — Quyền đọc biên nhận.** Chỉ mở quyền đọc cho admin đúng workspace với biên nhận
   `source/delete` đã xác nhận; biên nhận hội thoại và tác vụ của lượt chat giữ phạm vi chủ sở hữu.
3. **P1 — Dọn embedding.** Chỉ xóa tệp raw embedding thuộc nguồn bị xóa; với lô dùng chung, đối
   chiếu manifest với `chunk_ids` theo đúng thứ tự, giữ vector của nguồn còn lại, ghi tệp dẫn xuất
   và dọn tệp gốc; không xác minh được ánh xạ hoặc storage lỗi thì giữ biên nhận tiếp tục được.
4. **P2 — Quản lý kho.** **Ngừng dùng cho trợ lý** ở cấp kho thu hồi đúng phạm vi, đồng bộ chỉ mục,
   giữ tệp nguồn; cho xóa kho khi chỉ còn bản ghi thư mục đã xóa, vẫn chặn khi còn tài liệu/thư mục
   hoạt động.
5. **P2 — Trạng thái tài liệu.** Chỉ báo **Đang phục vụ** khi chỉ mục đang hoạt động thực sự chứa
   đúng phiên bản; phân biệt bản vừa phát hành với bản đang phục vụ; chỉ lượt xóa đã xác nhận còn
   `pending` mới khóa cập nhật/xóa; preview mở rồi hủy/hết hạn không thu hẹp quyền thao tác.

Phạm vi là backend và tài liệu hợp đồng; FE V2 không thuộc batch này. Giữ nguyên workspace là biên
quyền qua `resolve_workspace_access`, nguồn/canonical OCR/bảng/ô/header/footnote/bbox/revision/hash/
bằng chứng, idempotency/lease/audit và lỗi provider/hạ tầng báo thật. Không clear/reset/seed/reindex,
không upload lại, không thay publication, không restart phiên người dùng, không deploy, không Git
push; không chạy test trên DB ứng dụng; không cài thêm dependency; không retry model để làm xanh,
không nới assertion hoặc bỏ guard. F13 của phiên 908 vẫn là vấn đề chất lượng riêng. Giữ nguyên
5 database test cũ không liên quan: `4a262de990814899`, `711acdc069ac4b68`, `974f2878024d45d7`,
`9f76fb9421be44e1`, `f809d0c223404df1`.

## 2. Kết quả theo phạm vi

### P1.1 — Chặn ghi muộn, lease sở hữu và tiếp quản

- `ocr/review/detection.py`: cả nhánh thành công và lỗi đều đọc lại run trước khi ghi; run đã
  `cancelled`, hết hạn hoặc bị purge không nhận raw evidence/suggestions đến muộn; run còn
  `running` quá hạn chuyển `uncertain` với `ocr_spelling_interrupted` thay vì tự nhận hoàn tất.
- `lifecycle/effects.py`: hủy OCR/Compiler/Preparation giữ lease làm tín hiệu chờ purge; chỉ lượt
  chat đồng bộ mới hết hạn lease ngay để người gọi thấy dừng tức thì. Purge ghi checkpoint các job
  đã hủy trước khi chuyển trạng thái và chỉ dọn khi các job đó không còn `queued|running`.
- `lifecycle/purge.py`: mỗi bước dọn dùng UPDATE có điều kiện `status=pending`, đúng `worker_id`,
  lease còn hiệu lực (`_fence`); heartbeat gia hạn 120 giây; mất quyền sở hữu trả `not_claimed`
  và rollback, không ghi đè worker mới. `_record_failure` chỉ ghi lỗi/xóa lease khi hàng còn thuộc
  worker hiện tại hoặc chưa có chủ; biên nhận giữ nguyên `id`, `_purge_plan` và bước tiến độ để
  chạy lại cùng biên nhận. Hoàn tất cũng là UPDATE có fence, không dùng ghi vô điều kiện.
- Takeover chỉ nhận khi không có lease hiệu lực; giữ `confirmed_by`, ghi `takeover_by/takeover_at`.

### P1.2 — Quyền đọc biên nhận

- `lifecycle/service.py::detail`: chủ sở hữu luôn đọc được biên nhận của mình; admin workspace chỉ
  đọc thêm biên nhận `kind=source`, `action=delete`, `status!=preview` — tức lượt xóa nguồn đã xác
  nhận cần tiếp quản. Biên nhận hội thoại và tác vụ của lượt chat không mở cho admin.
- Test qua API với chủ sở hữu, admin cùng workspace và người ngoài workspace; preview vẫn chỉ chủ
  sở hữu xem được.

### P1.3 — Dọn embedding dùng chung

- `_filtered_batch_receipts` đọc raw receipt, xác minh từng entry bằng `index` và
  `vector_sha256` trong manifest; lô chỉ chứa chunk bị xóa thì xóa tệp raw; lô còn chunk khác thì
  ghi tệp dẫn xuất đã lọc, đánh số lại `index`, cập nhật `count`/`raw_sha256`/`chunk_ids`.
- `_reseal_indexes` ghi manifest dẫn xuất cho generation còn lại, giữ `previous_manifest_sha256`
  và lưu danh sách tệp cần dọn vào `result._purge_cleanup` trước khi xóa; lần chạy lại hoàn tất
  đúng danh sách đã ghi. Thiếu/sai ánh xạ trả `409 purge_index_mapping_unverified`, storage lỗi
  giữ biên nhận `pending`; không xóa mù và không gọi model/re-embed.
- Kiểm cả chỉ mục một nguồn và chỉ mục dùng chung; vector/dẫn chứng của nguồn còn lại được giữ.

### P2.4 — Ngừng dùng và xóa kho

- `withdraw` cấp kho thu hồi mọi `CompiledVersion` `published` thuộc kho trong một transaction,
  tăng `state_version`/`change_sequence`, đánh thức `kb_index_sync` và giữ nguyên tệp/revision.
- `inspect collection/delete` bỏ qua bản ghi `KBFolder` đã xóa mềm khi đếm thư mục; vẫn trả
  `409 collection_not_empty` khi còn tài liệu hoặc thư mục đang hoạt động.

### P2.5 — Trạng thái phục vụ và khóa thao tác

- `sources/summary.py`: `served_*` chỉ xuất hiện khi bản đang trỏ `serving_revision_no` còn
  `published` và `document_readiness` khớp đúng `version_id`/`version_state`/`bundle_sha256` của
  generation đang hoạt động. Con trỏ publication đơn thuần không được báo là đang phục vụ.
- `preparing_revision_no` phân biệt ba tình huống: không có gì mới → `null`; đang có bản mới hơn
  → số bản mới; chưa phục vụ được bản nào nhưng còn bản phát hành → số bản phát hành; không còn
  bản phát hành nào nhưng con trỏ serving còn trỏ bản cũ → số bản con trỏ (bản vừa bị thu hồi).
  `SourceServingState.served_revision_no` cho phép `null` khi không phục vụ.
- `pending_delete` chỉ tính `LifecycleAction.status="pending"`; preview đang mở/hết hạn hoặc biên
  nhận đã kết thúc không khóa `can_update`/`can_delete`.

### Migration

- `0020_reverse_flow` giữ nguyên nội dung đã đồng bộ: cột biên nhận `phase`, `progress` (JSONB,
  mặc định `{}`), `worker_id`, `lease_expires_at`, `attempt_count`, `last_error_at`,
  `confirmed_by`, `takeover_by`, `takeover_at`; mở rộng `ck_index_sync_status` với `empty`;
  downgrade chặn khi còn source-delete `pending` thiếu `not_before`, chuyển `empty` về `ready`.

## 3. Tệp thay đổi

- `backendV1/qnu/domains/lifecycle/purge.py` — fence/lease/heartbeat/failure/completion, checkpoint
  job, dọn batch embedding và `_purge_cleanup`.
- `backendV1/qnu/domains/lifecycle/effects.py` — lease chờ của OCR/Compiler/Preparation, withdraw
  cấp kho.
- `backendV1/qnu/domains/lifecycle/service.py` — quyền đọc biên nhận, đếm thư mục đã xóa khi xóa kho.
- `backendV1/qnu/domains/lifecycle/models.py`, `schemas.py`, `router.py`, `targets.py`,
  `purge_graph.py` — cột/phase/progress, API tiếp quản, allowlist thao tác.
- `backendV1/qnu/domains/knowledge/sources/summary.py`, `schemas.py`, `service.py`, `router.py` —
  serving theo readiness, preparing/published/served, khóa theo pending delete, staged revision.
- `backendV1/qnu/domains/knowledge/index/models.py`, `sync.py` — trạng thái `empty`, retire generation.
- `backendV1/qnu/domains/knowledge/preparation/service.py`, `schemas.py` — fencing cancel/link, lease,
  bước chuẩn bị.
- `backendV1/qnu/domains/knowledge/folders/service.py` — thứ tự kiểm khôi phục thư mục.
- `backendV1/qnu/domains/knowledge/compilation/models.py`, `modelops/connections/service.py`,
  `platform/schema.py` — ràng buộc/khóa ngoại, chặn xóa model còn tham chiếu, schema head.
- `backendV1/qnu/domains/ocr/review/detection.py` — chặn ghi muộn ở cả nhánh thành công và lỗi.
- `backendV1/alembic/versions/0020_reverse_flow.py` — giữ nguyên, đã đối chiếu.
- Test: `tests/integration/test_source_purge_716.py`, `test_ocr_text_review_651.py`,
  `test_lifecycle_659.py`, `test_lifecycle_runtime_659.py`, `test_knowledge_summary_api.py`,
  `test_knowledge_actions_708.py`, `test_index_api_647.py`, `test_preparation_intents.py`,
  `test_publication_646.py`, `test_publication_index_sync_878.py`, `test_provider_connections_702.py`,
  `test_compiler_edits_654.py`, `knowledge_support.py`; `tests/unit/test_source_purge_716.py`,
  `tests/unit/test_migration_baseline_661.py`.
- Tài liệu: `backendV1/docs/resource-lifecycle.md`,
  `docs/quy_trinh/47_hop_dong_luong_chinh_backend_v1.md`, nhật ký này, README, WORK_LOG,
  PROJECT_CONTEXT và snapshot phiên này.

## 4. Kiểm chứng

| Phạm vi | Lệnh | Kết quả | Receipt |
| :--- | :--- | :--- | :--- |
| Ruff toàn bộ 37 tệp Python thay đổi | `uv run ruff check <files>` | **All checks passed** | — |
| Định dạng tệp vừa sửa | `uv run ruff format --check` | **Pass sau khi format 2 tệp** | — |
| Whitespace diff | `git diff --check` | **OK** | — |
| Nhóm P1 (purge, chính tả, lifecycle, summary) | `uv run python scripts/test_database.py tests/integration/test_source_purge_716.py tests/integration/test_ocr_text_review_651.py tests/integration/test_lifecycle_659.py tests/integration/test_knowledge_summary_api.py -q` | **62 passed** (340,85s) | `qnu_v1_test_9e633021e1244db3`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 349,81s |
| Nhóm #2 lần đầu (tái hiện lỗi) | `uv run python scripts/test_database.py tests/integration/test_lifecycle_runtime_659.py tests/integration/test_index_api_647.py tests/integration/test_knowledge_actions_708.py tests/integration/test_preparation_intents.py tests/integration/test_publication_646.py tests/integration/test_publication_index_sync_878.py tests/integration/test_provider_connections_702.py tests/integration/test_compiler_edits_654.py tests/unit/test_source_purge_716.py tests/unit/test_migration_baseline_661.py -q` | **126 passed, 4 failed** (670,45s) | `qnu_v1_test_2adf89af69cd492e`; `pytest_exit=1` |
| Retest trọng tâm sau sửa | `uv run python scripts/test_database.py tests/unit/test_source_purge_716.py tests/integration/test_lifecycle_runtime_659.py::test_withdrawn_old_version_while_replacement_waits_never_activates_candidate tests/integration/test_knowledge_summary_api.py -q` | **23 passed, 1 failed** (123,66s) | `qnu_v1_test_a676a60e43d64fa8`; lỗi còn lại ở test double UPDATE |
| Unit purge sau khi mô phỏng UPDATE | `uv run python scripts/test_database.py tests/unit/test_source_purge_716.py -q` | **12 passed** (1,97s) | `qnu_v1_test_5b07ff01b54e44a1`; `pytest_exit=0`, 13,00s |
| Nhóm #2 hoàn tất (10 tệp) | như lệnh nhóm #2 | **130 passed** (641,60s) | `qnu_v1_test_f345003cc63b491f`; `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`, 662,05s |
| Full backend suite | `uv run python scripts/test_database.py tests -q` | **ĐANG CHẠY — cập nhật sau khi hoàn tất** | — |

- **Tái hiện trước khi sửa (4 FAIL):**
  `test_lifecycle_runtime_659.py::test_withdrawn_old_version_while_replacement_waits_never_activates_candidate`
  (`preparing_revision_no` trả 2 thay vì 1),
  `test_source_purge_716.py::test_partial_storage_failure_keeps_intent_and_same_receipt_can_resume`,
  `test_source_purge_716.py::test_worker_rechecks_actor_authority_before_any_delete`,
  `test_source_purge_716.py::test_remaining_index_gets_derived_manifest_without_reembedding`
  (test double thiếu trường lease/`result`/`scalar`). Sửa logic `preparing_revision_no`; bổ sung
  test double mô phỏng đúng UPDATE có fence và các trường mới; **không nới assertion**.
- Test chạy trên DB do harness tạo/drop; storage/vector/queue dùng cấu hình test. Không dùng DB ứng dụng.
- **Lỗi nền giữ nguyên:** `test_rag_verification_policy_672.py::test_assistant_chat_uses_persisted_hybrid_rerank_policy_and_checks_provider_access`
  nếu xuất hiện trong full suite vẫn là FAIL nền, không sửa trong batch.
- **F13 phiên 908 vẫn là vấn đề chất lượng riêng**, chưa sửa; test mock/refactor không chứng minh F13 đạt.
- **NOT RUN:** model/OCR thật, benchmark RAG, kiểm tải, trình duyệt/FE; không áp `0020_reverse_flow`
  lên DB ứng dụng, không restart API/worker, không reindex dữ liệu thật.

## 5. Rủi ro, giới hạn

- Dọn embedding dùng chung đã kiểm bằng fixture tổng hợp; chưa kiểm MinIO/S3 thật với version/delete
  marker hoặc Qdrant quy mô lớn.
- Lease/heartbeat/takeover đã kiểm trên PostgreSQL cô lập; vận hành thật cần theo dõi
  `GET /lifecycle/source-deletions/active` và audit `source.purge_takeover`.
- Khi không còn bản phát hành/phục vụ, `preparing_revision_no` lấy con trỏ serving còn lại; đây là
  quy ước đọc trạng thái để FE không báo sai bản đang phục vụ, không phải bản mới đang chuẩn bị.
- Migration `0020_reverse_flow` phải áp theo quy trình release trước khi chạy API/worker mới; batch
  này chỉ chạy trên DB cô lập.

## 6. Việc tiếp theo

- Chờ kết quả full backend suite, cập nhật bảng trên và bàn giao diff cho người dùng review.
- Áp migration `0020_reverse_flow` theo quy trình release trước khi khởi động API/worker mới; không
  tự migrate/restart/reindex trong batch.
- Kiểm chứng thật trên môi trường ứng dụng cho withdraw/xóa/replace sau khi có phê duyệt; giữ lỗi
  nền RAG và F13 cho việc riêng.
