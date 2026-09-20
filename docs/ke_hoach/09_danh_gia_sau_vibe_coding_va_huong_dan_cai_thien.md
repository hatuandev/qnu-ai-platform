# KẾ HOẠCH 09 — ĐÁNH GIÁ SAU VIBE CODING VÀ HƯỚNG DẪN CẢI THIỆN TIẾP

> Ngày đánh giá: 20/09/2026  
> Mốc mã nguồn: `f464622` (`main`, worktree sạch tại thời điểm review).  
> Phạm vi: kiểm chứng lại việc triển khai Kế hoạch 08 trên code, test, migration và dữ liệu live PostgreSQL/Qdrant.  
> Kết luận ngắn: **cải thiện rõ rệt nhưng chưa đạt Production Candidate; mức hợp lý hiện tại khoảng 7,1/10**.

---

## 1. Kết luận điều hành

Vibe coding theo tài liệu 08 đã tạo ra nhiều cải thiện có giá trị thật:

- Alembic đã trở thành nguồn quản lý schema chính; database live đang ở đúng head và `alembic check` sạch.
- Provider secrets live đã được chuyển đổi: 4 primary keys và 5 pool keys đều ở dạng `enc:v1`, không còn plaintext.
- Backend đã được tách facade cho Knowledge, Assistants và ModelOps; storage I/O đã dùng thread offload thay vì chặn event loop.
- Trust boundary đã có signed session claims, approval record có `payload_hash`, expiry và trạng thái consumed.
- RAG code đã có payload schema v1, tenant/workspace filters, cache partition và CLI reconciliation.
- Quality gate hiện tại xanh: Ruff, 280 Pytest, Biome, TypeScript và Vite build đều đạt.

Tuy nhiên, quá trình review bằng dữ liệu live cho thấy nhiều mục mới chỉ hoàn thành ở **mức code/unit test**, chưa hoàn thành ở **mức runtime/data**. Đáng chú ý nhất:

1. Công cụ reconciliation đang báo sai số chunk do dùng sai SQLAlchemy result API.
2. Dữ liệu live chưa được migrate sang lifecycle mới; bốn kho chính vẫn ở `completed/processed + index_status=pending`.
3. Worker reindex vẫn gửi payload cũ, không đủ 11 trường bắt buộc và sẽ bị indexer mới từ chối.
4. Các LLM adapter vẫn trả câu trả lời giả khi thiếu key hoặc dependency lỗi.
5. HITL được gọi là “atomic consumption” nhưng chưa có row lock/CAS; side effect vẫn có thể chạy hai lần khi có request đồng thời.
6. Assistant và provider adapters vẫn giả lập streaming bằng cách chờ toàn bộ kết quả rồi chia từ; usage có nguy cơ ghi hai lần.
7. Test suite xanh một phần nhờ `filterwarnings` che cả warning AsyncMock; chưa có Frontend unit tests, CI và E2E live Backend.

Vì vậy, trạng thái chính xác nên là:

> **Engineering Beta mạnh, đã có nền Production Candidate nhưng chưa vượt Release Gate.**

---

## 2. Bằng chứng kiểm chứng trực tiếp

### 2.1. Quality gate

| Kiểm tra | Kết quả review lại |
| :--- | :--- |
| Git worktree | Sạch |
| Backend Ruff | 0 lỗi |
| Backend Pytest | **280 passed trong 53,30 giây** |
| Frontend Biome | 164 tệp, 0 lỗi |
| Frontend TypeScript | 0 lỗi |
| Frontend production build | Thành công, 2.575 modules, 7,48 giây |
| Alembic head/current | Cùng `20260919_approval_payload_hash` |
| Alembic check | Không có schema diff |
| Database check | 30 bảng, PASSED |
| Provider secret audit | 0 plaintext, 0 corrupted |

### 2.2. Trạng thái dữ liệu Knowledge live

PostgreSQL thật có năm tài liệu và đủ chunks:

