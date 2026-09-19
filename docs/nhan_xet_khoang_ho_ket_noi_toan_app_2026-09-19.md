# NHẬN XÉT CÁC KHOẢNG HỞ KẾT NỐI TOÀN ỨNG DỤNG QNU AI PLATFORM

**Ngày rà soát:** 19/09/2026

**Phạm vi:** Frontend ↔ Backend API ↔ PostgreSQL/Redis/Qdrant/Storage ↔ Model Provider ↔ Workflow DAG ↔ Tools ↔ Evaluation

**Hình thức:** Rà soát tĩnh toàn bộ mã nguồn và đối chiếu contract. Không sửa mã runtime trong phiên này.

**Giới hạn kiểm chứng:** Tại thời điểm rà soát, `localhost:3001` và `localhost:8001` đều không hoạt động, vì vậy chưa thực hiện được kiểm thử E2E trực tiếp trên giao diện và API.

---

## 1. Kết luận điều hành

QNU AI Platform hiện **không thiếu phân hệ**. Dự án đã có gần đủ các khối quan trọng: Kho tri thức, OCR, Hybrid RAG, Trợ lý AI, ModelOps, Workflow DAG, Node Catalog, Tools, Hội thoại/Handoff và Evaluation. Một số đường nối đã làm tốt, đặc biệt là CRUD chính, version workflow, snapshot runtime, storage-first khi nạp tài liệu, cache invalidation và sự tương ứng giữa 13 node manifest với runtime handler.

Tuy nhiên, toàn hệ thống vẫn có một vấn đề kiến trúc nổi bật:

> Nhiều phân hệ đã tồn tại độc lập nhưng chưa chia sẻ cùng một nguồn sự thật và cùng một chính sách lỗi. Ở một số chỗ, lỗi kết nối được đổi thành “thành công mô phỏng”, khiến người vận hành khó phân biệt hệ thống thật đang chạy hay chỉ đang đi qua fallback.

Ba nhóm cần ưu tiên cao nhất:

1. **Tính trung thực của runtime:** bỏ các nhánh tạo câu trả lời, kết quả OCR, file xuất hoặc vector giả nhưng vẫn báo thành công.
2. **Kết nối control plane:** Trợ lý phải chọn model từ Provider thật; Workflow phải thi hành tool qua Tool Gateway; Knowledge Fact phải tuân theo trạng thái duyệt của tài liệu.
3. **Kết nối vòng đời hội thoại:** Chat Studio/Widget phải tạo conversation thật, tải attachment thật và nhận được phản hồi handoff từ cán bộ.

Nếu chưa xử lý các nhóm này, app có thể trình diễn tốt nhưng chưa đủ tin cậy để vận hành thật trong môi trường trường đại học.

---

## 2. Bản đồ mức độ kết nối hiện tại

| Luồng kết nối | Trạng thái | Nhận xét ngắn |
|---|---|---|
| Frontend ↔ Backend CRUD | **Khá** | Knowledge, Assistants, Workflows, ModelOps đã có API thật; vẫn còn contract lệch và màn hình dùng dữ liệu tĩnh. |
| Password Gate ↔ API Security | **Hở nghiêm trọng** | Giao diện có chặn đăng nhập nhưng các router nghiệp vụ chưa dùng dependency xác thực. |
| Assistant ↔ Provider/ModelOps | **Nối một phần** | Runtime có truyền tên model ở RAG node, nhưng form cấu hình dùng danh sách hardcode và chưa ràng buộc provider/model đang hoạt động. |
| Assistant ↔ Workflow DAG | **Khá** | Có runtime profile, workflow version, snapshot và chạy DAG; generic LLM node chưa tuân theo model policy đầy đủ. |
| Workflow ↔ Node Catalog | **Nối một phần** | 13 manifest có handler, nhưng compiler chưa validate schema/version/status; FE có catalog fallback lỗi thời. |
| Workflow ↔ Tool Gateway/HITL | **Hở nghiêm trọng** | API Caller node gọi tool registry trực tiếp, bỏ qua policy, approval và execution log của ToolService. |
| Knowledge ↔ OCR/Storage | **Khá** | Upload chính theo storage-first; Scan Studio và mock OCR vẫn có đường làm sai provenance. |
| Knowledge ↔ Qdrant/FTS/Facts | **Nối một phần** | Có hybrid retrieval và invalidation; trạng thái duyệt, tenant/workspace và fact lifecycle chưa đồng bộ nguyên tử. |
| Chat Studio/Widget ↔ Conversations | **Đứt nhiều đoạn** | Trợ lý hardcode, attachment chỉ là metadata, chưa ghi message vào conversation, widget gọi sai endpoint. |
| Runtime ↔ Evaluation | **Nối một phần** | Có evaluation run nhưng metric là heuristic proxy, không lưu per-case và có fallback sang một đường RAG khác. |
| Dashboard ↔ Dữ liệu vận hành | **Chưa trung thực hoàn toàn** | Có API thật nhưng quota gọi sai route; nhiều KPI/health có số hoặc trạng thái fallback cố định. |
| Channels/Developer ↔ Backend | **Chủ yếu prototype** | Chưa có persistence/deployment API; API key chỉ tồn tại trong state phía trình duyệt. |

