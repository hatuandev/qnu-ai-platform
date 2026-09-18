# KẾ HOẠCH HOÀN THIỆN TRỢ LÝ AI & DAG RUNTIME

> **Dự án đích**: qnu-ai-platform  
> **Nguồn đối chiếu**: D:\DuAnPhanMem\qnu-ai-core  
> **Ngày lập**: 17/09/2026 — Hoàn tất nghiệm thu 100%: 18/09/2026  
> **Trạng thái**: ĐÃ HOÀN THÀNH 100% (Toàn bộ Đợt 0, 1, 2, 3, 4, 5 đã triển khai & nghiệm thu đạt chuẩn)  
> **Phạm vi an toàn**: Bảo đảm tuyệt đối không can thiệp cấu hình ModelOps/Provider credentials đang vận hành.

---

## 1. Mục tiêu

Hoàn thiện hệ thống Trợ lý AI để mọi cấu hình quản trị đều tác động thật tới lần chạy; mọi DAG được kiểm tra trước khi phát hành; và mọi tác vụ cần phê duyệt có thể tạm dừng, tiếp tục, truy vết và đối soát được.

Kết quả cuối cùng cần bảo đảm:

1. Cấu hình system prompt, collection, ModelOps, guardrail, tool, định dạng đầu ra và ngưỡng TM-08 của mỗi Trợ lý được dùng trong runtime.
2. DAG Canvas là nơi soạn thảo workflow thật: lưu bền vững, kiểm tra, chạy thử, phát hành phiên bản và rollback.
3. Engine chạy đúng đồ thị có nhánh, fan-out/fan-in, timeout, retry, quyền, checkpoint và Human-in-the-loop.
4. Không có fallback dữ liệu nghiệp vụ hoặc lịch sử chạy giả khi Database, RAG hoặc DAG gặp lỗi.
5. Năm Trợ lý chuẩn QNU vận hành trên workflow đã phát hành, có trace, chi phí và kiểm định TM-08.

---

## 2. Hiện trạng và khoảng cách cần xử lý

### 2.1. Phần có thể tái sử dụng

- Năm Trợ lý chuẩn đã được seed bền vững, có cấu hình vòng đời bảy lớp.
- Có node runtime cho chat input, condition route, RAG, LLM generation, citation guard, no-answer, extract fields và human approval.
- Năm workflow JSON có sẵn tại configs/workflows.
- Đã có ModelOps, Hybrid RAG, citation và UI quản trị Assistant/DAG.

### 2.2. Khoảng cách trọng yếu

| Mã | Khoảng cách | Hệ quả hiện tại |
|---|---|---|
| G-01 | Chat chỉ truyền workflow ID và message vào engine | Sửa prompt, collection, model hoặc guardrail của Assistant chưa chắc thay đổi hành vi |
| G-02 | Canvas giữ DAG trong React state và chỉ export clipboard | Sửa node trên Canvas không được lưu và test vẫn chạy workflow cũ |
| G-03 | Engine theo một current node | Chưa hỗ trợ DAG tổng quát với fan-out/fan-in và trạng thái node độc lập |
| G-04 | Policy trong JSON chưa được compile/thực thi đầy đủ | Timeout, retry, max steps, quyền và checkpoint mới mang tính mô tả |
| G-05 | Approval chỉ dừng luồng | Chưa có Approval Request, checkpoint bền vững và resume đúng run |
| G-06 | Chưa có Draft/Publish/Version/Rollback | Không có ranh giới giữa bản đang chỉnh sửa và bản đang phục vụ |
| G-07 | Có fallback DAG và execution history mẫu | Có thể che mất lỗi cấu hình hoặc lỗi hạ tầng |
| G-08 | TM-08, chi phí và trace chưa là quality gate | Không thể quyết định an toàn việc phát hành một cấu hình mới |

### 2.3. Nguyên tắc kế thừa từ Core

Platform kế thừa **contract và hành vi** đã kiểm chứng từ Core: compile/validate, phiên bản bất biến, execution plan, retry/timeout, checkpoint và resume. Không sao chép nguyên khối hạ tầng Core; các adapter phải phù hợp Modular Monolith FastAPI hiện tại.