| Collection | Document status | Index status | Chunks | Facts |
| :--- | :--- | :--- | ---: | ---: |
| `col_admissions` | `completed` | `pending` | 7 | 8 |
| `col_drafting` | `processed` | `pending` | 6 | 7 |
| `col_library` | `completed` | `pending` | 6 | 7 |
| `col_question_bank` | `approved` | `index_failed` | 16 | 0 |
| `col_regulations` | `completed` | `pending` | 6 | 7 |

Theo filter RAG mới, hiện chỉ có 16 chunks của `col_question_bank` đủ điều kiện sparse vì status `approved`; **retrievable facts = 0**. Bốn kho còn lại bị loại khỏi sparse/facts vì vẫn dùng lifecycle cũ. Các Qdrant points cũ thiếu payload v1 nên không vượt qua dense filters mới.

### 2.3. Reconciliation live

CLI báo 75 discrepancies và `DB Chunks: 0` cho bốn collection dù truy vấn PostgreSQL trực tiếp cho thấy có đủ chunks. Nguyên nhân nằm trong `reconciliation_service.py`:

- chạy `select(KnowledgeChunk)`;
- gọi `chunk_exec.scalar()` trước, làm Result bị tiêu thụ một phần;
- sau đó mới gọi `chunk_exec.scalars().all()`;
- test dùng `MagicMock`, nên không mô phỏng hành vi Result thật và không phát hiện lỗi.

Hệ quả: orphan detection có thể báo sai. Không được chạy `knowledge reconcile --fix` cho tới khi sửa và kiểm thử bằng PostgreSQL thật.

---

## 3. Scorecard sau cải thiện

| Nhóm | Điểm trước | Điểm hiện tại | Nhận xét |
| :--- | :---: | :---: | :--- |
| Kiến trúc tổng thể | 7,0 | 7,6 | Facade rõ hơn, nhưng logic chỉ chuyển sang các sub-service 1.300–1.600 dòng |
| Backend API | 7,5 | 7,9 | Migration, async storage, schema checks tốt hơn; transaction boundary còn phân tán |
| Frontend | 7,5 | 7,6 | Build/type/lint tốt; chưa có unit test và nhiều page vẫn 500–1.000 dòng |
| Database | 5,0 | 8,3 | Alembic head/check tốt; startup chưa so revision với head và data migration còn thiếu |
| Knowledge/OCR | 7,5 | 7,4 | Pipeline mạnh; upload Knowledge còn đọc toàn bộ file, filename/MIME chưa siết |
| RAG | 6,5 | 5,8 | Code contract tốt hơn nhưng dữ liệu live gần như chưa retrievable đúng chuẩn |
| Assistant/Workflow | 7,0 | 6,9 | Versioning/HITL tốt hơn; approval race, client actor và durability còn hở |
| ModelOps | 5,5 | 6,0 | Secret tốt hơn; fake-success, giả streaming và accounting trùng vẫn là blocker |
| Evaluation | 5,5 | 7,2 | Có item drill-down và LLM judge; chất lượng vẫn phụ thuộc runtime RAG/LLM chưa sạch |
| Security | 4,0 | 6,9 | Secrets encrypted, session signed; thiếu rate limit, trusted decision actor và atomic approval |
| Testing | 6,5 | 7,0 | 280 tests pass; warning bị suppress, thiếu live integration/FE unit/CI |
| Observability | 5,0 | 5,8 | Có `/metrics`, nhưng registry in-memory, thiếu domain metrics và multi-worker correctness |
| Deployment | 4,5 | 5,5 | Có backend compose profile; còn `qdrant:latest`, chưa CI/restore drill/app production stack |

**Điểm tổng hợp đề xuất: 7,1/10.**

Điểm tăng khoảng 0,6 là hợp lý vì Database và secret management cải thiện thật. Chưa thể cộng đủ điểm RAG, Security, ModelOps và Production vì runtime evidence chưa đạt.

---

## 4. Các phát hiện cần xử lý

## P0-01 — Reconciliation đọc sai SQLAlchemy Result

**Vị trí:** `backend/app/modules/knowledge/services/reconciliation_service.py`, vùng xử lý `chunk_exec`.

### Vấn đề

