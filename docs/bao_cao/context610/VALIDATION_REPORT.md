# Context610 — GPT-OSS medium, đầu ra 8.192 và compiler ba DOCX

Ngày 23/10/2026. Yêu cầu: thử GPT-OSS với thinking medium, cấp 8.192 token đầu ra và chạy compiler ba DOCX 2024–2026. Không đổi model mặc định, nguồn, Quality Gate, index/publication hoặc Git.

## Kết quả

**Giới hạn đầu ra hoạt động trong lượt thử; toàn compiler FAIL.** Có 24 inference thật, tất cả finish=stop, không có MODEL_OUTPUT_BUDGET_EXHAUSTED. Compiler dừng trước PacketDraft do kế hoạch gói không vừa ngân sách workflow: HTTP422, reason=single_unit_budget. Chưa có bundle, assertions hoặc Markdown compiler hoàn chỉnh; không APPROVED.

| Chỉ số | Quan sát |
|---|---:|
| Nguồn | 3 DOCX 2024–2026, raw hashes giữ |
| Bằng chứng canonical | 381, dùng lại parser602 |
| Gói chọn bằng chứng | 12, mỗi proof được đưa vào một gói ban đầu |
| TopicSelection thật | 24: chọn và đối chiếu độc lập mỗi gói |
| Model yêu cầu / provider báo | ollama/gpt-oss:120b / gpt-oss:120b |
| Cấu hình gửi thực | reasoning_effort=medium, max_tokens=8192 ở cả 24 request |
| Max output quan sát | 2.795 token |
| Max input quan sát | 5.852 token |
| Tổng usage | 116.435 input / 28.781 output token |
| Phản hồi bị cắt / fallback | 0 / 0 |
| Thời gian API create | 97.227,91 ms |
| Max tổng request dự phòng thực đã gửi | 21.032 / workflow 24.000 |
| Job | kc_97140e757ca449f4b273c0644e736915, uncertain, bundle null |

Có request dùng hơn 2.500 output token, nên không còn áp cap cũ cho lượt này. Đây không phải A/B kiểm soát riêng biến output: reasoning effort cũng được đổi. Không suy rộng thành bảo đảm mọi request tương lai luôn hoàn thành trong 8.192.

Upstream không echo reasoning_effort hoặc công bố reasoning_tokens trong các phản hồi quan sát. Xác minh được medium được gửi tới endpoint 9router cùng request thật và request được phục vụ thành công; chưa có chứng cứ độc lập rằng upstream phía sau router thực thi chính xác mức này. Không lưu/hiển thị nội dung suy luận.

## Nguyên nhân dừng và đối soát ngoại tuyến

Hai lượt chọn giữ lại 192 proof. Đây là tập được giữ an toàn khi có liên quan, chưa phân loại hoặc bất đồng; chưa phải 192 facts đã được xác minh. Compiler hiện giới hạn 4 primary proof/gói, 30 gói và 64 lần gọi. Tập này cần ít nhất 48 gói; riêng draft/review đã ít nhất 96 calls, chưa tính 24 selection và tổng hợp.

Lỗi xảy ra trước ở một gói đơn: input + output 8.192 + dự phòng review đạt tối đa 26.699, lớn hơn workflow 24.000. Mọi draft đơn vẫn vừa nếu bỏ phần dự phòng review, nhưng không được bỏ dự phòng để coi toàn kế hoạch hợp lệ. Không có request vượt gate này được gửi lên model.

| Phương án mô phỏng, chưa gọi LLM | Kết quả |
|---|---|
| Context24K, primary4, output8192 | FAIL single_unit_budget |
| Context32K, primary4, output8192 | FAIL packet_count_budget |
| Context32K, primary12, output8192 | Xếp được 22 gói, max reserved31.909; tối thiểu68calls trước coverage/synthesis/direction, vẫn vượt64 |
| Context32K, primary24, output8192 | Vẫn22gói, max reserved31.981; tối thiểu68calls |

32K chỉ là mô phỏng planner, không đổi cấu hình đang chạy và không chứng nhận context cap của upstream. Không tăng total call/time limits hoặc gửi lại job uncertain để cố đạt PASS.

Tiền kiểm ban đầu của tôi chỉ bao phủ chọn bằng chứng: 12 gói/381 proof, output reserve8192 và scope metadata đều vừa. Nó chưa bao phủ kế hoạch trích xuất/review nên chưa phát hiện blocker này trước 24 calls. Đã bổ sung chẩn đoán ngoại tuyến toàn kế hoạch từ hai kết quả chọn đã lưu; không gọi lại LLM. Key `all_draft_packets_fit` trong preflight helper kế thừa thực tế đo các request TopicSelection, không phải chứng nhận draft/review hoặc toàn compiler.