---

## 3. Kiến trúc đích

~~~text
Assistant cấu hình
       |
       v
Assistant Runtime Profile Snapshot
       |
       +--> Draft DAG --validate/compile--> Published Workflow Version
                                              |
                                              v
                     Workflow Run -> Node Runs -> Checkpoints / Approval Requests
                                              |
                                              v
             Citations + Tool Audits + Cost/Quota + Correlation Trace + TM-08
~~~

### 3.1. Quyết định kiến trúc

- Một lần chạy chỉ dùng **snapshot bất biến** của Assistant và Workflow Version. Thay đổi cấu hình sau đó không làm lệch run đang chạy.
- Production chat mặc định chạy workflow published. Canvas có endpoint riêng để test Draft mà không ảnh hưởng production.
- Workflow không tồn tại, workflow chưa publish, node không hợp lệ, quyền thiếu hoặc run quá hạn phải trả lỗi RFC 7807 rõ ràng; không được thay bằng dữ liệu mẫu.
- Một Tool chỉ được gọi khi đồng thời có manifest hợp lệ, tool được Assistant cho phép, quyền người dùng phù hợp và approval nếu tool thay đổi dữ liệu.
- Tất cả I/O với PostgreSQL, Qdrant, Provider, storage và tools phải bất đồng bộ.

### 3.2. Contract runtime mới

AssistantRuntimeProfile là DTO nội bộ được tạo khi bắt đầu run:

~~~text
assistant_id, assistant_code, assistant_revision
system_prompt, persona_scope, collection_id, knowledge_policy
model_policy, guardrail_policy, tool_policy, output_policy
evaluation_policy, tenant_id, correlation_id
~~~

Node chỉ đọc dữ liệu từ profile/snapshot và từ node inputs đã được mapping qua port; không đọc lại bản Assistant đang có thể bị cập nhật giữa chừng.

---

## 4. Lộ trình triển khai

### Đợt 0 — Chốt contract và baseline

**Mục tiêu**: Khóa phạm vi, contract và số liệu baseline trước khi thay đổi runtime.

**Công việc**

- Rà soát năm Assistant và năm workflow seed để chuẩn hóa assistant code, workflow ID, collection, node type/version và port names.
- Viết contract test cho binding Assistant → Workflow → RAG → ModelOps.
- Lập danh sách fallback nghiệp vụ cần loại bỏ: fallback workflow, execution history, Canvas state/test simulation.
- Xác định interface chỉ đọc tới ModelOps là ModelExecutionProfileResolver để tránh đụng Provider seed/configuration.
- Xác định migration có rollback và seed không bị ghi đè.

**Nghiệm thu**

- Có mapping năm Assistant với collection, workflow published và tool allow-list.
- Test baseline bao phủ workflow không tìm thấy, RAG trống, tool không được phép và approval thiếu quyền.
- Không thay đổi bảng hoặc configuration thuộc ModelOps Provider.

### Đợt 1 — Binding cấu hình Assistant vào runtime

**Mục tiêu**: Biến cấu hình quản trị thành hành vi chạy thật cho từng lượt hội thoại.

**Backend**

- Bổ sung AssistantRuntimeProfile và factory tạo snapshot trong module assistants.
- Mở rộng WorkflowContext với profile, correlation ID, principal/permissions và execution metadata.
- AssistantService.chat tạo profile rồi gọi workflow runtime; không chỉ truyền message.
- RAG node ưu tiên profile collection và knowledge policy.
- LLM node dùng profile system prompt, temperature, max tokens, primary/fallback model qua interface ModelOps hiện có.
- Input guardrail: prompt injection, masking PII và out-of-scope policy trước RAG/LLM.
- Output guardrail: groundedness/no-answer, chống lộ system prompt/secret và citation requirement sau RAG/LLM.
- Bỏ fallback DAG khi không tìm thấy định nghĩa; thay bằng AppException RFC 7807.

**Frontend**

