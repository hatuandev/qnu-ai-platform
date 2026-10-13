# Phiên #425 — Chẩn đoán Custom AI Gateway báo lỗi khi thêm model

Ngày: 2026-10-13. Phạm vi: kiểm tra theo yêu cầu người dùng; tạm dừng công việc backup, không triển khai sửa runtime.

## Mục tiêu và phương pháp

Đối chiếu ảnh test `ollama/gpt-oss:120b` trên provider `qnu-9router` với cấu hình DB, request contract và phản hồi gateway thật. Áp dụng hướng dẫn ModelOps, Backend và Clean Code: giữ nguyên model ID/provider/endpoint, không fallback để làm probe thành công giả, không ghi hoặc xuất credential.

Đọc provider trong transaction PostgreSQL read-only; giải mã credential DB chỉ trong bộ nhớ. Gọi catalogue và hai completion bằng câu tổng hợp `Reply OK.`, `stream=false`, `temperature=0.2`, ngân sách lần lượt 32/256. Không gọi endpoint test có lưu capability observations, không thay đổi provider/model/key health hay quota DB.

## Bằng chứng thực tế

- Provider custom: `http://localhost:20128/v1`, có credential; models đã lưu vẫn là `gh/gpt-5.4-mini`, `gh/gpt-6-luna[1m]`; capabilities cho alias đang kiểm tra trống.
- GET `/models`: HTTP 200, 554 entries, có exact ID `ollama/gpt-oss:120b`.
- POST `/chat/completions`, 32 tokens: HTTP 200, JSON, 1.52s, served model `gpt-oss:120b`; `finish_reason=length`, `content=""`, `reasoning_content` dài 115 ký tự, completion tokens=32. Không lưu/hiển thị nội dung suy luận. Shared decoder QNU báo `MODEL_RESPONSE_PROTOCOL_ERROR`.
- Cùng model/prompt/endpoint, 256 tokens: HTTP 200, JSON, 1.60s, `finish_reason=stop`, `content="OK."`, completion tokens=81; decoder QNU thành công.
- Đây không phải upstream HTTP404, không phải catalogue thiếu model hoặc lỗi xác thực trong hai lần thử. Thành công probe không chứng minh mọi tác vụ/chatbot đều ổn.

## Nguyên nhân trong code

- `backend/app/modules/modelops/services/chat_probe.py`: probe bắt đầu ở 32 tokens và không thử tăng ngân sách khi completion hợp lệ nhưng bị cắt trước phần trả lời.
- `backend/app/modules/modelops/providers/chat_contract.py`: decoder yêu cầu nội dung trả lời không rỗng (đúng về an toàn), nhưng gộp trường hợp thiếu ngân sách với protocol lỗi. Cap256 hiện chỉ dùng khi thương lượng HTTP400 minimum-token.
- `backend/app/modules/modelops/providers/openai_adapter.py`: decode sau transport; `reasoning_content` không được dùng làm câu trả lời (cần giữ nguyên).
- `frontend/src/components/modelops/add-custom-model-dialog.tsx`: nhánh lỗi chung gắn nhãn cứng `404/Error` thay vì phân loại theo mã thực.
- `probe_chat` bắt `AppException` nhưng chưa chuyển `status_code` vào `http_status`; DTO FE cũng chưa có các trường mã lỗi/served model/capabilities mà BE đã khai báo.

## Đề xuất, chưa triển khai

1. Phân loại completion JSON có `finish_reason=length` và nội dung trả lời trống thành ngân sách chưa đủ; không gọi là model không tồn tại, không chấp nhận suy luận nội bộ là câu trả lời.
2. Chỉ health probe được thử lại có giới hạn (ví dụ thêm một lượt tối đa256 tokens, tổng deadline/chi phí rõ ràng), dựa trên cấu trúc phản hồi chứ không hardcode tên model. Giữ nguyên model/provider/auth/prompt; không tăng ngân sách runtime hoặc fallback ngầm.
3. Nếu hết ngân sách vẫn trống, báo chưa kiểm chứng do giới hạn token; nếu upstream404/401/429/timeout thì hiển thị đúng. Tách upstream HTTP status khỏi mã lỗi QNU để không mô tả HTTP200 như upstream502/404.
4. Đồng bộ DTO/UI, nhãn test không đoán404. Hỗ trợ regression empty+length, reasoning-only, empty+stop, malformed JSON/SSE,404/401/429/timeout, non-empty success và bounded retry.

## Kiểm chứng và giới hạn

Hai real completion và catalogue đạt như trên; không chạy Ruff/Pytest/Vite vì phiên này chỉ chẩn đoán và cập nhật tài liệu, không thay đổi source. Chưa kiểm thử tải, chất lượng RAG/DAG hoặc streaming model này.

Chỉ thay đổi tài liệu: nhật ký này, README nhật ký, PROJECT_CONTEXT và WORK_LOG. Không reset DB, thêm model, đổi primary/fallback, restart services, bật lịch backup/S3 hay đụng bản backup hợp lệ.

Bài học: catalogue availability, transport success và answer-content success là ba bằng chứng khác nhau; probe ngắn phải phân biệt giới hạn suy luận với lỗi giao thức thật.
