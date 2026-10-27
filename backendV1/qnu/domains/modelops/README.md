# modelops

Provider/key mã hóa, catalog/grant/default theo capability và quota/usage đã có API.
Runtime OCR, chat và dense embedding OpenAI-compatible đã nối vào xử lý tài liệu,
Compiler, [index/search](../../../docs/dense-indexing.md) và
[hỏi đáp](../../../docs/rag-answers.md).
[Hội thoại](../../../docs/assistants-conversations.md) dùng thêm chat để làm rõ
follow-up, có usage riêng và không tự fallback. Embedding dimension
và capacity gắn với endpoint/model, credential lấy từ DB có mã hóa.

Chưa có discovery/probe API, streaming hoặc key lease/cooldown/fallback runtime.
Xem [Compiler v1](../../../docs/compiler-v1.md) và ma trận port trong `backendV1/docs/`.