---

## 3. Các khoảng hở P0 — cần xử lý trước khi cho dữ liệu thật chạy qua hệ thống

### P0-01. Password Gate chỉ bảo vệ giao diện, chưa bảo vệ API

**Bằng chứng**

- Frontend chặn UI bằng `isAuthenticated` tại `frontend/src/App.tsx:85` và `frontend/src/App.tsx:286`.
- Backend có `get_current_actor` tại `backend/app/modules/auth/dependencies.py:15`.
- Các router nghiệp vụ hiện chỉ khai báo `Depends(get_db)`; chưa thấy router áp dụng `Depends(get_current_actor)`.
- Toàn bộ router được mount trực tiếp tại `backend/app/main.py:202-214`.

**Tác động**

Người dùng không biết mật khẩu vẫn có thể gọi trực tiếp API để xem/sửa/xóa dữ liệu nếu truy cập được backend. Đây là khoảng hở đúng ngay trong mô hình đăng nhập đơn giản mà dự án đang chọn.

**Khuyến nghị**

- Giữ mô hình một trang mật khẩu, không cần làm RBAC phức tạp.
- Áp dụng dependency xác thực ở cấp router cho toàn bộ API quản trị.
- Chỉ để public các endpoint thật sự cần public: `health`, login/logout và endpoint chat/widget đã giới hạn riêng.
- Cookie `secure=False` tại `backend/app/modules/auth/router.py:54` phải phụ thuộc môi trường.

### P0-02. Secret và API key chưa được bảo vệ đúng nghĩa

**Bằng chứng**

- Có giá trị mặc định chứa password/secret tại `backend/app/core/config.py:48`, `:69`, `:109`, `:112`, `:114`.
- Trường tên `api_key_encrypted` đang được gán trực tiếp từ API key tại `backend/app/modules/modelops/service.py:417`, `:615`, `:699`.
- API danh sách provider trả lại trường `api_key` từ giá trị này tại `backend/app/modules/modelops/service.py:556`.

**Tác động**

API key có thể bị lộ qua response, database dump hoặc log/debug. Tên trường “encrypted” tạo cảm giác an toàn nhưng chưa có bằng chứng về lớp mã hóa/giải mã tương ứng.

**Khuyến nghị**

- Không trả raw key trong bất kỳ response list/detail nào; chỉ trả `masked_key`, `has_key`, `last_four`.
- Mã hóa key trước khi lưu bằng master key từ environment/KMS.
- Loại secret thật khỏi default config; chỉ cho phép placeholder dev vô hại.
- Sau khi sửa, rotate toàn bộ key đã từng lưu hoặc hiển thị.

### P0-03. Nhiều adapter biến lỗi thật thành “kết quả thành công mô phỏng”

**Bằng chứng**

- Các adapter OpenAI, Gemini, Mistral, Cloudflare và Local vLLM có nhánh trả simulated response khi thiếu key hoặc lỗi kết nối: `backend/app/modules/modelops/providers/`.
- `LocalVLLMAdapter` có thể trả fallback success khi exception tại `backend/app/modules/modelops/providers/local_vllm_adapter.py:56`.
- `LLMGenerateNodeHandler` tạo nội dung mẫu “Văn bản sinh ra từ trợ lý QNU...” khi ModelOps lỗi tại `backend/app/modules/workflows/nodes/llm_generate_node.py:54`.
- Frontend Tools trả kết quả/file path giả khi backend lỗi tại `frontend/src/services/tools-api.ts`.
- OCR explicit engine failure rơi về `mock_ocr` tại `backend/app/modules/ocr/service.py:128-140`; mock chứa nội dung văn bản hành chính giống dữ liệu thật tại `backend/app/modules/ocr/adapters/mock_adapter.py`.
- Embedding có fallback deterministic mock tại `backend/app/modules/rag/vector_indexer.py:105-116` và `:160-199`.

**Tác động**

Provider test, Chat, Workflow, OCR, RAG, Tools và Evaluation có thể đồng loạt báo thành công dù dịch vụ thật đang hỏng. Đây là rủi ro lớn nhất đối với tính trung thực của hệ thống.

**Khuyến nghị**

