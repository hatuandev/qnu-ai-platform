# KẾ HOẠCH 07 — CẢI THIỆN TOÀN DIỆN QNU AI PLATFORM SAU CODE REVIEW

> Ngày lập: 19/09/2026  
> Mốc đánh giá: trạng thái dự án sau phiên #121; kết quả Frontend được kiểm tra lại sau khi session modular hóa OCR hoàn tất.  
> Phạm vi: Backend, Frontend, Database, Knowledge/OCR, RAG, Assistant, Workflow, ModelOps, Evaluation, Security, Testing, Observability và Deployment.  
> Mục tiêu: đưa dự án từ **Internal Beta mạnh** đến **Production Candidate có thể kiểm chứng**, không làm mất kiến trúc domain hiện tại và không đánh đổi chất lượng để tăng tốc.

---

## 1. Kết luận điều hành

QNU AI Platform đã vượt xa một prototype thông thường. Dự án hiện có:

- 13 domain Backend chính, phần lớn tuân theo cấu trúc `models/schemas/service/router`;
- khoảng 149 tệp Python Backend với 24.644 dòng;
- khoảng 159 tệp TypeScript/TSX Frontend với 32.470 dòng;
- 26 tệp test Backend với 5.778 dòng và 9 Playwright E2E specs;
- Knowledge/OCR, Hybrid RAG, ModelOps, Assistant lifecycle, Workflow DAG, Human-in-the-loop, Conversations/Handoff và Evaluation đều đã có code thật;
- Workflow ownership, immutable publish version và rollback đã được cải thiện đáng kể;
- Frontend đã có design system riêng, typed API services và nhiều trang được modular hóa.

Điểm yếu lớn nhất hiện nay **không còn là thiếu chức năng**. Khoảng cách tới production nằm ở sáu nhóm:

1. Secret, Dev Access Gate và tenant/workspace boundary chưa đủ an toàn.
2. LiveMode vẫn còn các đường fake-success/mock fallback có thể làm người dùng tin dữ liệu giả là thật.
3. Database schema đang phụ thuộc vào `create_all`, raw `ALTER TABLE` và auto-seed khi khởi động.
4. RAG/Tool/Workflow còn một số đường fail-open, filter lifecycle chưa hoàn toàn thống nhất.
5. Test nhiều nhưng chưa tạo được quality gate đáng tin cậy do warning, mock và E2E offline.
6. Một số service/page vẫn quá lớn, làm tốc độ phát triển tăng nhưng rủi ro regression cũng tăng theo.

### Đánh giá cập nhật

| Nhóm | Điểm tham khảo | Nhận xét |
| :--- | :---: | :--- |
| Kiến trúc tổng thể | 7.0/10 | Domain rõ, nhưng startup và service layer còn ôm nhiều trách nhiệm |
| Backend API | 7.5/10 | FastAPI async, DTO, Problem Details, 239 tests; transaction boundary còn phân tán |
| Frontend | 7.5/10 | Design system và feature depth tốt; một số page lớn, routing/state chưa hoàn chỉnh |
| Knowledge/OCR | 7.5/10 | Miền trưởng thành nhất; cần bỏ progress giả và củng cố cross-store integrity |
| RAG | 6.5/10 | Có FTS + Dense + RRF + rerank + threshold; lifecycle/workspace/mock embedding còn hở |
| Assistant/Workflow | 7.0/10 | Versioning/ownership tiến bộ mạnh; runtime policy, retry/cancel/approval còn thiếu |
| ModelOps | 5.5/10 | Feature rộng nhưng service rất lớn, mock key/raw secret và state in-memory còn tồn tại |
| Evaluation | 5.5/10 | Đã chạy Assistant/RAG thật; metric vẫn là heuristic nhưng mang tên Ragas/TM-08 |
| Security | 4.0/10 | Admin routes đã có gate, nhưng hardcoded secrets, plaintext key và rate limit còn thiếu |
| Testing | 6.5/10 | 239 test pass; 47 warnings, không coverage gate, Frontend chưa có unit test |
| Observability | 5.0/10 | Correlation/log/timing tốt; Prometheus/rate limit mới ở mức cấu hình |
| Production deployment | 4.5/10 | Có tài liệu và infra local; migration, image pinning, CI/CD và restore drill chưa đủ |

**Điểm tổng thể đề xuất: 6.5/10 — Internal Beta mạnh.**

Dự án có nền tốt để tiến lên production, nhưng không nên tiếp tục mở rộng thêm nhiều chức năng lớn trước khi xử lý các hạng mục P0 trong kế hoạch này.

---

## 2. Bằng chứng code review và trạng thái quality gate

### 2.1. Kết quả kiểm tra trực tiếp