`select(KnowledgeChunk)` trả entity rows, nhưng code thử lấy `scalar()` như một count rồi mới lấy `scalars().all()`. Trên PostgreSQL thật, lần đọc đầu tiêu thụ Result và làm danh sách chunks sai. Unit test mock không tái hiện điều này.

### Rủi ro

- Báo `DB Chunks: 0` dù dữ liệu tồn tại.
- Đánh dấu mọi Qdrant point là orphan sai.
- Nếu sau này `--fix` có delete orphan, có thể xóa vector hợp lệ.

### Cách sửa

```python
chunk_result = await db.execute(
    select(KnowledgeChunk).where(KnowledgeChunk.collection_id == collection_id)
)
all_chunks = list(chunk_result.scalars().all())
db_chunks_count = len(all_chunks)
```

Nếu chỉ cần count, chạy query riêng `select(func.count(KnowledgeChunk.id))`; không đọc cùng Result hai lần.

### Test bắt buộc

- Integration test bằng PostgreSQL thật với 2 documents, 3 chunks.
- Assert exact chunk IDs và orphan IDs.
- Test Result chỉ được tiêu thụ một lần.
- CLI phải trả exit code khác 0 khi có discrepancies thật; không chỉ log warning rồi exit 0.

---

## P0-02 — Lifecycle mới chưa được áp dụng vào dữ liệu live

### Vấn đề

Seeder chỉ tạo bản ghi mới rồi return sớm khi document đã tồn tại. Vì thế việc đổi manifest thành `status=ready/index_status=indexed` không cập nhật dữ liệu cũ. Live DB vẫn dùng `completed`, `processed`, `pending`.

### Rủi ro

- Dense retrieval không thấy point cũ do thiếu tenant/workspace/status/payload version.
- Sparse/facts loại bốn kho chính do status không thuộc allowlist.
- Dashboard có dữ liệu nhưng Assistant nhận `insufficient_context`.
- Evaluation có thể phản ánh sai chất lượng vì runtime không có evidence.

### Cách sửa đúng

1. Backup PostgreSQL và export Qdrant snapshot.
2. Viết CLI migration riêng, không ép seeder ghi đè:
   - `knowledge lifecycle-audit`;
   - `knowledge migrate-lifecycle --dry-run`;
   - `knowledge migrate-lifecycle --apply`;
   - `knowledge migrate-lifecycle --verify`.
3. Chỉ map `completed/processed → approved` khi có provenance và source file tồn tại.
4. Reindex từng document bằng payload v1.
5. Chỉ chuyển `ready/indexed` sau khi exact parity pass.
6. Không mass-approve tài liệu chưa được cán bộ đối soát.

### Acceptance criteria

- Mỗi collection có document `ready/indexed` hoặc trạng thái `review_pending` trung thực.
- Dense, sparse và facts trả cùng scope/revision.
- Reconciliation có 0 discrepancy thật.
- Golden query cho năm trợ lý trả evidence đúng collection.

---

## P0-03 — Background reindex worker không tương thích payload v1

**Vị trí:** `backend/app/workers/tasks.py`, `task_reindex_collection()`.

### Vấn đề

Worker chỉ gửi `id`, `point_id`, `content`, `document_id`, `section`, `page_number`, `metadata`. Indexer mới bắt buộc 11 trường và sẽ trả `INVALID_POINT_PAYLOAD`.

### Cách sửa

- Query join `KnowledgeChunk → KnowledgeDocument → KnowledgeCollection`.
- Chỉ lấy document `ready` hoặc thực hiện state transition rõ `approved → indexing`.
- Gắn đủ tenant, workspace, document revision, content hash, embedding model, schema version.
- Không reindex toàn bộ collection bằng chunks không kiểm tra lifecycle.
- Update `document.index_status` theo từng document, không chỉ update JobRecord chung.
- Invalidate cache sau khi toàn bộ document thành công.

### Test bắt buộc

- Worker integration test với PostgreSQL + fake Qdrant capture payload.
- Document pending/archived không được index.
- Một document lỗi không làm các document khác bị báo success giả.
- Cancel giữa chừng phải giữ trạng thái nhất quán.

---

## P0-04 — ModelOps vẫn fake-success trong LiveMode

### Bằng chứng