- Chỉ cho phép mock adapter qua dependency injection trong test hoặc chế độ demo có nhãn rõ ràng.
- Production/dev-live phải fail-closed: trả trạng thái `failed` hoặc `degraded`, không tạo nội dung nghiệp vụ giả.
- Không ghi token/cost, không tạo artifact và không đánh dấu index thành công cho dữ liệu mô phỏng.
- Nếu cần fallback thật, fallback phải là provider/engine thật đã cấu hình và có audit trail.

### P0-04. DAG gọi công cụ trực tiếp, bỏ qua Tool Gateway và Human-in-the-loop

**Bằng chứng**

- `backend/app/modules/workflows/nodes/api_caller_node.py` lấy tool từ `tool_registry` rồi gọi `tool.execute(params)` trực tiếp.
- Policy assistant, `requires_approval`, tenant/conversation context và `ToolExecutionLog` nằm trong `backend/app/modules/tools/service.py:77-173`.
- `BaseTool.requires_approval` mặc định là `False` tại `backend/app/modules/tools/builtin/base.py`; chưa thấy tool side-effect override bắt buộc phê duyệt.
- `human_approval_required` của assistant hiện chủ yếu được readiness kiểm tra/cảnh báo tại `backend/app/modules/assistants/readiness.py:285-299`.

**Tác động**

Một workflow có thể chạy tool thay đổi dữ liệu hoặc tạo file mà không qua danh sách tool được cấp, không có phê duyệt và không có log đầy đủ.

**Khuyến nghị**

- API Caller node chỉ được gọi `ToolService.execute_tool(...)`.
- Mọi side-effect tool phải khai báo `requires_approval=True` theo mặc định an toàn.
- Runtime phải truyền `assistant_id`, `tenant_id`, `conversation_id`, `correlation_id` và actor.
- Bổ sung trang Approval Inbox độc lập, không phụ thuộc người dùng đang mở In-Canvas Test Runner.

### P0-05. Structured Facts chưa tuân theo trạng thái duyệt và lưu trữ của tài liệu

**Bằng chứng**

- Fact được lưu ngay trong luồng upload khi tài liệu còn pending tại `backend/app/modules/knowledge/service.py:386-391` và `:544-545`.
- Truy vấn fact tại `backend/app/modules/rag/facts.py:39-45` chỉ lọc theo `collection_id`; không join kiểm tra `Document.status`, `is_active`, tenant hoặc workspace.
- Archive tài liệu tại `backend/app/modules/knowledge/service.py:668-690` không vô hiệu hóa/xóa fact.

**Tác động**

RAG có thể trả học phí, chỉ tiêu, điểm chuẩn hoặc số liệu từ tài liệu chưa được duyệt hay đã lưu trữ. Với dữ liệu tuyển sinh/quy chế, đây là lỗi nghiệp vụ nghiêm trọng.

**Khuyến nghị**

- Fact phải mang `document_id`, tenant/workspace, trạng thái hiệu lực, version và provenance.
- Retrieval chỉ dùng fact từ tài liệu `approved + active`.
- Approve/archive/delete/re-version phải cập nhật fact trong cùng một workflow nhất quán.
- Tốt nhất chỉ publish fact sang facts layer sau bước Human Verification.

### P0-06. Widget nhúng hiện chưa gọi được đúng Assistant API

**Bằng chứng**

- Widget gọi `/assistants/${ASSISTANT_ID}/chat_stream` tại `frontend/public/embed/qnu-chat-widget.js:314`.
- Backend chỉ có `POST /assistants/{reference}/chat` và nhận cờ `stream` tại `backend/app/modules/assistants/router.py:101-129`.
- `API_BASE` mặc định lấy `window.location.origin` của trang đang nhúng tại `frontend/public/embed/qnu-chat-widget.js:20`.
- Mã nhúng sinh từ trang Channels chưa truyền `data-api-base` phù hợp.

**Tác động**

Khi nhúng trên website tuyển sinh hoặc cổng thông tin QNU, widget có thể gọi nhầm domain và luôn nhận 404/CORS error.

**Khuyến nghị**

- Dùng đúng endpoint `/assistants/{reference}/chat` với `stream: true`.
- Bắt buộc cấu hình `data-api-base` hoặc sinh URL tuyệt đối từ deployment config.
- Bổ sung danh sách CORS cho domain QNU được phép và kiểm tra origin chặt chẽ.
- Kiểm thử thật trên một trang khác origin trước khi công bố widget.

---

## 4. Các khoảng hở P1 — làm hệ thống chạy sai cấu hình hoặc mất dấu vận hành

### P1-01. Form Trợ lý AI chưa lấy model từ Quản lý Provider

**Bằng chứng**

