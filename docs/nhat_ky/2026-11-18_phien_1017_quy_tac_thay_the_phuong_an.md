# Phiên 1017 — Chặng C: prompt v39 và mở cổng gọi lại khi chỉ thiếu nhóm nối câu

Ngày: 2026-11-18. Phạm vi được duyệt: lớp trả lời (prompt + cổng appeal); không reindex, không đổi dữ liệu/index.

## Yêu cầu và giả định

- Sau Chặng A (phiên 1016), Q01 vẫn chỉ trả lời 1/4 lượt dù trace truy xuất trùng khít 4 lượt: abstain là quyết định phía sinh. Chặng C (được duyệt) thêm một quy tắc generic vào prompt cho lớp câu hỏi **đề nghị dùng kết quả của phương án này thay cho phương án khác** (Q01: dùng điểm tổ hợp Toán, Văn, Địa thay cho Toán, Lý, Hóa).
- Giả định kiểm chứng được: nếu model nhận quy tắc "danh mục đóng quyết định, quy định quy đổi công bố sau không phải lý do insufficient_evidence", Q01 sẽ kết luận đúng thay vì abstain. Kết quả bên dưới cho thấy prompt một mình **chưa đủ**; nút chặn thật là cổng appeal đếm nhầm nhóm nối câu tuỳ chọn.

## Thay đổi mã (2 tệp)

- `backendV1/qnu/domains/rag/answer/drafting.py`: `PROMPT_VERSION` `qnu.rag.answer/v38` → `qnu.rag.answer/v39`; thêm một quy tắc: khi người hỏi đề nghị dùng kết quả/điểm/chứng chỉ của một phương án cho vị trí phương án khác của cùng đối tượng, đây là câu hỏi danh mục — phương án chỉ thay được khi thuộc danh mục đã nêu hoặc nguồn nêu rõ quy tắc cho phép; nếu không, kết luận rõ "không được dùng thay" kèm dẫn chứng; quy định quy đổi công bố sau không làm đổi kết luận và **không phải lý do insufficient_evidence**; kết luận không phụ thuộc việc người hỏi có nêu tên đối tượng.
- `backendV1/qnu/domains/rag/answer/coverage.py`: sửa `plan_ready` — bỏ qua nhóm `kind == "continuation"` khi xét "kế hoạch đã sẵn sàng". Nhóm nối câu chỉ hoàn thiện một câu bị cắt, mang `optional: True`, đã bị packing bỏ qua khi cần (`protected=group["kind"] != "continuation"`), `bounded_scope` không tính, và coverage `_structures` không tính là yêu cầu câu hỏi — chỉ mỗi `plan_ready` còn đếm, khiến appeal bị chặn oan cho Q01. Một caller duy nhất: `service.py:459`. Thêm docstring giải thích.
- Không đổi prompt lần hai, schema, dữ liệu, index; không commit/push.

## Kiểm chứng mã

- `ruff check` + `ruff format --check` tệp `coverage.py`: PASS.
- Import smoke `plan_ready` với plan chỉ có nhóm continuation thiếu đơn vị: trả `True` (PASS).
- API `:8002` khởi động lại nạp mã mới (health 200; mọi lượt đo mang `prompt_version = qnu.rag.answer/v39`).

## Đo live (nguyên corpus/index `idx_a88196a1f0ba`, gen 2, 184 chunk)

**Baseline v39 trước sửa cổng (bộ 12 câu, `qnu_rules_eval_v39full.json`):** Q01 `insufficient_evidence` với `appeal.attempted=false, outcome=skipped_structure`; Q04 abstain đúng (đối tượng "Quản trị hàng không" ngoài danh mục) cũng `skipped_structure`; Q02 phủ định đúng; Q03 phủ định đúng; Q05 hoãn kết luận đúng (thiếu điểm chuẩn); Q08 đúng ("1,4"); Q09 đúng (loại PT3); Q10 phủ định ngầm (điểm mở đã biết); Q11 đủ 8/8 ngành; Q12 đúng tổng đài; Q06/Q07 giữ 409 đã biết. Q01 lặp ×3 trước sửa cổng: **0/3** (cả ba `skipped_structure`) — prompt v39 một mình không mở được đường gọi lại.

