# Context597 — Ổn định điều kiện nguồn và kiểm chứng RAG

Ngày 22/10/2026. Triển khai đề xuất Context596: giữ nguyên model, nguồn PDF,
canonical, index và Quality Gate. Không reindex, xuất bản, restart, deploy hoặc commit/push.

## Kết quả cuối

<!-- FINAL_RESULTS_START -->
Đã chạy trọn **64 câu** trên mã chốt: **58/60 câu tri thức = 96,67%**, gồm 49/50
câu có đáp án và 9/10 câu ngoài phạm vi nguồn; hội thoại đạt 4/4. Mục tiêu 85% đạt.
**Không có lỗi runtime**; 141/141 trích dẫn khớp tọa độ/hash nguồn.
Còn hai FAIL: **P06 và X09**, phân tích dưới đây.

**765 kiểm thử tập trung PASS**, Ruff trên 14 file PASS, **37 regression mới PASS**.
Full Pytest vẫn **FAIL**: 3.275 PASS / 18 lỗi nền / 17 SKIP, 23 subtests PASS;
từng ID/nguyên nhân khớp Context595,
không lỗi pytest mới hoặc thiếu ID không giải thích. Không tuyên bố toàn RAG hết lỗi.
<!-- FINAL_RESULTS_END -->

## Phương pháp sửa

| Vấn đề | Thay đổi và giới hạn |
|---|---|
| Điều kiện bị mất qua vòng sửa | Lưu mệnh đề nguồn chính xác đã được audit xác định bắt buộc theo câu hỏi/plan, collection và provenance. Vòng sửa sau không tự bỏ nghĩa vụ đó. Không buộc đưa mọi câu trong một đoạn chứng minh rộng vào đáp án. |
| Audit bỏ sót tiền đề ngay từ đầu | Kiểm tra riêng các mệnh đề nguồn chưa có public owner khi audit bản nháp cho rằng đã đủ. Input chỉ gồm câu hỏi, body nguồn, đoạn nguồn server đã gắn và các clause; không có văn bản bản nháp hoặc verdict lịch sử. |
| Gắn điều kiện sai nhánh | Input tách trích đoạn được chọn khỏi block nền; instruction yêu cầu xét đúng nhánh và ngoại lệ/biện pháp thay thế. Định nghĩa để tính không mặc nhiên bắt buộc khi chỉ hỏi trạng thái thiếu dữ liệu. Verdict ngữ nghĩa vẫn do model đánh giá và còn false positive như X09; không dùng từ khóa riêng của benchmark. |
| Budget và scope | ModelOps hiện tại, tối đa hai lượt kiểm tra quan hệ/request, một attempt/lượt, cache theo nội dung và phạm vi. `governs` phải là ID trích đoạn có thật, cùng binding/index/source/hash; không được thay bằng ID block nền. Không tạo annotation, fact hoặc approval đã lưu. |
| Phục hồi quá mức hoặc bị chặn sai | Chỉ chép exact source trong context và kiểm chứng lại. Claim không liên quan đã bị loại không chặn phục hồi claim hợp lệ. Chọn lại giữ claim an toàn trước đó, rồi audit toàn bộ. Loại feedback lịch sử khỏi bước kiểm chứng độc lập. |
| Fact dẫn xuất không có tọa độ | Chỉ canonical có origin và offset hợp lệ mới làm clause nguồn hoặc bằng chứng giữ nguyên clause. Không lấy display text của reviewed fact làm canonical, không thay offset thiếu bằng 0. Đây là lỗi TypeError tái hiện trước sửa. |
| Đoạn trích quá rộng | Thêm ID hẹp cho field có nhãn và vị từ ngày đầy đủ. Giữ whole-body ID, native list, dòng bảng và qualification sau dấu chấm phẩy; không sửa canonical. |
| Tham chiếu F08 | Quote trong user turn vẫn exact. Text tự nhiên so với rewritten query chấp nhận case/whitespace; mã và URL giữ kiểm tra chặt. Không đổi metric, bỏ dấu, đoán synonym hay nới scope. |
| Raw row chưa rõ | Fallback mô tả/quy tắc có thể giữ nguyên dòng được hỏi và trạng thái hạn chế. Consumer số liệu vẫn chặn; unknown không thành 0. N18 ở lượt thứ hai đi qua đường tọa độ hàng có sẵn, nên không quy riêng gain này cho fallback. |
| Nhiễu benchmark | Chạy tuần tự, kiểm lease trước bắt đầu, không chạy model phụ đồng thời. Run-intent và lock ngăn phát lại cùng lượt. Không đổi quota, key, fallback hoặc timeout trong DB. |

