# Phiên 785 — Tắt suy luận answer và dùng output tối đa

## Phạm vi và thay đổi

Người dùng yêu cầu tắt suy luận và cho output tối đa. Áp dụng cho tác vụ trả lời `answer` của model Qwen hiện tại trong phiên E2E `93faa11f0caf`; giữ task compiler đã off. Dùng skill ModelOps resilience và clean-code. Không đổi model/provider, corpus, index, prompt hoặc retry câu benchmark.

- ModelOps: giữ `chat_template_kwarg/enable_thinking=false`, thêm `answer` vào nhóm off, bảo toàn compiler và các trường không liên quan. Ghi qua API có kiểm quyền/audit.
- Assistant tuyển sinh hiện tại: revision 1 → 2; output 4096 → **16384**, đúng tối đa model đang khai báo; `context_max_bytes` 110592 → **98304** để dành 16384 output và 16384 overhead trong context 131072. Byte evidence là cận dự toán bảo thủ, không phải tokenizer đo thực; guard toàn payload của ModelOps vẫn hoạt động.
- `frontendV1/e2e/stages/admissions-policy.ts`: bỏ chặn cứng 4096; lượt tạo assistant mới lấy `max_output_tokens` đã khai báo, từ chối capacity thiếu hoặc không đủ chỗ cho evidence/overhead.
- `frontendV1/tests/admissions-integrity-775.test.ts`: kiểm output tối đa động 4096/8192/16384/32768 và context thiếu chỗ phải BLOCKED.
- Cập nhật hướng dẫn test; không cập nhật fingerprint của cohort cũ để giả thành cùng cấu hình.

## Kiểm chứng thực chạy

- RED: kiểm tra mới trước sửa helper có **4 FAIL / 33 PASS**, đúng hành vi cap 4096 cũ. Log cục bộ `tmp/budget785-red.log`.
- `node node_modules/vitest/vitest.mjs run tests/admissions-integrity-775.test.ts tests/admissions-pipeline-777.test.ts tests/admissions-replay-764.test.ts` trong frontendV1: **58 PASS**, exit 0.
- Biome hai file source/test: PASS; E2E TypeScript: PASS; `npm run build`: PASS, có cảnh báo bundle lớn vốn có.
- Full frontend `node node_modules/vitest/vitest.mjs run`: **FAIL**, exit 1, 571 PASS / 33 FAIL / 69 file (9 file lỗi). Đối chiếu đủ tên 33 assertion với JSON phiên779: thêm 0, mất 0, đúng tập lỗi nền; không sửa để làm xanh. Log `tmp/vitest785-full.log`. Full backend NOT RUN vì không sửa backend.
- Probe model thật qua `prepare_chat_request(task=answer)` và managed adapter/usage: Qwen nhận output **16384**, directive off/value false; JSON ngắn hợp lệ, finish_reason=stop, **0 ký tự reasoning**, completion 6 token, tổng 33 token, **0.62 giây**. Metadata an toàn ở `tmp/v1-e2e/93faa11f0caf/answer-probe-785.json`; không lưu raw/key. Chỉ một inference, không retry.
- Lượt thao tác đầu đã lưu policy nhưng assertion dùng `effective.answer` không tồn tại trong response API (API hiện chỉ liệt kê compiler/review). Sửa script kiểm policy đã lưu và kiểm directive thực tại inference; không cần sửa backend hoặc restart. Không có model dispatch trước probe thành công.

## Giới hạn và bước tiếp

Probe ngắn xác minh cấu hình, không chứng minh 9 câu lỗi đã được sửa hay benchmark đạt. Chưa chạy lại 16/53 câu, không sửa kết quả lịch sử 37/16 hoặc 7/9. Cấu hình đã đổi: benchmark tiếp theo cần cohort mới có fingerprint cấu hình mới, không tiếp tục/gộp PASS vào cohort cũ. Không cleanup/init/reindex/recompile hoặc restart dịch vụ.

Output tối đa là trần, model hoàn tất sớm vẫn trả ngay; không ép sinh đủ 16384 token. Tăng trần/tắt suy luận không tự giải quyết lỗi schema, evidence hoặc retrieval.