- Danh sách model bị hardcode tại `frontend/src/pages/assistant-detail-page.tsx:114-122` và `frontend/src/pages/assistant-create-page.tsx:42-49`.
- ModelOps đã có API provider tại `frontend/src/services/modelops-api.ts:14` và `backend/app/modules/modelops/router.py:98-105`.
- `AssistantModelPolicy` chỉ lưu tên model, chưa lưu provider/model identity ổn định tại `backend/app/modules/assistants/schemas.py:31-35`.

**Tác động**

Model mới thêm ở Quản lý Provider không xuất hiện trong Trợ lý; model đã tắt/xóa vẫn có thể được chọn; tên model trùng giữa provider gây mơ hồ.

**Khuyến nghị**

- Tạo endpoint catalog model dành cho assistant, chỉ trả model có capability chat/completion và provider đang active.
- Lưu `primary_provider_id + primary_model_name` và tương tự cho fallback.
- Khi edit assistant, hiển thị trạng thái “model không còn khả dụng” thay vì âm thầm đổi model.

### P1-02. Fallback model chưa được thực thi đúng chính sách

**Bằng chứng**

- Schema ModelOps có `fallback_model_name` tại `backend/app/modules/modelops/schemas.py:34-36`, nhưng service generate chưa dùng field này làm chuỗi fallback rõ ràng.
- `get_active_providers` có mặc định `only_active=False` tại `backend/app/modules/modelops/service.py:483-490`.
- Generate/stream lấy provider bằng `get_active_providers(db)` tại `backend/app/modules/modelops/service.py:1677` và `:1849`.
- Generic `llm.generate` node không truyền model policy như `rag.answer` node.

**Tác động**

Khi primary lỗi, runtime có thể thử một provider bất kỳ thay vì đúng fallback đã cấu hình; provider inactive cũng có thể lọt vào cascade.

**Khuyến nghị**

- Xây chuỗi deterministic: primary identity → fallback identity → no-answer/error.
- Loại provider inactive từ runtime routing.
- Dùng cùng một resolver model policy cho mọi node sinh nội dung.

### P1-03. Usage/quota của chat streaming chưa đáng tin cậy

**Bằng chứng**

- Assistant service đọc thuộc tính không tồn tại `assistant.preferred_model_name`, sau đó fallback `gpt-4o-mini` tại `backend/app/modules/assistants/service.py:318` và `:442`.
- Assistant service tự ước lượng/ghi usage với provider `qnu_workflow`, trong khi ModelOps non-stream cũng ghi provider/model/token thật tại `backend/app/modules/modelops/service.py:1771-1791`.
- Nhánh streaming tại `backend/app/modules/modelops/service.py:1845-1929` chưa có logic quota/usage tương đương non-stream.

**Tác động**

Có nguy cơ ghi trùng, gán sai model/provider và bỏ sót usage của streaming; dashboard chi phí không phản ánh runtime thật.

**Khuyến nghị**

- Chỉ một tầng chịu trách nhiệm ghi usage: ModelOps adapter boundary.
- Trả `provider_id`, `model_name`, token usage và request ID từ ModelOps về workflow/assistant.
- Streaming phải finalize usage một lần khi stream hoàn tất hoặc bị hủy.

### P1-04. Chat Studio chưa kết nối với danh sách Trợ lý thật

**Bằng chứng**

- `frontend/src/pages/chat-studio-page.tsx` khai báo hằng `ASSISTANTS` gồm 5 trợ lý.
- Trạng thái “Đã kết nối” là nhãn tĩnh.
- Trang chat chưa dùng assistant list/readiness từ backend.

**Tác động**

Tạo trợ lý mới, tắt trợ lý hoặc đổi readiness không phản ánh vào Chat Studio. Người dùng có thể chọn một chatbot không còn sẵn sàng.

**Khuyến nghị**

- Query `/assistants` và chỉ hiện assistant active/readiness phù hợp.
- Deep link bằng assistant code/id; giữ lựa chọn qua URL.
- Hiển thị nguyên nhân unavailable từ readiness report.

### P1-05. Attachment trong Chat Studio mới chỉ là hình thức

**Bằng chứng**

- File được đổi thành metadata và gán `ocrStatus: "completed"` tại `frontend/src/pages/chat-studio-page.tsx:146-164`.
- Request trong `frontend/src/hooks/use-rag-stream.ts:136-141` chỉ gửi message, conversation, tenant và stream; không gửi file hoặc attachment reference.

**Tác động**

Người dùng tưởng trợ lý đã đọc file nhưng backend không nhận nội dung file.

**Khuyến nghị**

- Upload attachment qua storage/ingestion endpoint, nhận `attachment_id` hoặc `document_id`.
- Chỉ báo OCR completed khi job thật hoàn tất.
- Chat request truyền attachment reference và scope retrieval tạm thời rõ ràng.