| Kiểm tra | Kết quả tại thời điểm review |
| :--- | :--- |
| Backend Ruff | Đạt, 0 lỗi |
| Backend Pytest | **239 passed**, 47 warnings, khoảng 63 giây |
| Frontend TypeScript | Đạt, 0 lỗi |
| Frontend Biome | Đạt, 162 tệp, 0 lỗi |
| Frontend Build | Đạt, 2.573 modules, hoàn thành trong 6,62 giây |
| CI pipeline | Chưa có workflow CI trong repository |
| Frontend unit/component tests | Chưa có; hiện chỉ có Playwright E2E |

Trong khi review, Frontend từng tạm thời đỏ do session OCR đang ghi file đồng thời. Sau khi phiên #121 hoàn tất, toàn bộ lint/typecheck/build đã xanh trở lại. Tình huống này vẫn cho thấy dự án cần merge gate/CI để trạng thái đỏ tạm thời không bị đưa vào nhánh dùng chung mà không được phát hiện sớm.

### 2.2. Quy mô tệp lớn còn lại

#### Backend

| Tệp | Dòng xấp xỉ | Nhận xét |
| :--- | ---: | :--- |
| `modelops/service.py` | 2.295 | Provider CRUD, key pool, health, generation, quota, usage và defaults trộn chung |
| `knowledge/service.py` | 1.926 | Ingestion, storage, parse, index, lifecycle, facts và jobs cùng service |
| `ocr/layout_detector.py` | 1.149 | Thuật toán lớn, cần chia stage/strategy và benchmark riêng |
| `assistants/service.py` | 1.143 | CRUD, chat, SSE, usage, bundle, version, clone, generate spec |
| `workflows/service.py` | 1.019 | Definition, draft, publish, execute, checkpoint, approval và ownership |

#### Frontend

| Tệp | Dòng xấp xỉ | Nhận xét |
| :--- | ---: | :--- |
| `services/verification-data.ts` | 1.395 | Fixture/demo lớn nằm trong production bundle |
| `pages/modelops-page.tsx` | 1.031 | Nhiều phần ModelOps trong một route |
| `pages/scan-studio-page.tsx` | khoảng 260 sau phiên #121 | Đã được modular hóa; tiếp tục giữ page ở vai trò orchestrator |
| `pages/assistant-create-page.tsx` | 866 | Wizard, API state, mapping và validation trộn nhau |
| `pages/dag-canvas-page.tsx` | 753 | Canvas, version, test runner và control plane cùng page |
| `pages/runs-page.tsx` | 734 | Runs và approval inbox cần tách section/hook |

### 2.3. Các phát hiện quan trọng

#### P0 — Bảo mật và tính trung thực

1. `backend/app/core/config.py` còn giá trị mặc định thật-looking cho database password, MinIO secret, JWT secret, internal API key và Dev Access password; `DEV_AUTH_ENABLED=True` mặc định.
2. `modelops/service.py` khởi tạo provider/key pool bằng mock key, số token sử dụng giả và trạng thái active; một số key còn giữ trong dictionary in-memory.
3. `app/core/crypto.py` đã có hàm mã hóa Fernet nhưng chưa được dùng trong ModelOps; trường `api_key_encrypted` vẫn đang nhận raw key.
4. `frontend/src/services/tools-api.ts` trả `status: success`, đường dẫn artifact, số liệu tuyển sinh và metadata được dựng cứng khi Backend lỗi.
5. `ingestion-progress-modal.tsx` dùng chuỗi `setTimeout` và duration cố định để mô phỏng MinIO/OCR/Chunking/Qdrant đã hoàn tất.
6. Chat Studio nạp năm trợ lý mẫu khi API trả rỗng; Assistant Create/Detail nạp danh sách model hardcode khi Provider trả rỗng.
7. `vector_indexer.py` fallback sang deterministic mock embeddings khi embedding thật lỗi.
8. `/health/live` được Frontend chuyển thành trạng thái database/Redis “connected”, dù endpoint liveness không kiểm tra dependency.

#### P0 — Database và data integrity

1. `main.py` chạy `Base.metadata.create_all`, raw `ALTER TABLE`, `CREATE INDEX` và seed nhiều domain khi ứng dụng khởi động.
2. Repository chỉ có hai Alembic migrations trong khi code hiện có gần 30 bảng ORM.
3. Startup bắt `Exception`, chỉ warning rồi tiếp tục chạy; service có thể online với schema/seed thiếu một phần.
4. PostgreSQL, Qdrant, Redis và MinIO chưa có transaction chung/outbox đầy đủ; lỗi giữa chừng có thể tạo orphan hoặc ghost citation.
5. Sparse RAG chấp nhận document status `completed/approved/processed`, trong khi dense index dùng `approved`; hai nhánh chưa có một lifecycle canonical.
6. RAG sparse chưa enforce `workspace_id`; nhiều API nhận tenant/workspace từ payload/header thay vì actor đã xác thực.