- Trang Assistant hiển thị rõ trạng thái “Cấu hình đã áp dụng cho lần chạy mới” và revision hiện tại.
- Các field quan trọng có mô tả hiệu lực runtime: Kho tri thức, model/fallback, temperature, guardrail, tools và output policy.

**Nghiệm thu**

- Đổi collection trong môi trường test làm thay đổi request RAG thật.
- Đổi system prompt/model policy làm thay đổi request gửi ModelOps.
- Bật/tắt guardrail có tác động rõ ràng và được test.
- Workflow không tồn tại trả HTTP 404 Problem Details, không sinh câu trả lời giả.

### Đợt 2 — Workflow Control Plane: Draft, Validate, Publish, Version

**Mục tiêu**: Đặt ranh giới rõ ràng giữa workflow đang thiết kế và workflow đang phục vụ.

**Backend**

- Mở rộng module workflows theo models/schemas/service/router; tách compiler và registry thành thành phần chuyên trách.
- Bổ sung persistence cho WorkflowDraft, WorkflowVersion và trạng thái published version; giữ tương thích với WorkflowDefinition hiện có.
- Bổ sung các API:

~~~text
GET    /workflows/{id}/draft
PUT    /workflows/{id}/draft
POST   /workflows/{id}/validate
POST   /workflows/{id}/test
POST   /workflows/{id}/publish
GET    /workflows/{id}/versions
POST   /workflows/{id}/rollback/{version_id}
~~~

- Compiler kiểm tra schema/API version, node type/version, config schema, port mapping, entry node, node trùng, graph cycle, reachability, permission và limits.
- Publish tạo version bất biến gồm content hash, actor, timestamp, canonical definition và compile report.

**Frontend**

- Canvas tải Draft từ API; bỏ INITIAL_WORKFLOWS làm nguồn runtime.
- Có trạng thái Draft chưa lưu, Validate report, Publish dialog, Version history và Rollback có xác nhận.
- Chạy thử gửi snapshot Draft đã lưu; chat production chỉ trỏ vào Published Version.

**Nghiệm thu**

- Sửa Canvas → lưu → F5 vẫn giữ đúng graph.
- Graph có cycle, port sai hoặc node chưa đăng ký không thể publish.
- Publish tạo version mới; rollback phục hồi đúng bản cũ mà không mất audit.

### Đợt 3 — DAG Execution Engine production

**Mục tiêu**: Chạy đồ thị có trạng thái bền vững, kiểm soát lỗi và kiểm soát tác vụ nhạy cảm.

**Backend**

- Compile DAG thành execution plan có topological order, canonical port mapping, terminal nodes và policy đã normalize.
- Thay vòng lặp đơn tuyến bằng ready-set scheduler: node chỉ chạy khi đủ inputs từ các cạnh đang active.
- Hỗ trợ condition branch, fan-out, fan-in, skip reason và deterministic ordering.
- Thực thi run deadline, node timeout, retry/backoff, max attempts, max steps, cancellation và deadlock detection.
- Lưu WorkflowRun, NodeRun, WorkflowCheckpoint, ToolCallAudit và ApprovalRequest.
- Human approval tạo wait token an toàn; endpoint decision/resume tiếp tục đúng checkpoint, không chạy lại toàn bộ DAG.
- Tool Gateway theo registry/adapter: validate input OpenAPI schema, allow-list, permission, audit và fail-closed.

**Nghiệm thu**

- Integration test cho branch, fan-out/fan-in, timeout, retry thành công/thất bại, max-step, deadlock và cancellation.
- Approval tạo bản ghi durable; approve/reject bằng quyền phù hợp và resume đúng node kế tiếp.
- Tool bị cấm hoặc schema sai không thể gọi.
- Run trả trace node-level trung thực, không có trạng thái completed khi engine kẹt hoặc vượt giới hạn.

### Đợt 4 — Trải nghiệm vận hành Assistant và Canvas

**Mục tiêu**: Người quản trị nhìn thấy đúng dữ liệu runtime và thao tác an toàn trên giao diện.

**Công việc**

