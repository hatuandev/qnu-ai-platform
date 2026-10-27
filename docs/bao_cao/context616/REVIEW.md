# Context616 — Trạng thái đang thực hiện

**Chưa nghiệm thu compiler.** Người dùng chuyển yêu cầu sang kiểm kê các mức token và yêu cầu không đặt thêm trần token cố định. Lượt thử13 đã dừng trước inference mới; không chạy lại để vượt qua chỉ đạo này.

## Đã thực hiện

Các thay đổi compiler được mô tả trong [thiết kế](DESIGN_AND_IMPLEMENTATION.md). Regression cuối hiện có **61 PASS**, exit0, tại `backend/storage/context616/checks-semantic-final/review-envelope-fixed.xml`:58 case grounding616 và ba case ngân sách checkpoint611. Ruff trên14 app +4 test đạt, exit0. Số trong XML/log là căn cứ; không cộng các lượt chạy lại thành số test mới.

Tiền kiểm ngoại tuyến trên draft thật đã dựng được5 nhóm tổng hợp vừa cả generation lẫn rendered-review envelope. Bằng chứng tại `backend/storage/context616/all-stage-preflight.json`. Đây không phải kết quả model chạy thật đạt.

Ba DOCX2024–2026, canonical381 proof và snapshot nguồn giữ nguyên. Các lượt thật dùng GPT-OSS medium, đầu ra8192 qua ModelOps trong process thử; defaults DB vẫn `gh/gpt-6-luna`. Không chạy64 câu, reindex, xuất bản, restart, stage, commit hoặc push.

## Các blocker đã tìm thấy

- Guard trước đây chặn đúng nhãn chỉ số sai, nhưng model vẫn phải tự viết binding; đã chuyển sang chọn literal/record.
- Header canonical chưa rõ cần native grid và hai witness độc lập; không nâng hàng đầu hoặc bold thành header tự động.
- Chuỗi số ghép có thể lọt vào menu subject; đã tách vai trò lexical/quantity.
- Review truth bị câu hỏi dẫn hướng; đã tách khỏi coverage và giữ mọi verdict thất bại.
- Native proof chưa đi đủ tới tổng hợp; đã giữ candidate/hai dòng mẫu/format cùng nguyên văn nguồn.
- Gói tạo section có thể vừa nhưng gói review nội dung server-rendered vượt giới hạn. Planner mới đo trước cả hai; không cắt raw source.
- Sửa semantic tối đa một candidate, chỉ chấp nhận binding thay đổi và review mới đạt. ID mới/đảo proof/verdict mới cho cùng assertion cũ không phải sửa thành công.

## Thử thật chưa đạt và các lượt dừng

Lượt8 hoàn tất lưu/đọc nhưng `needs_attention` do subject số ghép, coverage header trống và review tổng hợp thiếu native proof. Lượt9 dừng `topic_unit_budget`,0 inference mới. Lượt10 dừng `single_assertion_synthesis_budget`,19 inference mới. Lượt11 dừng `single_review_item_budget`,45 inference mới. Các lỗi này được giữ nguyên trong artifact; không gọi là PASS.

Lượt12 bị ngắt sau6 receipt import,0 inference mới; job fixture được ghi uncertain qua service hiện có, không giả thành completed. Lượt13 dừng theo yêu cầu kiểm kê token,128 stage quan sát,0 inference mới. Không tự gửi lại một intent đang dở.

Receipt wire của18 bước trích xuất/review đã hoàn tất ở lượt11 được dựng dẫn xuất sau lượt chạy khi adapter/schema/prompt của các contract ấy chưa đổi. Artifact ghi rõ `captured_at_inference=false`; không gọi đó là wire được capture ngay lúc inference hay inference mới. Chỉ dùng trong fixture nghiệm thu với fingerprint khớp và mỗi receipt một lần. Chưa có kết quả cuối cho lượt13.

Ba full regression giữa quá trình đã bị dừng khi phát hiện batch còn thay đổi: **INCOMPLETE**, không ghép kết quả. Full cuối trên bản mã hiện tại **NOT RUN**. Baseline đúng là `context614/final-validation/full-final.xml`:3622PASS/18FAIL nền/17SKIP, thêm23 subtest PASS; không dùng XML acceptance-final cũ3618PASS thay baseline cuối.

## Kiểm kê token ngày24/10/2026

| Lớp | Giá trị xác minh |
|---|---|
| CompilerPolicy mặc định | Context24000, output2500 |
| WikiPolicy mặc định | Context24000, output2500; packet24000 **ký tự** |
| Script thử616 | GPT-OSS medium, context24000, output8192; process override, không phải giới hạn model đã xác minh |
| ModelOps model capacity profiles | Không có profile `token_limits` nào được khai báo |
| Chatbot tuyển sinh DB | gh/gpt-6-luna; max_tokens5000; thinking_budget0; không fallback |
| ModelOps request schema | max_tokens mặc định2000; không phải context vật lý của model |
| Form chatbot schema | max_tokens128–32000; thinking_budget0–4096 là tham số tương thích cũ |
| Quota tháng10/2026 | monthly_token_limit0, không blocked;0 nghĩa là không đặt quota token tháng |

Phép ước lượng đầu vào hiện dùng số byte UTF-8 của messages cộng1024 framing, **không phải tokenizer chính xác**. Vì vậy `input_upper_bound` có thể lớn hơn nhiều so với prompt_tokens provider báo. Trần24000 là fallback phần mềm, chưa chứng minh model thực tế hết context.

Người dùng yêu cầu bỏ kiểu ghim trần tùy ý. Chưa thay model/defaults/profile/DB trong lượt kiểm kê này. Việc tiếp theo là phân giải capacity thật của model/endpoint và thay fallback/override cố định bằng chính sách động; không tự chọn một con số khác hoặc gọi model vô hạn. Giữ chia nhóm và Quality Gate.

## Môi trường và bàn giao

DB/MinIO/Qdrant loopback đã tiền kiểm; unit/full dùng DB có nonce và LocalStorage riêng. Shared DB chỉ đọc cấu hình/seals cùng các ghi usage/lease hợp lệ của ModelOps. Không migration/DDL nguồn thật. Không kiểm lại vector trong lượt này nên không tuyên bố hash vector đã xác minh.

DB thử checks-final, checks-acceptance, checks-gate, checks-repair đã dọn theo nonce. DB `checks` chứa ba fixture/compiler receipt và `checks-semantic-final` còn giữ để tiếp tục; không dọn khi đang cần bàn giao. Storage bằng chứng giữ theo chính sách bảo vệ, không retry/bypass thao tác xóa đệ quy đã bị chặn ở các phiên trước. Chưa hoàn tất cleanup toàn phiên.

Không APPROVED toàn compiler, không có benchmark64 hoặc published-chatbot E2E PASS. Cần tiếp tục từ trạng thái này, kiểm tra process/receipt trước khi gửi inference tiếp, hoàn tất live validation, full test-ID comparison và cleanup sau khi thống nhất cách phân giải capacity.