#### P0/P1 — Runtime policy

1. Tool Gateway đã được cải thiện để đi qua `ToolService` khi có DB session, nhưng nhánh không có DB vẫn gọi tool trực tiếp; production phải fail-closed.
2. HITL hiện dựa vào `parameters.is_approved`; cần approval record/token bất biến thay vì boolean do caller cung cấp.
3. Workflow engine có giới hạn bước nhưng chưa có timeout node, retry/backoff, cancellation và idempotency contract đầy đủ.
4. Chat SSE thực chất chạy xong toàn workflow rồi chia chuỗi answer thành từng từ với `sleep`; chưa stream token thật từ LLM và chưa hủy xử lý server-side khi client ngắt.
5. Usage token được ước lượng bằng độ dài chuỗi; có rủi ro sai accounting và ghi trùng giữa sync/stream.

#### P1 — Maintainability và async correctness

1. Có khoảng 155 vị trí `except Exception`/`pass`; nhiều lỗi phụ bị nuốt để giữ happy path.
2. Local/S3 storage khai báo API async nhưng gọi `Path.read_bytes/write_bytes` và boto3 đồng bộ trực tiếp trên event loop.
3. S3 driver gọi network để kiểm tra/tạo bucket ngay khi module được import.
4. Service tự `commit/rollback` ở nhiều cấp, làm transaction boundary khó dự đoán.
5. Frontend fetch phân tán, chưa có một HTTP client chung xử lý credentials, RFC 7807, correlation ID, timeout và cancellation.

#### P1 — Testing, Evaluation và vận hành

1. 239 Backend tests qua nhưng còn 47 warnings, chủ yếu do AsyncMock không tương thích hành vi sync của `Session.add` và un-awaited coroutine.
2. Chưa có coverage threshold; số test cao không chứng minh các path production đã được phủ.
3. Playwright chỉ tự khởi động Vite, có test bỏ qua lỗi Backend/offline; chưa có pipeline E2E live bắt buộc.
4. Evaluation đã gọi Assistant/RAG thật, nhưng `RagasTM08Evaluator` là phép đo lexical/heuristic tự viết, chưa phải Ragas chuẩn hoặc LLM-as-judge đã hiệu chỉnh.
5. Kết quả evaluation theo test case chưa được lưu đầy đủ để drill-down/audit.
6. `ENABLE_PROMETHEUS` và `RATE_LIMIT_PER_MINUTE` có trong config nhưng chưa có middleware/endpoint thực thi tương ứng.
7. Docker Compose còn image `latest`, default password, expose trực tiếp datastore ports và chưa thể hiện deployment stack hoàn chỉnh của app.

---

## 3. Nguyên tắc cải thiện

1. **Không big-bang rewrite.** Giữ Modular Monolith, domain contracts và design system hiện tại.
2. **Truth before polish.** Không thêm tính năng hoặc UI đẹp nếu trạng thái dữ liệu còn có thể giả thành công.
3. **Fail closed với security và side effect.** Thiếu actor, DB session, approval hoặc secret hợp lệ thì dừng, không fallback thực thi.
4. **Degrade honestly với AI dependency.** Có thể chuyển dense sang sparse-only, nhưng phải có nhãn degraded và tuyệt đối không dùng mock vector trong LiveMode.
5. **Một nguồn sự thật cho lifecycle.** Document, Workflow, Assistant, Provider và Evaluation phải có state machine thống nhất giữa DB, API và UI.
6. **Mỗi đợt nhỏ, có rollback.** Không gom toàn bộ kế hoạch vào một branch/session lớn.
7. **Không sửa chồng session.** Mỗi đợt phải kiểm tra worktree, file ownership và quality gate trước khi bắt đầu.

---

## 4. Thứ tự ưu tiên tổng quát

```text
P0 Baseline xanh
  → P0 Secrets/Auth/Tenant Boundary
    → P0 Truthful Runtime
      → P0 Database & Cross-store Integrity
        → P1 RAG/ModelOps/Workflow Hardening
          → P1 Evaluation & Testing
            → P2 Maintainability/Observability/Deployment
```

Không nên triển khai các bước phía sau nếu quality gate của bước trước vẫn đỏ.

---

## 5. Kế hoạch triển khai chi tiết

## Đợt 0 — Khóa baseline và giải quyết xung đột session

**Thời lượng dự kiến:** 0,5–1 ngày  
**Mức ưu tiên:** P0  
**Mục tiêu:** tạo một mốc mã nguồn sạch để các đợt sau có thể đo regression.

### Công việc

