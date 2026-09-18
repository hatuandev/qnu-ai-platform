# NHẬN XÉT TỔNG THỂ DỰ ÁN QNU AI PLATFORM

> Ngày đánh giá: 18/09/2026  
> Phạm vi: Backend, Frontend, dữ liệu, Assistant, Workflow/DAG, RAG, ModelOps, Evaluation, bảo mật, kiểm thử và vận hành  
> Mốc mã nguồn: nhánh `main`, commit `cd667f0`  
> Trạng thái đánh giá: mã nguồn có thay đổi chưa commit thuộc phiên ModelOps/Provider đang chạy song song

---

## 1. Kết luận điều hành

QNU AI Platform đã vượt qua giai đoạn prototype giao diện. Dự án hiện có một nền tảng quản trị AI tương đối rộng, API và cơ sở dữ liệu thật, OCR/ingestion hoạt động, danh mục Node/Assistant/Workflow đã được đồng bộ, và có một số luồng DAG đã chạy end-to-end.

Tuy nhiên, dự án **chưa đạt mức production-ready**. Trạng thái phù hợp nhất hiện nay là:

> **Internal Beta / Engineering Preview** — đủ tốt để trình diễn, thử nghiệm nội bộ, tiếp tục hoàn thiện nghiệp vụ và thu thập phản hồi; chưa phù hợp để mở cho người dùng thật hoặc dùng làm nguồn quyết định nghiệp vụ quan trọng.

Nguyên nhân chính không nằm ở việc thiếu màn hình. Ngược lại, dự án đã có nhiều màn hình và cấu hình. Khoảng cách lớn nhất nằm ở việc các cấu hình đó **chưa được nối đầy đủ xuống runtime**, một số chỉ số chất lượng đang được tạo từ dữ liệu mô phỏng, frontend vẫn che lỗi backend bằng mock, và lớp bảo mật chưa được áp dụng trên router.

### Điểm đánh giá tổng hợp

| Nhóm đánh giá | Điểm / 10 | Nhận xét ngắn |
| :--- | :---: | :--- |
| Kiến trúc tổng thể | 6.5 | Phân miền rõ nhưng còn nhiều file quá lớn và startup làm quá nhiều việc |
| Backend API | 7.0 | FastAPI async, DTO, RFC 7807 và logging khá tốt |
| Frontend và UX quản trị | 7.5 | Giao diện rộng, nhất quán, có deep link; maintainability còn yếu |
| Knowledge/OCR/Ingestion | 7.0 | Phần trưởng thành nhất, có pipeline thật và kiểm thử đáng kể |
| RAG runtime | 4.5 | Retrieval có thật nhưng synthesis chưa gọi LLM, lexical search chưa phải FTS thật |
| Assistant runtime | 5.0 | Cấu hình 7 lớp tốt nhưng model/tool/evaluation chưa thực thi đầy đủ |
| Workflow Control Plane | 6.5 | Có draft, version, publish, rollback, checkpoint và approval |
| DAG Runtime Engine | 4.5 | Chạy DAG cơ bản tốt nhưng thiếu timeout, retry, cancellation, schema và permission |
| ModelOps | 6.5 | Có provider/key pool/circuit breaker/quota; đang được thay đổi ở phiên khác |
| Evaluation/TM-08 | 2.5 | Kết quả hiện được tính từ câu trả lời và context mô phỏng |
| Bảo mật và phân quyền | 3.0 | Có utility JWT/PII nhưng router chưa thực thi auth/RBAC/tenant isolation |
| Quan sát vận hành | 5.5 | Có correlation ID, structured log và trace cơ bản; thiếu metrics/trace chuyên sâu |
| Kiểm thử | 6.5 | 172 backend tests pass, nhưng nhiều ca quan trọng dựa vào mock |
| Triển khai production | 4.5 | Có Docker infra và tài liệu, nhưng lifecycle schema/secrets/CI chưa đủ chặt |
| Khả năng bảo trì | 4.5 | Nhiều file từ 700 đến gần 3.000 dòng, trái với mục tiêu SRP |

**Điểm tổng thể đề xuất: 5.6/10.**

