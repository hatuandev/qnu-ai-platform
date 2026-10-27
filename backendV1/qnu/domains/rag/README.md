# rag

Đã có [API hỏi đáp có trích dẫn](../../../docs/rag-answers.md) đồng bộ trong `answer/`:
tái sử dụng knowledge/index search → evidence → ModelOps chat → kiểm ID/citation và
nguồn hiện hành sau HTTP. [Hội thoại](../../../docs/assistants-conversations.md)
đã gọi lại pipeline này với resolved query/persona và checkpoint; chưa streaming.
[RAG policy](../../../docs/rag-policies.md) nối dense/hybrid/rerank vào
snapshot trợ lý, lọc metadata trước TopK, context cùng mục và judge tùy chọn.