- Xác nhận mọi session song song đã hoàn tất hoặc handoff rõ file ownership trước khi bắt đầu đợt mới.
- Chốt kết quả xanh hiện tại thành baseline có commit/tag rõ ràng.
- Chạy lại toàn bộ Backend + Frontend gate trên cùng một commit.
- Ghi lại số test, warning, bundle size và danh sách services cần cho E2E live.
- Không đưa file OCR cache, scan lớn hoặc artifact test vào Git.

### Tiêu chí hoàn thành

- Ruff 0 lỗi.
- Pytest full suite pass.
- Biome 0 lỗi.
- TypeScript 0 lỗi.
- Vite build thành công.
- Mojibake 0 lỗi.
- `git status` không chứa file nhị phân >500 KB chưa được xác nhận.

---

## Đợt 1 — Security, Secret và Tenant Boundary

**Thời lượng dự kiến:** 3–5 ngày  
**Mức ưu tiên:** P0  
**Mục tiêu:** bảo đảm một mật khẩu đơn giản vẫn được triển khai đúng cách, không mở rộng thành RBAC phức tạp nhưng không để secret mặc định.

### Backend

- Đổi các secret mặc định trong `Settings` thành rỗng/`None`; validate fail-fast khi `ENVIRONMENT=production`.
- `DEV_AUTH_ENABLED=False` mặc định cho production; chỉ bật rõ ràng bằng env ở local/internal deployment.
- Không lưu Dev Access password plaintext; dùng bcrypt hash từ `DEV_ACCESS_PASSWORD_HASH`.
- Tách `PROVIDER_ENCRYPTION_KEY` khỏi `SECRET_KEY`; sử dụng `encrypt_secret/decrypt_secret` thật sự.
- Viết migration chuyển raw provider key sang ciphertext versioned; không trả raw key qua API/log.
- Xóa toàn bộ mock key, token usage giả và provider active giả khỏi LiveMode.
- Actor xác thực là nguồn duy nhất của `tenant_id/workspace_id`; không tin payload/header do client tự chọn đối với admin mutation/RAG.
- Thêm rate limit cho login và public chat/widget; có lockout/backoff nhẹ cho login sai.
- Siết CORS theo environment; cấm `*` khi `allow_credentials=True`.
- Dùng approval record bất biến cho Tool side effects, không dùng `parameters.is_approved` làm bằng chứng.

### Kiểm thử bắt buộc

- Production không khởi động nếu thiếu JWT/provider encryption key hoặc còn default password.
- Raw provider key không xuất hiện trong DB dump/API/log.
- Tenant A không truy cập collection/assistant/run của tenant B.
- Public chat bị rate-limit đúng contract RFC 7807.
- Cookie auth có `HttpOnly`, `Secure` production, `SameSite` phù hợp và logout xóa đúng path/domain.

---

## Đợt 2 — Truthful Runtime và loại bỏ fake-success

**Thời lượng dự kiến:** 3–5 ngày  
**Mức ưu tiên:** P0  
**Mục tiêu:** khi dependency lỗi, người dùng thấy lỗi/degraded thật; không có nghiệp vụ nào được báo thành công giả.

### Frontend

- Xóa offline success fallback trong `tools-api.ts`.
- Thay `IngestionProgressModal` bằng trạng thái job thật từ Backend/SSE/polling.
- Chat Studio không tự nạp năm trợ lý mẫu khi API lỗi/rỗng; phân biệt error với empty.
- Assistant Create/Detail không tự nạp model hardcode khi Provider API rỗng; chặn lưu/publish và chỉ rõ lý do.
- Tách fixture `verification-data.ts` khỏi production bundle; chỉ lazy-load khi `?mode=demo` hoặc người dùng chọn “Xem mẫu”.
- Health UI dùng `/health/ready` cho dependency health, `/health/live` chỉ cho process liveness.

### Backend

- Vector embedding lỗi trong LiveMode phải trả `index_failed` hoặc chuyển sparse-only có cờ `degraded`; không sinh mock vectors.
- Provider thiếu credential phải là `unavailable`, không active.
- Tool/export lỗi phải trả failed, không trả metadata/path artifact được dựng trước.
- Assistant spec generator có thể dùng template deterministic nhưng phải gắn `generation_mode=template`, không giả là kết quả LLM.

### Tiêu chí hoàn thành

- Tắt Backend: UI không xuất hiện dữ liệu nghiệp vụ mới và không hiện success.
- Tắt Qdrant: truy vấn hoặc sparse-only degraded có nhãn, hoặc fail rõ; không citation giả.
- Tắt MinIO: upload thất bại, không chạy progress giả.
- Tắt Provider: model không khả dụng bị chặn ngay ở cấu hình/publish gate.
- E2E có assertion “không fake success” cho Tools, Ingestion, Chat, Provider và Embedding.

---