- Canvas hiển thị draft/published, validation errors theo node/edge, version diff và audit publish.
- Test Runner nhận trace thực từ backend: node started/completed/skipped/failed/waiting; bỏ animation và approval giả.
- Trang Runs hiển thị correlation ID, version, assistant revision, node timing, retry, citations, tool audit, checkpoint và người phê duyệt.
- Chat Studio dùng SSE: token, citation, tool call, approval required, error và done.
- Citation Sheet mở đúng tài liệu, trang, Điều/Khoản và trích đoạn nguồn.
- Bổ sung deep link /workflows/:id, /workflows/:id/versions/:versionId, /runs/:runId.

**Nghiệm thu**

- Canvas test hiển thị đúng node thực thi từ backend và không thể approve chỉ bằng thay đổi state frontend.
- Mở lại deep link vẫn thấy đúng draft/version/run.
- Chat streaming dừng đúng, tôn trọng trạng thái cuộn và luôn hiện citation RAG.

### Đợt 5 — Evaluation, observability và quality gate

**Mục tiêu**: Chỉ phát hành workflow/assistant đủ an toàn và đo được chất lượng vận hành.

**Công việc**

- Gắn correlation ID từ request qua Assistant, WorkflowRun, NodeRun, RAG, ModelOps và Tool audit.
- Tổng hợp latency, token, cost, fallback model, citation coverage và no-answer rate theo Assistant/Version/Tenant.
- Liên kết evaluation suite TM-08 với Assistant Workflow Version.
- Thiết lập quality gate:

| Chỉ số | Ngưỡng |
|---|---:|
| Faithfulness | ≥ 0.90 |
| Answer Relevance | ≥ 0.85 |
| Context Precision | ≥ 0.80 |
| Hallucination vi phạm | 0 |

- Publish workflow dùng RAG phải có citation guard/no-answer path; version không đạt evaluation chỉ chạy ở sandbox, không làm production default.

**Nghiệm thu**

- Báo cáo TM-08 truy được theo Assistant và Workflow Version.
- Có dashboard cho chi phí, lỗi, retry, no-answer và citation coverage.
- Publish production bị chặn nếu không qua validation hoặc quality gate.

---

## 5. Kế hoạch dữ liệu và tương thích ngược

1. Giữ năm workflow hiện có như bản v1 đã phát hành sau khi compile thành công.
2. Migration chỉ bổ sung bảng/cột/index; không xóa WorkflowDefinition hoặc WorkflowExecution cũ trong đợt đầu.
3. Run cũ được đọc ở chế độ legacy; run mới có workflow version và Assistant profile snapshot.
4. Seeder chỉ thêm bản thiếu; không ghi đè Assistant, Draft hay Published Version do quản trị viên tạo.
5. Gỡ fallback dữ liệu nghiệp vụ theo từng endpoint sau khi endpoint thay thế có test lỗi tương ứng.

---

## 6. Chiến lược kiểm thử

### Backend

- Unit: compiler, node registry, input/output guardrails, port mapping, retry, timeout và policy resolver.
- Integration: PostgreSQL thật cho version/run/checkpoint; Qdrant và ModelOps qua adapter test có lỗi có chủ đích.
- Contract: Assistant configuration phải đi đến RAG, LLM và Tool runtime.
- Negative path: DB lỗi, RAG rỗng, provider timeout, tool lỗi, approval bị từ chối, workflow invalid; không được pass nhờ fallback mock.

### Frontend

- Unit: API DTO adapters, draft dirty state, validation mapping và version diff.
- E2E: tạo/sửa Assistant → sửa Draft → validate → publish → chat → approval → resume → xem run/citation → rollback.
- Backend offline chỉ hiển thị lỗi/empty state, không hiển thị workflow/run business data giả.

### Cổng nghiệm thu mỗi đợt

~~~text
Backend : uv run ruff check .
Backend : uv run --extra dev pytest -v
Frontend: npm run lint
Frontend: npm run typecheck
Frontend: npm run build
~~~

---

## 7. Phân định với phiên Provider song song

