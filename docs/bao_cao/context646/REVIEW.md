# Context646 — Phiên bản, duyệt và xuất bản bản biên soạn v1

Ngày 26/10/2026. Người dùng yêu cầu triển khai bước 3 sau Compiler645: quản lý
phiên bản, duyệt, xuất bản, thay thế và thu hồi, ưu tiên BE. Vòng đời này do QNU
định nghĩa; tham khảo Kotaemon ở tổ chức nguồn và citation, không tuyên bố repo
đó có đúng workflow này. Không thêm framework hoặc dependency.

## Kết quả triển khai

- `knowledge/publication` có model/schema/router/service/access, evidence checks,
  preview/decision và API đọc bản hiện hành. Document key tường minh; version_no
  theo document, tách khỏi generation của Compiler theo collection.
- Workflow `draft → approved → published`, thay thế atomic làm bản cũ superseded;
  withdraw không xóa bytes. Phục hồi bản cũ cần approve + publish mới.
- Admin/editor đăng ký version; reviewer/admin approve; admin publish/withdraw;
  member đọc trong workspace có quyền. Resolver kiểm lại quyền lúc xác nhận,
  không coi ID hoặc cờ model/client là bằng chứng quyền/approval.
- Preview ghim actor/action/reason, hash, sequence, bản active và hạn dùng; commit
  cần đúng preview SHA và Idempotency-Key. State drift, expiry, sai actor/hash hoặc
  reused key khác yêu cầu bị chặn. Receipt/audit cùng transaction với trạng thái.
- Snapshot ghim run/input/draft/Markdown/bundle hash, provider/model/prompt và
  source revision/OCR generation/canonical/manifest hash. Kiểm bytes/hash nguồn
  gốc, canonical, manifest, Compiler snapshot và artifact qua BlobStore.
- Publish cần receipt approve khớp bundle/state; read published cần receipt publish
  khớp, đúng source revision hiện hành và bytes nguyên vẹn. Nguồn mới/stale/mất/hỏng
  báo lỗi, không tự chuyển revision hoặc trả rỗng giả. Withdraw vẫn dùng được khi
  nguồn/artifact hỏng. Draft/history không tự được xem là nguồn indexing.
- `content` trong response published giữ nguyên draft Compiler; trạng thái hiệu lực
  ở envelope `version.status` + receipt. Không ghi lại output gốc để đổi cờ duyệt.
- Migration `0008_publication`: 4 bảng v1, composite FKs, unique idempotency/scope
  và partial unique index tối đa 1 published/document. Không đổi migration cũ.

## Sửa lỗi storage được nêu trong bước 3

Baseline mới tái hiện đúng lỗi: replace bị PermissionError rồi lần đọc đối chiếu
đích cũng bị từ chối tạm thời. Driver hiện có không đọc lại nên báo thất bại dù
đích có toàn bộ bytes mong đợi. Đây là cơ chế lỗi WinError5 đã thấy ở Context642/645.

Sửa hẹp `qnu/adapters/storage/local.py`: 64 striped locks cố định theo path chuẩn
hóa/case trong process; ghi vẫn staging + atomic replace trong `to_thread`. Đọc
PermissionError tối đa 6 lần, tổng backoff 155ms; nếu replace bị từ chối thì chỉ
thành công khi **toàn bytes khớp**. Permanent denial/khác bytes/staging lỗi vẫn
báo lỗi, giữ bản đã commit và dọn temporary. Không thêm khóa phân tán, không coi
một lần test xanh là bảo đảm mọi filesystem đã hết lỗi.

## Kiểm chứng đã chạy

- Baseline: **2 FAIL** đúng API publication 404 và transient destination read denial.
- Lượt migration đầu có **migration_exit 1**: snapshot autogenerate thiếu tiền tố
  `sa.` ở `Text()` của JSONB. Đã sửa migration mới, không sửa assertion ứng dụng.
- Smoke sau sửa: **12 PASS / 0 FAIL / 0 SKIP**, 6,13 giây, exit 0.
- Focused đầu: **32 PASS / 0 FAIL / 0 SKIP**, 50,85 giây, exit 0.
- Focused cuối: **35 PASS / 0 FAIL / 0 SKIP**, 72,20 giây, exit 0; bao gồm migration
  khớp ORM/sentinel, negative cases publication và hồi quy LocalBlobStore cũ.
