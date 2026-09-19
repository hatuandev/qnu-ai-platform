# HƯỚNG DẪN CẢI THIỆN CODE QNU AI PLATFORM ĐỂ ĐẠT PRODUCTION CANDIDATE

> Ngày lập: 19/09/2026  
> Mốc tham chiếu: code review sau khi hoàn thành Giai đoạn 4 của Kế hoạch 07.  
> Điểm xuất phát tham khảo: **6,5/10 — Internal Beta mạnh**.  
> Mục tiêu: **8,5+/10 — Production Candidate có bằng chứng**, không thay đổi sai kiến trúc Modular Monolith hiện tại và không “tăng điểm” bằng mock, test hình thức hoặc tài liệu không khớp runtime.

---

## 1. Cách hiểu đúng về “tăng điểm đánh giá”

Điểm của dự án không nên tăng chỉ vì có thêm nhiều màn hình, nhiều test hoặc nhiều abstraction. Điểm chỉ tăng khi rủi ro vận hành thật giảm và có bằng chứng tái lập được.

| Cấp độ | Dấu hiệu | Cách đánh giá |
| :--- | :--- | :--- |
| Có code | Có class, API, UI hoặc test | Chưa đủ để cộng điểm production |
| Có tích hợp | Frontend gọi được Backend, Backend gọi được dependency | Chỉ cộng điểm khi lỗi được phản ánh trung thực |
| Có dữ liệu thật | PostgreSQL, Qdrant, MinIO và Redis đồng nhất | Phải kiểm tra lifecycle, tenant và revision |
| Có khả năng phục hồi | Retry, timeout, idempotency, reconciliation | Phải có test đường lỗi và metric quan sát |
| Sẵn sàng production | Migration, secret, CI, backup/restore, runbook | Phải vượt qua release gate trên môi trường sạch |

### Mục tiêu điểm theo nhóm

| Nhóm | Hiện tại tham khảo | Mục tiêu | Điều kiện chính để đạt |
| :--- | :---: | :---: | :--- |
| Kiến trúc & maintainability | 7,0 | 8,5 | Service/page lớn được chia theo use case, transaction rõ |
| Database & data integrity | 5,0 | 9,0 | Alembic là nguồn sự thật, schema live đúng head, không auto-repair |
| RAG & Knowledge | 6,5 | 9,0 | Có dữ liệu retrievable thật, payload versioned, no-answer đúng |
| Assistant & Workflow | 7,0 | 8,5 | Approval tin cậy, retry/timeout/cancel/idempotency |
| ModelOps | 6,0 | 8,5 | Key mã hóa, stream thật, quota/cost ghi đúng một lần |
| Security | 5,0 | 8,0 | Dev Access Gate đơn giản nhưng actor/tenant/approval đáng tin cậy |
| Testing & CI | 6,5 | 8,5 | Hết warning quan trọng, test live, coverage gate, CI bắt buộc |
| Observability & deployment | 5,0 | 8,0 | Metrics/rate limit/readiness/backup-restore được diễn tập |

---

## 2. Chín nguyên tắc bắt buộc khi sửa code

1. **Sửa nguồn sự thật trước giao diện.** Database schema, lifecycle và runtime contract phải đúng trước khi tô đẹp UI.
2. **Không fake-success.** Dependency lỗi phải trả `failed`, `degraded` hoặc `insufficient_context`; không dựng dữ liệu thành công giả.
3. **Alembic sở hữu schema.** `create_all()` chỉ được dùng trong test cô lập; production không tự tạo/sửa bảng khi startup.
4. **Trusted context sở hữu danh tính.** `tenant_id`, `workspace_id`, actor và quyền duyệt không lấy từ payload do client tự khai báo.
5. **Một side effect chỉ được ghi nhận một lần.** Usage, quota, cost, approval và tool execution cần idempotency key hoặc unique constraint.
6. **RAG chỉ truy xuất phiên bản đã duyệt.** Không dùng blacklist trạng thái; dùng positive allowlist `ready + is_retrievable + đúng revision`.
7. **Async thật ở biên I/O.** Không gọi `boto3`, `Path.read_bytes()` hoặc network đồng bộ trực tiếp trong event loop.
8. **Test phải làm lộ lỗi.** Mỗi luồng quan trọng có ít nhất một ca dependency down, dữ liệu rỗng, tenant sai hoặc approval hết hạn.
9. **Refactor theo lát cắt nhỏ.** Không big-bang rewrite; mỗi phiên phải có rollback, acceptance criteria và file ownership rõ.