Mười file ứng dụng: mới `evidence_obligations.py`, `source_dependency_review.py`;
sửa `evidence_audit.py`, `evidence_indexed_audit.py`, `evidence_passages.py`,
`evidence_verification.py`, `prose_fallback.py`, `source_labels.py`,
`intent_contracts.py`, `schemas.py`. Không đổi API public hoặc migration;
hai bộ nhớ theo dõi là PrivateAttr theo request.

Ba file test mới: `test_evidence_stability_597.py`,
`test_source_dependency_repair_597.py`, `test_source_provenance_boundaries_597.py`.
Test592 đổi tên case-error thành metric-error, giữ kiểm lỗi metric thật; các ca
case/whitespace hợp lệ được thêm riêng. Mapping đổi tên có trong đối chiếu ID.

## Kiểm thử trên mã chốt

| Kiểm tra | Kết quả | Exit / bằng chứng |
|---|---|---|
| Baseline trước batch1 | 7 FAIL / 5 PASS | 1; [JUnit](../../../backend/storage/context597/checks/baseline.xml) |
| Baseline trước batch2 | 4 FAIL đúng lỗi cần sửa | 1; [JUnit](../../../backend/storage/context597/checks-release/baseline-source.xml) |
| Baseline provenance trước batch3 | 6 FAIL đúng lỗi origin/offset và nhánh nguồn | 1; [JUnit](../../../backend/storage/context597/checks-final/baseline-origin.xml) |
| Baseline phạm vi trích đoạn trước batch4 | 4 FAIL đúng lỗi gộp scope | 1; [JUnit](../../../backend/storage/context597/checks-closure/baseline-excerpt.xml) |
| Focused cuối | **765 PASS** | 0; [receipt](../../../backend/storage/context597/checks-closure/focused-closure-run.json) |
| Ruff 14 file | **PASS** | 0; [receipt](../../../backend/storage/context597/checks-closure/ruff-run.json) |
| Full Pytest cuối | **3275 PASS / 18 FAIL / 17 SKIP**, 23 subtests PASS | **1**, full vẫn FAIL; [JUnit](../../../backend/storage/context597/checks-closure/full-closure.xml) |
| Exact comparison với595 | **37 ca mới PASS**, không lỗi mới/đổi nguyên nhân/thiếu ID không giải thích | 0; [comparison](../../../backend/storage/context597/checks-closure/full-closure-comparison.json) |
| Code seal trong full | Không đổi app/test/FE | [seal](../../../backend/storage/context597/checks-closure/full-closure-code-after.json) |

Regression bao gồm đổi scope/revision/hash, mất context, định nghĩa tách nhiều
claim, mã gần giống, quote không exact, ngày phối hợp, native list/table/semicolon,
unknown row chỉ mô tả, source-review cache/budget, reviewed fact có offset None
hoặc offset giả và không đưa nội dung draft vào kiểm tra nguồn.

## Các lượt 64 độc lập

| Mã tại thời điểm chạy | Tri thức | Positive | Negative | Social | FAIL |
|---|---|---|---|---|---|
| Sau batch1, acceptance-final | 53/60 | 44/50 | 9/10 | 4/4 | N18, P06, P07, P08, P14, P16, X09 |
| Sau batch2, acceptance-release | 58/60 | 48/50 | 10/10 | 4/4 | P07 TypeError, P16 semantic incomplete |
| Sau batch3, acceptance-handoff | 57/60 | 47/50 | 10/10 | 4/4 | P10, P13 EVIDENCE_TIMEOUT, P16 |
| Sau batch4, acceptance-verified | **58/60** | **49/50** | **9/10** | **4/4** | **P06, X09** |

Lượt đầu: 139 Luna calls, không fallback/runtime error, 123/123 citations resolve.
Lượt thứ hai: 158 Luna calls, không fallback, 147/147 citations resolve;
P07 có runtime error. Giữ nguyên các kết quả đỏ; không ghép retry thành điểm mới.
Lượt thứ hai phát hiện bind_quote của fact dẫn xuất có start/end None, nhưng bước
so literal clause cộng offset trước kiểm origin; đã tái hiện bằng probe offline
và regression. P16 bị đòi định nghĩa của nhánh tính thành công dù chỉ hỏi trạng thái
thiếu dữ liệu; batch3 sửa input và hướng dẫn kiểm đúng nhánh nguồn.

Các lượt giữ cùng 64 query/rubric/gold, 33 mapping fact, nguồn bytes/canonical,
revision/index và profile. Nhãn là **draft source-rubric do Codex đối soát**, không
phải human holdout; không gọi judge LLM. Sampling model khác nhau nên không quy
toàn bộ thay đổi điểm cho từng hunk mã. Benchmark là candidate RAG service thật
với actor có quyền; **không phải published assistant HTTP/browser E2E**.