## Đợt 3 — Database Migration và Cross-store Integrity

**Thời lượng dự kiến:** 4–6 ngày  
**Mức ưu tiên:** P0  
**Mục tiêu:** schema và dữ liệu thay đổi có thể nâng cấp/rollback có kiểm soát.

### Công việc

- Tạo Alembic baseline bao phủ toàn bộ bảng/index/constraint hiện tại.
- Tạo migration riêng cho mọi thay đổi sau baseline; không raw `ALTER TABLE` trong `main.py`.
- Gỡ `Base.metadata.create_all` khỏi production startup.
- Tách seed thành command idempotent có tham số `--environment`/`--catalog`; không seed nghiệp vụ khi app boot.
- Startup fail readiness nếu migration/schema không đúng version.
- Chuẩn hóa transaction boundary: router/request hoặc use-case sở hữu commit; service con không tự commit tùy ý.
- Bổ sung FK, `ondelete`, unique constraint và index cho document/fact/chunk/version/run/log.
- Triển khai outbox/reconciliation cho PostgreSQL ↔ Qdrant ↔ MinIO ↔ Redis.
- Dùng state machine canonical cho document: `uploaded → processing → review_pending → indexing → ready | failed | archived`.

### Tiêu chí hoàn thành

- Database rỗng có thể `alembic upgrade head` thành công.
- Database phiên bản trước có thể nâng cấp không mất dữ liệu.
- App không tự thay schema khi boot.
- Failure injection ở Qdrant/MinIO không tạo document `ready` sai.
- Reconciliation phát hiện và sửa orphan/ghost theo audit trail.

---

## Đợt 4 — RAG Data Integrity và Groundedness

**Thời lượng dự kiến:** 5–7 ngày  
**Mức ưu tiên:** P0/P1  
**Mục tiêu:** câu trả lời chỉ dùng đúng tài liệu, đúng revision, đúng tenant/workspace và có citation kiểm chứng được.

### Công việc

- Dùng một status canonical `ready` cho cả sparse, dense, facts và citation.
- Enforce đồng thời `tenant_id`, `workspace_id`, `collection_id`, `document_id/revision`, `is_retrievable` ở PostgreSQL và Qdrant.
- Truyền `workspace_id` xuyên suốt schema → service → retriever → vector filter.
- Loại `completed/processed` khỏi retrieval nếu chưa qua review/index gate.
- Sửa sparse query để không có biến chưa khởi tạo và không nuốt lỗi truy vấn.
- Tách dense failure khỏi empty result; trả metadata `retrieval_mode` và `degraded_reason`.
- Version hóa cache theo tenant/workspace/collection/document revision/assistant/model/policy.
- Bổ sung claim–citation verification trước output; số liệu/facts ưu tiên Structured Fact Layer.
- Rebuild index khi content revision thay đổi; archive/delete phải invalidate vector, facts và cache.

### Kiểm thử bắt buộc

- Không retrieve document pending/archived/index_failed.
- Không cross-tenant/cross-workspace.
- Citation trỏ đúng document, page, section, quote và revision.
- Edit/approve/reindex/delete không để ghost citation.
- Embedding down: không có mock vector trong LiveMode.
- Golden set Admissions/Regulations đạt threshold đã chốt.

---

## Đợt 5 — ModelOps và Assistant Runtime Hardening

**Thời lượng dự kiến:** 5–8 ngày  
**Mức ưu tiên:** P1  
**Mục tiêu:** cấu hình model trên UI thực sự quyết định runtime và usage/quota chính xác.

### Tách `modelops/service.py`

- `provider_service.py`: CRUD và capability catalog.
- `credential_service.py`: encrypted key pool và rotation.
- `routing_service.py`: primary/fallback/circuit breaker.
- `generation_service.py`: sync/stream adapters.
- `quota_service.py`: reservation, atomic usage và limit.
- `usage_service.py`: normalized usage/cost events.
- `health_service.py`: provider/model probes có TTL.

### Runtime contract

- Model catalog chỉ trả model có credential và capability phù hợp.
- Primary/fallback resolve deterministic theo provider/model ID, không chỉ model name mơ hồ.
- Publish Gate xác nhận hai model thực sự khả dụng và fallback không cùng failure domain nếu policy yêu cầu.
- Streaming dùng token stream thật từ adapter; client disconnect phải cancel upstream.
- Usage lấy token thật từ provider hoặc tokenizer; ghi đúng một lần bằng idempotency key.
- Quota reserve trước request và reconcile sau response; tránh vượt quota do concurrent calls.
- Không mutate global `settings` khi người dùng cập nhật provider.

### Tiêu chí hoàn thành

