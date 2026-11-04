# Phiên 860 — Hội thoại qua LLM

## Yêu cầu và phương pháp

Người dùng muốn mọi câu mới đi qua LLM, gồm lời chào, thay vì phản hồi mẫu.
Đã bỏ regex và câu trả lời cố định trong `conversations/routing.py`.
Router dùng JSON schema `qnu.conversation.route/v2` để phân biệt giao tiếp với
câu cần dữ kiện. Tên và persona lấy từ snapshot trợ lý, chỉ gửi các trường cần
thiết, không gửi credential hoặc cấu hình quyền cho model.

Routing và làm rõ câu nối tiếp được gộp vào một request trong `rewriting.py`.
Lượt giao tiếp lấy nguyên lời đáp do model sinh. Knowledge tiếp tục qua pipeline
RAG và kiểm dẫn chứng hiện có. Router không được trả lời dữ kiện khi chưa có nguồn.
Phân loại bằng model vẫn có thể sai, cần đánh giá thêm trên câu hỏi thực tế.

`execution.py` dùng kết quả routing. Schema `direct_reply` giữ tương thích với
lịch sử và UI hiện tại. Các lượt mới có usage, provider, model và reasoning trong
`rewrite_trace`. Dùng task `answer` để áp dụng đúng lựa chọn runtime và chính sách
reasoning hiện có. Ngân sách đầu ra lấy caller/ModelOps, không thêm trần cố định.
Quyền, lease, idempotency và kiểm thay đổi model vẫn được kiểm trước/sau inference.

## Kiểm chứng

- Regression trước sửa đã tái hiện câu chào trả bằng code thay vì model.
- Ruff trên module hội thoại và các test bị ảnh hưởng đạt exit 0.
- Harness DB cô lập chạy 5 tệp trọng tâm, có 72 PASS và 1 FAIL do test mới viết
  nhầm trạng thái usage thành `settled`. Giá trị hợp đồng đúng là `completed`.
  Đã sửa assertion theo service và kiểm riêng ca đó đạt 1 PASS, exit 0.
  Không thay logic accounting để làm test đạt.
- Các ca trọng tâm gồm lời đáp lấy từ model, replay không gọi thêm, giao tiếp
  không chạy embedding, lỗi HTTP/JSON/truncated không trả câu mẫu, mixed question
  vẫn qua RAG, follow-up, dừng lượt, đổi quyền/assistant/model và scope metadata.
- Full backend đã được khởi chạy nhưng bị dừng trước hoàn tất, không được coi
  PASS. Lượt này có một dấu lỗi trong tiến độ, chưa có báo cáo tổng hợp để xác định
  test ID từ chính lượt full. DB thử riêng đã dọn và kiểm sentinel còn nguyên.
- Kiểm riêng lỗi nền đã ghi trong Context850 vẫn FAIL tại
  `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`.
  DOCX có bảng và giữ span/số liệu nhưng fixture không có ô đánh dấu `header` như
  assertion dòng 109 yêu cầu. Chưa sửa parser hoặc fixture trong nhiệm vụ hội thoại.
- Thử router bằng Qwen thật qua ModelOps, không restart app, không gọi OCR/compiler
  hoặc gửi corpus. Cohort đầu 3/4 đúng nhãn, câu cảm ơn được đáp phù hợp nhưng gắn
  nhãn greeting. Đã làm rõ nghĩa từng route trong prompt, không thêm câu đáp mẫu.
  Cohort sau 6/6 đúng route, mỗi câu đúng một request và không retry.

| Loại ca | Kết quả cohort sau | Thời gian toàn bộ gọi routing |
|---|---|---|
| Lời chào | greeting, có lời đáp từ model | 1,83 giây |
| Cảm ơn | courtesy, có lời đáp từ model | 1,50 giây |
| Hỏi danh tính | identity, có lời đáp từ model | 1,38 giây |
| Chào kèm câu hỏi dữ kiện | knowledge, answer null | 0,95 giây |
| Cảm ơn kèm câu hỏi dữ kiện | knowledge, answer null | 1,02 giây |
| Xin chỉ dẫn nội bộ | protected_request, model tự từ chối | 1,47 giây |

Cohort sau dùng tổng cộng 5.451 token provider đo được, `enable_thinking=false`
ở cả 6 request. Kết quả local lưu tại `tmp/context860/live-routing-final.json`.
Đây là smoke test routing, chưa phải benchmark đầy đủ đáp án RAG hay bảo đảm
chống mọi prompt injection. Lượt knowledge trong smoke test không gọi bước answer.

## Sử dụng

Khởi động lại backend bằng Ctrl+C ở cửa sổ dev rồi chạy `./make.ps1 dev` để nạp mã.
Gửi câu mới sẽ gọi model. Replay khóa cũ giữ lịch sử đã lưu. Không cần clear,
seed hoặc lập lại chỉ mục. Phiên này chưa restart dịch vụ hay thay cấu hình model.
