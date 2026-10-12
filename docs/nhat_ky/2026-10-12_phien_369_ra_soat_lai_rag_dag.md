# Phiên #369 — Rà soát lại RAG và DAG sau tối ưu OCR

Ngày: 2026-10-12. Chỉ phân tích code và kiểm tra có phạm vi; không sửa runtime, cấu hình ModelOps, qnu-sso, dữ liệu, reset/restart hoặc inference thật. Skills RAG/clean-code định hướng scope/snapshot/evidence và kiểm chứng phẫu thuật; nội dung skill không thay thế bằng chứng code hiện tại.

## Kiến trúc đang có

RAG ask: input guard → retrieval snapshot → cache → intent/facts → dense Qdrant và lexical PostgreSQL → RRF/reranker → context/neighbor/citations → ModelOps → output/numeric guard → cache. Lexical weighted ILIKE chính, FTS ts_rank_cd bổ sung và unaccent; chưa BM25. Dense/sparse được gather song song; nguồn/chỉ mục được pin theo snapshot/epoch.

DAG: workflow/version/compiler → engine → routed node inputs → RAG/LLM/tools/guard/HITL → output/history. Node RAG gọi chung rag_service.ask, không cần xây retrieval thứ hai trong DAG. Các sửa join bất cân xứng/nhánh điều kiện và routed inputs #343 vẫn có trong code và regression đạt. Engine fan-out hiện thực thi một ready node mỗi lần (engine.py:78), không chạy nhiều node độc lập song song. HITL có pending/selected edges; chưa kiểm thử browser/resume production mới.

## Các điểm cần xử lý, theo ưu tiên

### P1: Tenant/workspace và failure semantics

1. `rag/service.py:425,446` không truyền req.tenant_id vào cả primary/fallback LLMGenerateRequest, mặc định qnu-default. Probe cô lập tenant_probe → qnu-default. Cần giữ tenant/assistant code/quota/cost xuyên các lời gọi. `WorkflowExecuteRequest`, `WorkflowContext`, runtime profile chưa có workspace; `rag_answer_node.py:106` không truyền workspace nên AskRequest mặc định workspace_qnu. Kho workspace khác có thể bị từ chối/sai phạm vi vận hành; không kết luận đã leak dữ liệu từ finding này. Scope phải lấy từ actor/assistant ownership ở entry point, không tin body tùy ý.
2. `rag/service.py:437–478` catch mọi lỗi ModelOps rồi trả fact/candidate; probe ALL_PROVIDERS_UNAVAILABLE trở thành excerpt. Caller tiếp tục đánh answered và có thể cache nếu evidence/citations đạt. Cần phân biệt không có tri thức và hạ tầng/model hỏng; bảo toàn error code. Extractive degraded mode nếu muốn phải explicit policy/status/telemetry, không tự nhận như LLM trả lời. Node RAG/LLM còn nhánh db=None tạo text answered/provider/token giả (`rag_answer_node.py:184`, `llm_generate_node.py:103`); production entry point có DB nhưng handler contract chưa fail-fast. Dispatcher có thể nâng insufficient_context thành answered bằng guidance; cần scope/provenance/citation review, không suy ra guidance giả chỉ từ nhánh này.

### P2: Policy và khả năng truy xuất nguồn ADR-012

