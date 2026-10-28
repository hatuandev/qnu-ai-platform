# modelops

Provider/key mã hóa, catalog/grant/default theo capability và quota/usage đã có API.
Runtime OCR, chat và dense embedding OpenAI-compatible đã nối vào xử lý tài liệu,
Compiler, [index/search](../../../docs/dense-indexing.md) và
[hỏi đáp](../../../docs/rag-answers.md).
[Hội thoại](../../../docs/assistants-conversations.md) dùng thêm chat để làm rõ
follow-up, có usage riêng; model chọn cụ thể luôn được ghim. Embedding dimension
và capacity gắn với endpoint/model, credential lấy từ DB có mã hóa.

Đã có [discovery/probe và lịch sử kiểm tra](../../../docs/modelops-diagnostics.md).
Kết quả thử tách khỏi capacity/dimension/default/grant; đổi cấu hình/khóa làm
kết quả cũ stale. Đã có [nhóm khóa, dự phòng trước tác vụ và registry](../../../docs/modelops-resilience.md): lease PostgreSQL, cooldown401/429, deadline chung, trace gắn usage và quyền/capacity được kiểm lại. Mặc định tắt, không đổi model giữa run hoặc trong chỉ mục embedding. Streaming/Responses/tools chưa triển khai.
Xem [Compiler v1](../../../docs/compiler-v1.md) và ma trận port trong `backendV1/docs/`.