Điểm này không có nghĩa dự án yếu. Nó phản ánh rằng nền móng và bề rộng tính năng đã tốt, nhưng mức độ bảo đảm cho dữ liệu, runtime, bảo mật và vận hành vẫn thấp hơn mức mà giao diện và tài liệu tiến độ đang thể hiện.

---

## 2. Phương pháp và bằng chứng đánh giá

Bản nhận xét được lập dựa trên:

1. Đọc `AGENTS.md`, `docs/memory/PROJECT_CONTEXT.md` và các quy trình hiện hành.
2. Rà soát mã nguồn Backend/Frontend, tập trung vào Assistant, Workflow, RAG, ModelOps, Evaluation, Security và API client.
3. Đối chiếu các hợp đồng và runtime quan trọng với `qnu-ai-core`.
4. Kiểm tra trực tiếp dịch vụ đang chạy tại port 8001 và 3001.
5. Chạy lại bộ kiểm tra trên worktree hiện tại.

### Trạng thái dịch vụ tại thời điểm đánh giá

| Thành phần | Kết quả |
| :--- | :--- |
| Backend liveness | HTTP 200 |
| Backend readiness | PostgreSQL và Redis đều connected |
| Frontend | HTTP 200 tại port 3001 |
| Node Catalog | 13 manifests |
| Assistants | 5 trợ lý |
| Workflow Definitions | 5 workflow |
| Knowledge Collections | 5 collection |
| ModelOps Providers | 11 bản ghi |
| Workflow Executions | 25 bản ghi |

### Kết quả kiểm thử chạy lại

| Kiểm tra | Kết quả |
| :--- | :--- |
| `uv run ruff check .` | Pass, 0 lỗi |
| `uv run --extra dev pytest -q` | **172 passed**, 17 warnings, 93.91 giây |
| `npm run lint` | Pass, 93 files |
| `npm run typecheck` | Pass |
| `npm run build` | **Pass** sau khi phiên ModelOps #84 hoàn tất; built trong 8.82 giây, có cảnh báo bundle JS 1.50 MB |
| `python scripts/check_mojibake.py` | Pass, 231 files UTF-8 sạch |

Trong lúc đánh giá, build từng lỗi tại file ModelOps đang được phiên song song chỉnh sửa. Sau khi phiên #84 hoàn tất, build đã được chạy lại và pass. Cảnh báo còn lại là bundle JS sau minify khoảng 1.50 MB, nên cần code splitting trước production.

---

## 3. Những điểm dự án đang làm tốt

### 3.1. Có cấu trúc domain tương đối rõ

Backend đã chia được các miền chính:

- `assistants`
- `knowledge`
- `ocr`
- `rag`
- `modelops`
- `workflows`
- `tools`
- `evaluation`
- `document_types`
- `jobs`
- `node_catalog`

Router phần lớn giữ vai trò tiếp nhận request và gọi service. Pydantic DTO, SQLAlchemy async và exception dạng Problem Details đã được sử dụng khá nhất quán.

### 3.2. Knowledge/OCR là phần trưởng thành nhất

Pipeline tài liệu đã có nhiều thành phần thật:

- Upload và lưu trữ tài liệu.
- Parse PDF, Word, Excel và văn bản.
- OCR nhiều tầng.
- Phát hiện layout, bảng, vùng chữ và con dấu.
- Human-in-the-loop verification.
- Chunking và structured facts.
- Index Qdrant.
- Job history, cancel, retry, cleanup và reindex.

Đây là phần có nhiều test thực tế nhất và tạo ra giá trị rõ nhất cho sản phẩm.

### 3.3. Control Plane Workflow có nền tảng tốt

Platform đã có:

- Workflow definition.
- Draft với optimistic revision.
- Validate trước publish.
- Immutable version record.
- Rollback tạo version mới.
- Execution và node execution logs.
- Checkpoint và human approval.
- UI DAG Canvas, version history và in-canvas runner.

Đây là nền móng tốt để tiếp tục nâng runtime lên gần Core, thay vì phải viết lại từ đầu.

### 3.4. Frontend có chiều rộng và nhận diện nhất quán