3. `llm_generate_node.py:64` provider chỉ từ node config, bỏ model_policy.preferred_provider_id. Probe profile configured-provider → request null dù model lấy từ profile. Chốt precedence node override có chủ đích > profile > defaults, dùng chung resolver/contract cho RAG, LLM và node phụ.
4. `rag/service.py:148,380`: cache có model/tenant/workspace/history/snapshot/epoch, nhưng caller không truyền policy_version nên v1 cố định. Provider, system prompt, assistant revision, reranker/guardrail policy không được fingerprint: đổi policy cùng collection/question/model có thể dùng đáp án policy cũ. Cần fingerprint canonical runtime policy; tách cache authorization scope và invalidate khi policy/revision thay đổi.
5. `retriever.py:293` doc_match lexical dùng KnowledgeDocument.file_name/title; chunk ADR-012 có document_id nullable và metadata từ snapshot nên tên/mã nguồn mới không được boost/match tương đương legacy. Unaccent cũng phụ thuộc title legacy. `expand_with_neighbors:556,572` inner join KnowledgeDocument + document_id=candidate.document_id: nguồn binding-only không thể có neighbors dù chunk_index/binding/index_revision đủ. Probe SQL xác nhận inner join. Sửa để query metadata/source snapshot và neighbors theo binding/index_revision/chunk_index, giữ strict snapshot/tenant/workspace, không quay lại phụ thuộc Repository. Không phải toàn bộ ADR-012 RAG mất: content dense/lexical và facts đã hỗ trợ binding; chỉ các nhánh bổ sung này thiếu.

### P3: Trải nghiệm và quan sát

6. `assistant_chat_service.py:454–459`: chat_stream chờ workflow thực thi xong rồi chia answer thành words, sleep0,012s và phát SSE. Đây là SSE phát lại câu trả lời có sẵn, không phải token streaming trực tiếp từ ModelOps. Có thể gây chờ lâu trước token đầu. Nếu làm streaming thật cần bảo vệ citation/guardrails, không gửi text chưa được kiểm định một cách tùy tiện.
7. Engine exception path trả failed trước khi append trace của node lỗi (engine.py:120–140); lỗi ở execution có nhưng node trace thiếu. Fan-out tuần tự chưa phải bug correctness; chỉ cân nhắc concurrency sau đo latency, không gather các nodes dùng chung AsyncSession/shared mutable context mà chưa cô lập session/state/budget/cancellation.

## Kiểm chứng và giới hạn

- Ngoài sandbox: **83 passed / 11,94s** cho test_dag_routing_regression, test_workflows, test_workflow_hitl_and_history, test_rag, test_rag_generic_reuse, test_rag_entity_scoped_formatting, test_vllm_reranker. Đây là unit/regression, phần ModelOps/HTTP được mock theo test; không coi là server inference/browser chatbot E2E.
- Probe in-process không ghi DB/Redis, ModelOps bị patch: outage → excerpt, tenant mặc định sai, profile provider bị bỏ, schema/context không workspace và SQL neighbor legacy join. Probe đầu thiếu messages hợp lệ bị DTO reject đã được chỉnh thành ChatMessage trước kết luận; không dùng lỗi fixture đó làm lỗi ứng dụng.
- Hai lượt sandbox bị kẹt ở import/dependency; dừng riêng PID25656/28640/30180/17448 (test/probe do phiên này tạo) sau xác minh command line. Chạy lại ngoài sandbox đạt; không kill backend/worker của user. Chưa xác định chính xác dependency gây kẹt, không khẳng định Docker/server đang offline.
- Không chạy full pytest/Ruff/build vì chưa sửa code. Các lỗi nền full suite ở #364 không được coi là đã sửa chỉ vì targeted83 đạt. Không benchmark BM25 hoặc các thuật toán tài liệu13; không live hỏi đáp/truy xuất Qdrant mới.

## Đợt tiếp theo đề xuất

Giữ kiến trúc. Đợt1: scope/context/model-policy và error contract; viết regression trước vì liên quan tenant/quota và lỗi hạ tầng. Đợt2: policy-aware cache + lexical metadata/neighbors ADR-012. Đợt3: traces/streaming và benchmark chất lượng/latency rồi mới chọn BM25/MMR/parent-child sâu hơn theo tài liệu13. Không tự động triển khai các đợt trong phiên phân tích này.

Sau sửa cần E2E chatbot thực sự qua DAG với một kho đã publish: đúng tenant/workspace/provider, câu hỏi có/không evidence, model outage, policy change/cache, metadata query, pause/resume. Không chỉ test /rag/ask trực tiếp. Không thay đổi quy trình OCR/Repository đã được thống nhất.
