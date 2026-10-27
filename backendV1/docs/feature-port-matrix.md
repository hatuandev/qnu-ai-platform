# Ma trận port tính năng

Head hiện hành là [`0003_rag_policy_metadata`](migrations.md), sau baseline
`0001_initial_schema` gộp schema đến0015 phát triển cũ. Các số revision và trạng
thái trong phần ghi nhận các batch dưới đây là lịch sử.

Context673: [RAG policy](rag-policies.md) nối lựa chọn retrieval vào snapshot trợ lý,
metadata có nguồn và human acknowledgement, filter trước TopK, context cùng mục,
judge observe/enforce và trace từng nhánh. Không cài Meilisearch, không thay corpus
hoặc tự kích hoạt generation/config phục vụ.

Context666: [human review gate](publication-review-gate.md), [GC dẫn xuất](storage-cleanup.md),
[recovery mã hóa vào đích mới](recovery.md) và [readiness/worker](readiness.md).
Đã thử API/ARQ/model thật trên PDF được phép và tìm kiếm sau phục hồi; không coi
kết quả chức năng đó là nghiệm thu chất lượng hay triển khai production.

Context658 bổ sung [operations](operations.md) và [hybrid/evaluation](hybrid-evaluation.md).
Job view lấy trạng thái thật; recovery có preview/acceptance, không resend uncertain.
Evidence backup không kèm credential, chưa có database restore. Rerank động qua
ModelOps; dense/FTS/RRF giữ scope/provenance; đánh giá pin snapshot và cùng ứng viên.
Đây là phạm vi API backend, không phải nghiệm thu chất lượng hoặc production.

Context652: [review ngữ nghĩa Compiler](compiler-review.md) có API durable request,
nguồn/draft/bundle pin, kiểm coverage hai chiều và báo cáo excerpts JSON/Markdown.
Model reviewer chọn qua ModelOps, quota/usage/raw/idempotency; không sửa/approve.
Migration0012/2bảng; full qua4nhóm **460PASS/0FAIL/0SKIP**,25ca mới/0ca mất,
383,56s wall. OpenAPI75path/101operation,70path cũ giữ; chưa live/quality,
auto-call worker, UI hoặc migrate phục vụ. [Báo cáo652](../../docs/bao_cao/context652/REVIEW.md).

Context651: [sửa văn bản hậu OCR](ocr-text-review.md) có API đoạn/ô, gợi ý chính tả
và text versions tạo Markdown/JSON cùng nội dung. Chưa có màn hình, chưa dùng
bản sửa trong Compiler hoặc migrate phục vụ; không suy quality từ model giả lập.
Toàn bộ suite cuối qua sáu nhóm **435PASS/0FAIL/0SKIP**,22ca mới/0ca mất.
Các lượt tuần tự trước bị dừng/lỗi có ghi riêng tại [báo cáo651](../../docs/bao_cao/context651/REVIEW.md).

Context649: [trợ lý/hội thoại](assistants-conversations.md) có config/revision,
owner, cặp question/result lưu DB, idempotency/sequence/lease và follow-up qua
ModelOps. Live hai lượt + history/replay PASS trên dữ liệu tổng hợp; chất lượng
ngữ nghĩa chưa nghiệm thu, chưa migrate DB phục vụ.
Full v1 **413PASS/0FAIL/0SKIP**,17ca mới/0ca mất; migration0010/3bảng,
OpenAPI65path/89operation. [Báo cáo649](../../docs/bao_cao/context649/REVIEW.md).

Context648: [API hỏi đáp có trích dẫn](rag-answers.md), tái sử dụng dense search và
runtime chat ModelOps; kiểm citation/nguồn/quyền sau generation. Live BGE-M3 +
Qwen3.5-9B/Qdrant PASS với dữ liệu mẫu, chưa đánh giá chất lượng corpus thật.
Full cuối396PASS/0FAIL/0SKIP,20ca mới/0ca mất; lượt đầu kẹt shutdown Windows,
retry cùng code sạch, chưa sửa nguyên nhân gốc. Xem [báo cáo648](../../docs/bao_cao/context648/REVIEW.md).

Context647: dense embedding ModelOps, job index publication và Qdrant generation,
search trả đoạn/citation đã nối. Full v1 **376PASS/0FAIL/0SKIP**,42ca mới/0ca mất.
Live BGE-M3/ARQ/Qdrant PASS trên dữ liệu mẫu riêng;
chưa migrate DB phục vụ. Xem [index/search](dense-indexing.md) và
[báo cáo647](../../docs/bao_cao/context647/REVIEW.md).