Frontend đã bao phủ gần đầy đủ các domain quản trị. Hệ thống màu Academic Teal, semantic tokens, dark mode, master-detail routing và các component AI tạo ra trải nghiệm sản phẩm khá thuyết phục.

Các trang Assistant, Knowledge, OCR, Workflow, ModelOps và Tools có thể dùng để demo nghiệp vụ và trao đổi yêu cầu với người dùng cuối.

### 3.5. Khả năng kiểm thử tốt hơn mặt bằng prototype

172 backend tests pass là một nền tảng đáng ghi nhận. Dự án có Ruff, Biome, TypeScript, Vite build, Playwright suites và script kiểm tra mojibake. Đây là hệ thống bảo vệ tốt nếu tiếp tục chuyển test từ mock sang integration/contract tests.

### 3.6. UTF-8 hiện tại không có lỗi

Kiểm tra raw UTF-8 từ API cho thấy tên tiếng Việt được trả về đúng. Việc PowerShell mặc định từng hiển thị chuỗi như `Trá»...` là vấn đề giải mã của terminal, không phải bằng chứng database bị hỏng. Script `check_mojibake.py` cũng xác nhận 231 file sạch.

---

## 4. Các vấn đề nghiêm trọng cần xem lại

## 4.1. P0 — Authentication và authorization chưa được áp dụng

Module `app/core/security.py` có hàm tạo/giải mã JWT, bcrypt và PII masking. Tuy nhiên các router nghiệp vụ chỉ phụ thuộc `get_db`; chưa thấy dependency bắt buộc xác thực người dùng, RBAC hoặc kiểm tra quyền.

Hệ quả:

- Người gọi API có thể tự gửi `tenant_id` hoặc `X-Tenant-Id`.
- Endpoint Provider, API key, workflow publish, approval, upload và tools chưa có lớp quyền rõ ràng.
- Tenant isolation hiện là quy ước dữ liệu, chưa phải security boundary.

Ngoài ra cấu hình có giá trị mặc định cho `SECRET_KEY`, `INTERNAL_API_KEY`, MinIO credentials và `DEV_AUTH_ENABLED=True`. Những default này chỉ phù hợp dev; nếu cấu hình môi trường thiếu, production có thể chạy bằng secret đoán được.

**Đề xuất:** chưa triển khai ra ngoài mạng nội bộ cho tới khi có authentication middleware/dependency, RBAC, tenant context đáng tin cậy và startup fail-fast khi production thiếu secret.

## 4.2. P0 — Evaluation/TM-08 hiện tạo cảm giác an toàn giả

`EvaluationService.run_evaluation()` không gọi Assistant/RAG runtime thật. Service tự tạo `simulated_answer` và `simulated_contexts` từ ground truth rồi tính điểm trên dữ liệu đó.

`get_summary_metrics()` trả về các số cố định:

- Faithfulness 0.94.
- Answer relevance 0.91.
- Context precision 0.88.
- Total evaluations 1420.

Gap Inbox cũng là danh sách hardcode.

Workflow publish có đọc `EvaluationRun` gần nhất để làm quality gate, nhưng EvaluationRun lại có thể được tạo từ dữ liệu mô phỏng. Như vậy gate tồn tại về mặt kỹ thuật nhưng chưa chứng minh được chất lượng runtime thực.

**Đề xuất:** đây là hạng mục cần sửa trước khi dùng nhãn “đạt TM-08” trên UI hoặc trong tài liệu nghiệm thu.

## 4.3. P0 — Frontend vẫn trả dữ liệu nghiệp vụ mock khi backend lỗi

`api-client.ts` còn các tập dữ liệu mock cho:

- Collections và documents.
- Ingestion tasks.
- Providers và quota.
- Tools.
- Evaluation metrics và Gap Inbox.
- Verification document.

`use-rag-stream.ts` còn `MOCK_ASSISTANT_DATA`. Khi endpoint chat lỗi, hook tự sinh câu trả lời RAG, citation và thậm chí artifact DOCX/PDF fallback.

Điều này nguy hiểm hơn một lỗi giao diện thông thường: người dùng có thể tưởng dữ liệu giả là kết quả thật từ backend/RAG.