- `OpenAIAdapter`, `GeminiAdapter`, `CloudflareAdapter`, `MistralAdapter`: thiếu/dummy key thì dựng câu trả lời thành công giả.
- `LocalVLLMAdapter`: bắt mọi exception và trả câu “Phản hồi từ máy chủ AI nội bộ” dù server đang chết.

### Rủi ro

Đây là vi phạm trực tiếp Truthful Runtime và Zero Hallucination. Circuit breaker, fallback, cost và Evaluation đều có thể ghi một lượt thành công không tồn tại.

### Cách sửa

- Chỉ cho mock adapter trong `ENVIRONMENT=test` hoặc DemoMode explicit.
- Provider thật thiếu credential phải trả `PROVIDER_CREDENTIAL_MISSING`.
- Local server lỗi phải raise typed adapter error để circuit breaker chuyển provider.
- Readiness/publish gate phải kiểm tra provider ping thật, không chỉ `is_active` trong DB.
- Tách `MockLLMAdapter` thành module test, không đặt mock branch trong adapter production.

### Acceptance criteria

- Tắt provider: request fail/fallback thật, không có câu trả lời dựng sẵn.
- Usage log không được ghi `success` cho mock/offline path.
- Evaluation không thể pass khi tất cả provider đều unavailable.

---

## P0-05 — HITL chưa atomic thật và actor quyết định vẫn do client khai báo

### Bằng chứng

- ToolService đọc approval bằng `select(...)` không `FOR UPDATE` hoặc compare-and-set.
- Tool side effect chạy trước khi approval được chuyển `consumed` và commit.
- Hai request đồng thời có thể cùng đọc `approved`, cùng chạy tool rồi cùng ghi `consumed`.
- Không đối chiếu `approval.tool_name` với `request.tool_name`.
- API decision vẫn nhận `decided_by` từ request body; actor signed cookie không được dùng làm nguồn quyết định.

### Cách sửa

1. Router inject `AuthActor`; xóa `decided_by` khỏi request DTO.
2. Khi quyết định, ghi `actor.actor_id`/`display_name` từ trusted context.
3. Khi execute tool, claim approval atomically:
   - `UPDATE ... SET status='executing' WHERE id=:id AND status='approved' AND expires_at>now() RETURNING ...`; hoặc
   - transaction + `SELECT ... FOR UPDATE SKIP LOCKED`.
4. Kiểm tra tool name, execution ID, checkpoint ID, tenant và payload hash.
5. Side effect ngoài DB dùng idempotency key `approval_id` tại adapter/tool hoặc outbox.
6. Success: `executing → consumed`; transient failure: policy rõ `executing → approved/retryable`; permanent failure: `failed`.

### Test bắt buộc

- Hai coroutine cùng dùng một approval: chỉ một side effect xảy ra.
- Approval của tool A không dùng cho tool B.
- Approval tenant A không dùng cho tenant B.
- Client giả `decided_by` không ảnh hưởng audit actor.

---

## P1-01 — Streaming vẫn là streaming giả và usage bị ghi trùng

### Bằng chứng

- Assistant `chat_stream()` đợi `workflow_service.execute()` hoàn tất, sau đó `answer.split(" ")` và `sleep(0.012)`.
- Provider adapters gọi `generate()` rồi chia words trong `stream()`.
- ModelOps đã ghi provider usage/quota; Assistant lại ghi một bản `qnu_workflow` với token ước lượng.

### Cách sửa

- Adapter dùng SSE/chunked stream thật của upstream.
- ModelOps phát typed events và final usage event.
- Workflow engine hỗ trợ async event sink/iterator thay vì chỉ response cuối.
- Assistant chỉ forward event, không tự tạo token.
- Chỉ ModelOps sở hữu usage accounting; Assistant ghi trace reference, không ghi token/cost lần hai.
- Thêm `provider_request_id` hoặc `usage_id` unique để chống retry ghi trùng.
- Hỗ trợ cancellation khi client ngắt kết nối.

### Acceptance criteria

- Time-to-first-token xảy ra trước completion.
- Không có `split()`/sleep mô phỏng trong production path.
- Một request chỉ tạo một usage log canonical.
- Fallback ghi đúng provider/model thực tế.