---

## 3. Thứ tự triển khai an toàn

```text
Khóa baseline và ownership
  → Đồng bộ schema/migration
    → Chuyển đổi dữ liệu và secrets
      → Rebuild chỉ mục RAG
        → Siết trust boundary/HITL
          → Stream + usage accounting
            → Workflow durability
              → Refactor maintainability
                → CI, observability và release gate
```

Không nên đảo thứ tự ba bước đầu. Nếu schema chưa đúng mà đã reindex hoặc seed lại dữ liệu, kết quả có thể tiếp tục bị lệch và khó phân biệt lỗi code với lỗi dữ liệu cũ.

### Quy tắc phối hợp với session seed/provider đang chạy

- Session seed/provider được quyền sở hữu các tệp seed và dữ liệu Provider trong thời gian đang chạy.
- Session cải thiện schema chỉ tạo migration, kiểm tra và công cụ chuyển đổi; không đồng thời sửa manifest seed/provider.
- Không chạy seed, migration dữ liệu hoặc reindex trên cùng database từ hai session.
- Trước mỗi đợt ghi dữ liệu phải lưu: Git commit, Alembic revision, số bản ghi từng bảng và số point Qdrant.
- Sau khi session song song kết thúc, chạy lại full gate trên **cùng một commit và cùng một database snapshot**.

---

## 4. Giai đoạn A — Khóa baseline có thể tái lập

### Mục tiêu

Biết chính xác trạng thái nào đang được cải thiện và không trộn thay đổi của nhiều session.

### Cách làm đúng

1. Ghi lại `git status`, commit nền, Alembic head/current và phiên bản image của PostgreSQL, Qdrant, Redis, MinIO.
2. Chụp số liệu nền:
   - số bảng ORM và số bảng thật;
   - số documents theo status/index status;
   - số chunks/facts retrievable;
   - số collection/points Qdrant;
   - số provider/key đang active;
   - số test pass, warning, bundle size.
3. Gắn ownership cho từng nhóm file nếu có nhiều session.
4. Không stage cache OCR, file scan, `.env`, artifact hoặc file nhị phân lớn.

### Bằng chứng hoàn thành

- Có một báo cáo baseline ngắn chứa commit SHA, schema revision và counts.
- Full Backend/Frontend gate chạy trên cùng commit.
- Không có file không rõ chủ sở hữu trong phạm vi sắp sửa.

---

## 5. Giai đoạn B — Chuẩn hóa Database và Migration

### Vấn đề cần xử lý

Code đã có migration mới nhưng database live có thể chưa ở revision mới nhất. Ngoài ra, `KnowledgeDocument.index_status/index_error` cần migration chính thức; startup vẫn còn nguy cơ dựa vào `Base.metadata.create_all()` và auto-seed.

### Thiết kế đích

- `alembic upgrade head` là con đường duy nhất để thay đổi schema production.
- Startup chỉ kiểm tra dependency và schema revision; nếu thiếu migration quan trọng thì fail-fast với lỗi rõ ràng.
- Seed là lệnh quản trị idempotent, không phải side effect tự động của việc khởi động API.
- Mọi model phải được import vào Alembic metadata; `alembic check` không phát hiện diff ngoài ý muốn.

### Các bước thực hiện

1. Tạo backup database trước migration và kiểm tra có thể đọc được backup.
2. Bổ sung migration cho toàn bộ cột/index/constraint còn thiếu, đặc biệt:
   - `knowledge_documents.index_status`;
   - `knowledge_documents.index_error`;
   - các cột Evaluation mới;
   - khóa ngoại/cascade và unique constraint phục vụ idempotency.
3. Làm cho migration chịu được hai trường hợp:
   - database sạch từ revision gốc;
   - database hiện tại đã có một phần cột do `create_all()` hoặc code cũ tạo.
4. Thử upgrade trên bản sao database hiện tại và trên database rỗng.
5. Chuyển `create_all()` và startup seed ra khỏi production lifespan.
6. Thêm kiểm tra revision vào readiness hoặc startup; tuyệt đối không âm thầm tiếp tục khi schema thiếu.