**Sau sửa cổng — Q01 lặp ×3 (`qnu_q01_repeat_gate_1019.json`):** lượt 1 appeal chạy nhưng `still_insufficient` (model vẫn nói "chưa có tài liệu nêu quy định thay thế"); lượt 2 appeal `answered` (kết luận đúng nhưng vòng vèo); lượt 3 appeal `answered` với phủ định gọn theo phạm vi: "…thí sinh không thể dùng kết quả của tổ hợp thứ nhất để thay thế cho tổ hợp thứ hai. [E15]". **2/3 trả lời, 1/3 abstain trung thực** (trước sửa: 0/3).

**Sau sửa cổng — bộ 12 câu (`qnu_rules_eval_gatefix.json`):**

| Câu | v39 trước sửa cổng | v39 + sửa cổng | Nhận xét |
|---|---|---|---|
| Q01 | abstain, `skipped_structure` | **answered qua appeal** (`attempted=true, outcome=answered`), phủ định đúng theo danh mục kèm [E14][E15][E16][E17] | Đúng nút chặn; cổng mở đúng thiết kế |
| Q02 | answered (không appeal) | answered qua appeal, phủ định đúng | Không hồi quy |
| Q03 | answered | answered (không appeal), phủ định đúng | Không đổi |
| Q04 | abstain đúng, `skipped_structure` | **abstain đúng giữ nguyên**; appeal `attempted=true → still_insufficient` (một lượt gọi lại, model vẫn từ chối, không bịa) | Hành vi mong muốn: thử lại có kiểm soát rồi vẫn abstain |
| Q05 | answered (hoãn kết luận) | answered qua appeal, hoãn kết luận đúng | Không hồi quy |
| Q06/Q07 | 409 `answer_scope_clarification_required` | 409 giữ nguyên | Đã biết |
| Q08 | answered đúng | answered đúng (không appeal) | Không đổi |
| Q09 | answered đúng (loại PT3) | answered đúng (không appeal) | Không đổi |
| Q10 | answered (phủ định ngầm) | answered, cùng nội dung quy đổi IELTS | Điểm mở giữ nguyên |
| Q11 | đủ 8/8 ngành | đủ 8/8 ngành | Không đổi |
| Q12 | đúng tổng đài | đúng tổng đài | Không đổi |

- Trace mọi lượt: `prompt_version = qnu.rag.answer/v39`; appeal ghi ở `trace.appeal` (kết quả cuối sau khi thay bằng lượt gọi lại không còn trường `appeal` cấp ngoài).
- Kết luận trung thực: (1) prompt v39 một mình không sửa được Q01 trong lần đo này; (2) sửa cổng theo đúng mô hình nhóm nối câu hiện có mở lại lượt gọi lại đã thiết kế cho Q01/Q02/Q04/Q05; (3) Q01 lên 3/4 lượt trả lời đúng trong ngày đo (2/3 lặp + 1 suite), 1/4 abstain trung thực; phần dao động còn lại nằm ở quyết định sinh của model, không phải truy xuất hay cổng.

## Vệ sinh dữ liệu

- Đã lưu trữ qua lifecycle 36/36 hội thoại kiểm thử của phiên 1016–1017 (12 câu Chặng A + lượt đuôi + Q01 lặp, 12 câu v39full, 3 lượt Q01 trước sửa cổng, 3 lượt sau sửa cổng, 12 câu gatefix); tất cả về `completed`.

## Không chạy / chưa chứng minh

- **pytest/full suite: NOT RUN** (theo quy định hiện hành).
- **12 câu Kiri: NOT RUN** — danh sách câu ledger không còn lưu trữ, không tái lập bằng câu đoán.
- Chưa chứng minh hành vi trên kho khác/đường nhiều kho; corpus đo duy nhất là bộ tuyển sinh hiện hành.
- Không commit/push/deploy; không đổi `.env`, dữ liệu, index.

## Rủi ro và bước sau

- Cổng mới làm appeal chạy cho mọi lượt `insufficient_evidence` có kế hoạch chỉ thiếu nhóm nối câu — chi phí thêm tối đa một lượt gọi model cho các lượt abstain đó (Q04 là ví dụ: thử lại rồi vẫn abstain). Đây là ngân sách đã thiết kế của `APPEAL_VERSION v4`, không phải nới guard.
- Q01 còn 1/4 abstain do model; nếu muốn ổn định hơn nữa cần hướng khác (ví dụ buộc trích dẫn mục danh mục khi câu hỏi thay thế), phải đo riêng và được duyệt.
- Q10 (phủ định ngầm) vẫn mở; Q06/Q07 409 là hành vi đã biết.