## Phạm vi thực thi và bảo vệ

Không sửa mã ứng dụng. Helper thí nghiệm chỉ cấu hình trong process: cùng WikiPolicy output8192/context24000 cho packing, preflight, request thực và configuration hash; route thử gắn medium/output vào experiment identity. Adapter request được bổ sung đúng reasoning_effort=medium trong process riêng, không giả thinking_budget dạng số đã được chuyển thành medium. Trước chạy có control payload, giữ guard truncation và xác minh overrides được trả về sau context.

Actual ASGI compiler handler, actor có quyền và ModelOps/9router thực. DB49tables riêng có ownership nonce, LocalStorage riêng; kiểm tra development/loopback DB, MinIO, Qdrant trước chạy. Shared DB chỉ đọc ngoài usage/lease inference vốn có. Source fixture của thử nghiệm dùng canonical parser602 ghim hash và readiness format-only; không chứng nhận lại toàn source Quality Gate hoặc chạy parser mới. Không frontend/browser E2E, không benchmark64, không phục vụ chatbot.

Postcheck PASS: 457 app Python files, shared collections/bindings/revisions/indexes/assistants/provider rows giữ nguyên; primary defaults và admissions vẫn gh/gpt-6-luna. Qdrant2.943points/full payload khớp baseline602,0retrievable, không publication. DB qnu_test_context610_ba2607c8b8d7 đã xóa sau kiểm ownership và xác nhận không còn; Storage artifact giữ để đối soát theo chính sách bảo vệ hiện hành, không thử vượt chặn dọn Storage.

## Kiểm tra và lệnh thực chạy

Cwd repo root, Python `backend/.venv/Scripts/python.exe`, OPENBLAS_NUM_THREADS=1 chỉ trong shell thử.

| ID | Lệnh/helper | Exit | Đánh giá |
|---|---|---:|---|
| CFG610-01 | Offline adapter controls trong context610_experiment | 0 | PASS5checks: policy8192, medium payload, truncation guard, failed usage observation, override restoration; không inference |
| ENV610-01 | context610_live_checks.py setup | 0 | PASS môi trường/ownership/49tables riêng |
| SEAL610-01 | context610_live_checks.py seals --label before | 0 | PASS baseline hash các row, read-only |
| PLAN610-01 | context610_live_oss.py | 0 | PASS selection preflight12/381; không PASS full plan |
| LIVE610-01 | context610_live_oss.py --execute | 0 | Helper hoàn tất; compiler FAIL HTTP422/uncertain, không lấy exit0 làm PASS |
| BUD610-01 | context610_budget_diagnosis.py | 0 | PASS tái hiện hai blocker và mô phỏng32K; không inference thêm |
| POST610-01 | context610_postcheck.py | 0 | PASS nguồn/app/vector seals |
| SEAL610-02 | context610_live_checks.py seals --label after | 0 | PASS exact shared row hashes |
| CLEAN610-01 | context610_live_checks.py cleanup | 0 | PASS DB ownership/drop/readback; Storage còn giữ |

Full Pytest/Ruff/FE NOT RUN do không đổi app. Full Context608 3.564PASS/18FAIL nền/17SKIP là lịch sử, không coi PASS hiện tại. Kiểm Markdown UTF8/LF/link và git diff --check có phạm vi tài liệu ở bước bàn giao.

Artifact local `backend/storage/context610/`: summary.json, offline/result.json, live-oss/preflight.json, wire-requests.json, wire-completions.json, response-shapes.json, phase-summary.json, create-response.json, run-complete.json, budget-diagnosis-private.json, postcheck-final.json, shared-row-verification.json và live-checks/isolation.json. Các wire/phase files ở live-oss; nội dung private không đưa vào Git. Helpers trong .antigravity-bridge/validation/context610_*.py. Không gọi lại create/probe có intent cũ.

## Hướng xử lý tiếp

Cần sửa chính sách compiler đồng bộ theo model và từng giai đoạn, bao gồm preflight full plan, output/review reserve, giới hạn calls/time và lưu checkpoint cho các giai đoạn đã hoàn tất để resume có hash thay vì lặp selection. Đánh giá cách chia ngữ cảnh bắt buộc và review để giữ đủ proof ledger/scope; không cắt proof, nới semantic validation hoặc tăng mù mọi giới hạn. Thí nghiệm này chưa triển khai các thay đổi ứng dụng đó và chưa đủ để nghiệm thu chất lượng toàn compiler GPT-OSS.