- Ruff `qnu scripts tests alembic`: **PASS**, exit 0.
- Format 13 file thuộc feature/storage/migration/tests: **PASS**.
- OpenAPI: **54 path / 72 operation**, thêm 9 path/11 operation; path cũ không đổi.
- Full v1: **334 PASS / 0 FAIL / 0 SKIP**, 237,43 giây, pytest exit 0;
  harness 244,24 giây. Chạy full một lần cuối batch, không nới/bỏ ca cũ.
- So JUnit với full-final645: **17 ca mới đều PASS, 0 ca cũ bị bỏ**. Ca
  `test_same_key_writers_do_not_fail_storage_under_contention` từng FAIL645 nay PASS
  sau sửa driver; ca deterministic transient-read mới cũng PASS.
- Đối chiếu **6 DB test, 0 còn lại**, toàn bộ receipt xác nhận dọn DB và giữ
  sentinel/version legacy. Bao gồm lượt migration thất bại đã được dọn.
- Kiểm UTF-8/LF, literal giống credential và liên kết thuộc phạm vi mới/sửa:
  **33 file PASS**; diff-check các index đã sửa PASS. Liên kết lịch sử ngoài phạm
  vi không được sửa. Artifact kiểm cuối: `final-document-source-check.json`.
- So nguồn baseline: **475/475 file Python legacy app giữ SHA256**; Compiler/
  ModelOps/OCR runtime cũ của v1 không sửa. Không mất dữ liệu hoặc reset thay đổi
  chưa commit của người dùng.

17 ca mới: 14 integration (real FastAPI/PostgreSQL/BlobStore, OCR/chat HTTP loopback
giả lập) và 3 unit storage. Ca tích hợp kiểm full lifecycle, replacement/history,
role/actor/revocation, preview/hash/expiry/idempotency/stale, concurrent publish,
source đổi giữa preview/commit, missing source, artifact tamper, cờ approved thiếu
receipt và phục hồi phiên bản có duyệt lại. Không gọi LLM thật hoặc dựng benchmark.

## Lệnh và bằng chứng

Cwd `D:/DuAnPhanMem/qnu-ai-platform/backendV1`. Wrapper ignored đọc hạ tầng có sẵn
vào process con, không in credential; harness tạo/migrate/dọn DB riêng loopback
`qnu_v1_test_*`, giữ sentinel/version legacy. Không dùng DB phục vụ để thử trạng thái.

```text
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py baseline tests/integration/test_publication_646.py tests/unit/test_local_storage_retry_646.py -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py focused-final tests/integration/test_publication_646.py tests/unit/test_local_storage_retry_646.py tests/unit/test_local_blob_store.py tests/integration/test_knowledge_regressions_639.py tests/migrations -q --tb=short
.venv/Scripts/python.exe -X utf8 -B storage/context646/run_checks.py full tests -q --tb=short
.venv/Scripts/ruff.exe check qnu scripts tests alembic --output-format concise
```

Artifacts cục bộ ignored: baseline hash, các log/XML/receipt, OpenAPI diff, scope
verification, `test-summary.json` và `cleanup-verification.json`.
Dữ liệu mẫu/response không đưa vào Git. Không lưu credential, PII,
prompt riêng hoặc Base64 OCR vào báo cáo/memory/log.

## Giới hạn

- Chưa áp migration 0008 vào DB phục vụ, chưa restart/deploy API/worker; chưa publish
  tài liệu thật, reindex hoặc thay active publication đang phục vụ.
- Chưa chunk/embedding/vector index/RAG/FE v1. Bước indexing sau phải gọi ranh giới
  read published có kiểm quyền/hash/nguồn; không lấy toàn list version hoặc draft.
- Duyệt là quyết định của actor có quyền, không phải benchmark chứng minh LLM/OCR
  luôn đúng. Chất lượng chuyên sâu vẫn để sau theo yêu cầu. Không tự seed approval.
- Lịch sử và artifact không có delete/edit endpoint; chưa có review rejection hoặc
  chỉnh sửa văn bản tại chỗ. Nội dung mới đi qua Compiler run/version mới.
- Khóa storage chỉ trong process, read retry có giới hạn; không thay thế distributed
  locking hoặc giải quyết mọi nguyên nhân Windows sharing violation.

[API và vận hành](../../../backendV1/docs/compiled-publication.md) ·
[Quy trình 23](../../quy_trinh/23_phien_ban_va_xuat_ban_backendv1.md).
