# Phiên #342 — Review RAG và DAG trong lúc triển khai OCR Studio

## Phạm vi

Review read-only runtime RAG, workflow compiler/engine và các node chính. Không sửa production code, không khởi động lại dịch vụ, không tác động qnu-sso hoặc công việc OCR Studio đang được người dùng triển khai. Dùng skills clean-code, RAG pipeline và ModelOps để kiểm tra provenance, fallback và cấu hình động.

## Kiến trúc hiện tại

RAG: input guard → retrieval snapshot → cache → intent/facts → dense Qdrant + PostgreSQL FTS → RRF/reranker → dựng ngữ cảnh → ModelOps → output/citation/numeric guard → cache/response.

DAG: workflow definition/version → compiler → input/query/route → RAG hoặc LLM/tools → citation guard/HITL → output → execution history. Engine có traces và routing theo ports, nhưng các handler chưa dùng ports nhất quán. RAG node gọi trọn pipeline ask, không chỉ retrieval.

## Findings

### P1 — Join có thể chạy khi nhánh dài chưa hoàn tất

`workflows/engine.py:214`: chỉ tính predecessor đã nằm trong active_node_ids. Predecessor ở sâu trong nhánh dài chưa được kích hoạt bị bỏ qua. Probe trong process riêng, dùng handler test-only và không ghi DB, graph:

root → a_short → b_join → out; root → z_long → zz_tail → b_join.

Kết quả thực tế: completed, thứ tự root/a_short/b_join/out/z_long/zz_tail. Join chỉ nhận input a_short. Node output chạy trước zz_tail nhưng workflow vẫn thành công. Test fan-in hiện tại chỉ có nhánh dài bằng nhau nên chưa bắt lỗi này. Cần scheduler tracking trạng thái cạnh/nhánh selected, skipped và pending; không chỉ chờ tất cả predecessor tĩnh vì nhánh condition không được chọn sẽ gây deadlock.

### P1 — RAG che lỗi ModelOps bằng câu trả lời grounded fallback

`rag/service.py:437-478` catch mọi lỗi, thử fallback rồi trả fact_markdown/candidate đầu tiên. Response có thể thành answered và cache được dù provider hoàn toàn không hoạt động. Không phải dữ liệu giả, nhưng che outage/quota và vi phạm contract ALL_PROVIDERS_UNAVAILABLE. Cần phân biệt no-context với infrastructure failure, giữ mã lỗi hoặc explicit degraded extractive mode có policy và telemetry; không báo thành công như LLM đã sinh.

### P1 — Scope tenant/workspace không truyền xuyên luồng

`rag/service.py:425-435,446-456`: LLMGenerateRequest không truyền req.tenant_id, nên dùng mặc định qnu-default của DTO; quota/cost có thể ghi sai tenant dù retrieval đã scoped. `workflows/nodes/base.py` và WorkflowExecuteRequest không có workspace; RAGAnswerNode tạo AskRequest không truyền workspace nên luôn dùng workspace_qnu. Kho trong workspace khác không truy vấn đúng. Không khẳng định leak tenant từ finding này; hệ retrieval có kiểm tra ownership.

### P2 — Node LLM bỏ provider trong policy trợ lý

`workflows/nodes/llm_generate_node.py:61-64`: preferred_provider_id chỉ lấy config node, không fallback profile.model_policy.preferred_provider_id. Model lấy được từ profile nhưng provider lại bị phân giải khác, có thể gọi nhầm server/credential. Một số node phụ cũng cần rà scope/model policy chung thay vì resolver rải rác.

### P2 — Dây nối trên canvas chưa quyết định input ở một số node

Engine ghi dữ liệu cạnh vào context.node_inputs, nhưng RAGAnswer/LLMGenerate/OutputChat chủ yếu đọc shared node_data như rag_answer/llm_content/user_message. Workflow nhiều node RAG/LLM có thể ghi đè kết quả, output không phản ánh source_port/target_port người dùng nối. Cần ưu tiên input routed với contract typed, legacy compatibility được kiểm soát. Các cạnh chung target_port cũng bị overwrite trong engine; compiler cần kiểm soát cardinality hoặc aggregation rõ ràng.

## Kiểm chứng

- Chạy `uv run --extra dev pytest tests/test_workflows.py tests/test_citation_guard_node.py tests/test_rag_data_truth_and_lifecycle.py tests/test_rag_generic_reuse.py -q`: **48 passed, 1 failed**, 8.52s.
- Failure: test_reconciliation_detects_discrepancies, kỳ vọng legacy_payload_schema nhưng discrepancies rỗng. Cần xác định fixture legacy lỗi thời hay regression runtime trước khi sửa; không suy ra chắc chắn production reconciliation hỏng chỉ từ test mock này.
- Probe DAG nhánh bất cân xứng tái hiện P1 như trên. Handler probe chỉ sống trong process độc lập, không thêm registry production hoặc tệp source.
- Không rerun inference/browser E2E, full pytest, Ruff hoặc FE build: không sửa production code. Kết quả E2E #341 chỉ chứng minh RAG trực tiếp trong ca giới hạn, không chứng minh end-to-end chatbot DAG.

## Hướng ưu tiên

Giữ kiến trúc RAG và DAG nhưng sửa tính đúng trước: scheduler joins → typed routed inputs → scope tenant/workspace/provider → error/degraded contract → cache fingerprint theo policy và guardrails. Cache hiện scoped snapshot/epoch/history/model nhưng chưa thấy fingerprint system prompt/provider/assistant policy tại caller; cần kiểm thử riêng khi đổi chính sách trợ lý. Không thay toàn bộ thành framework mới. Query rewrite còn vocabulary hardcode, cần review riêng theo AGENTS, không mở rộng sửa trong phiên này.

## Bàn giao

Chỉ tạo báo cáo #342 và cập nhật ba index/memory tài liệu. Không sửa code đang vibe. Chưa nghiệm thu production-ready; các findings trên cần regression tests trước sửa, sau đó kiểm thử chatbot thật qua DAG, không chỉ /rag/ask.