### Không làm

- Không dùng raw `ALTER TABLE` trong `main.py`.
- Không sửa trực tiếp database rồi bỏ qua migration.
- Không đánh dấu tài liệu `ready` hàng loạt chỉ để RAG có dữ liệu.
- Không tạo một migration khổng lồ vừa đổi schema vừa seed toàn bộ nghiệp vụ mà không có dry-run.

### Acceptance criteria

- `alembic current` trùng `alembic heads`.
- `alembic check` sạch.
- Database mới khởi tạo từ migration có đủ bảng/cột/index.
- Bản sao database cũ upgrade thành công và giữ nguyên dữ liệu.
- API từ chối khởi động hoặc readiness đỏ khi schema revision không hợp lệ.

---

## 6. Giai đoạn C — Mã hóa Provider Secrets và chuyển đổi dữ liệu cũ

### Vấn đề cần xử lý

Code mới đã mã hóa key khi tạo/cập nhật, nhưng dữ liệu live cũ có thể vẫn là plaintext. Chỉ sửa code không tự bảo vệ các bản ghi đã tồn tại.

### Cách làm đúng

1. Chuẩn hóa ciphertext có prefix/version, ví dụ `enc:v1:<payload>`.
2. Viết lệnh migration dữ liệu một lần với ba chế độ:
   - `--dry-run`: chỉ đếm plaintext/encrypted/invalid;
   - `--apply`: mã hóa trong transaction theo batch;
   - `--verify`: bảo đảm không còn plaintext và runtime giải mã được.
3. Không ghi raw key ra console/log; chỉ in ID bản ghi và trạng thái.
4. Backup trước khi chạy; lưu số lượng trước/sau.
5. Thiết kế rotation: đọc được key version cũ trong cửa sổ chuyển đổi, mọi lần ghi mới dùng version mới.
6. Sau khi chuyển đổi, xóa đường “chấp nhận plaintext như ciphertext hợp lệ” khỏi production path hoặc chỉ giữ trong migration tool.

### Acceptance criteria

- 100% provider key và key-pool key có prefix mã hóa hợp lệ.
- API chỉ trả masked value.
- Log, exception và snapshot test không chứa secret.
- Provider ping/generation vẫn hoạt động sau restart.
- Production fail-fast khi thiếu `PROVIDER_ENCRYPTION_KEY`.

---

## 7. Giai đoạn D — Khôi phục tính đúng của Knowledge và RAG

### 7.1. Chuẩn hóa lifecycle

Dùng một state machine duy nhất, ví dụ:

```text
uploaded → extracting → review_pending → approved
approved → indexing → ready
indexing → index_failed → indexing
ready → archived
```

`approved` nghĩa là nội dung đã được con người chấp nhận; `ready` nghĩa là revision tương ứng đã có đầy đủ chỉ mục cần thiết. Hai trạng thái không được dùng thay thế nhau.

### 7.2. Payload Qdrant bắt buộc

Mỗi point phải có tối thiểu:

```text
tenant_id
workspace_id
collection_id
document_id
document_revision
chunk_id
document_status
is_retrievable
content_hash
embedding_model
payload_schema_version
```

Indexer phải fail nếu thiếu metadata, không tự gán `tenant_qnu`, `workspace_qnu` hoặc `completed` để “cho chạy được”.

### 7.3. Retrieval policy

- Dense, sparse và facts dùng cùng tenant/workspace/collection scope.
- Chỉ lấy `status=ready`, `is_retrievable=true`, đúng `document_revision`.
- Dùng positive allowlist, không chỉ loại `pending/archived` bằng blacklist.
- Cache key chứa tenant, workspace, collection, content revision, assistant, model và policy version.
- Khi approve/edit/archive/delete/reindex phải invalidate đúng partition.

### 7.4. Rebuild dữ liệu cũ

1. Chụp counts PostgreSQL/Qdrant trước khi chạy.
2. Xác định document nào đủ evidence để chuyển sang `approved/ready`; document chưa đối soát phải giữ `review_pending`.
3. Xóa/rebuild point cũ không đủ payload metadata thay vì vá mặc định mơ hồ.
4. Reindex theo document revision từ dữ liệu PostgreSQL canonical.
5. Chỉ đánh dấu `ready` sau khi Qdrant upsert thành công và reconciliation pass.