---

## P1-02 — Public chat còn tin `tenant_id` từ request và chưa rate limit

### Vấn đề

`AssistantChatRequest` vẫn có `tenant_id`; chat router là public và chuyển thẳng giá trị này vào workflow. `RATE_LIMIT_PER_MINUTE` mới chỉ là config, chưa có middleware thực thi.

### Cách sửa

- Public widget dùng server-side tenant/workspace cố định theo assistant/channel token.
- Admin playground lấy scope từ signed actor.
- Không nhận tenant tùy ý trong public body.
- Chỉ cho chat với assistant `published`, active và channel-enabled.
- Thêm Redis sliding-window/token-bucket theo IP + assistant + session.
- Giới hạn attachment count/size và concurrent SSE connections.

---

## P1-03 — RAG allowlist vẫn cho phép `approved`

Lifecycle mới định nghĩa `approved` là đã được người kiểm duyệt nhưng chưa chắc index hoàn chỉnh; `ready` mới là retrievable. Tuy nhiên dense, sparse và facts đều cho `approved`.

### Cách sửa

- Production retrieval chỉ lấy `status='ready'` và `index_status='indexed'`.
- Nếu muốn sparse degraded trước dense, phải dùng policy explicit như `allow_approved_sparse_degraded`, mặc định false và có nhãn degraded.
- Test phải khẳng định `approved/index_failed` không được trả về trong chế độ chuẩn.

---

## P1-04 — Upload và Local Storage chưa đủ an toàn

### Bằng chứng

- Knowledge upload, preview và Excel import vẫn `await file.read()` không giới hạn.
- OCR có giới hạn 25 MB nhưng Knowledge chưa dùng chung helper.
- Chưa xác thực magic bytes/MIME thống nhất.
- `LocalStorageDriver._resolve()` vẫn dùng `str(target).startswith(str(base_path))`; đường sibling có cùng prefix có thể lọt kiểm tra.

### Cách sửa

- Tạo `ValidatedUpload` dùng chung: max size, extension allowlist, MIME/magic, NFC filename, basename/safe slug.
- Đọc theo chunk hoặc `file.read(max+1)` với limit.
- Dùng `target.is_relative_to(base_path)` sau `resolve()`.
- Object key dùng UUID/hash, filename chỉ là metadata.
- Thêm path traversal tests cho sibling-prefix, absolute path, `..`, mixed separators.

---

## P1-05 — Refactor mới giảm facade nhưng chưa giảm độ phức tạp thật

Các file lớn hiện tại:

| Tệp | Dòng xấp xỉ |
| :--- | ---: |
| `modelops/services/provider_service.py` | 1.612 |
| `knowledge/services/ingestion_service.py` | 1.376 |
| `ocr/layout_detector.py` | 1.149 |
| `workflows/service.py` | 1.055 |
| `evaluation/dataset_seeder.py` | 958 |
| `knowledge/seeder.py` | 917 |

Frontend vẫn có `verification-data.ts` 1.395 dòng, `modelops-page.tsx` 1.031, `assistant-create-page.tsx` 866 và nhiều page 500–750 dòng.

### Cách cải thiện

- Provider: tách credential/key pool, health probing, CRUD, preset catalog và runtime sync.
- Ingestion: tách upload/storage, extraction, studio view, approval/indexing, lifecycle/jobs.
- Workflow: tách definition/version, execution/checkpoint, approval.
- Frontend: page orchestrator + domain hooks + sections/dialogs + form mapper.
- Di chuyển demo fixture ra lazy demo module hoặc test fixture, không nằm trong production import graph.

Refactor phải kèm characterization tests; không chỉ di chuyển nguyên khối sang file mới.

---

## P1-06 — Test xanh nhưng còn khoảng mù quan trọng

### Vấn đề