Context646: lifecycle bản biên soạn đã có document/version, preview/receipt và
duyệt/xuất bản/thay thế/thu hồi. Full v1 **334 PASS/0 FAIL/0 SKIP**, gồm17ca mới;
storage Windows sửa theo repro và qua hồi quy, chưa migrate DB phục vụ.
Xem [publication API](compiled-publication.md) và [báo cáo646](../../docs/bao_cao/context646/REVIEW.md).

Context645: runtime chat và Compiler draft đã nối. Model `gh/gpt-6-luna` thử thật
qua 9router/ModelOps/ARQ thành công với tài liệu mẫu; 31 ca mới PASS. Full cuối
316 PASS/1 FAIL vì lỗi LocalBlobStore Windows đã ghi trước; chưa migrate DB phục vụ.
Xem [Compiler v1](compiler-v1.md) và [báo cáo645](../../docs/bao_cao/context645/REVIEW.md).

| Domain | Trạng thái | Ghi chú |
|---|---|---|
| identity | 🟡 dev + SSO JWT/JWKS | Dev gate tường minh, RSA/issuer/audience/expiry có test; chưa live QNU SSO |
| workspaces | 🟢 API + PostgreSQL test | Membership, role, audit, revocation/case/concurrency; resolver là cổng quyền |
| modelops | 🟡 control plane + OCR/chat/embedding/rerank | Provider/key/default/grants, quota/usage; dimension/capacity gắn endpoint/model; chưa probe API/lease/fallback runtime |
| document_types | ⬜ khung | |
| repository | ❌ bỏ | Theo quyết định 2026-10-26; nguồn file thuộc trực tiếp collection (Context637) |
| ocr | 🟢 PDF/DOCX → bằng chứng + API | Render, ModelOps Nemotron, raw/canonical/markdown/manifest; PDF thật riêng đã chạy, chưa quality acceptance |
| knowledge | 🟡 collections + Compiler/publication/index | Upload/revision, draft/lifecycle và index/search ghim publication theo generation |
| rag | 🟡 dense/hybrid/rerank + answer | Search/answer chọn mode; scope/citation kiểm sau HTTP; conversation mặc định dense, chưa streaming |
| assistants | 🟡 config BE | Một collection, ModelOps chat, persona/style, budgets, revision/active; chưa public/tools/SSE |
| conversations | 🟡 owned persistent chat | Question/result/source/error, follow-up, idempotency/sequence/lease; chưa share/FE/stream |
| tools / workflows | ⬜ khung | ngoài MVP |
| evaluation | 🟡 so sánh retrieval qua API | Snapshot/candidates/labels/metrics/errors; chưa human benchmark/answer quality gate |
| operations | 🟡 jobs/evidence backups | Progress/usage thật, recovery preview/outbox, retention thủ công; chưa full DR restore |

Ký hiệu: 🟢 đã port + có kiểm chứng · 🟡 một phần · ⬜ khung thư mục · ❌ loại bỏ.

## Ghi nhận scaffold trước batch636 (lịch sử)

- Ruff toàn `backendV1/`: PASS.
- Unit test (workspace policy + modelops policy + health + contract): PASS.
- OpenAPI: 6 path workspaces, 6 path modelops.
- Migration 0002/0003: **chưa chạy** — Postgres/Docker đang tắt (NOT RUN).
- Integration API test (`tests/integration`): **NOT RUN** — cần `TEST_DATABASE_URL`.

## Kiểm chứng Context636 — 2026-10-26

- Full v1 cuối: **60 PASS / 0 FAIL / 0 SKIP**, 12,39s, exit0, đúng venv/uv.lock v1.
- PostgreSQL thật, migration0001–0004 và ORM diff PASS; sentinel/version legacy giữ, DBtest đã dọn.
- Ruff, OpenAPI35operation và lockfile check PASS. Backend/app475file giữ hash.
- Chưa migrate DB ứng dụng, live SSO/inference/OCR/UI; đây là control plane và hợp đồng metering.
- [Báo cáo636](../../docs/bao_cao/context636/REVIEW.md).

## Kiểm chứng Context637 — 2026-10-26 (knowledge collections)

- Full v1 cuối: **104 PASS / 0 FAIL / 0 SKIP**, 32,49s, exit0, harness cô lập + PostgreSQL thật.
- Migration `0005_knowledge_collections` khớp ORM; sentinel/version legacy giữ; DBtest đã dọn.
- Ruff toàn `backendV1/` PASS; OpenAPI31 path (thêm 6 path collection/source/revision).
- Luồng chạy thật: xác thực → workspace → tạo collection → upload → lưu nguồn/phiên bản → chi tiết → tải lại đúng bytes gốc.
- Chưa có parser/OCR/worker ingestion/chunk/embedding/index/publication/RAG/frontend; nguồn dừng ở `stored`.
- [Báo cáo637](../../docs/bao_cao/context637/REVIEW.md).