### 7.5. Reconciliation đúng nghĩa

Không chỉ so sánh tổng số point. Cần kiểm tra:

- document revision và content hash;
- tenant/workspace/collection;
- payload schema version;
- chunk IDs kỳ vọng so với point IDs thực tế;
- point thừa, thiếu và point thuộc document không còn retrievable;
- MinIO object còn tồn tại và checksum khớp.

### Test bắt buộc

- pending/review document không thể xuất hiện trong kết quả;
- tenant A không đọc point của tenant B;
- point thiếu metadata bị từ chối index hoặc retrieval;
- revision cũ không được trích dẫn sau khi tài liệu được sửa;
- Qdrant down chuyển degraded/no-answer trung thực;
- truy vấn không có evidence trả no-answer, không sinh citation giả.

### Acceptance criteria

- Mỗi collection production có ít nhất một tài liệu `ready` có provenance thật, hoặc được hiển thị rõ là chưa có dữ liệu.
- Số document/chunk/point đúng theo reconciliation report.
- Không còn legacy point thiếu tenant/workspace/revision.
- Golden dataset TM-08 chạy qua runtime thật, không lấy ground truth làm answer fallback.

---

## 8. Giai đoạn E — Trust Boundary, Dev Access Gate và HITL

Không cần xây RBAC/SSO phức tạp ở giai đoạn này. Trang nhập một mật khẩu vẫn phù hợp, nhưng phải tạo được principal tin cậy phía server.

### Principal tối thiểu

Cookie ký số `HttpOnly` nên đại diện cho:

```text
actor_id
display_name
role=admin
tenant_id=tenant_qnu
workspace_id=workspace_qnu
issued_at
expires_at
session_version
```

Backend lấy principal từ cookie/dependency và ghi đè mọi tenant/workspace/actor do client gửi lên.

### Approval record đúng

Một approval cần chứa:

```text
approval_id
execution_id
checkpoint_id
node_id
tool_name
payload_hash
requested_by
status
expires_at
decided_by
decided_at
decision_reason
```

Tool side effect chỉ được chạy khi service **consume atomically** một approval hợp lệ có payload hash khớp. `is_approved=true` hoặc `decided_by` trong body không phải bằng chứng phê duyệt.

### Public chat/widget

- Assistant phải thuộc allowlist public và đang published.
- Tenant/workspace cố định phía server, không nhận tùy ý từ request.
- Rate limit theo IP + assistant + session.
- Có giới hạn kích thước câu hỏi, attachment và số kết nối SSE.
- Không lộ system prompt, internal error hoặc provider response thô.

### Acceptance criteria

- Người chưa login không gọi được admin mutation.
- Sửa tenant/actor trong request không thay đổi trusted context.
- Approval hết hạn, sai payload hoặc đã dùng bị từ chối.
- Hai request resume đồng thời chỉ một request thực thi side effect.
- Audit log truy được ai yêu cầu, ai duyệt và payload nào đã chạy.

---

## 9. Giai đoạn F — Streaming thật và usage accounting đúng một lần

### Thiết kế đích

Adapter provider phát token/chunk ngay khi nhận được từ upstream. ModelOps chuyển tiếp `StreamEvent` typed; Workflow/Assistant không đợi toàn bộ answer rồi chia từ giả lập.

Ví dụ event contract:

```text
message_start
content_delta
citation
tool_call
approval_required
usage
message_end
error
```

### Quy tắc accounting

- Chỉ một tầng sở hữu việc ghi `LLMUsageLog` và tăng quota: khuyến nghị ModelOps.
- Assistant/Workflow chỉ gắn correlation metadata, không ghi usage lần hai.
- Ưu tiên token usage từ provider; nếu phải ước lượng thì đánh dấu `usage_source=estimated`.
- Dùng `request_id/provider_request_id` làm idempotency key.
- Quota nên reserve trước, reconcile sau; rollback reservation nếu upstream chưa nhận request.
- Client disconnect phải truyền cancellation xuống provider khi adapter hỗ trợ.

### Test bắt buộc

- Nhận delta đầu tiên trước khi completion kết thúc.
- Client cancel dừng generation và không ghi full usage giả.
- Retry/fallback không nhân đôi usage log.
- Primary fail rồi fallback thành công ghi đúng provider/model thực tế.
- Hai request đồng thời không vượt quota do race condition.