**Đề xuất:** tách dứt khoát `DemoMode` và `LiveMode`. LiveMode phải hiển thị lỗi/empty state, tuyệt đối không thay câu trả lời nghiệp vụ bằng mock.

## 4.4. P0 — RAG có retrieval nhưng chưa có generation thật

`RagService.ask()` thực hiện fact lookup và hybrid retrieval, sau đó dựng `full_prompt`. Nhưng prompt này không được gửi đến ModelOps hoặc LLM.

Câu trả lời được tạo bằng cách:

- Chèn fact table.
- Lấy nguyên chunk đầu tiên.
- Gắn một số câu hỏi tiếp theo viết sẵn.

Do đó tên gọi “RAG answer generation” hiện chưa chính xác. Đây mới là retrieval + deterministic composition.

Ngoài ra `search_sparse_fts()` đang dùng chuỗi `ILIKE '%token%'`, chưa phải PostgreSQL FTS với `tsvector`, `tsquery` và ranking.

**Đề xuất:** nối Answer Composer với ModelOps bằng prompt có context bị giới hạn, bắt buộc citation/no-answer, đồng thời xây FTS thật và kiểm thử retrieval quality.

## 4.5. P0 — Chất lượng tài liệu giữa các collection chưa đủ để vận hành 5 Assistant

Dữ liệu thật tại thời điểm đánh giá:

| Collection | Documents | Chunks |
| :--- | ---: | ---: |
| `col_question_bank` | 2 | 17 |
| `col_drafting` | 1 | 6 |
| `col_library` | 0 | 0 |
| `col_regulations` | 0 | 0 |
| `col_admissions` | 0 | 0 |

Năm Assistant đã tồn tại, nhưng ba Assistant quan trọng chưa có dữ liệu trong collection tương ứng. Vì vậy “5 trợ lý sẵn sàng” mới đúng ở lớp catalog/configuration, chưa đúng ở lớp nghiệp vụ.

**Đề xuất:** định nghĩa readiness riêng cho từng Assistant và không gắn trạng thái `active/ready` nếu collection chưa có tài liệu được duyệt, chunks, vector và golden dataset.

## 4.6. P1 — Assistant 7 lớp mới nối runtime một phần

| Lớp cấu hình | Trạng thái thực tế |
| :--- | :--- |
| Persona & Scope | Có system prompt và input sanitizer |
| Knowledge Binding | Có dùng `collection_id`; `retrieval_limit` chưa được áp dụng đầy đủ |
| ModelOps | Có temperature/max tokens; primary/fallback model chưa truyền xuống request ModelOps |
| Guardrails | Có regex injection, PII mask và no-answer cơ bản; chưa phải policy engine đầy đủ |
| Tools | Có `enabled_tools` trong cấu hình nhưng workflow không tự gọi Tool Gateway |
| Output & Citations | Có định dạng/citation guard cơ bản |
| Evaluation | Có lưu threshold nhưng chưa gate runtime bằng đánh giá thật |

`LLMGenerateRequest` không có trường primary/fallback model. ModelOps hiện chọn provider theo priority toàn hệ thống. Vì vậy model người quản trị chọn trên Assistant có thể không phải model thực sự phục vụ request.

## 4.7. P1 — DAG Runtime chưa đạt mức “production engine”

Engine hiện làm tốt các tác vụ cơ bản:

- Ready-set scheduling.
- Branch theo `selected_port`.
- Fan-out/fan-in đơn giản.
- Max steps.
- Deadlock/stall detection.
- Pause và resume approval.

Nhưng còn thiếu:

- Timeout theo node và toàn run.
- Retry/backoff theo mã lỗi.
- Cancellation và deadline.
- Input/output JSON schema validation.
- Mapping dữ liệu theo `target_port`.
- Thực thi edge condition tổng quát.
- Permission và connection reference validation.
- Idempotency cho side-effect node.
- Skip reason và audit chi tiết.
- Song song thật cho các nhánh độc lập.

Compiler hiện chủ yếu kiểm tra node, edge, cycle, reachability, terminal, max steps và citation guard. Nó chưa đạt mức compiler của Core về manifest version, schema/port compatibility, permissions, connections, graph limits và immutable execution plan.

