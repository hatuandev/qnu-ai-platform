# Phiên 784 — Kiểm tra độc lập kết quả prompt phiên783

## Phạm vi

Người dùng đã chạy prompt review/retest và yêu cầu xem kết quả. Đọc nhật ký783, report JSON, harness tạm, mã evaluator và DB chỉ đọc. Không sửa ứng dụng/harness783, không gọi model, không đổi key/config/nguồn/index hoặc kết quả gốc.

Áp dụng skill qnu-rag-evaluation và clean-code. Báo cáo review sau đây phân biệt số đo được xác minh với nhận định chưa có bằng chứng.

## Kết quả thực xác minh

- Cohort retest16-782 có16record/16ID đúng câu hỏi benchmark: **7 PASS / 9 FAIL / 0 NOT_RUN**.
- DB có16turn/16idempotency-key/16conversation riêng,12completed/4failed. Ledger có16embedding,16rerank,16chat; attempt đều1, tổng usage535208token đã đo, không cótokenunknown trong tập audit. Không thấy retry trong lượt này.
- Replay evaluator offline trên12response đã lưu cho đúng7PASS/5FAILabstain;4lượt còn lại lỗi model/backend nên không córesponse để chấm. Replay không gọi retrieval/model và không ghi đèreport.
-12response đều đúng provider/index/promptv9; với các câu có response cũ, configuration_hash khớp. Không dùng12response để chứng minh cấu hình của mọi request lỗi đã được khóa bằng harness.
-7PASS: F18, I25-07, BC24-02, BC24-04, BC24-10, MX-01, MX-04.
-9FAIL: F13/BC24-05response_invalid;F14/I25-04output_truncated;I25-05/BC24-08/MX-02/MX-05/MX-10model_abstained.
- Checkpoint53cũ vẫn FAIL/trỏ report780 với37PASS16FAIL. Không gộp7PASS mới vào53cũ. MX-01cũ được DB ghi uncertain/conversation_turn_interrupted; MX-01PASS mới là turn riêng.
- Số compilation review của3compiler hiện dùng vẫn0: đây là review mã/bằng chứng và retest câu hỏi, không có report AI review compiler mới. Prompt chỉ yêu cầu điều kiện khi chạy AI review, không bắt buộc tự thêm lượt này.

## Findings

### P1 — Playwright báo xanh dù9câu FAIL

tmp/retest16.spec.ts kết thúc bằng console.log, không assert cuối theo failed/not_run/halted. Toàn bộ lỗi từng câu bị catch rồi ghi JSON; tmp/run_retest16.py chỉ trả process.returncode. Vì vậy tmp/results.json có expected1/unexpected0 dù JSON có9FAIL.

Đây là false-green của orchestration, không làm7PASS riêng lẻ mất giá trị nhưng không được dùng trạng thái Playwright để nghiệm thu cohort. Cần giữ việc hỏi hết rồi assert số câu/sai/chưa chạy và trả exitnonzero; bảo toàn report lỗi trước assertion.

### P2 — Scope single có thể mở thành all nếu thiếu binding

tmp/retest16.spec.ts:90–103 chỉ gán documentIds khi tìm được binding; nếu thiếu, vẫn POSTconversation vớiundefined, tương đương toànkho. Bộ chấm có thể bắt citation sai nhưng request đã mở phạm vi trước model. Lượt hiện tại đủbinding nên chưa có bằng chứng truy xuất sai scope; đây là guardhồiquy cho lần chạy khác.

Cần failclosed và tái sử dụng askAdmissionQuestion hoặc logic kiểm scope hiện có thay vì nhân bản thiếuguard.

### P2 — Fingerprint được chép từ checkpoint, không khóa lại cấu hình thực

Harness đọc index/provider/budget/reranker nhưng không gọi freezeCohort, không đọc/đốichiếu assistantconfig và không kiểm prompt/configtrace từng câu. Report fingerprints.cohort lấy nguyên giá trị cũ. Các giá trị thực của12response hiện khớp ở phần audit được, nhưng report chưa đủ chứng minh không đổi giữa các request hoặc cho những request lỗi.

Ngoài ra report không lưuconversation/turn/idempotency-key mỗi câu; khóacohort cố định sẽ replay nếu chạy lại harness cùngtên. Lượt hiện tại DBđã chứng minh16turn mới, nhưng harness không tự phân biệt replay/fresh và không nên dùng nguyên như một runner nghiệmthu bềnvững.

### P2 — Một số nội dung nhật ký783 sai nguồn hoặc kết luận quá mức

- Bảng IELTS thực tế ởtrang vật lý9, ba mức quyđổi; nhật ký ghi trang6 và dãy mức khác. Canonical đã kiểm hash781 vẫn làbằng chứng hiện có.
- MX-02 thực tế hỏi chỉtiêu SưphạmTin2025 và điểmTHPT2026; MX-10 hỏi số lượng BìnhĐịnh2024 và ngưỡng CNTT2026. Các mô tả họcphí/ngânsách trong nhật ký không phải câu benchmark.
- Không phải toàn bộ tài liệu thứhai rơi khỏicontext: retestMX-02 có15chunk2026/5chunk2025;MX-10 có13chunk2026/7chunk2024. Vấn đề là thiếu đúngfact/ô cần thiết; không kết luận chỉmột tài liệu vào prompt.
- MX-01PASS dùng2tài liệu, không phải3 như bảngnhật ký ghi.
- F13 mới lỗi answer_response_invalid trước evaluator, nên không dùng lỗi checker củaF13cũ để giải thích failure mới này.
- Không córaw/errorpath để khẳng định cụ thể JSON thiếufield/bọcMarkdown. Chưa córeasoningtokenraw để kết luận hai lỗi length đều do suy luận; tasknotconfigured chỉ chứng minh directiveanswer chưa áp.
- Câu kết luận “không có hallucination, mọi nguyên nhân xác đáng/tuyệt đối” không được chứng minh. Prosecompiler sai metric đã được phát hiện; một số quyết định model chưa thểgiải thích từ raw.

Không sửa nhật ký783 âmthầm; bản784 ghi đốichiếu và mức tin cậy để người dùng dùng đúng số đo.

## Nhận xét

Đợt prompt làm được phần thực nghiệm có giá trị:16request mới/mộtlần, giữ bộchấm chung, giữ báo cáo cũ, quan sát cùngnhóm lỗi lặp lại. Tuy nhiên không triển khai sửaapp và7câu tự đổiPASS là dấuhiệu thiếu ổnđịnh đầu cuối, không chứngminh đã sửa lỗi.

Cần sửa tính trung thực của runner/report trước nghiệmthu tiếp; sau đó xử lý bảngheader/numericaxis, compiler giữ nghĩa, coverage từngý và schema/answerreasoning như khuyếnnghị781. Không chạy lại model trong phiênreview này.

## Bằng chứng và kiểm tra

- Report: tmp/v1-e2e/93faa11f0caf/runs/admissions-retest16-1793513615753840800/retest16-answers.json.
- Harness: tmp/retest16.spec.ts, tmp/run_retest16.py; Playwright summary tmp/results.json.
- Audit chỉđọc: tmp/audit784.json. Offline evaluator: node tmp/recheck784.cjs;12response khớp7PASS/5FAIL, không API/modelcall. Lần chạyđầu helper sai đườngdẫn typescript đã sửa riêngfiletmp, không độngapp.
- Diff/UTF-8/LF/liênkếtmemory được kiểmtra; khôngfullsuite cho review/tài liệu thuần.