### P1-06. Chat ↔ Conversation ↔ Handoff chưa thành một vòng kín

**Bằng chứng**

- Chat Studio chưa tạo hoặc truyền `conversationId` ổn định.
- Assistant chat service chưa gọi `conversation_service.record_message`.
- Backend có `/conversations/messages` tại `backend/app/modules/conversations/router.py:81-91`, nhưng chưa thấy đường nối từ chat/widget.
- Cán bộ có thể ghi reply vào conversation, nhưng chat/widget không subscribe/poll để nhận reply đó.

**Tác động**

Màn hình Hội thoại & Handoff không phản ánh đầy đủ hội thoại thực; phản hồi của cán bộ không quay lại người hỏi.

**Khuyến nghị**

- Tạo conversation ngay tin nhắn đầu tiên và ghi cả user/assistant/tool/handoff message.
- Dùng SSE/WebSocket hoặc polling có cursor để trả staff reply về đúng client.
- Handoff giữ cùng correlation/conversation ID xuyên suốt.

### P1-07. Node Catalog chưa phải contract runtime bắt buộc

**Bằng chứng**

- Compiler chủ yếu kiểm tra node type trong registry, hình dạng DAG và max steps tại `backend/app/modules/workflows/compiler.py`.
- Chưa validate config theo `config_schema`, version và status trong manifest.
- FE fallback sang catalog tĩnh tại `frontend/src/components/admin/node-catalog-drawer.tsx:54-143` và `:159-178`.
- Catalog tĩnh có `core.llm.generate` tại `:89`, trong khi runtime registry không có type này.
- Khi thả node, canvas khởi tạo `workflowConfig: {}` tại `frontend/src/pages/dag-canvas-page.tsx:405-424`.

**Tác động**

UI cho phép tạo node mà publish/runtime không hiểu; thiếu required config chỉ phát hiện muộn; node experimental không được phân biệt rõ.

**Khuyến nghị**

- Backend validate JSON Schema tại save/publish/run.
- FE render property form trực tiếp từ schema và dùng default từ manifest.
- Khi API catalog lỗi, hiển thị lỗi rõ; không dùng catalog lỗi thời cho thao tác publish.
- Chặn hoặc gắn cờ experimental theo môi trường.

### P1-08. Property Inspector hiển thị cấu hình không phản ánh config thực

**Bằng chứng**

- Visual tab trong `frontend/src/components/admin/property-inspector.tsx` có các giá trị mô tả cứng như Top K/RRF, trong khi config thật chủ yếu sửa qua JSON editor.

**Tác động**

Người dùng có thể tin rằng đã cấu hình node nhưng payload DAG không đổi.

**Khuyến nghị**

- Mọi control phải bind hai chiều với `workflowConfig`.
- Dùng schema-driven form; JSON editor chỉ là chế độ nâng cao và cùng một nguồn state.

### P1-09. Approve tài liệu và index Qdrant chưa nguyên tử

**Bằng chứng**

- Tài liệu được chuyển `approved` và commit tại `backend/app/modules/knowledge/service.py:1421-1423`.
- Qdrant indexing diễn ra sau đó tại `:1434-1448`.
- Vector indexer bắt exception và trả `0` tại `backend/app/modules/rag/vector_indexer.py:246-253`.

**Tác động**

Tài liệu có thể hiển thị approved nhưng không có vector; người vận hành không biết retrieval đang thiếu dữ liệu.

**Khuyến nghị**

- Dùng trạng thái `approved_pending_index`, `indexed`, `index_failed` hoặc outbox/job có retry.
- Chỉ công bố tài liệu retrievable khi cả lifecycle và index state đạt yêu cầu.
- Không nuốt lỗi Qdrant thành `0` mà thiếu trạng thái degraded.

### P1-10. Job ingestion báo hoàn tất trước khi dữ liệu có thể truy xuất

**Bằng chứng**

- Upload tạo JobRecord `completed` và gán `points_reindexed = chunk_count` tại `backend/app/modules/knowledge/service.py:547-565`, dù tài liệu còn chờ duyệt và chưa index.
- Startup backfill cũng có logic tương tự tại `:1510-1540`.

**Tác động**

UI và dashboard báo hoàn tất trong khi Qdrant chưa có point.

**Khuyến nghị**

- Tách job `extract/chunk` khỏi job `approve/index`.
- Chỉ dùng `points_reindexed` từ kết quả Qdrant thật.
- Hiển thị rõ các mốc: stored → extracted → verified → approved → indexed.

### P1-11. Tenant/workspace chưa được truyền nhất quán vào vector index và retrieval

**Bằng chứng**