## 4.8. P1 — Workflow execution chưa thực sự khóa vào immutable version

Khi chạy, service lấy DAG hiện tại từ `WorkflowDefinition` rồi chỉ ghi `published_version_id` vào execution record.

Khi resume sau approval, service lại gọi `get_workflow_spec()` theo workflow hiện tại. Nếu workflow đã được publish/rollback trong lúc chờ duyệt, run cũ có thể tiếp tục bằng DAG mới.

**Đề xuất:** execution phải load `WorkflowVersion.dag_spec` đúng với `workflow_version_id`; checkpoint và resume phải dùng chính snapshot đó.

## 4.9. P1 — SSE Chat chưa phải streaming thật

Frontend gửi `stream: true`, chấp nhận `text/event-stream` và có SSE parser. Nhưng endpoint `/assistants/{reference}/chat` trả `AssistantChatResponse` JSON.

Frontend sau đó dùng `streamSimulatedText()` để hiển thị từng ký tự. Đây là streaming UX, không phải token streaming từ server/provider.

**Đề xuất:** hoặc triển khai SSE thật với event `token`, `citation`, `tool_call`, `error`, `done`; hoặc công khai endpoint là JSON và bỏ tuyên bố streaming runtime.

## 4.10. P1 — Startup lifecycle che giấu lỗi schema/seed

Startup hiện:

- Chạy `Base.metadata.create_all()`.
- Chạy raw `ALTER TABLE` và tạo index.
- Seed/sync nhiều domain.
- Bắt toàn bộ exception và chỉ log warning rồi vẫn cho ứng dụng chạy.

Điều này giúp dev thuận tiện nhưng production có thể báo liveness thành công trong khi schema hoặc seed đang hỏng.

**Đề xuất:** production chỉ chạy Alembic migration đã version hóa; seed tách thành command/job idempotent; lỗi migration hoặc cấu hình bắt buộc phải làm startup fail-fast.

## 4.11. P1 — Kiến trúc file đang đi ngược quy tắc SRP

Các file lớn nhất hiện tại:

| File | Số dòng gần đúng |
| :--- | ---: |
| `frontend/src/pages/modelops-page.tsx` | 2.959 |
| `frontend/src/services/api-client.ts` | 2.493 |
| `backend/app/modules/modelops/service.py` | 2.029 |
| `backend/app/modules/knowledge/service.py` | 1.470 |
| `frontend/src/services/verification-data.ts` | 1.395 |
| `frontend/src/pages/collection-detail-page.tsx` | 1.178 |
| `backend/app/modules/ocr/layout_detector.py` | 1.149 |
| `frontend/src/pages/assistant-detail-page.tsx` | 986 |
| `backend/app/modules/workflows/service.py` | 865 |

Đây là technical debt đáng kể. Nó làm review khó, tăng rủi ro merge conflict và khiến một thay đổi nhỏ có thể ảnh hưởng nhiều trách nhiệm.

## 4.12. P1 — Tài liệu trạng thái đang “đánh dấu hoàn thành” sớm

`PROJECT_CONTEXT.md` và Kế hoạch 04 có các tuyên bố như:

- Xóa hoàn toàn mock.
- SSE streaming hoàn chỉnh.
- Tool gateway và permission validation đã hoàn thành.
- DAG engine production.
- TM-08 quality gate hoàn chỉnh.
- Frontend/backend hoàn thành 100%.

Các tuyên bố này không còn khớp hoàn toàn với mã nguồn hiện tại. Đây là vấn đề quản trị dự án: phiên sau đọc memory sẽ tiếp tục dựa trên trạng thái lạc quan sai và dễ xây thêm UI trên runtime chưa hoàn tất.

**Đề xuất:** thay cột `Done` bằng ba cột độc lập:

1. UI/Configuration ready.
2. Runtime integrated.
3. Production verified.

---

## 5. Nhận xét theo từng phân hệ

### 5.1. Backend Core

**Điểm tốt**