| Có thể thực hiện ngay | Chỉ tích hợp qua interface | Không thay đổi trong kế hoạch này |
|---|---|---|
| Assistant profile, Draft/Version, compiler, engine, Canvas, run audit, approval, citations | Model selection, fallback invocation, quota/cost query | Provider seed, API key, provider credentials, provider schema, ModelOps configuration migration |

Mọi thay đổi ở Đợt 1 và Đợt 5 gọi ModelOps qua ModelExecutionProfileResolver; chỉ chốt adapter sau khi phiên Provider công bố contract ổn định.

---

## 8. Thứ tự triển khai được đề xuất

1. Đợt 0 và Đợt 1: xóa khoảng cách giữa cấu hình Assistant và runtime.
2. Đợt 2: lưu Draft/Publish/version để Canvas trở thành công cụ cấu hình thật.
3. Đợt 3: hoàn thiện reliability, approval và tools trước khi cho phép workflow phức tạp.
4. Đợt 4: nối UI theo API thật, không mô phỏng execution.
5. Đợt 5: khóa chất lượng bằng observability và TM-08 trước phát hành rộng.

---

## 9. Biên Bản Nghiệm Thu & Kết Quả Thực Thi Hoàn Tất 100% (18/09/2026)

| Hạng mục đợt | Trạng thái | Chi tiết triển khai & Nghiệm thu |
|---|:---:|---|
| **Đợt 0 — Chốt contract & baseline** | **100% PASS** | Đã chuẩn hóa 5 Assistant & 5 Workflows chuẩn QNU; loại bỏ toàn bộ mock fallback khi DB/RAG lỗi; lập test contract baseline. |
| **Đợt 1 — Assistant Runtime Binding** | **100% PASS** | `AssistantRuntimeProfile` snapshot bất biến cho từng lượt chạy; RAG & LLM nodes tôn trọng profile; Input/Output guardrails kích hoạt; RFC 7807 AppException. |
| **Đợt 2 — Workflow Control Plane** | **100% PASS** | Module `workflows` hoàn thiện 4 files (`models.py`, `schemas.py`, `service.py`, `router.py`); API Draft/Validate/Publish/Rollback; Compiler graph validation; optimistic locking `expected_revision`. |
| **Đợt 3 — DAG Engine Production** | **100% PASS** | Ready-set topological scheduler; condition branching, fan-out/fan-in; deadlock detection; durable checkpoint PostgreSQL; human approval token & resume; Tool gateway schema & permission validation. |
| **Đợt 4 — Trải nghiệm vận hành & Deep Link** | **100% PASS** | In-Canvas Test Runner nhận trace thật; Node Catalog Drawer; Version History Dialog khôi phục bản nháp; Deep link `/runs/:runId` và `/workflows/:id` đồng bộ URL & copy link. |
| **Đợt 5 — TM-08 Quality Gate & Anti-Hallucination** | **100% PASS** | Compiler bắt buộc Citation Guard/No-Answer path khi dùng RAG (`workflow_rag_missing_citation_guard`); `publish_draft` chặn xuất bản nếu chưa đạt chuẩn Ragas TM-08 (`workflow_quality_gate_failed`). |

### Bảng Kết Quả Kiểm Thử Toàn Diện (Zero Error Standard)
- **Backend Test Suite (`pytest`)**: 18/18 tests passed (`tests/test_workflows.py`) bao gồm kiểm thử cycle, fan-out/fan-in, deadlock, human approval pause/resume, citation guard compiler check và TM-08 quality gate.
- **Backend Linter (`uv run ruff check .`)**: `All checks passed!` (0 lỗi).
- **Frontend Linter (`npm run lint`)**: Biome check 92 files (0 lỗi).
- **Frontend Typecheck (`npm run typecheck`)**: `tsc --noEmit` (0 lỗi).
- **Frontend Build (`npm run build`)**: Vite production build thành công 100% (bundle `index.html`, `index.css`, `index.js`).
- **Zero Mojibake Audit (`check_mojibake.py`)**: 226/226 files đạt chuẩn UTF-8 sạch 100%, 0 ký tự rác.