- Chunks gửi đi index từ approve chưa mang tenant/workspace tại `backend/app/modules/knowledge/service.py:1437-1445`.
- Vector indexer dùng mặc định `tenant_qnu`/`workspace_qnu` tại `backend/app/modules/rag/vector_indexer.py:222-234`.
- RAG request/cache/retrieval chủ yếu mang tenant, chưa nhất quán workspace.

**Tác động**

Khi mở rộng nhiều workspace/tenant, vector có thể không được tìm thấy hoặc bị lọc sai.

**Khuyến nghị**

- Bắt buộc tenant/workspace/document lifecycle trong Qdrant payload.
- Dùng một `RetrievalScope` xuyên suốt upload, index, cache, sparse và dense retrieval.
- Thêm integration test hai tenant có cùng câu hỏi nhưng dữ liệu khác nhau.

### P1-12. Xóa/archive chưa đảm bảo dọn sạch cả DB, Qdrant và Storage

**Bằng chứng**

- Xóa collection tại `backend/app/modules/knowledge/service.py:441-472` chưa dọn original objects tương ứng.
- Một số nhánh xóa/archive tiếp tục cập nhật DB khi Qdrant delete thất bại.

**Tác động**

Có thể còn file mồ côi trong S3/local hoặc vector “ma” vẫn được retrieve sau khi tài liệu đã archive/delete.

**Khuyến nghị**

- Dùng cleanup job idempotent với trạng thái từng driver.
- Retrieval nên đối chiếu lifecycle hoặc payload version để giảm nguy cơ stale vector.
- Có reconciliation job định kỳ giữa DB ↔ Qdrant ↔ Storage.

### P1-13. Evaluation chưa đo đúng toàn bộ đường chạy Assistant

**Bằng chứng**

- UI chạy cứng assistant/dataset tuyển sinh và sample size 5 tại `frontend/src/pages/evaluation-page.tsx:89-91`.
- Evaluator hiện là lexical heuristic tự viết tại `backend/app/modules/evaluation/evaluator.py`, chưa có dependency `ragas` trong `backend/pyproject.toml`.
- Khi assistant chat lỗi, evaluation fallback sang RAG với collection đoán `col_{assistant_code}` tại `backend/app/modules/evaluation/service.py:114-128`.
- Kết quả per-case chưa được persist đầy đủ dù có response model tương ứng.

**Tác động**

Điểm “Ragas TM-08” có thể không đại diện cho cấu hình assistant/DAG/provider thật; khó truy nguyên câu nào làm điểm giảm.

**Khuyến nghị**

- Hoặc tích hợp Ragas thật, hoặc đổi tên minh bạch thành “TM-08 heuristic proxy”.
- Không fallback sang pipeline khác khi đang đánh giá assistant; runtime lỗi phải là kết quả lỗi.
- Lưu từng case: input, expected, answer, contexts, citations, provider/model, latency, token và error.

### P1-14. Dashboard và quota đang có contract sai hoặc số liệu fallback

**Bằng chứng**

- FE gọi `/models/quota?tenant_id=...` tại `frontend/src/services/modelops-api.ts:305`.
- Backend cung cấp `/modelops/quotas/{tenant_id}` tại `backend/app/modules/modelops/router.py:284-308`.
- Dashboard fallback faithfulness `0.942`, collection count `5` tại `frontend/src/pages/dashboard-page.tsx:72-73`.
- Health client gọi `/health/live` rồi suy diễn dependency connected; backend đã có `/health/ready` phù hợp hơn.

**Tác động**

Quota có thể không tải; dashboard vẫn trông “xanh” khi Redis/PostgreSQL/Qdrant/provider không sẵn sàng.

**Khuyến nghị**

- Sửa route quota theo một contract duy nhất.
- Không dùng số nghiệp vụ mặc định khi API lỗi; hiển thị unavailable/degraded.
- Dashboard dùng readiness tổng hợp và ghi rõ nguồn/thời điểm dữ liệu.

---

## 5. Các khoảng hở P2 — nên xử lý để app dễ vận hành và mở rộng

### P2-01. Channels mới là màn hình cấu hình cục bộ

Danh sách assistant/widget config trong `frontend/src/pages/channels-page.tsx` còn hardcode, chưa có model/API lưu channel, domain allowlist, deployment version hoặc trạng thái health. Nên xây Channel entity riêng hoặc ghi rõ đây là trang prototype.

### P2-02. Developer/API Keys mới là mô phỏng phía trình duyệt

`frontend/src/pages/developer-page.tsx` chứa API key tĩnh và create/revoke chỉ sửa local state; code sample dùng bearer key `qnu_live_*` trong khi backend không có API-key authentication tương ứng. Không nên hiển thị tuyên bố mã hóa AES-256 nếu chưa có backend quản lý key thật.

### P2-03. Admission Score tool chứa dữ liệu nghiệp vụ hardcode

