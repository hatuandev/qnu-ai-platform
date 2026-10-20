# Context562 — Thay đổi triển khai

## Backend

| File / nhóm | Thay đổi phục vụ yêu cầu |
|---|---|
| `rag/intent_rules.py` | Fast path toàn thông điệp, mixed prefix, phụ thuộc ngữ cảnh và lọc các lượt giao tiếp |
| `rag/intent_contracts.py` | Sáu intent, typed decision/referent và kiểm trích đoạn |
| `rag/conversation_router.py` | Phân luồng trước retrieval, phản hồi từ cấu hình, fallback và debug kết quả |
| `rag/conversation_resolution.py` | Tái dùng resolver, gộp hybrid call, bảo vệ ngành/mã/năm/phủ định, giữ dialogue acts |
| `rag/intent_debug.py`, `rag/schemas.py` | Debug server scope, private state không phải client DTO |
| `rag/evidence_model.py` | Router chọn một attempt; các caller evidence vẫn giữ mặc định hai attempt; trace model thực gọi |
| `rag/service.py` | Guard trước fast reply, giải ngữ cảnh rồi tiếp tục pipeline hiện hành |
| `assistants/services/assistant_history.py` | Lịch sử đúng trợ lý/config, bỏ social khi chọn chủ đề, lỗi DB trung thực |
| `assistants/services/assistant_chat_service.py` | Chat JSON/SSE dùng helper lịch sử chung |
| `assistants/services/assistant_rag_chat.py` | Truyền danh tính server, trạng thái SSE trung thực |
| `assistants/services/conversation_access.py`, `assistants/router.py` | Continuation capability và admin-only debug, JSON/SSE cùng contract |
| `conversations/router.py` | Chặn đọc lịch sử quản trị khi thiếu quyền audit |
| `core/middleware.py` | Expose continuation response header trong CORS hiện có |

## Frontend

`use-rag-stream.ts` mặc định không xin debug; dùng auth hiện có, nhận/gửi continuation header, khôi phục đúng session và giữ rõ lỗi stream. `use-chat-history.ts` giữ session theo đúng đoạn chat; `public-chat-view.tsx` khôi phục session khi chọn đoạn khác và khi đọc lại lịch sử.

Widget nhúng độc lập đã có tại `public/embed/qnu-chat-widget.js`, không dùng React hook. Đã cập nhật widget giữ conversation ID/capability trong bộ nhớ, encode assistant ID, buffer SSE qua ranh giới chunk/UTF-8, nhận status/done/error và báo thật khi luồng bị ngắt. Widget vẫn gọi cùng backend router; không tạo business pipeline khác. Ba test chạy mã widget thật trong VM với DOM/stream giả, sau đó kiểm thêm hai lượt trên widget thật qua trang harness local tạm. Harness đã xóa sau kiểm tra.

Sandbox chỉ xin trace khi có quyền quản trị; Retrieval Inspector bổ sung thông tin phân luồng. `chat-bubble.tsx` và Sandbox dùng loading chung phù hợp cả lời chào lẫn Knowledge. `assistant-chat-route.ts` encode assistant thành một path segment và có test default/debug/session ownership.

## Kiểm thử và tương thích

Thêm ba bộ backend routing/conversation/API cùng corpus 116 câu. Unit tests workflow cũ được stub repository lịch sử tại đúng ranh giới thay vì trả AssistantModel cho mọi câu SQL. Kiểm tra thứ tự lịch sử vẫn giữ assertion cũ, cập nhật mock cho hai thao tác đọc thread/messages. Các integration test mới dùng DB test thật chứng minh persistence và session ownership, không chỉ mock lịch sử.

Endpoint và JSON payload chat cũ giữ nguyên. Response bổ sung header tiếp tục phiên. Đây là thay đổi có chủ ý với client public tự tích hợp: ID đơn lẻ không còn đủ nối vào một phiên đã tồn tại. Hook dùng chung đã cập nhật. Token không cấp quyền admin hay truy cập source.

Không sửa parser, ingestion, semantic annotation, evidence packing, publication hoặc model config trong Context562. Các file DOCX đã sửa từ Context561 và các thay đổi chưa commit trước phiên được giữ nguyên. Không commit/push/stage/reset/restart/deploy.

Frontend formatter trong repo đặt CRLF, còn AGENTS yêu cầu LF; kiểm Biome có override `--line-ending=lf` cho đúng phạm vi file sửa, không đổi cấu hình formatter toàn repo.