- FastAPI async và SQLAlchemy `AsyncSession`.
- Exception handler có `correlation_id`.
- Structured logging bằng Structlog.
- Health probes PostgreSQL/Redis.
- Alembic đã được khởi tạo.
- Service/module organization nhìn chung rõ.

**Cần cải thiện**

- Áp auth dependency vào router.
- Không cho client tự xác định tenant tùy ý.
- Chuyển startup schema repair sang migrations.
- Chia nhỏ các service trên 500 dòng.
- Không nuốt lỗi DB/external service nếu lỗi đó làm thay đổi tính đúng đắn nghiệp vụ.

### 5.2. Frontend

**Điểm tốt**

- Design system nhất quán.
- Phân cấp trang list/detail tương đối rõ.
- Có loading/error/empty state ở nhiều domain.
- TanStack Query được sử dụng ở các màn hình mới.
- DAG Canvas và Assistant Control Center có giá trị demo cao.

**Cần cải thiện**

- Tách `modelops-page.tsx`, `api-client.ts`, `collection-detail-page.tsx` và Assistant pages.
- Thay manual pathname router bằng router chính thức có route definitions, params và error boundaries.
- Loại mock fallback khỏi LiveMode.
- Không hiển thị số mặc định như evaluation KPI khi API không có dữ liệu.
- Bổ sung unit/component tests; hiện phần lớn kiểm thử frontend là E2E.

### 5.3. Knowledge và OCR

**Điểm tốt**

- Đây là miền có chiều sâu kỹ thuật tốt nhất.
- Có nhiều parser/OCR strategy.
- Có verification studio và page-level data.
- Có structured facts, Qdrant và storage abstraction.

**Cần cải thiện**

- Xóa deterministic mock embedding khỏi LiveMode.
- Phân biệt rõ lỗi Qdrant/embedding với “không có kết quả”.
- Bổ sung provenance/checksum/version cho từng document/chunk/fact.
- Đảm bảo MinIO/S3 là đường chính ở production, local chỉ dành cho dev.

### 5.4. RAG

**Điểm tốt**

- Có Dense + lexical + RRF k=60 + reranker.
- Có fact layer và citation object.
- Có semantic cache và no-answer path.

**Cần cải thiện**

- Thực hiện LLM synthesis thật qua ModelOps.
- Dùng PostgreSQL FTS thật thay ILIKE.
- Không biến lỗi retrieval thành danh sách rỗng mà không phản ánh degraded state.
- Citation guard cần kiểm tra claim-evidence, không chỉ kiểm tra “có citation”.
- Retrieval parameters phải lấy từ Assistant profile.

### 5.5. Assistant

**Điểm tốt**

- Schema 7 lớp được thiết kế đúng hướng.
- CRUD/import/export/seed và runtime profile snapshot đã có.
- UI cấu hình tương đối đầy đủ.

**Cần cải thiện**

- Tạo `AssistantExecutionPolicy` đã resolve và bất biến cho mỗi run.
- Resolve model chính/dự phòng thành provider/model cụ thể.
- Chỉ cho phép gọi tool nằm trong `enabled_tools`.
- Enforce scope, citations, no-answer và evaluation policy tại runtime.
- Chỉ đánh dấu Assistant `ready` khi dependency readiness đạt chuẩn.

### 5.6. Workflow/DAG

**Điểm tốt**

- Control plane đã có đủ khái niệm nền tảng.
- Checkpoint và approval được lưu PostgreSQL.
- Compiler bắt được các lỗi graph cơ bản.

**Cần cải thiện**

- Tạo immutable `ExecutionPlan` như Core.
- Bind manifest exact version/hash.
- Validate port/schema/permission/connections.
- Thêm timeout/retry/cancel/idempotency.
- Resume đúng workflow version.
- Thêm endpoint run detail và node attempts đầy đủ.

### 5.7. ModelOps

**Điểm tốt**

- Adapter pattern, provider priority, circuit breaker, key pool, quota và usage log đã có.
- Phiên song song đang bổ sung health probing cho từng model.

**Cần cải thiện**

- Sau khi phiên song song ổn định, tách `service.py` thành provider registry, credential service, health probe, routing, quota/cost và generation service.
- Tách trang danh sách và trang chi tiết Provider thành file độc lập.
- Thêm model resolution contract để Assistant chỉ định primary/fallback.
- Duy trì build gate và xử lý cảnh báo bundle lớn bằng code splitting.