- Chọn model trên Assistant và trace runtime thể hiện cùng provider/model/version.
- Provider key rotation không cần restart app và không sửa global settings.
- Primary lỗi → fallback đúng policy; cả hai lỗi → No-Answer/degraded, không fake answer.
- Sync và stream có usage/cost nhất quán, không double count.

---

## Đợt 6 — Workflow, Tool Gateway và Human-in-the-loop

**Thời lượng dự kiến:** 5–7 ngày  
**Mức ưu tiên:** P1  
**Mục tiêu:** DAG chạy bền vững, có thể audit và không bypass policy.

### Công việc

- Giữ immutable workflow version/pin/rollback đã hoàn thành ở phiên #120.
- Validate NodeManifest version, input/output JSON Schema và port compatibility khi compile/publish.
- Mỗi node có timeout, retry policy, backoff, retryable error list và idempotency key.
- Thêm cancellation token cho execution và node external call.
- DB session/ToolService bắt buộc cho tool node ở LiveMode; nhánh direct registry chỉ tồn tại trong test adapter rõ ràng.
- Approval tạo `approval_request_id` gắn actor, action hash, parameters hash, expiry và workflow version.
- Resume chỉ chấp nhận approval record hợp lệ; không tin boolean trong input.
- Tách transaction của side effect và audit log qua outbox để không mất trace.
- Xác định rõ fan-out parallel, join semantics và giới hạn concurrency.

### Tiêu chí hoàn thành

- Node timeout/retry/cancel được kiểm chứng bằng failure injection.
- Không tool side effect nào chạy nếu thiếu allowlist/approval/audit.
- Resume chạy đúng immutable version ban đầu.
- Một request retry không tạo hai artifact hoặc hai side effect.

---

## Đợt 7 — Evaluation trung thực và Quality Gate AI

**Thời lượng dự kiến:** 4–6 ngày  
**Mức ưu tiên:** P1  
**Mục tiêu:** điểm chất lượng phản ánh đúng runtime thay vì chỉ là chỉ số giao diện.

### Công việc

- Đổi tên evaluator hiện tại thành `HeuristicPrecheckEvaluator` nếu tiếp tục dùng lexical overlap.
- Tích hợp Ragas thật hoặc LLM-as-judge đã hiệu chỉnh cho faithfulness, relevance và context precision.
- Version hóa dataset, ground truth, expected source và provenance.
- Lưu từng evaluation item: input, answer, contexts, citations, model, workflow version, policy version, scores và reason.
- Không fallback âm thầm Assistant → RAG rồi vẫn báo cùng loại run; ghi rõ execution path.
- Thêm regression comparison giữa bản published hiện tại và candidate.
- Publish Gate dùng run mới nhất của đúng assistant/workflow/model/knowledge revision.
- Human review sample cho câu có số liệu, điều khoản và kết quả sát threshold.

### Tiêu chí hoàn thành

- Có thể drill-down từ điểm tổng đến từng câu, câu trả lời và citation.
- Chạy lại cùng version/dataset cho kết quả trong sai số định trước.
- Candidate giảm dưới threshold bị chặn publish.
- No-Answer đúng không được dùng để “ăn điểm” faithfulness một cách máy móc.

---

## Đợt 8 — Maintainability, Async I/O và Frontend Architecture

**Thời lượng dự kiến:** 6–10 ngày, chia nhiều PR nhỏ  
**Mức ưu tiên:** P1/P2

### Backend

- Tách `knowledge/service.py`, `assistants/service.py`, `workflows/service.py` theo use-case.
- Chuyển local file I/O sang `asyncio.to_thread` hoặc aiofiles; dùng aioboto3/async wrapper cho S3.
- Không thực hiện network/bucket creation ở module import; chuyển sang startup health/provision command.
- Giảm broad exception theo boundary; error không quan trọng phải có structured event, error quan trọng phải propagate.
- Chuẩn hóa Repository/Unit-of-Work ở những use-case nhiều bảng/cross-store; không tạo abstraction hình thức cho CRUD đơn giản.

### Frontend

- Hoàn tất tách `modelops-page`, `assistant-create-page`, `dag-canvas-page`, `runs-page` và các studio lớn.
- Xây HTTP client chung: credentials, timeout, abort, RFC 7807 parser, correlation ID và typed error.
- Chuẩn hóa query keys, mutation invalidation và optimistic rollback.
- Tách Demo assets/fixtures khỏi production chunk.
- Tiếp tục Kế hoạch 06: route config là nguồn duy nhất cho sidebar, breadcrumb, page title và deep link.
- Thực hiện các ưu tiên trong báo cáo UI/UX: responsive shell, semantic status, accessibility và typography.

### Chỉ số mục tiêu

- Page orchestrator lý tưởng 150–350 dòng.
- Service domain lớn được tách thành các use-case/module dưới khoảng 500 dòng khi hợp lý.
- Không tăng thêm broad exception/pass không có giải thích.
- Không blocking I/O trực tiếp trong async function.

