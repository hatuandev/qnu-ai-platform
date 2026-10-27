# Context620 — Thử gh/gpt-5.6-luna với capacity tự động

Ngày24/10/2026. **Model gọi được và tốt hơn ở ca5.081; toàn compiler vẫn NOT APPROVED.**

## Model và context đã kiểm tra

User yêu cầu thử `gh/gpt-5.6-luna`, không ghim trần context thủ công. Alias này được gửi nguyên vẹn qua protected ModelOps/9router; provider trả `gpt-5.6-luna`. Không fallback sang model khác. Model là primary của tiến trình thử, không đổi mặc định toàn app (`gh/gpt-6-luna`).

Endpoint công bố **1.050.000 context / 128.000 output** token. Đây là metadata provider, không phải bằng chứng đã stress-test1triệu token. Không gán200K thủ công, không tuyên bố context vật lý vô hạn. Đầu ra từng request được tính từ phần context còn lại và output capacity thật đã khai báo. Tokenizero200k_base lấy từ registry; calibration ghi nhận2.010token template cho system/user.

Probe JSON marker: requestedalias đúng, servedmodel đúng,2035input/17output,stop/0fallback/marker khớp. Lượt compiler cuối dùng66inference; max32452input/1927output, tất cảstop,0fallback,1schema rejection được correction trong giới hạn hiện có. Đếm input cục bộ và provider khớp delta0 ở cả66request. Không có overflow, output truncation hoặc trần phần mềm24K/2500/8192 trong lượt này. Không thử riêng input200K hoặc1triệu để tiết kiệm chi phí; chỉ báo mức input thật đã quan sát.

## Sửa tối thiểu cần thiết để chạy phép thử

Lượt service đầu bị chặn `model_configuration_changed_during_build` trước inference compiler. Khi request capability đã tồn tại, `save_chat_capabilities` vẫn ghi cùng nội dung với observed_at mới. Configuration hash bao gồm row ấy; cache discovery cũng đổi fingerprint, gây calibration lặp và làm guard coi cấu hình đã đổi.

Chỉ sửa `modelops/services/chat_capabilities.py`: nếu endpoint và capabilities hoàn toàn bằng bản ghi hiện tại, không UPDATE/commit hoặc đổi timestamp. Khác endpoint/capability vẫn lưu mới và phải kiểm tra cấu hình như trước. Không bỏ fingerprint, không loại credential khỏi guard, không sửa logic compiler hoặc Quality Gate.

Baseline4test:3PASS/1FAIL, exit1, tái hiện commit thừa. Thêm case qua route resolver/fingerprint thực: năm regression mới đềuPASS. Focused124PASS/exit0; Ruff2filePASS. Full cuối **3764PASS/18FAIL nền/17SKIP**, exit1,798,54giây. Cả18testID và nguyên nhân khớp baseline618(3759/18/17);5ID mớiPASS, không mất test hoặc regression. Suite tổng vẫnFAIL, không gộp subtest lịch sử. [Danh sách lỗi nền](../context617/REVIEW.md).

Đã có một lượt direct-engine chẩn đoán trước sửa, **INCOMPLETE**:16stage hoàn tất,stage17 đang chạy có thể uncertain khi dừng để tránh calibration lặp. Không tiếp tục/resend intent này; không lấy nó làm PASS. Lượt service sau sửa có intent/receipt riêng, chạy đúng code phát hành sau sửa. Probe/calibration và các lượt chẩn đoán được ghi riêng, không gọi tất cả là66inference tổng toàn phiên.

## Nghiệm thu trên cùng ba DOCX

Giữ381canonicalproofs, rawsourcehashes và snapshot `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`. Câu kiểm tra vẫn là: số5.081 trong bảng Giới tính năm2025 là gì, có phải tổng chỉ tiêu tuyển sinh không. Không chạy64câu, không reindex/publish.

Lượt service cuối chạy64stage rồi pause hợp lệ; resume đọc lại checkpoint, chỉ gọi thêm2stage, tổng66. Tạo được nội dung12assertions/3sections nhưng finish bị chặn **`grounded_coverage_review_missing`**, chưa có persisted bundle cuối được chấp nhận. Đã tái dựng từ đúng66checkpoint hoàn tất/rejected với identity/config và Storage hash khớp;0inference thêm, không giả là một E2EPASS.

