---
name: qnu-chatbot-builder
description: Create or configure a QNU assistant across persona, knowledge binding, ModelOps, guardrails, tools, citations and acceptance evaluation. Use for chatbot lifecycle work; not routine uploads or ordinary chat questions.
---

# Vòng đời chatbot có kiểm chứng

Đọc assistant/workflow schema và cấu hình runtime hiện tại. Tái dùng hệ thống có sẵn; không tạo pipeline thứ hai chỉ để khớp sơ đồ mẫu. Các bước là checklist đầu cuối, không phải bằng chứng mọi thành phần đã triển khai.

1. **Persona và scope:** xác định chủ thể trường/phòng ban, nghiệp vụ và cách xử lý ngoài phạm vi; dữ kiện trường cần bằng chứng chính thức, không chỉ kiến thức LLM.
2. **Knowledge binding:** gắn collection/binding/snapshot được phép; chọn parser/chunker theo cấu trúc nguồn. Số liệu bảng cần nguồn tới ô/header/năm/đơn vị. Dùng [ingestion](../qnu-knowledge-ingestion/SKILL.md) khi thay luồng nguồn.
3. **ModelOps:** chọn primary/fallback theo task, capability và quyền; generation params, token/timeout/quota từ cấu hình đã được xác nhận. Không hardcode tên model, dimension hoặc similarity threshold chung. Dùng [ModelOps](../qnu-modelops-resilience/SKILL.md) khi thay adapter/routing.
4. **Guardrails:** kiểm tra quyền/scope trước retrieval và tool; prompt injection defense không chỉ là blacklist câu chữ. Không truyền secret/PII không cần thiết vào model. Thiếu evidence thì no-answer/clarify; lỗi model/DB phải là lỗi, không giả hotline hay empty data. Thông tin liên hệ lấy từ cấu hình/nguồn đã xác minh.
5. **Tools và hội thoại:** registry allowlist, schema và execution context do server tạo; giới hạn steps/calls/time/tokens, cancellation. Công cụ ghi cần preview, approval gắn actor+args+expiry, idempotency và audit. Explain/reformat/filter/follow-up giữ scope và snapshot nguồn, không dùng văn bản assistant cũ làm sự thật. Ưu tiên workflow xác định khi đáp ứng được, không mặc định ReAct/swarm.
6. **Output và citations:** chọn bảng/checklist/timeline/đoạn văn theo câu hỏi. Mỗi số/khẳng định quan trọng truy được về source/version/page/block hoặc ô thật. Enumeration không được mất hàng vì TopK; phép quy đổi/tính toán dùng rule/source đã duyệt, ghi rounding policy rõ.
7. **Nghiệm thu:** chạy các ca positive/negative, sai năm/metric, unknown, mâu thuẫn, đa tenant, follow-up đổi năm, provider outage và tool approval. Dùng [đánh giá RAG](../qnu-rag-evaluation/SKILL.md); ngưỡng sản phẩm phải được chọn trước theo tập dữ liệu/metric, không coi điểm Ragas hoặc ngưỡng similarity mẫu là bảo đảm không bịa.

Bàn giao cấu hình thực, binding/model/task, trường hợp được hỗ trợ, cổng chưa đạt, lệnh và kết quả đã chạy. Cấu hình/sửa code không tự cho phép publish nguồn, kích hoạt rule, chạy model ngoài hoặc deploy. Kiểm thử theo [gate chung](../../rules/verification.md).