---

## 10. Giai đoạn G — Workflow durability và side-effect safety

### Bổ sung policy trên node

Mỗi node cần policy rõ:

```text
timeout_seconds
max_attempts
backoff_strategy
retryable_error_codes
idempotency_scope
on_failure
```

### Quy tắc retry

- Retry: timeout, 429, network tạm thời, 5xx được allowlist.
- Không retry: validation, policy violation, approval denied, prompt injection, dữ liệu thiếu bắt buộc.
- Tool tạo file/gửi thông báo/cập nhật dữ liệu phải có idempotency key.
- Checkpoint phải lưu workflow version, node input hash và state transition.
- Resume luôn chạy đúng immutable workflow version đã ghim.

### Acceptance criteria

- Node treo bị timeout có trace rõ.
- Workflow có thể cancel và không tiếp tục chạy node mới.
- Retry không tạo hai artifact hoặc hai lần thay đổi dữ liệu.
- Restart worker vẫn resume được checkpoint hợp lệ.
- Approval denied kết thúc theo nhánh nghiệp vụ, không bị xem là lỗi kỹ thuật để retry.

---

## 11. Giai đoạn H — Upload, Storage và async correctness

### Upload an toàn

- Giới hạn kích thước ở reverse proxy và Backend.
- Kiểm tra extension, MIME và magic bytes; không chỉ tin `Content-Type`.
- Chuẩn hóa filename bằng basename, Unicode NFC và safe slug.
- Stream/chunk upload; không `await file.read()` toàn bộ với file lớn.
- Tính checksum và lưu metadata provenance.

### Storage driver

- Kiểm tra path containment bằng `Path.resolve()` + `is_relative_to()`, không dùng so sánh chuỗi `startswith`.
- Local I/O dùng `anyio`/`aiofiles` hoặc thread pool có kiểm soát.
- S3 dùng async client hoặc bọc sync SDK trong thread pool.
- Không gọi network khi import module; tạo bucket/check dependency trong lifespan/readiness.
- Tên object không phụ thuộc trực tiếp filename người dùng.

### Test bắt buộc

- traversal như `../`, absolute path và prefix giả bị chặn;
- file vượt kích thước bị từ chối trước khi chiếm hết bộ nhớ;
- MIME giả bị phát hiện;
- S3 down không làm event loop treo;
- upload trùng retry không tạo orphan object.

---

## 12. Giai đoạn I — Refactor để giảm chi phí bảo trì

Refactor sau khi schema và runtime đã ổn định. Không tách file chỉ để giảm số dòng; ranh giới phải theo use case và transaction.

### Backend đề xuất

| Module hiện tại | Tách thành |
| :--- | :--- |
| `modelops/service.py` | `provider_catalog_service`, `credential_service`, `routing_service`, `generation_service`, `usage_service`, `quota_service` |
| `knowledge/service.py` | `collection_service`, `document_service`, `ingestion_service`, `indexing_service`, `reconciliation_service` |
| `assistants/service.py` | `assistant_lifecycle_service`, `assistant_runtime_service`, `assistant_version_service` |
| `workflows/service.py` | `definition_service`, `execution_service`, `checkpoint_service`, `approval_service` |

Router tiếp tục mỏng; service use case sở hữu transaction; repository/adapter không tự commit.

### Frontend đề xuất

- Page chỉ làm route orchestration, query/mutation wiring và layout.
- Tách server state vào query hooks theo domain.
- Tách form schema/mapping khỏi JSX.
- Tách sections/dialogs có state độc lập.
- Không đưa demo fixture vào production path.
- Một HTTP client chung xử lý credentials, timeout, cancellation, RFC 7807 và correlation ID.

### Ngưỡng thực dụng

- Service mới nên dưới khoảng 400 dòng; component/page mới dưới khoảng 250 dòng.
- Hàm nên dưới 40 dòng, trừ thuật toán cần giữ liền mạch và có test chuyên biệt.
- Không tạo abstraction chỉ có một implementation nếu chưa tạo được boundary có giá trị.

### Acceptance criteria