<!-- HANDOFF_EVIDENCE_START -->
Batch3 postcheckPASS,57/60. P10 còn gap ở footnote bổ sung; P16 bị yêu cầu định
nghĩa của nhánh khác; P13 EVIDENCE_TIMEOUT sau11lời gọi structured hợp lệ. Không có
bằng chứng MODEL_CONTEXT_EXCEEDED. Full batch3 lịch sử3271PASS/18FAILnền/17SKIP.

Batch4 sửa **cấu trúc** payload quan hệ: mỗi primary source quote có ID riêng,
text chỉ là quote đã bind; toàn block đưa vào source_context làm nền. Nhiều quote
trong một block không gộp làm một target. Bốn regression bổ sung đã FAIL trước sửa.
Probe riêng P10/P13/P16 sau sửa **3/3PASS**, postcheckPASS; không gộp vào điểm64.
[Bằng chứng probe](../../../backend/storage/context597/acceptance-closure-probe/review.json).

Lượt64 mã chốt:148Luna calls thành công/0fallback,1.037.633input và37.011output tokens,
prompt lớn nhất24.525tokens; không ước tính chi phí khi thiếu đơn giá. p50 tri thức
0,581s, p95 50,847s, max75,876s; đây là tổng thời gian service/request, khác timeout
provider30s cho từng call. Nguồn/model/code/vector và lịch sử revision khớp trước/sau;
0chat/thread/gap được tạo. Ngưỡng85% đạt cả tri thức và positive.

[Summary cuối](../../../backend/storage/context597/acceptance-verified/summary.json),
[nhãn từng ID](../../../backend/storage/context597/acceptance-verified/labels-final.json),
[so sánh từng ID](../../../backend/storage/context597/acceptance-verified/baseline-comparison.json),
[postcheck](../../../backend/storage/context597/acceptance-verified/postcheck.json).

| So với595 | Kết quả |
|---|---|
| Khôi phục9ID trước FAIL | N17/N18/N19/N20/M05/F08/P07/P12/P15 |
| Hai ID giảm | P06/X09, vẫn tínhFAIL |
| Thay đổi điểm | 51/60→58/60; positive41/50→49/50, negative10/10→9/10 |

So với591: F03gain, P06/X09loss; điểm59/60→58/60. Không chỉ chọn baseline có lợi.
Đây là kết quả các mẫu model khác nhau; không có paired ablation để quy toàn bộ
chênh lệch cho một hunk. Không ghép probe3/3 hoặc câu PASS ở lượt trước vào lượt cuối.
<!-- HANDOFF_EVIDENCE_END -->

## Hai câu còn FAIL và giới hạn

| ID | Kết quả quan sát và nguyên nhân | Phạm vi kết luận |
|---|---|---|
| P06 | Audit loại claim hàngE-A về “không tác động chỉ tiêu SV”, với lý do reference chưa chứng minh vai trò điều kiện loại trừ. Repair giữ được các điều kiện khác nhưng topic này vẫn chưa được verifier xác nhận. | Nguồn/hàng có trong context; không có binding rejection. Source-only dependency review **không được gọi** ở ca này. Chưa có chứng cứ lỗi parser hoặc context overflow. [Trace](../../../backend/storage/context597/acceptance-verified/p06-failure-diagnostic.json). |
| X09 | Đường đầu bị NUMERIC_GROUNDING_FAILED với số90. Prose fallback đã có quy tắc thiếuA nhưng source review lại bắt thang điểmQ; verifier loại phần bổ sung là không liên quan. Kết quả cuối chỉ từ chối số chung, không nêu lý do thiếuA. | GiữFAIL theo rubric; không coi mọi abstention là đúng. Phạm vi payload đã sửa nhưng verdict ngữ nghĩa vẫn có false positive. Không nới numeric guard hoặc bỏ obligation để cho qua. [Trace](../../../backend/storage/context597/acceptance-verified/x09-failure-diagnostic.json). |

Các ca F08/P07/P12/P15 của đề xuất596 đều PASS trên mã chốt, nhưng chưa thể cam
kết độ ổn định100%. P07/P16 còn trả đoạn nguồn dài, P07 có thứ tự list2→1→3;
P15 đúng hai nhãn ngày nhưng còn thêm ngày kết thúc. Các điểm trình bày này không
nằm trong tiêu chíFAIL của frozen rubric; không giấu hoặc tự sửa rubric.