`backend/app/modules/tools/builtin/admission_score_tool.py` chứa điểm/chỉ tiêu trực tiếp trong code. Nên truy vấn Structured Facts đã duyệt hoặc hệ thống UIS có cache/version, tránh phải deploy code để cập nhật số liệu tuyển sinh.

### P2-04. Exam exporter chưa dùng Storage Driver chung

`backend/app/modules/tools/builtin/exam_matrix_tool.py` ghi trực tiếp vào local artifacts. Cần dùng storage abstraction để tuân theo dual-driver Local/S3 và trả artifact reference có thời hạn.

### P2-05. Scan Studio lưu bản Markdown dẫn xuất nhưng thiếu provenance file gốc

Luồng Save của `frontend/src/pages/scan-studio-page.tsx` tạo file Markdown rồi upload. Cần liên kết rõ original object, engine/version, extracted artifact và verified revision để có thể audit ngược.

### P2-06. Sparse fallback chưa áp dụng scope đồng nhất

FTS path có join/filter tenant; ILIKE fallback trong `backend/app/modules/rag/retriever.py` chưa áp dụng tenant theo cùng một cách. Cần dùng chung builder scope cho mọi nhánh retrieval.

### P2-07. Collection inactive chưa được chặn nhất quán ở RAG

`is_active` có trên collection nhưng retrieval/ask chưa luôn kiểm tra. Collection tắt nên không được dùng bởi assistant mới; trường hợp assistant đang bind collection tắt cần readiness báo lỗi rõ.

### P2-08. Trang Runs chưa phải nơi xử lý approval vận hành

Backend có pending approvals và In-Canvas Test Runner có nút quyết định, nhưng trang `/runs` chủ yếu hiển thị trạng thái. Cần bổ sung thao tác approve/reject, nội dung yêu cầu, actor, timeout và audit log tại một màn hình vận hành độc lập.

---

## 6. Những phần đã kết nối tốt, nên giữ nguyên hướng kiến trúc

1. **Router coverage đầy đủ:** 13 nhóm router chính được mount trong `backend/app/main.py:202-214`.
2. **Node manifest/runtime parity:** 13 type trong `configs/nodes/*.json` đều có runtime handler tương ứng.
3. **Workflow versioning:** Có draft/publish/version/snapshot/checkpoint; đây là nền tảng đúng cho control plane trợ lý.
4. **Assistant runtime profile:** Việc snapshot cấu hình giúp truy vết phiên chạy tốt hơn chỉ đọc cấu hình mutable hiện tại.
5. **Knowledge storage-first:** Luồng upload chính lưu object trước khi bóc tách; hướng thiết kế phù hợp MinIO/Local dual driver.
6. **Hybrid RAG:** Dense + sparse + fusion/reranking và semantic cache đã có cấu trúc tốt.
7. **Cache invalidation:** Approve/archive/delete đã có ý thức invalidation, chỉ cần hoàn thiện tính nguyên tử và trạng thái lỗi.
8. **Frontend service separation:** Nhiều page đã tách API service/TanStack Query thay vì nhồi fetch vào UI.

Những điểm này cho thấy dự án không cần viết lại. Hướng phù hợp là **siết contract và nối kín lifecycle**, không thay đổi toàn bộ cấu trúc.

---

## 7. Lộ trình khắc phục đề xuất

### Đợt 0 — Khóa tính trung thực và an toàn runtime

1. Bỏ fake-success khỏi LLM/OCR/Tools/Embedding/Workflow ở chế độ live.
2. Mask + encrypt provider key; rotate key cũ.
3. Áp auth dependency cho API quản trị.
4. Bắt API Caller node đi qua ToolService + approval + audit.
5. Chặn facts của tài liệu pending/archived.

**Điều kiện hoàn tất:** Mọi lỗi dịch vụ thật đều hiện `failed/degraded`; không có dữ liệu nghiệp vụ mô phỏng được trình bày như thật.

### Đợt 1 — Nối Assistant với ModelOps

1. Tạo model catalog theo capability và provider active.
2. Form assistant lấy model động; lưu cả provider ID và model name.
3. Thực thi primary/fallback deterministic cho mọi LLM node.
4. Hợp nhất usage/quota logging; hoàn thiện streaming usage.
5. Sửa contract quota FE/BE.

**Điều kiện hoàn tất:** Tắt provider/model ở ModelOps thì assistant không còn chọn/chạy model đó; log chỉ ghi một lần với đúng provider/model.

### Đợt 2 — Nối kín Chat, Widget và Handoff

1. Chat Studio lấy assistant thật.
2. Upload attachment thật và truyền attachment reference.
3. Tạo conversation, ghi message, correlation ID.
4. Cán bộ reply quay lại chat/widget.
5. Sửa widget endpoint, API base, CORS và deployment config.