- Không đổi public API ngoài thay đổi đã version hóa.
- Test characterization được viết trước khi di chuyển logic rủi ro.
- Không tạo vòng import hoặc transaction commit phân tán.
- Mỗi module mới có trách nhiệm và owner rõ trong tên file.

---

## 13. Giai đoạn J — Testing và CI có giá trị

### Backend

- Sửa 47 warning, đặc biệt AsyncMock `Session.add` bị giả thành coroutine không được await.
- Dùng fixture session factory phản ánh đúng SQLAlchemy: `add()` sync, `execute/commit/refresh()` async.
- Đặt coverage tối thiểu thực dụng: 80% toàn dự án, 90% cho security, RAG filtering, approval và accounting.
- Thêm integration test với PostgreSQL/Qdrant/Redis/MinIO thật cho critical paths.
- Không mock tầng đang cần kiểm chứng; ví dụ test RAG integration không mock cả retriever.

### Frontend

- Thêm Vitest + React Testing Library cho route resolver, auth guard, API error mapping, model selectors, stream reducer và approval banner.
- Playwright live stack phải khởi động cả Backend và Frontend hoặc Docker Compose test profile.
- Dữ liệu E2E được seed vào database test riêng, không phụ thuộc máy cá nhân hoặc đường dẫn screenshot ngoài repo.
- Test phân biệt rõ empty, error, degraded, demo và live.

### Pipeline CI bắt buộc

```text
1. Secret/binary/mojibake scan
2. Backend ruff + migration check
3. Backend unit/integration tests + coverage
4. Frontend lint + typecheck + unit tests + build
5. Live E2E critical path
6. Container build + vulnerability scan
7. Migration smoke test trên database sạch và database nâng cấp
```

Nhánh chính chỉ nhận merge khi toàn bộ required checks đạt.

---

## 14. Giai đoạn K — Observability và Deployment

### Observability tối thiểu

- Prometheus metrics thật cho request rate/error/latency, provider latency/fallback, RAG retrieval/no-answer, workflow duration/failure, queue depth, token/cost/quota.
- Structured log có `correlation_id`, `tenant_id`, `assistant_id`, `workflow_execution_id`; không log secret/PII thô.
- Alert cho error rate, provider exhaustion, index backlog, reconciliation drift và database migration mismatch.
- Readiness kiểm tra dependency cần thiết; liveness chỉ kiểm tra process.

### Deployment

- Pin image bằng version hoặc digest; không dùng `latest`.
- Datastore không expose public port ở production.
- Container chạy non-root, read-only filesystem nếu phù hợp, secret qua environment/secret store.
- Có pre-deploy migration job, post-deploy smoke test và rollback procedure.
- Backup không chỉ tồn tại trên tài liệu: phải diễn tập restore và ghi RTO/RPO thực tế.

### Acceptance criteria

- Dashboard và alert hoạt động khi cố ý làm provider/Qdrant/DB lỗi trong staging.
- Restore được database và object storage sang môi trường cô lập.
- Rollback release không làm schema/data mất tương thích.
- Runbook đủ để một người khác vận hành mà không cần hỏi tác giả code.

---

## 15. Ma trận tăng điểm dự kiến

| Gói cải thiện | Mức tăng kỳ vọng | Bằng chứng bắt buộc |
| :--- | :---: | :--- |
| Schema/Alembic và dữ liệu live đồng nhất | +0,8 đến +1,0 | Upgrade sạch/cũ pass, schema head khớp |
| RAG lifecycle, payload, reindex, reconciliation | +0,6 đến +0,8 | Retrieval thật, tenant/revision tests, no-answer |
| Secret migration và trusted actor/HITL | +0,4 đến +0,6 | Không plaintext, approval atomic, access tests |
| Streaming và accounting exactly-once | +0,3 đến +0,5 | Delta thật, usage không trùng, cancellation |
| Workflow durability | +0,3 đến +0,4 | Timeout/retry/cancel/idempotency tests |
| Test/CI live | +0,4 đến +0,6 | Required checks, coverage, live E2E |
| Observability/deployment/restore | +0,4 đến +0,6 | Metrics, alert drill, restore drill |
| Refactor maintainability | +0,2 đến +0,4 | Complexity giảm, API/test không regression |

Các mức tăng không cộng cơ học. Ví dụ RAG chỉ được cộng đầy đủ nếu database schema, dữ liệu và tenant boundary cùng đúng.

