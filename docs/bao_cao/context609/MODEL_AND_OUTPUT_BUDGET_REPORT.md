# Context609 — Thử GPT-OSS và điều tra ngân sách đầu ra

Ngày 23/10/2026. Người dùng yêu cầu thử `ollama/gpt-oss:120b`, sau đó hỏi nguyên nhân hết 2.500 token và khả năng tăng đầu ra. Đây là thí nghiệm qua ModelOps/9router, không chuyển model mặc định, không thay mã ứng dụng hoặc Quality Gate.

## Kết quả quan sát

| ID | Kết quả | Bằng chứng và giới hạn |
|---|---|---|
| OSS-JSON-01 | PASS | Gọi thật, 1.560,13 ms; JSON đúng năm tổng hợp 2032 và ngày đầy đủ null; 2.126 input/109 output, finish=stop. |
| OSS-COMPILER-01 | FAIL | Ba DOCX 2024–2026 được ghim hash, dùng lại 381 proof của parser602. Bước chọn đầu tiên trả JSON hợp lệ: 6.151 input/1.950 output, 763 ký tự nội dung, finish=stop. Bước chọn độc lập tiếp theo lỗi MODEL_OUTPUT_BUDGET_EXHAUSTED. API create HTTP503 sau 13.956,23 ms, job uncertain, bundle null. Chưa đến bước trích assertions hoặc biên soạn hoàn chỉnh. |
| OSS-ROUTE-01 | PASS | Requested alias ollama/gpt-oss:120b; provider báo served model gpt-oss:120b. Hai usage thành công không có fallback. Usage của lượt thất bại không được lưu, không coi bằng 0. |
| OSS-INVARIANTS-01 | PASS | 457 file app Python không đổi; nguồn, knowledge rows, defaults/admissions và danh mục model giữ nguyên. Primary vẫn gh/gpt-6-luna. Qdrant 2.943 points, full payload khớp baseline602, 0 retrievable, không publication. |
| OSS-ISOLATION-01 | PASS | Development, DB/MinIO/Qdrant loopback. Compiler dùng DB local riêng có ownership nonce và LocalStorage riêng, không migration shared DB. DB thử đã xóa theo đúng ownership; Storage giữ lại theo chính sách bảo vệ. |
| OSS-HIGHER-OUTPUT-01 | NOT RUN | Chưa gọi lại với 4.096/8.192 token, chưa đổi policy hoặc mặc định. |

Process helper hoàn tất không có nghĩa compiler PASS: tiêu chí compiler ở đây là HTTP503/uncertain/bundle null, nên giữ FAIL. Không gọi lại job uncertain.

## Vì sao hết 2.500 token?

`WikiPolicy.max_output_tokens` mặc định 2.500. `compilation_modelops.generator` tạo `WikiPolicy()` riêng; giá trị chat max_tokens trong giao diện trợ lý không tự đổi ngân sách compiler. Cả WikiPolicy và LLMGenerateRequest hiện chấp nhận tối đa 8.192.

Decoder phát MODEL_OUTPUT_BUDGET_EXHAUSTED khi upstream trả finish_reason=length. Nhật ký đúng lượt xác nhận mã lỗi này; ModelOps bọc lại thành ALL_PROVIDERS_UNAVAILABLE/HTTP503. Đây là đầu ra chưa hoàn thành trong ngân sách yêu cầu; không phải bằng chứng model thực sự sinh vượt giới hạn, hoặc thiếu context. Chưa lưu được raw response/usage của lượt lỗi nên chưa xác định độ dài JSON dở dang hay số token suy luận chính xác.

GPT-OSS có cơ chế suy luận; nội dung JSON người dùng nhìn thấy có thể ngắn hơn tổng token đã sinh. Lượt thành công 763 ký tự nhưng provider ghi 1.950 output là dấu hiệu cần quan sát thêm, không đủ để tính lượng reasoning. Adapter hiện chỉ gửi enable_thinking=true khi giá trị thinking bật; thinking_budget=0 không gửi yêu cầu tắt hoặc reasoning_effort. Vì vậy không thể suy từ nhãn “0 = tắt” rằng đường 9router→GPT-OSS đã tắt suy luận.

Theo [Ollama Thinking](https://docs.ollama.com/capabilities/thinking), điều khiển suy luận phụ thuộc model và mặc định runtime. [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility) hỗ trợ max_tokens và reasoning_effort. [Model card chính thức](https://huggingface.co/openai/gpt-oss-120b) mô tả mức low/medium/high. Chưa kiểm chứng phiên bản, khả năng chuyển tiếp reasoning_effort hoặc context/output cap thực tế của upstream sau 9router; không lấy thông số model gốc làm cấu hình runtime đã xác nhận.

## Có thể tăng đến đâu?

8.192 token là trần request hiện tại của app, không phải kết luận về trần model/provider. Không nên đặt vô hạn hoặc chỉ đổi một hằng số. Compiler kiểm cả ngân sách đầu vào, đầu ra và dự phòng sửa phản hồi trong workflow 24.000 token.

Preflight các draft packet ghi nhận input upper bound lớn nhất 19.197; đây là ước lượng bảo thủ theo byte UTF-8 và framing, không phải số token thực đo. Chưa phải max của mọi lượt động hoặc correction.

| Đầu ra dự phòng | Tổng với input bound 19.197, chưa thêm feedback | So với workflow 24.000 |
|---|---:|---|
| 2.500 | 21.697 | Vừa |
| 4.096 | 23.293 | Vừa ở bước này |
| 8.192 | 27.389 | Không vừa |

Để dự phòng 8.192 trong workflow 24.000, input upper bound phải không quá 15.808 trước phần dự phòng feedback. Phương án kế tiếp: thử đúng packet lỗi với 4.096 nếu preflight của packet đó đạt; nếu cần 8.192, đóng gói lại input và giữ đầy đủ proof ledger/context closure. Truyền cùng policy qua packing, preflight, request thực, cache/configuration hash và kiểm tra kết quả; không tăng riêng adapter rồi để các phần khác vẫn dự phòng 2.500. Không cắt bằng chứng hoặc hạ validation để vừa ngân sách. Chưa triển khai phương án này.

## Bằng chứng và tái kiểm

Artifact local, không đưa corpus/prompt/raw riêng vào Git:

- `backend/storage/context609/probe/result.json`: probe tổng hợp.
- `backend/storage/context609/live-oss/{preflight,phase-summary,response-shapes,create-response,run-complete}.json`: compiler và hình dạng đầu ra.
- `backend/storage/context609/live-oss/runtime-private.log`: mã lỗi gốc; không sao chép toàn log vào báo cáo.
- `backend/storage/context609/{usage-summary,postcheck-final,shared-row-verification}.json`: usage và bất biến.
- `backend/storage/context609/live-checks/isolation.json`: DB đã dọn, Storage còn lưu.

Helpers trong `.antigravity-bridge/validation/`: context609_probe_oss.py, context609_live_oss.py, context609_live_checks.py, context609_postcheck.py. Không chạy lại helper create/probe vì đã có intent/receipt; chưa có lý do resend. Thí nghiệm gọi inference thật, API compiler ASGI thật trong DB cô lập; không phải browser E2E, không parser mới, không chứng nhận toàn source Quality Gate, không benchmark64.

Không sửa app trong Context609 nên không chạy lại full Pytest/Ruff/FE. Full Context608 3.564 PASS/18 FAIL nền/17 SKIP là lịch sử, không phải full PASS của lượt này. Không reindex, approve/publish, restart/deploy, stage/commit/push. Chưa đủ bằng chứng nghiệm thu GPT-OSS cho toàn compiler.