## Kiểm chứng Context639 — 2026-10-26 (sửa review638)

- Sửa ghi local nguyên vẹn khi writer lỗi, fingerprint idempotency có title hiệu lực,
  và downgrade0005 từ chối trước khi version đổi. Append revision từ chối title422.
- Sổ upload cũ vẫn replay đúng title, không backfill; đường dẫn dài/rename đồng thời
  trên Windows có regression, không coi file sai bytes là thành công.
- Baseline3FAIL → focused24PASS → full v1 **121PASS/0FAIL/0SKIP**,40,58s,exit0.
- Ruff toàn v1/format7file/OpenAPI31path PASS;17ca mới.10DBtest dọn,475legacy app giữ hash.
- DB phục vụ chưa migrate, luồng vẫn `stored`; chưa OCR/index/RAG hoặc live S3.
- [Báo cáo639](../../docs/bao_cao/context639/REVIEW.md).

## Kiểm chứng Context641 — capacity ModelOps

- API nhận token_limits theo model; context/input/output không trần chung8K/32K,
  unknown/configured/stale, binding endpoint/model. Public API kiểm budget có quyền.
- Gỡ trần validation32768 của cấu hình output OCR; default8192 vẫn là workflow budget.
- Focused44PASS; full snapshot152PASS/2FAIL/0SKIP,33ca capacity mới PASS. Full còn lỗi
  regression downgrade639 sau migration0006 và PermissionError local writer đồng thời.
- Ruff/format/OpenAPI PASS;4DBtest dọn,475legacy app giữ. Không migrate DB phục vụ.
- Runtime OCR đang được viết riêng chưa gọi guard; chưa discovery hoặc live inference.
- [Điểm nối OCR](model-capacity.md) · [Báo cáo641](../../docs/bao_cao/context641/REVIEW.md).

## Kiểm chứng Context640 — 2026-10-26 (luồng xử lý PDF/DOCX)

- Upload PDF/DOCX → revision gốc → yêu cầu xử lý trong cùng transaction → dispatch sau
  commit → worker claim có lease → render → OCR từng trang qua ModelOps runtime → raw +
  canonical JSON + Markdown + manifest → đọc qua API (8 route mới).
- Migration `0006_ocr_processing` (3 bảng, composite FK theo workspace, partial unique
  index một lượt hoạt động/revision, `downgrade()` từ chối). Không sửa 0005.
- Port chọn lọc từ `backend/app/modules/ocr` (layout Nemotron, adapter), bỏ Repository,
  cơ chế quyền cũ và các luồng chưa cần; ghi rõ phần viết lại trong báo cáo.
- Full v1 cuối: **249 PASS / 0 FAIL / 0 SKIP**, 83,39s, exit0, harness cô lập.
  95 ca mới: 81 unit + 14 integration. Baseline trước batch 154 (152 PASS + 2 FAIL của 641).
- Đóng hai lỗi còn mở của Context641: regression downgrade639 (nay kiểm bất biến "không
  hạ cấp âm thầm" thay vì chuỗi của riêng 0005) và `PermissionError` local writer (chỉ do
  `basetemp` ngoài harness).
- Ruff toàn v1 PASS; OpenAPI **39 path / 54 operation** (+8 path processing-runs).
- Live Nemotron: **NOT RUN** — không có endpoint/credential thật; provider loopback trong
  test là mock, được ghi rõ, không dùng để tuyên bố chất lượng OCR.
- Chưa có Compiler/chunk/embedding/index/publication/RAG/frontend; chưa migrate DB phục vụ.
- [Thiết kế luồng](ocr-processing.md) · [Báo cáo640](../../docs/bao_cao/context640/REVIEW.md).

## Kiểm chứng Context643 — sửa sáu lỗi OCR642

- Startup, capacity/quota, pin target/prompt, heartbeat/fencing/recovery, raw retention
  đã nối runtime. DOCX section header/footer chưa hỗ trợ trả lỗi, không bỏ âm thầm.
- Baseline6FAIL → focused76PASS → full **265PASS/0FAIL/0SKIP**,98,51s.16ca mới;
  Ruff/format/OpenAPI PASS. Replay user response1PASS, raw khớp bytes,10block/bảng6x6.
- 5DBtest dọn,475legacy giữ; DB chính chưa migrate. Driver local không đổi, không
  suy đã sửa nguyên nhân PermissionError642 từ một lượt fullPASS.
- Chưa live inference/so ảnh nguồn; OCR thật cần capacity + accounting ảnh trong
  ModelOps. Chưa Compiler/index/RAG. [Báo cáo643](../../docs/bao_cao/context643/REVIEW.md).