- `filterwarnings` đang ignore cả `AsyncMockMixin... was never awaited`; “0 warnings” chưa hoàn toàn là kết quả sửa tận gốc.
- Reconciliation unit test dùng MagicMock nên bỏ lọt lỗi Result consumption.
- Không có test worker reindex với payload v1.
- Không có concurrency test HITL thật.
- Frontend chưa có Vitest/React Testing Library.
- Playwright chỉ tự bật Vite, không bật Backend.
- Không có `.github/workflows` hoặc CI tương đương trong repository.

### Cách sửa

- Xóa ignore AsyncMock sau khi fixture đúng.
- Dùng Testcontainers/Docker services cho PostgreSQL, Qdrant, Redis, MinIO integration tests.
- Thêm Frontend unit tests cho auth guard, stream reducer, API errors, model selector và approval UX.
- Playwright test profile phải bật Backend + seeded test DB.
- CI bắt buộc chạy migration smoke test trên DB sạch và snapshot cũ.

---

## P1-07 — Observability mới ở mức single-process baseline

`MetricsRegistry` là bộ đếm in-memory tự viết. Nó mất dữ liệu khi restart, sai tổng khi chạy nhiều worker và chưa có histogram, provider/RAG/workflow/quota metrics.

### Cách sửa

- Dùng `prometheus-client` hoặc OpenTelemetry metrics.
- Histogram latency theo route template, không theo raw ID path.
- Metrics bắt buộc: provider fallback/error/latency, RAG result/no-answer, indexing backlog/failure, workflow node duration/retry, approval age, token/cost/quota.
- Bảo vệ `/metrics` theo network/internal key nếu deployment yêu cầu.
- Thêm alert rules và staging failure drill.

---

## P2 — Deployment và tài liệu trạng thái

- `qdrant/qdrant:latest` còn trong môi trường đang chạy; cần pin version/digest.
- Chưa có CI/CD bắt buộc, restore drill và production app compose hoàn chỉnh được kiểm chứng.
- `PROJECT_CONTEXT.md` đang mô tả Giai đoạn D hoàn tất 100%, nhưng live data/reconciliation không chứng minh điều đó. Cần phân biệt “code complete” và “runtime verified”.
- Startup schema readiness mới kiểm tra core tables, chưa so revision hiện tại với expected head.

---

## 5. Lộ trình cải thiện đề xuất

## Đợt 0 — Đóng băng auto-fix và sửa audit truth (0,5–1 ngày)

1. Tạm không dùng `knowledge reconcile --fix` trên dữ liệu live.
2. Sửa Result consumption.
3. Thêm PostgreSQL integration test.
4. Làm CLI exit non-zero khi có discrepancy/error.
5. In đầy đủ `point_id/document_id/chunk_id/details`, không log `None` như hiện tại.

**Gate:** report counts phải khớp SQL trực tiếp.

## Đợt 1 — Migrate lifecycle và rebuild RAG live (1–2 ngày)

1. Backup PostgreSQL/Qdrant.
2. Audit provenance/storage của 5 documents.
3. Migrate status có dry-run/apply/verify.
4. Sửa worker payload v1.
5. Reindex từng document, kiểm tra exact parity.
6. Chuyển retrieval mặc định sang ready-only.
7. Chạy golden queries của năm assistants.

**Gate:** 0 discrepancy, 5 collection có evidence thật hoặc empty state trung thực.

## Đợt 2 — Truthful ModelOps, streaming và accounting (2–4 ngày)

1. Xóa mock branches khỏi production adapters.
2. Tạo MockAdapter test-only.
3. Triển khai upstream streaming thật cho provider ưu tiên.
4. Xây typed stream event contract xuyên ModelOps → Workflow → Assistant → Frontend.
5. Xóa usage logging khỏi Assistant; thêm idempotency key tại ModelOps.
6. Test cancel/fallback/quota concurrency.

**Gate:** provider down không fake success; one request = one usage record.

## Đợt 3 — HITL và trusted public boundary (2–3 ngày)

1. Actor từ dependency, bỏ `decided_by` client.
2. Atomic claim approval + idempotent side effect.
3. Bind approval với tool/execution/checkpoint/tenant.
4. Public channel token quyết định assistant/scope.
5. Redis rate limiter cho login/chat.

**Gate:** concurrency/replay/cross-tenant tests pass.

## Đợt 4 — Upload/storage hardening (1–2 ngày)