---

## Đợt 9 — Testing, CI và Observability

**Thời lượng dự kiến:** 4–7 ngày  
**Mức ưu tiên:** P1/P2

### Testing

- Sửa toàn bộ 47 pytest warnings; fixture phải mô phỏng đúng `AsyncSession` (`add` là sync, `execute/commit/refresh` là async).
- Thêm coverage report và threshold: tổng Backend ≥80%, domain critical ≥90% branch cho auth/RAG/Tool/Workflow.
- Bổ sung Vitest + React Testing Library cho hooks, state contract, model selector, error/degraded states và critical forms.
- Tách E2E thành hai lane:
  - Offline/failure E2E: xác nhận không mock/fake success.
  - Live integration E2E: khởi động Backend + PostgreSQL + Redis + Qdrant + MinIO.
- Contract tests cho FE/BE DTO và NodeManifest/OpenAPI schema.
- Failure injection tests: DB down, provider 429/timeout, Qdrant down, MinIO down, Redis down và client cancellation.

### CI

- PR gate: secret scan → Ruff → Pytest → Biome → Typecheck → Build → Mojibake → unit tests.
- Nightly: live E2E, RAG golden set, evaluation regression, dependency vulnerability scan.
- Không merge nếu warning mới hoặc quality gate đỏ.

### Observability

- Hiện thực `/metrics` thật với request latency/error, LLM usage/cost, retrieval mode, no-answer rate, workflow/node latency, queue depth.
- Thêm rate-limit middleware và metric.
- Chuẩn hóa trace/correlation xuyên Assistant → Workflow → RAG/Tool → Provider.
- Dashboard và alert cho error rate, p95 latency, quota, circuit breaker, index backlog và handoff SLA.

---

## Đợt 10 — Production Deployment và Disaster Recovery

**Thời lượng dự kiến:** 3–5 ngày  
**Mức ưu tiên:** P2, bắt buộc trước Go-Live

### Công việc

- Pin version/digest cho Postgres, Qdrant, Redis, MinIO, Gotenberg và app images; bỏ `latest`.
- Tạo production compose/Dokploy stack riêng, không expose datastore ports công khai.
- Container chạy non-root, filesystem read-only khi có thể, resource limits và healthcheck đầy đủ.
- Chạy migration như release step trước app rollout; có rollback/runbook.
- Backup PostgreSQL, MinIO và Qdrant theo lịch; mã hóa và retention policy.
- Thực hiện restore drill, không chỉ có lệnh tài liệu.
- Thiết lập SLO ban đầu: availability, p95 latency, ingestion success, citation validity và no-answer rate.
- Canary/blue-green cho thay đổi Assistant/Workflow/RAG policy quan trọng.

### Tiêu chí Go-Live

- Không hardcoded/default production secret.
- Migration/rollback đã diễn tập.
- Restore drill thành công trên môi trường tách biệt.
- Live E2E và RAG golden set đạt.
- Alert hoạt động và có người chịu trách nhiệm xử lý.
- Không còn P0 mở.

---

## 6. Ma trận ưu tiên công việc

| ID | Hạng mục | Mức | Tác động | Phụ thuộc |
| :--- | :--- | :---: | :--- | :--- |
| IMP-01 | Baseline xanh sau session song song | P0 | Mở khóa mọi đợt | Không |
| IMP-02 | Xóa default secrets và mã hóa provider key | P0 | Security/Data breach | IMP-01 |
| IMP-03 | Trusted tenant/workspace actor | P0 | Data isolation | IMP-02 |
| IMP-04 | Loại fake-success/mock trong LiveMode | P0 | Niềm tin dữ liệu | IMP-01 |
| IMP-05 | Alembic đầy đủ, bỏ schema mutation lúc startup | P0 | Data safety/deployment | IMP-01 |
| IMP-06 | RAG lifecycle/revision/filter thống nhất | P0 | Groundedness | IMP-03, IMP-05 |
| IMP-07 | Tool approval record và fail-closed | P0 | Side-effect safety | IMP-02, IMP-03 |
| IMP-08 | ModelOps key/routing/quota hardening | P1 | Runtime reliability/cost | IMP-02, IMP-04 |
| IMP-09 | Workflow timeout/retry/cancel/idempotency | P1 | Runtime reliability | IMP-07 |
| IMP-10 | Evaluation thật và item audit | P1 | Quality governance | IMP-06, IMP-08, IMP-09 |
| IMP-11 | Split service/page lớn + async storage | P1 | Maintainability/performance | Sau P0 |
| IMP-12 | CI, coverage, live E2E, metrics | P1 | Regression prevention | Chạy xuyên suốt |
| IMP-13 | Production stack và restore drill | P2 | Go-Live | Tất cả P0/P1 chính |