Hướng tiếp theo nếu cần tăng độ ổn định: kiểm chứng vai trò header/hàng trong audit
cho P06; phân biệt số giả định của câu hỏi và định nghĩa thật sự cần cho nhánh thiếu
đầu vào ở X09. Cần thí nghiệm riêng, không được tắt guard hoặc coi source chưa rõ là0.

## Lượt trung gian được giữ để truy vết

- Full batch1 đầu có thêm regression semicolon trong `test_rag_chat_441`; giữ test,
  sửa code rồi full đạt 3256 PASS / 18 FAIL / 17 SKIP. JUnit đầu 3254/19/17 còn nguyên.
- Full batch2 đầu 3263 PASS / 19 FAIL do tên DBtest có chữ `597r` không khớp guard
  chỉ cho số. Xác minh owner/nonce, đổi tên DBtest riêng sang5972; không sửa guard.
  Cùng mã chạy lại đạt 3264 PASS / 18 FAIL / 17 SKIP.
- Setup batch4 đầu dừng trước tạo DB vì chưa có thư mục báo cáo; tạo đúng thư mục rồi chạy lại. Helper comparison ban đầu thiếu nhãn full-closure trong danh sách cho phép; bổ sung đúng nhãn receipt đã có, không sửa app/test hoặc chạy lại full vì lỗi helper.
- Một lệnh focused dùng hai tên file không tồn tại: exit4, 0 tests, **không PASS**.
  Lỗi fixture mock thiếu contract/extra clause được ghi riêng; không sửa app cũ
  hoặc bỏ test để làm xanh. Kết quả cuối dùng đường dẫn đã xác minh.

## An toàn dữ liệu và giới hạn

DB/MinIO/Qdrant loopback development được xác minh trước mỗi benchmark.
Pytest dùng bốn DBtest owner/nonce riêng, Storage local tạm, ngoại vi127.0.0.1:1,
tắt auto migrate/seed. Chỉ tạo schema trong DBtest; không migration DB dùng chung.
Copy duy nhất typed defaults metadata phục vụ handler test đã mock, không copy
credentials hoặc provider hoạt động. Cả bốn DBtest đã dọn sau khi kiểm owner/nonce; Storage tạm giữ theo policy.

Kiểm duyệt tự động trước đó đã chặn thao tác xóa Storage tạm theo chính sách bảo vệ; giữ thư mục, không thử công cụ khác hoặc tắt bảo vệ để xóa.
Giữ ModelOps usage/lease audit và evidence đo. Không chép raw corpus, prompt riêng,
credential hoặc Base64 vào Git. Giữ thay đổi chưa commit có trước task.

Source rev12 `ks_rev_993a7ad91b32`, index `idx_rev_6bf0d6f86b1b`, canonical SHA256
`ad0dc2900b502fbe84ed5549263be49f4d55d4df5c17001414ea2f748d2c9152` được ghim.
Namespace2943points/0retrievable, activeIndexnull và trạng thái chưa xuất bản
không bị đổi bởi benchmark. Code kiểm thử không tự phê duyệt PDF cũ.

Frontend lint/build, published HTTP/browser E2E, dense/hybrid/rerank ablation,
Hit@K/Recall@K/MRR **NOT RUN**. Không sửa frontend trong task này. Không tự restart
services để nạp mã mới; kết quả đo áp dụng candidate service gọi từ runner.

## Lệnh và artifact

Cwd repo root, Python3.12 `backend/.venv/Scripts/python.exe`:

- `-X utf8 .antigravity-bridge/validation/context597_checks_closure.py` cho setup,
  test trọng tâm, seed-defaults metadata và cleanup; từng command/cwd/exit nằm
  trong `*-run.json` của checks-closure.
- `-X utf8 .antigravity-bridge/validation/context597_gate_closure.py full-closure`;
  full subprocess từ backend. `context597_compare_closure.py full-closure` đối chiếu595.
- `-m ruff check` trên mười appfile và bốn testfile nêu trên; không autofix toàn repo.
- Lượt64 đầu dùng `context597_acceptance_{preflight,prepare,run,postcheck,score}.py`;
  lượt2 dùng `context597_release_*`; lượt3 dùng `context597_handoff_*`; lượt4 dùng `context597_verified_*`.
  Các thư mục tương ứng là acceptance-final/release/handoff/verified.

Bằng chứng gốc: [lượt1](../../../backend/storage/context597/acceptance-final/summary.json),
[lượt2](../../../backend/storage/context597/acceptance-release/summary.json).
Run-intent chỉ gửi một lần; không dùng completion cũ thay lượt hiện hành.
Helper này gọi service ứng dụng và ModelOps hiện có, không dùng CLI/model API fallback.