**Điều kiện hoàn tất:** Một hội thoại bắt đầu từ widget có thể xuất hiện trong Handoff, được cán bộ trả lời và người dùng nhận lại phản hồi.

### Đợt 3 — Siết Knowledge/RAG lifecycle

1. Thêm index lifecycle/outbox/retry.
2. Facts chỉ publish sau approve; archive/version đồng bộ.
3. Chuẩn hóa RetrievalScope tenant/workspace/status/version.
4. Dọn DB/Qdrant/Storage bằng cleanup job idempotent.
5. Phân biệt embedding thật với degraded/test.

**Điều kiện hoàn tất:** Không có approved document thiếu index mà không cảnh báo; không retrieve được pending/archived/cross-tenant data.

### Đợt 4 — Biến Node Catalog thành contract thật

1. Validate JSON Schema/version/status ở backend.
2. Schema-driven Property Inspector ở frontend.
3. Bỏ catalog fallback lỗi thời khi authoring.
4. Approval Inbox tại `/runs`.

**Điều kiện hoàn tất:** Workflow hợp lệ trên Canvas chắc chắn compile được; required config thiếu bị chặn trước publish.

### Đợt 5 — Evaluation và Observability trung thực

1. Chọn Ragas thật hoặc đổi tên heuristic proxy.
2. Lưu per-case result và runtime metadata.
3. Không fallback sang pipeline khác khi eval assistant.
4. Dashboard chỉ hiển thị dữ liệu thật/readiness thật.
5. Gắn correlation ID xuyên assistant → workflow → model → retrieval → tool.

**Điều kiện hoàn tất:** Có thể truy từ một điểm số hoặc một câu trả lời về đúng tài liệu, chunk, workflow version, provider/model, tool call và lỗi liên quan.

---

## 8. Bộ kiểm thử nghiệm thu tối thiểu cho các đường nối

1. Gọi API quản trị không có cookie/token phải nhận `401`.
2. Provider sai key phải test thất bại; không có simulated response.
3. Provider inactive không được assistant chọn hoặc runtime sử dụng.
4. Primary fail chỉ chuyển đúng fallback đã cấu hình.
5. Stream chat ghi đúng một usage record với provider/model thật.
6. Tài liệu pending/archived không đóng góp vector, sparse result hoặc structured fact.
7. Qdrant down trong lúc approve phải tạo `index_failed/pending_retry`, không báo indexed.
8. Tool side-effect trong DAG phải dừng ở pending approval và có audit log.
9. Workflow có node config thiếu required field phải không publish được.
10. Attachment chat phải được upload, OCR/ingest và xuất hiện trong retrieval provenance.
11. Widget nhúng trên một origin khác phải chat được qua API base cấu hình.
12. Staff reply phải quay lại đúng conversation trên widget/chat.
13. Evaluation runtime lỗi phải ghi failed/partial, không tự chấm zero như completed.
14. Dashboard khi dependency down phải hiển thị degraded/unavailable, không dùng số fallback.
15. Xóa collection phải có kết quả reconciliation: DB = 0 document, Qdrant = 0 point, Storage = 0 object thuộc collection.

---

## 9. Thứ tự ưu tiên thực tế

Nếu nguồn lực có hạn, nên tập trung theo thứ tự:

1. **Dẹp fake-success và bảo vệ secret/API.**
2. **Nối Assistant ↔ ModelOps đúng provider/model/fallback.**
3. **Bắt Workflow Tool qua policy + approval.**
4. **Siết Knowledge Facts và index lifecycle.**
5. **Nối Chat/Widget ↔ Conversation/Handoff.**
6. **Schema-driven Nodes và Approval Inbox.**
7. **Evaluation/Dashboard trung thực.**
8. **Hoàn thiện Channels/Developer sau cùng.**

Đây là thứ tự giảm rủi ro vận hành tốt hơn so với tiếp tục mở rộng thêm chatbot, node hoặc dashboard mới.

---

## 10. Nhận xét cuối

Kiến trúc hiện tại **đủ tốt để tiếp tục phát triển, không cần viết lại**. Vấn đề chính là các contract liên phân hệ chưa được ép buộc và lỗi chưa được biểu diễn trung thực. Khi hoàn thành Đợt 0 đến Đợt 3, năm trợ lý Admissions, Drafting, Library, Question Bank và Regulations mới thực sự dùng chung một platform thống nhất thay vì năm giao diện chạy trên các đường dữ liệu chưa kín.

Tài liệu này nên được dùng làm backlog tích hợp cấp hệ thống. Mỗi phát hiện P0/P1 khi triển khai cần có integration test xuyên tầng, không chỉ unit test của riêng module.
