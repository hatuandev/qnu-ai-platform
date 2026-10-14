# Phiên #440 — Đề xuất tách DAG khỏi chatbot hỏi đáp

## Yêu cầu

Người dùng hỏi giá trị DAG và muốn tập trung RAG cho chatbot trả lời chính xác. Phiên này phân tích kiến trúc, chưa chuyển tuyến chat hoặc sửa mã.

## Đối soát

- `AssistantChatService.chat` và `chat_stream` hiện luôn xây WorkflowExecuteRequest và gọi workflow_service.execute.
- Trace #438: input.chat → condition.route → query.rewrite → core.knowledge.answer → guard.citation_policy → output.chat/output.no_answer. Không thấy tác vụ ghi bên ngoài/HITL trong40lượt.
- RAGAnswerNodeHandler xây AskRequest, chuyển policy/model/history vào rag_service.ask; còn gọi consulting_dispatcher cho yêu cầu phù hợp.
- RagService.ask có input guard, phân giải snapshot đa tenant và evidence policy. Direct RAG và DAG cùng gọi answer_with_evidence nên lỗi binding/audit/temporal của#438/#439 không mất đi khi bỏ workflow.
- Conversation history/persistence, prepare_user_message(maskPII), trợ lý active/runtime scope, knowledge gap logging và SSE hiện thuộc AssistantChatService hoặc node wrappers; chuyển RAG trực tiếp phải giữ các chức năng đó trong lớp chat chung. Không nên đổi FE sang gọi /rag/ask rồi coi như tương đương toàn bộ chat hiện tại.

## Phương án đề xuất

Chatbot hỏi đáp tri thức chạy AssistantChatService → RAG pipeline trực tiếp → câu trả lời cótríchdẫn. Giữ endpoint trợ lý, policyModelOps/knowledge/guardrails, history và log; bỏ workflow bắt buộc khỏi mode hỏi đáp. Workflow/DAG để tùy chọn cho tác vụ nhiều bước, xuất báo cáo, API hành động và phê duyệt, không xóa toàn module.

Chạy lại cùng20câu sau khi ổn định RAG; supported không phải accuracy, không dùng tốc độ làm thay thế chất lượng. Bỏ DAG giảm lớp điều phối, không hứa sẽ sửa toàn lỗi RAG hoặc giảm thời gian19–20s kiểm chứng.

## Trạng thái

Chỉ đọc mã/artifact và ghi đề xuất. Không code/modelcalls/config/DB/reindex/publication mutation. Không chạy build/lint/tests vì không thay mã.
