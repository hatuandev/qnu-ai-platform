# Phiên 787 — Review độc lập lượt retest9

## Phạm vi

User đã chạy prompt retest và yêu cầu xem kết quả. Áp dụng qnu-rag-evaluation/clean-code. Đọc diff, runner/core/evaluator, report786, code answer và DB chỉ đọc. Không sửa ứng dụng, cấu hình, benchmark/gold, cohort cũ; không gọi model hoặc chạy lại câu hỏi.

## Kết quả xác minh

- Cohort `retest9-786-1793515952895`: **0 PASS / 9 FAIL / 0 NOT_RUN / 0 UNCERTAIN**, đủ9ID yêu cầu. Playwright có1 unexpected/0expected/0flaky,165.586s (~2.76phút). False-green cuối runner đã được sửa cho lượt này.
- DB có9conversation riêng,9turn riêng,9idempotency-key khớp report; mỗi conversation đúng1turn. Có9embedding/9rerank/9chat execution, toàn attempt1/codeok; usage314421token,0unknown. Không thấy retry trong tập ledger này.
- Snapshot cả9conversation: assistantrevision2/output16384/context98304byte. Năm response hoàn tất khớp DB/report, promptv9, cùng config/inferencehash, reasoning off/applied/valuefalse. Bốn failed turn không lưu response trace/raw nên không khẳng định đã đo reasoning0 riêng từng request; compiler probe785 không thay phép đo này.
- F13: backend completed, evaluator FAIL do không có một statement đơn lẻ đồng thời chứa15,THPTvàngoạilệ. Model tách15/THPT và ngoại lệ thành2statement cùngE1. Đây là giới hạn checker thực tế; chưa tự đổiPASS. Rubric còn yêu cầu giữ đối tượng tốt nghiệp2026; câu trả lời mới chỉ nói “theo thông báo năm2026”, cần kiểm nghĩa trước khi công nhận toàn bộđúng.
- F14/I25-04/BC24-08/MX-05: DBfailed/answer_response_invalid. Không có chat_output_truncated trong lượt9này. Upstream executionsuccess không chứng minh parse/schema hợp lệ.
- I25-05/BC24-05/MX-02/MX-10: backendcompleted nhưng insufficient_evidence; evaluatorFAIL vì nhãn answerable. Không có lỗi provider/quota làm nền cho bốn abstain này. Abstain đơn thuần không chứng minh thiếu đúngfact/cell ở context; cần kiểm snapshot evidence/catalog tương ứng trước kết luận chi tiết.

## Findings còn lại trong runner/report

### P2 — Drift detection chưa dừng cohort đầy đủ

`tmp/retest9.spec.ts:157–180` chỉ đọc lại assistant/reasoning; chat provider/reranker/indexmanifest vẫn dùng object preflight. Fingerprint core không chứa capacity/endpoint/embeddingconfig; không có đối chiếu trace sau mỗi câu. Vì vậy chưa chứng minh được freeze toàn cấu hình như prompt yêu cầu.

Ngoài ra checkConfigDrift ném `DRIFT_DETECTED`, nhưng catch ở dòng296 gọi stopsAdmissionsCohort, regex hiện không nhận mã này. Probe offline gọi đúng helper/classifier trảfalse: drift bị ghiFAIL của câu hiện tại, không halted; nếu config đổi lại, câu sau có thể tiếp tục. Không có bằng chứng drift thực xảy ra trong cohort786; đây là lỗ hổng guard cho lần sau.

### P2 — Uncertain terminal bị coi như failure thường

`tmp/retest9.spec.ts:250–253` gộp statusfailed/uncertain → recordFAIL, không sethalted. Lỗi mạng trong GETwait cũng đi vào catch có thể đểFAIL thay vìUNCERTAIN. Prompt yêu cầu uncertain giữ nguyên và dừng phần chưagửi; hiện chưa đảm bảo. GET sauPOSTerror lấyturnđầu tiên thay vìđối chiếu turnkey/requestidentity. DB lượt này toànterminal5completed/4failed nên chưa ảnh hưởng kết quả9thực tế.

### P2 — Kiểm thử “không dispatch trùng” chưa chứng minh hành vi

Unit phần idempotency chỉ kiểm9ID duy nhất. Không có kiểm boundary dispatch/resume để chứng minh không gửi lại khi crash/uncertain. assertRunnerCompletion cũng không kiểm dispatched/turnidentity: probe synthetic toànrecordsPASS nhưngdispatchedfalse/dispatched0 vẫn được chấp nhận. Không làm0/9thànhPASS ở lượt này; cần guard thực trước dùng runner nghiệmthu tiếp.

### P2 — Báo cáo786 kết luận vượt bằng chứng

- Các dòng schemaerror ghi0/0token là thiếu số đo response, không phải usage0; DB cóusagechat thật cho cả4failedturn. Nên dùngnull hoặcledger khi trườngsplitprompt/completion thiếu.
- Code hiện không truyền output_schema và chỉ validate JSON saucall; đúng là khoảng trống contract. Nhưng chưa lưu raw/ValidationErrorpath nên chưa biết cụ thể thiếufield,bọcmarkdown hay validator nào thất bại. Không quy toàn nguyên nhân cho thiếuSchema, không hứaSchema ép đúng100%.
- Chỉ có thể nói lượt này không quan sáttruncated; không kết luận triệt tiêuhoàntoàn hay suy luận là nguyên nhân duy nhất khi đồng thời đổioutput/evidencebudget. Tốcđộ mẫu này nhanh hơn không chứng minh mọi workload nhanh tương ứng.
- Không lặp kết luận “mất tài liệu thứhai” từ báo cáo cũ: review784 đã ghi MX-02/MX-10 có cảhai nguồn, thiếu đúngfact khác mấtnguồn. Report786 không lưu snapshotcontext failedđủ để quy lại nguyên nhân từngcase. F13 cócheckerissue nhưng chưa chứng minh toànđápán đúng nguồn/nghĩa.

## Kiểm tra thực chạy và bước tiếp

- `node node_modules/vitest/vitest.mjs run tests/retest9-integrity.test.ts` từfrontendV1:12PASS,exit0. Không model/APIcall từunit.
- `node tmp/review787.cjs`: replay5response cùngevaluator cho5FAIL khớp; probe driftclassifierfalse và synthetic0dispatchaccepted tái hiện gap; exit0 là probe chạy xong, không phải nghiệmthu guardPASS.
- `backendV1/.venv/Scripts/python.exe tmp/audit787.py`: DBtransactionREADONLY, đối chiếu9turn/usage/execution; metadataan toàn `tmp/audit787.json`. Không inkey,khôngđổiDB.
- Fullsuite/appbuild/modelretest NOT RUN vì chỉreview. Giữ kếtquả53cũ37/16, retest16cũ7/9 và retest9mới0/9 riêngbiệt.

Ưu tiên tiếp: sửa guardrunner/báocáo; thêm tracechẩnđoán an toàn và hợpđồngschema cótestnegative; kiểmcheckerF13 cùngđiềukiệnnguồn; sauđó xử lýcatalog bảng và coverage theo từngý. Chưaautofix hoặc retry trongphiênreview.