### 5.8. Evaluation

**Điểm tốt**

- Có dataset/test case/run model và threshold rõ.
- Có hook vào workflow publish.

**Cần cải thiện**

- Gọi Assistant runtime thật cho từng golden question.
- Lưu answer, retrieved contexts, citations, model/provider, tokens và latency.
- Dùng Ragas hoặc evaluator được kiểm định thay vì chủ yếu token overlap.
- Tổng hợp metrics từ DB, không trả hằng số.
- Gap Inbox phải được tạo từ các lượt no-answer thực.

### 5.9. Triển khai và vận hành

**Điểm tốt**

- Có compose cho PostgreSQL, Qdrant, Redis, MinIO và Gotenberg.
- Có Dockerfile backend và tài liệu Dokploy.

**Cần cải thiện**

- Repository hiện chỉ có compose hạ tầng local; tài liệu từng nhắc `docker-compose.prod.yml` nhưng file không có trong worktree.
- Chưa thấy CI workflow được commit.
- Cần backup/restore drill cho PostgreSQL, MinIO và Qdrant.
- Health readiness nên kiểm tra thêm Qdrant, MinIO và provider bắt buộc theo deployment profile.
- Cần Prometheus endpoint/dashboard, distributed trace và alert rule thực tế.

---

## 6. So sánh ngắn với qnu-ai-core

Platform đã kế thừa tốt từ Core ở các mặt:

- Node manifests.
- Workflow definitions.
- Taxonomy.
- Khái niệm Assistant/Runtime Profile.
- Control Plane và DAG Canvas.

Nhưng Core vẫn mạnh hơn rõ ở compiler/runtime:

- Trusted compile context.
- API/schema version validation.
- Manifest và port compatibility.
- Permission/connection validation.
- Immutable execution plan và content hash.
- Timeout, retry/backoff, cancellation và deadline.
- Node input schema validation.
- Durable run/attempt trace.

Hướng phù hợp không phải sao chép toàn bộ Core. Nên chọn các invariant quan trọng của Core rồi đưa vào Platform theo thứ tự ưu tiên: immutable plan, security context, port/schema validation, runtime policy và durable attempts.

---

## 7. Lộ trình hoàn thiện đề xuất

### Giai đoạn 0 — Lập lại “nguồn sự thật” của dự án

Mục tiêu: chấm dứt chênh lệch giữa UI, tài liệu và runtime.

- Tối ưu bundle frontend bằng route-level code splitting và manual chunks.
- Gắn nhãn Demo/Live rõ ràng.
- Lập capability matrix cho từng module.
- Cập nhật `PROJECT_CONTEXT` theo ba mức UI / Runtime / Production.
- Không dùng cụm từ “100% hoàn thành” nếu chưa qua acceptance gate production.

### Giai đoạn 1 — Security và Truthfulness Gate

Mục tiêu: hệ thống không trả dữ liệu giả và không để truy cập trái phép.

- Authentication, RBAC và trusted tenant context.
- Secret validation và production fail-fast.
- Gỡ mock business fallback khỏi LiveMode.
- Evaluation gọi runtime thật.
- Metrics và Gap Inbox lấy từ dữ liệu thật.

### Giai đoạn 2 — Hoàn thiện Assistant Runtime

Mục tiêu: cấu hình trên UI phải thực sự điều khiển execution.

- Model primary/fallback resolution.
- Retrieval policy binding.
- Tool allowlist và approval policy.
- Guardrail policy enforcement.
- SSE streaming thật.
- Cost/quota/audit gắn với assistant revision.

### Giai đoạn 3 — Nâng DAG Runtime lên Production

Mục tiêu: run có tính lặp lại, chịu lỗi và kiểm toán được.

- Immutable execution plan.
- Resume theo exact version.
- Port/schema validation.
- Timeout, retry/backoff, cancellation.
- Permission/connection validation.
- Idempotency cho side effects.
- Node attempts và run detail API.