| Tiêu chí | GPT-OSS Context619 | Luna Context620 |
|---|---|---|
| Dòng5.081 ở đúng bảng Giới tính | Không có assertion đúng target | Có2assertions gắn đúng canonical dòngTổng/Giới tính, scalar5.081 |
| Vai trò năm2025 | Bị gán publication, review từ chối | Data2025, có source proof |
| Tách chỉ tiêu2024 và số nhập học2025 | Lượt trước chưa có kết quả đúng đầy đủ | Các assertion này được truth review hỗ trợ |
| Chỉ tiêu2026 nguồn có5173 | Không đủ kết quả ở lượt trước để so sánh | Vẫn gánunknown/null và dùng câu giới hạn phạm vi làm limitation; truth và synthesis đều từ chối |
| Coverage | Chưa đạt | Còn3packet incomplete;2proof coverage chưa được xử lý đầy đủ và một assertion sai |
| Lưu/biên nhận | Chặn semantic_repair_rejected_candidate_effective | Chặn grounded_coverage_review_missing |
| Nghiệm thu toàn compiler | NOT APPROVED | NOT APPROVED |

Đây là một câu nghiệm thu trên cùng snapshot ba nguồn, không phải benchmark64 hoặc kết luận chất lượng chung của mọi model. Window provider khác nhau theo model; không quy toàn bộ thay đổi chỉ cho độ thông minh. Mọi input của hai lượt đều dưới33K, nên không có bằng chứng lỗi hiện tại do thiếu cửa sổ context200K.

Hai assertion target5081 có cùng nội dung/binding nhưng ID cục bộ khác nhau sau các bước extraction/coverage repair. Đây là nội dung trùng lặp, không phải hai nguồn hoặc hai phép kiểm chứng độc lập; không dùng số lượng này để tăng điểm chất lượng.

Assertion2026 có giá trịnull/unknown, attribute là literal về tổng tuyển sinh đại học chính quy, nhưng source proof chỉ rõ5173 cập nhật từ4500. Limitation được chọn là câu “không tự động áp dụng cho mùa tuyển sinh khác”, chứng minh phạm vi, không chứng minh thiếu giá trị. Guard ngữ nghĩa từ chối là đúng; không đổiunknown thành số hoặc tự approve trong phiên thử model.

Ledger coverage bị thiếu ở packet ban đầu chưa có assertion, sau targeted coverage repair đã có assertion. Validator hiện yêu cầu coverage ledger ở packet sau khi có nội dung. Cần hoàn thiện vòng đời biên nhận riêng, không hạ Quality Gate hoặc gán complete=true. Bundle replay có machine_complete=false và synthesis_complete=false, kể cả tạm bỏ qua lỗi lưu vẫn chưa đủ nghiệm thu.

## Artifact, bảo toàn và giới hạn

- `backend/storage/context620/capacity.json`, probe intent/result: metadata và probe exactalias.
- `compiler-live/`: service đầu0compiler inference FAIL do observation/configuration; giữ nguyên.
- `compiler-direct/`: lượt chẩn đoánINCOMPLETE, không resendintent uncertain.
- `compiler-live-final/`: phases/metrics/receipts, postcheck và independent-review-private,0inference khi review.
- `focused/`, `final/`: baseline/focused/full XML và exitcode; `test-id-comparison.json` giữ exactIDs/cause.

Ba DB thử nghiệm620 được dọn theo nonce sở hữu sau export; Storage bằng chứng giữ policy bảo vệ, không bypass lệnh xóa đã bị chặn. Các DB616 cũ giữ nguyên bàn giao trước.

Nguồn/binding/revision/index/assistant/defaults giữ nguyên. Provider có ghi observation/negotiated capability hợp lệ ở các probe trước sửa; sau sửa service cuối postcheck sáu nhóm shared domain đều giữ. Shared DB chỉ đọc domain/config và ghi lease/usage/capability observation theo ModelOps được phép, không migration dữ liệu nguồn. Không đo lại hash vector payload; không thực hiện vector write, publication, restart/deploy hoặc commit/push.

Một appfile và một testfile thay đổi để sửa prerequisite ModelOps; parser, compiler semantics, source Markdown/JSON và Quality Gate không đổi. Không tiếp tục gọi LLM hoặc sửa thêm thuật toán sau kết quả nghiệm thu này.

Đối soát tiếp ở [Context621](../context621/CAUSE.md) xác định rõ hơn: correction62 đã có assertion5.173đúng và được reviewer hỗ trợ, nhưng cùng candidate còn assertionunknownsai. Candidate bị loại toàn bộ nên bản cuối vẫnunknown. Không diễn giải kết quả620 thành model chưa từng trích được số5.173.