---

## 7. Phân chia thành PR/session an toàn

Không triển khai một đợt bằng một PR khổng lồ. Mỗi PR nên có một mục tiêu có thể rollback độc lập:

1. `security/settings-validation`
2. `security/provider-key-encryption`
3. `runtime/remove-frontend-fake-success`
4. `runtime/remove-mock-embeddings`
5. `database/alembic-baseline`
6. `database/remove-startup-schema-seed`
7. `rag/canonical-lifecycle-filters`
8. `rag/revision-cache-citations`
9. `modelops/split-credentials-routing`
10. `workflow/approval-idempotency`
11. `evaluation/versioned-item-results`
12. `qa/ci-live-e2e-observability`

Mỗi PR phải cập nhật quy trình, memory, snapshot và work log tương ứng; không gom tài liệu cuối cùng sau nhiều đợt.

---

## 8. Definition of Done toàn chương trình

### Security

- [ ] Không có secret/key/password thật-looking mặc định trong source.
- [ ] Provider credentials được mã hóa và rotation được kiểm thử.
- [ ] Tenant/workspace lấy từ trusted actor ở mọi path nhạy cảm.
- [ ] Public endpoints có rate limit và abuse protection cơ bản.

### Data và RAG

- [ ] Không retrieve document chưa ready hoặc sai revision.
- [ ] Không mock embedding/fake citation trong LiveMode.
- [ ] PostgreSQL–Qdrant–MinIO–Redis có reconciliation và audit.
- [ ] Citation mở được đúng tài liệu/trang/đoạn nguồn.

### Runtime

- [ ] Assistant dùng đúng published workflow/model/knowledge revision.
- [ ] Tool side effect luôn qua allowlist + approval + audit.
- [ ] Workflow có timeout/retry/cancel/idempotency.
- [ ] Streaming và usage accounting là dữ liệu thật.

### Quality

- [ ] Backend và Frontend quality gate xanh trên CI.
- [ ] Pytest không warning ngoài allowlist đã giải thích.
- [ ] Có frontend unit tests và live E2E.
- [ ] Evaluation có item-level evidence và versioning.

### Operations

- [ ] Alembic là nguồn sự thật duy nhất của schema.
- [ ] Production image pin version, non-root và không expose datastore.
- [ ] Metrics/alerts hoạt động.
- [ ] Backup/restore drill thành công.

---

## 9. Những việc chưa nên làm

- Không thêm chatbot chuyên trách thứ sáu trước khi năm trợ lý hiện tại qua runtime/evaluation gate.
- Không thêm provider mới khi key storage/routing/quota chưa được harden.
- Không tăng số node DAG trước khi schema/timeout/retry/cancel hoàn chỉnh.
- Không gọi heuristic hiện tại là “Ragas đạt chuẩn” trong báo cáo chính thức.
- Không tiếp tục dùng UI fallback để làm màn hình luôn có dữ liệu.
- Không refactor toàn bộ repository trong một session.
- Không sửa chồng các file đang thuộc session khác nếu chưa handoff.

---

## 10. Thứ tự triển khai khuyến nghị ngay sau kế hoạch

Ba đợt nên bắt đầu trước:

1. **Đợt 0 — Baseline xanh:** kết thúc session OCR hiện tại và đưa toàn bộ quality gate về xanh.
2. **Đợt 1 — Security/Secrets:** loại default secret, mã hóa Provider key và khóa tenant boundary.
3. **Đợt 2 — Truthful Runtime:** xóa fake-success trong Tools/Ingestion/Chat/Model selector/Embedding.

Sau ba đợt này, dự án chưa hoàn tất production nhưng đã loại được rủi ro lớn nhất: **hệ thống hiển thị thành công hoặc dữ liệu có vẻ hợp lệ trong khi dependency thật không hoạt động**.

---

## 11. Kết luận

QNU AI Platform đang đi đúng hướng và đã cải thiện đáng kể so với lần đánh giá tổng thể trước. Kiến trúc domain, Knowledge/OCR, Workflow ownership/versioning, typed Frontend và test suite là những tài sản nên giữ.

Kế hoạch cải thiện không đề xuất viết lại dự án. Trọng tâm là biến những gì đã có thành một hệ thống **đáng tin, kiểm chứng được và vận hành được**: loại secret/mock/fake-success, chuẩn hóa migration và data lifecycle, khóa RAG/Tool/Workflow policy, sau đó mới tối ưu maintainability, testing và deployment.

Nếu thực hiện đúng thứ tự, dự án có thể tiến từ Internal Beta mạnh lên Production Candidate mà không làm sai lệch cấu trúc cốt lõi hoặc làm giảm chất lượng chức năng hiện tại.