### Giai đoạn 4 — Hoàn thiện dữ liệu 5 Assistant

Mục tiêu: mỗi Assistant có dữ liệu chính thức đủ để trả lời.

- Nạp tài liệu chính thức cho Admissions, Regulations và Library.
- Chuẩn hóa version/effective date/provenance.
- Structured facts cho học phí, điểm chuẩn, chỉ tiêu và thời hạn.
- Golden dataset tối thiểu 50 câu/Assistant.
- Đánh giá retrieval và generation trên dữ liệu thật.

### Giai đoạn 5 — Production Operations

Mục tiêu: có thể triển khai, quan sát và phục hồi an toàn.

- CI bắt buộc Ruff/Pytest/Biome/TypeScript/Build/E2E critical path.
- Alembic-only production migration.
- Backup/restore drill.
- Metrics, tracing, alerting.
- Load test và chaos test provider/Qdrant/Redis.
- Runbook sự cố và rollback.

---

## 8. Acceptance Gate đề xuất trước khi gọi là production-ready

Một phiên bản chỉ nên được gắn nhãn production khi đáp ứng toàn bộ:

- [ ] Không có dữ liệu nghiệp vụ mock trong LiveMode.
- [ ] Tất cả endpoint thay đổi dữ liệu có auth và permission.
- [ ] Tenant/workspace được lấy từ identity đáng tin cậy.
- [ ] Không có secret mặc định nguy hiểm ở production.
- [ ] 5 Assistant có collection thật, tài liệu approved, chunks và vector.
- [ ] Assistant primary/fallback model điều khiển được ModelOps runtime.
- [ ] Tool Gateway enforce allowlist và HITL.
- [ ] RAG gọi generation thật hoặc được công bố rõ là extractive answer.
- [ ] TM-08 chạy trên câu trả lời và contexts thật.
- [ ] Workflow run và resume khóa vào immutable version.
- [ ] DAG có timeout, retry, cancellation và idempotency.
- [ ] Backend full suite, frontend lint/typecheck/build đều pass.
- [ ] E2E critical path chạy với backend thật và không dựa mock.
- [ ] Migration, backup và restore đã được thử nghiệm.
- [ ] Monitoring/alerting đủ phát hiện DB, Redis, Qdrant, MinIO và provider failure.

---

## 9. Thứ tự xử lý khuyến nghị

Nếu chỉ chọn 10 việc để làm tiếp, nên ưu tiên:

1. Tách DemoMode/LiveMode và tắt business mock fallback trong LiveMode.
2. Thay Evaluation mô phỏng bằng execution thật.
3. Áp authentication/RBAC/tenant isolation lên router.
4. Nối Assistant primary/fallback model xuống ModelOps.
5. Nối RAG Answer Composer với ModelOps và citation/no-answer gate.
6. Khóa Workflow run/resume vào immutable WorkflowVersion.
7. Bổ sung timeout/retry/cancel/schema/permission cho DAG.
8. Nạp dữ liệu chính thức cho ba collection đang rỗng.
9. Tách các file 1.000–3.000 dòng thành module/component có một trách nhiệm.
10. Tối ưu bundle frontend và bổ sung CI production build bắt buộc.

---

## 10. Nhận xét cuối cùng

Dự án có tiềm năng tốt và đã tích lũy được nhiều thành phần khó: OCR, ingestion, UI kiểm tra tài liệu, workflow control plane, provider adapters và hệ thống quản trị khá hoàn chỉnh. Điểm cần thay đổi lúc này không phải tiếp tục thêm nhiều màn hình, mà là **thu hẹp khoảng cách giữa điều hệ thống tuyên bố và điều runtime thực sự bảo đảm**.

Giai đoạn tiếp theo nên ưu tiên theo nguyên tắc:

> Dữ liệu thật trước, runtime invariant tiếp theo, bảo mật và kiểm toán sau đó; UI mới chỉ được mở rộng khi luồng bên dưới đã có acceptance test thật.

Nếu làm theo thứ tự này, Platform có thể tiến từ một Internal Beta giàu tính năng sang một nền tảng AI nội bộ đáng tin cậy mà không cần viết lại toàn bộ kiến trúc.