1. Shared upload validator.
2. File size/MIME/magic/filename/path containment.
3. Stream uploads và checksum.
4. S3/Local failure tests.

**Gate:** traversal và oversized uploads bị chặn trước xử lý OCR.

## Đợt 5 — Test, CI và maintainability (3–5 ngày)

1. Bỏ warning suppression nội bộ.
2. Frontend unit test baseline.
3. Backend live integration suite.
4. Playwright full stack.
5. CI required checks.
6. Tách tiếp Provider/Ingestion/Workflow services theo use case.

**Gate:** PR không thể merge khi migration, live RAG, FE unit hoặc E2E critical path đỏ.

## Đợt 6 — Observability và release drill (2–3 ngày)

1. Prometheus/OpenTelemetry chuẩn.
2. Domain dashboards và alerts.
3. Pin images, production network/secrets.
4. Backup/restore và rollback drill.

**Gate:** staging failure drill + restore report đạt RTO/RPO đã định.

---

## 6. Definition of Done để đạt 8,5+/10

- [ ] `alembic current == heads`, `alembic check` sạch trên CI.
- [ ] Migration sạch và migration từ snapshot cũ đều pass.
- [ ] Provider secrets 0 plaintext và rotation test pass.
- [ ] Reconciliation counts đúng PostgreSQL thật, 0 false orphan.
- [ ] Năm collection có lifecycle canonical và exact DB–Qdrant parity.
- [ ] Retrieval production chỉ dùng document `ready/indexed` đúng revision.
- [ ] Không còn fake-success trong LLM/OCR/Tool/RAG production path.
- [ ] Streaming có time-to-first-token thật và cancellation.
- [ ] Usage/quota/cost exactly-once.
- [ ] Approval atomic, actor trusted, bind tool/execution/tenant và chống replay.
- [ ] Public chat rate limit + assistant/channel allowlist.
- [ ] Knowledge uploads có size/MIME/magic/path controls.
- [ ] Backend unit + integration, Frontend unit và Playwright full-stack cùng chạy trong CI.
- [ ] Không suppress warning do code/test của dự án tạo ra.
- [ ] Metrics/alerts/domain dashboards hoạt động multi-worker.
- [ ] Backup restore và release rollback được diễn tập.
- [ ] Tài liệu memory/quy trình khớp runtime live.

---

## 7. Thứ tự sửa ngay được khuyến nghị

Ba việc nên làm trước mọi tính năng mới:

1. **Sửa reconciliation + integration test PostgreSQL thật.** Đây là công cụ quyết định có được phép sửa dữ liệu hay không.
2. **Sửa worker payload v1 và migrate/reindex năm kho.** Đây là điều kiện để Assistant/RAG có dữ liệu thật.
3. **Loại fake-success ModelOps.** Nếu không, mọi evaluation, cost và readiness phía sau đều không đáng tin.

Sau ba việc này mới chuyển sang atomic HITL và streaming/accounting. Không nên tiếp tục mở rộng UI hay thêm chatbot mới trước khi các gate trên đạt.

---

## 8. Kết luận cuối

Việc triển khai theo tài liệu 08 **đã cải thiện dự án**, đặc biệt ở schema migration, secret encryption, async storage và cấu trúc facade. Đây là tiến bộ thật, không phải chỉ thay đổi bề mặt.

Điểm còn thiếu nằm ở khoảng cách giữa unit test và dữ liệu/runtime thật. Hiện tượng reconciliation báo 0 chunks trong khi PostgreSQL có dữ liệu là ví dụ rõ nhất: code có test nhưng test chưa đại diện cho dependency thật. Tương tự, HITL có trạng thái consumed nhưng chưa atomic, provider có adapter nhưng vẫn fake-success, streaming có SSE nhưng token chỉ được chia sau khi workflow kết thúc.

Nếu hoàn thành Đợt 0–3 và chứng minh bằng live integration tests, dự án có thể lên khoảng **8,0–8,3/10**. Khi bổ sung CI, full-stack E2E, observability và restore drill, mục tiêu **8,5+/10 Production Candidate** mới có đủ cơ sở.
