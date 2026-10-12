# Phiên #370 — Tích hợp nhất quán RAG/DAG/ModelOps

Ngày: 2026-10-12. Triển khai ưu tiên #369 theo yêu cầu người dùng: scope, provider/error contract, cache và retrieval nguồn ADR-012. Không triển khai BM25/token streaming/parallel DAG, không sửa OCR hay qnu-sso, không reset/migration/restart hoặc publish dữ liệu user.

## Quyết định

Giữ một RagService dùng chung cho API và DAG, ModelOps là chủ sở hữu failover/quota/key rotation. Không thay outage bằng excerpt thành công. Scope entry point từ actor (RAG/workflow execute) hoặc assistant+collection persisted (public chat); không từ tenant hint tùy ý. Dispatcher facts dùng cùng published snapshot để không bypass publication gate. Skills Backend/RAG/ModelOps/clean-code giữ async/RFC7807, thuật toán existing và regression-first; không thay cả kiến trúc.

## Thay đổi

- `rag/schemas.py`, `service.py`: assistant code/revision/runtime policy; cache v2 canonical request fingerprint, get/set đều truyền cùng version. ModelOps nhận tenant/code/model/provider/fallback/max limits; gọi một lần, bảo toàn AppException, bọc lỗi bất ngờ, từ chối content rỗng. Không grounded synthesis fallback âm thầm. Namespace v1 không reuse; defaults DB bên ngoài request không tự được fingerprint, cần invalidate/cache revision khi đổi defaults.
- `rag/router.py`: search/ask/facts dùng actor scope; facts endpoint pin published revisions. `rag/retriever.py`: lexical/unaccent thêm snapshot title/document number metadata; neighbor nhánh binding không cần KnowledgeDocument, giữ binding/index_revision và collection scope/active; legacy nhánh riêng vẫn còn. Không thêm BM25 hoặc đổi RRF/reranker.
- `assistants/runtime.py`, schemas/chat service: đọc kho để suy ra tenant/workspace, kiểm tra tenant kho thuộc trợ lý; profile và WorkflowExecuteRequest giữ scope. Public tenant hint không quyết định scope. Thông báo lỗi workflow không còn chỉ nói soạn thảo; failure có error_code ở response/SSE done, usage failed ghi error. Không thay SSE replay thành live model tokens.
- Workflow schemas/context/service: workspace explicit; req/profile scope mismatch fail; execution.runtime_profile JSONB lưu workspace cả khi không có assistant, resume dùng đúng workspace; legacy thiếu workspace mặc định QNU. Version query thêm workflow_id. Không schema DB migration. Engine exception có failed node trace/latency/error_code, response/outputs giữ code.
- RAG node: noDB fail-fast, scope/policy/model/provider/snapshot sang RagService và dispatcher; không nâng insufficient_context bằng guidance. LLM node: provider node override > profile, ModelOps errors propagate, bỏ fake text/provider/token và fallback_text thành công khi model lỗi. Query rewrite/route micro-LLM chuyển tenant/code. Join/routed engine #343 không đổi.
- `modelops/services/inference_service.py`: nhận vllm/openai_compatible trong chat cascade, dynamic proxy model compatibility trước family matching; vẫn tránh embedding/reranker-only gọi chat. Không sửa URL/model/key DB.
- `tools/consulting_dispatcher.py`: facts có collection/tenant/workspace/active binding/published revision filter, snapshot chung; export intent LLM nhận tenant/provider. Export business heuristics tồn tại từ trước chưa được refactor trong phiên này.
- `knowledge/services/vector_generation_service.py`: materialization DB/Qdrant bổ sung file_name/document_number/chunk_index. Không mutate các index đã publish; nguồn/index cũ thiếu metadata cần build/publish có chủ đích.
- Tests mới `test_rag_modelops_contract.py`; fixtures tests assistants/workflows/HITL/routed và fallback RAG cập nhật contract. Fixture ModelOps explicit ở test greeting, không dùng production fallback giả để làm xanh. Đồng bộ Quy trình03/04/06 và memory/indexes.

## Kiểm chứng

- **Regression trước sửa: 8 fail** đúng tenant default, provider profile bị bỏ, outage/quota không raise, noDB fake success, cache không version và neighbor legacy join. Không dùng lỗi fixture làm bằng chứng bug.
- **152 focused passed /8,11s**: RAG contract, DAG routing, workflows/HITL, assistants, RAG formatting/generic, ModelOps/vLLM, vector load và source ingestion. Bao gồm model outage/quota/noDB, failed trace, actor override body, cross-tenant assistant/collection, policy fingerprint, failed Ask không cache, lexical metadata và neighbors SQL. Unit/adapters có boundary mocks, không coi là server inference/E2E.
- **Ruff toàn backend đạt**; warning đọc artifacts test cũ ngoài phạm vi. Full final **903 passed /13 failed /2 skipped /27,80s** với basetemp mới trong storage; không setup errors. 13 lỗi nền cùng danh sách #364/#369: dispatch export/facts seed, legacy publishing permissions, reconciliation contract và role cookie. Lượt full trước900passed/13fail/2skip; ba regression cuối tăng count. Không sửa lan các lỗi nền.
- **Live DB**: 5 kho mặc định chưa có active_vector_generation_id, kho admissions có1active/2pending binding nhưng không published snapshot revisions. Do đó không thể nghiệm thu grounded chatbot bằng tài liệu hiện tại khi không tự publish dữ liệu user.
- **Live RAG và node RAG DAG** ngoài sandbox, DB/Redis/Qdrant thật, không patch: Ask trả insufficient_context/0citations/snapshot0binding; DAG completed nhưng rag_status insufficient_context. Không báo answered hay lấy nguồn chưa xuất bản. Đây là service/node smoke trong bộ nhớ, chưa browser/full assistant endpoint E2E.
- **Live DAG LLM → ModelOps** với profile admissions thật: completed, provider Cloudflare, total_tokens1830, text92ký tự, tracecompleted. Không patch HTTP/ModelOps. Quota/key rotation/usage có tác động audit bình thường của lần inference. Không chứng minh vLLM có chat: provider vLLM hiện model bge-m3 và catalog embedding/reranker, Cloudflare chat có key nên cascade hoạt động. Không in secret, không sửa key/status/config có chủ đích.
- Không chạy Vite build/FE lint vì không đổi FE source; các response fields mới optional, tests API/SSE coverage có. Không restart backend/worker hoặc chạy lại source user. Chưa live failure injection/credential rotation/concurrency, chưa grounded browser chatbot E2E, chưa manual quality benchmark.

## Giới hạn/bàn giao

Không tuyên bố production-ready hoặc full-suite green. Scope lịch sử hội thoại, quyền quản trị workflows/approvals và toàn bộ tool/subnode ngoài entry points sửa ở đây còn cần security audit riêng. Cache chưa fingerprint tự động các thay đổi DBdefaults; query/dispatcher vocabulary business heuristics chưa tổng quát hóa. Engine vẫn sequential, chat SSE replay vẫn như trước; không lén mở rộng sang parallel mutable context/AsyncSession.

Code cần được backend/worker đang chạy nhận (API reload hoặc restart khi cần). Không cần reset/migration; worker generation builds mới ghi metadata bổ sung. Trước E2E grounded: người dùng chọn/publish index mong muốn và cấu hình chat policy/provider phù hợp; không dùng source ready như nguồn phục vụ khi chưa publish. Đợt tiếp theo là test thật chatbot qua DAG trên kho đã xuất bản, sau đó streaming/trace nâng cao và benchmark thuật toán13.