---

## 16. Definition of Done cho mỗi Pull Request/phiên làm việc

### Trước khi code

- [ ] Đọc `PROJECT_CONTEXT.md` và quy trình liên quan.
- [ ] Xác nhận file ownership, session song song và trạng thái worktree.
- [ ] Viết rõ vấn đề, invariants, acceptance criteria và rollback.
- [ ] Nếu có schema/data change: chuẩn bị backup và dry-run.

### Trong khi code

- [ ] Không hardcode secret/dữ liệu nghiệp vụ/mock success.
- [ ] Có type hints/DTO, guard clauses và error contract RFC 7807.
- [ ] Không tự commit transaction ở nhiều tầng.
- [ ] Không nuốt exception; fallback phải có metric/log và nhãn degraded.
- [ ] Cập nhật quy trình nếu luồng/lifecycle thay đổi.

### Trước khi bàn giao

- [ ] Test happy path và ít nhất một failure path.
- [ ] Backend: Ruff + full Pytest pass, warning mới = 0.
- [ ] Frontend: Biome + TypeScript + build pass; unit/E2E phù hợp pass.
- [ ] Mojibake scan pass; không có file nhị phân/secret bị stage.
- [ ] Migration chạy được trên DB sạch và bản sao DB cũ nếu có schema change.
- [ ] Ghi nhật ký, snapshot memory và bằng chứng số liệu trước/sau.

---

## 17. Những cách “tăng điểm” sai cần tránh

- Tăng số test nhưng toàn bộ dependency bị mock và không có failure path.
- Tự đánh dấu document `ready` hoặc provider `active` để dashboard đẹp.
- Dùng fallback mock khi service thật down rồi gọi đó là resilience.
- Chỉ tách file lớn thành nhiều file nhưng transaction và trách nhiệm vẫn trộn.
- Thêm dashboard metrics từ dữ liệu gán cứng.
- Ghi “đã mã hóa” trong tài liệu trong khi database cũ vẫn plaintext.
- Chạy test xanh trên SQLite/mock nhưng không kiểm tra PostgreSQL/Qdrant live.
- Gộp nhiều migration, seed và reindex vào một bước không backup/rollback.
- Chấm TM-08 bằng ground truth được đưa ngược vào answer/context.

---

## 18. Ba phiên nên thực hiện tiếp theo

### Phiên 1 — Schema truth và migration gate

- Bổ sung migration `index_status/index_error` và các schema còn thiếu.
- Đưa database clone lên Alembic head.
- Tách production startup khỏi `create_all`/auto-seed.
- Thêm migration smoke test sạch/cũ.

**Điều kiện dừng:** schema chưa khớp thì chưa chạy seed/reindex.

### Phiên 2 — Data truth và RAG rebuild

- Audit lifecycle và provenance của từng document.
- Rebuild Qdrant points với payload schema bắt buộc.
- Nâng reconciliation từ count-only lên revision/hash/payload parity.
- Chạy golden queries và no-answer tests.

**Điều kiện dừng:** không đánh `ready` khi reconciliation chưa pass.

### Phiên 3 — Secret migration và trusted approval

- Chuyển provider/key-pool plaintext sang ciphertext bằng dry-run/apply/verify.
- Lấy actor/tenant/workspace từ signed session.
- Thay boolean approval bằng record + payload hash + consume atomic.
- Thêm rate limit cho login/public chat.

**Điều kiện dừng:** không xóa backup hoặc compatibility key cho tới khi provider smoke test pass.

---

## 19. Kết luận

QNU AI Platform không cần viết lại. Nền tảng hiện có đủ domain và chiều sâu để trở thành sản phẩm tốt. Phần cần làm tiếp là **biến những gì đã có thành hệ thống có thể tin cậy**: schema đúng, dữ liệu thật, RAG truy xuất đúng revision, secret được chuyển đổi, approval không thể giả mạo, streaming/accounting không bị nhân đôi, và mọi release đều có bằng chứng CI/restore.

Nếu triển khai đúng thứ tự trên, mức **8,5+/10** là mục tiêu hợp lý. Nếu chỉ tiếp tục thêm chức năng/UI mà chưa khóa schema, dữ liệu và trust boundary, điểm thực chất sẽ gần như không tăng dù codebase lớn hơn.
