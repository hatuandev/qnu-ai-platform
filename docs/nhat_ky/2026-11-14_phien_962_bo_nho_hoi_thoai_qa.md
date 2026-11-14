# Phiên 962 — 2026-11-14 — Bộ nhớ hội thoại: định tuyến v4 nhớ cả Q&A

## Yêu cầu và chẩn đoán

- Người dùng test Chat bằng 4 ảnh chụp ("Xin chào", "bạn tên gì?", "bạn sinh năm bao nhiêu", "bạn có thể làm gì?"): các lượt này trả lời trực tiếp được, nhưng những câu sau không trả lời được; người dùng nghi thiếu memory hội thoại.
- Nguyên nhân xác nhận từ mã và dữ liệu live: `rewriting.py` lọc bỏ lượt `direct_reply` khỏi lịch sử (mọi lượt trong 4 ảnh có `history_turn_ids: []`), và prompt định tuyến chỉ gửi `previous_user_questions`, không gửi lời đáp trước của chính trợ lý. Model không có gì để nhớ.
- Người dùng chọn hướng "Nhớ cả Q&A (Khuyến nghị)": thêm lời đáp cũ vào lần gọi định tuyến, kể cả lượt giao tiếp; lời đáp cũ chỉ giữ mạch hội thoại, không làm bằng chứng.

## File sửa

- `backendV1/qnu/domains/conversations/routing.py` — `ROUTING_VERSION = "qnu.conversation.route/v4"`.
- `backendV1/qnu/domains/conversations/rewriting.py` — lịch sử gồm mọi lượt `completed` (kể cả `direct_reply`); thêm `HISTORY_ANSWER_MAX_CHARS = 600` và `_history_answer()`.
- `backendV1/tests/unit/test_conversation_routing_855.py` — payload 4 khóa; test cắt/fallback `_history_answer`.
- `backendV1/tests/integration/test_conversations_649.py` — follow-up khẳng định `previous_assistant_answers` đúng nội dung; lượt giao tiếp vào `history_turn_ids` và payload định tuyến; payload RAG không chứa lời đáp trực tiếp.
- Không sửa frontend; không đụng các test bảo vệ (`test_answers_api_648.py`, `test_chat_stop_updates_664.py`, chunking/hybrid/table_layout...).

## Phương pháp

- Payload định tuyến mới: `{"current_question", "previous_user_questions", "previous_assistant_answers"}` (JSON, `ensure_ascii=False`).
- Lời đáp cũ lấy `result["answer"]` hoặc fallback `result["message"]`, strip, cắt 600 ký tự; budget `CONVERSATION_HISTORY_MAX_BYTES` (mặc định 16000) tính cả byte câu hỏi + lời đáp, vượt → 422 `conversation_history_limit` trước khi gọi model.
- Prompt v4: lời đáp cũ là dữ liệu không tin cậy, chỉ để hiểu người dùng đang nhắc tới gì, không lặp dữ kiện từ đó cho câu hỏi knowledge; route `identity` mở rộng cho câu hỏi lại thông tin đã cho trong hội thoại (chưa có thì nói chưa biết, không bịa); `needs_clarification` chỉ khi đại từ/cụm thay thế không xác định được chủ thể, câu tự nêu chủ đề ("Điều 5 quy định gì?") vẫn là câu knowledge độc lập.
- Hai vòng chỉnh prompt sau khi quan sát live: bản đầu đặt clarify quá rộng gây 409 `conversation_clarification_required` giả; bản hai vẫn chặn "Tên mình là gì?"; bản cuối (identity mở rộng + clarify hẹp) chạy đúng hai lần liên tiếp.

## Lệnh thật và kết quả

- Ruff check + format trên 4 tệp đã sửa: PASS.
- Live trên dev2 (API 8002, worker V1, FE V2 3002), model thật qwen3.8-27b-q4 qua provider `prv_9b75bf884822`, trợ lý `ast_3f577d75f723` (history_turns=3):
  - Hội thoại `cnv_fddfd88621f3` và chạy lại `cnv_84bd4c378ccc` cùng kịch bản 4 lượt:
    1. "Mình tên là Minh, bạn nhớ nhé." → `direct_reply` identity ("Xin chào Minh...").
    2. "Tên mình là gì?" → `direct_reply` identity "Tên của bạn là Minh nhé." (trước đây bị route knowledge / clarify).
    3. "Điều 5 quy định gì?" → knowledge, 4 nguồn/14 ứng viên.
    4. "Còn khoản 2 thì sao?" → knowledge, `resolved_question` = "Khoản 2 của Điều 5 quy định điều gì?", 3 nguồn/3 ứng viên.
  - `history_turn_ids` tăng 0→1→2→3; `needs_clarification=false` cả 4 lượt; prompt token 822→852/857→868/872→1069/1063 (tăng do Q&A trong payload, đã chặn 600 ký tự/lời đáp).
- pytest: NOT RUN (người dùng yêu cầu không chạy) — `NOT RUN ≠ PASS`.
- Không migration, không re-index, không commit/push. Dev DB vẫn `0026`.

## Ghi chú dữ liệu

- Các lượt "Quy định về học phí năm 2026?" hỏng trong lịch sử là `index_not_ready` trước khi index `idx_c5272814f942` hoàn tất 2026-11-14T06:55:55Z; bộ tài liệu hiện không có nội dung học phí 2026 nên câu "thiếu bằng chứng" là trung thực, không phải lỗi memory.
- Stack dev để chạy tiếp: background `dev2`, API :8002 (PID 8380), FE :3002 (PID 11608).

## Rủi ro và bước sau

- Lời đáp cũ có thể sai/lỗi thời → prompt cấm dùng làm bằng chứng; RAG không nhận lời đáp cũ, chỉ nhận câu hỏi độc lập đã viết lại.
- Định tuyến vẫn là 1 lời gọi model/lượt, không thêm agent; chi phí tăng nhẹ theo độ dài lịch sử (budget byte chặn).
- Chờ người dùng duyệt commit; migration 0027+0028 vẫn treo.
