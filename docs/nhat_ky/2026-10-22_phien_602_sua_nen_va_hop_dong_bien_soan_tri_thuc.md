# Phiên602 — Sửa nền và hợp đồng biên soạn tri thức

Ngày 22/10/2026. Người dùng cho triển khai đợt1 và2 sau khi đánh giá các mô hình
LLM Wiki, rồi yêu cầu tiếp tục. Phạm vi là sửa nền và thiết kế/hợp đồng cho lớp
biên soạn; không tự thực hiện đợt3 hoặc thay toàn pipeline hiện tại.

## Hiện trạng đã đối chiếu và phương pháp

Đã đọc AGENTS, PROJECT_CONTEXT, rules kiểm chứng/memory và skill clean-code,
backend, ingestion, rag-pipeline, rag-evaluation. So Git/diff/file thật và chụp
app đầu602, bảo toàn thay đổi600/601 chưa commit; không dùng memory làm bằng
chứng test hoặc Git HEAD để thay toàn bộ phần đang sửa.

1. DOCX: Docling chia một paragraph thành text items. Chỉ nối các fragment cùng
   parent/level khi khớp duy nhất một paragraph OOXML đầy đủ, giữ raw fragments,
   locator/hash, không nối qua paragraph/table/list/header hoặc nguồn mơ hồ.
2. Query year: tách lexer literal khỏi kiểm vai trò năm; xử lý năm sát chữ,
   khoảng/ngày/năm học mà không suy năm từ mã định danh. Dùng chung trong
   validation và prose recovery; source role vẫn phải có bằng chứng.
3. Wiki: phân trang inventory512 sections, kiểm đủ toàn nguồn, stable continuation
   và reuse theo revision; literal ngắn chỉ do server trích nguyên văn, không
   biến thành fact hoặc cho generated mode vượt contract.
4. Evidence: chỉ bỏ derived duplicate khi có canonical owner duy nhất cùng
   identity; phục hồi cả sentence, cùng block/source/offset. Reselection cuối
   phải giữ qualifier vừa được audit xác định rồi verifier/audit lại, vẫn hai
   vòng và cùng budget. Không xoá obligation hoặc hạ Quality Gate.
5. Đợt2: schema entity/assertion/time/scope/relation/section và pure binding.
   Kiểm permission/source-set/proof/revision/hash/IDs, unknown/conflict không
   thành scalar. Receipt luôn evidence_bound/review_only, không entailment,
   persistence mới, endpoint hoặc serving certification.

16 file app khác snapshot đầu602: parser2; wiki7; RAG5; compilation2. Bốn file
test mới gồm51 ca và fixture integration600 nhận DB602 có ownership guard.
Danh sách đầy đủ trong `backend/storage/context602/checks/application-diff-scope.json`
và [báo cáo triển khai](../bao_cao/context602/IMPLEMENTATION_REPORT.md). Không sửa
frontend trong phiên này; các file FE đang dirty là thay đổi có trước.

## An toàn môi trường và baseline

Xác minh DB phát triển/MinIO/Qdrant loopback trước chạy. DB riêng
`qnu_test_context602_b842423bcce8`, Storage runtime riêng, guard không cho pytest
chạm model hoặc dịch vụ thật. Chỉ sao chép một defaults row không hoạt động,
0 secret/credential/provider. Không migration DB ứng dụng.

Các baseline tái hiện hợp lệ: foundation9 FAIL/6 PASS, recovery3 FAIL/1 PASS,
reselection2 FAIL. Fixture sai ban đầu giữ riêng, không tính làm lỗi app.21/51
test có baseline riêng:14 FAIL/7 control PASS;30 ca khác không chạy trước sửa.

## Kết quả thực chạy

| Kiểm tra | Kết quả / exit |
|---|---|
| Full baseline602 | 3362 PASS /18 FAIL /17 SKIP, +23 subtest PASS; exit1 |
| Focused cuối | 889 PASS,1 warning; exit0 |
| Full cuối | 3413 PASS /18 FAIL /17 SKIP, +23 subtest PASS; exit1 |
| Regression mới | 51 PASS,0 failure ID mới/đổi cause/mất ID cũ |
| Ruff | 21 file PASS; exit0 |
| FE lint/typecheck/build/browser | NOT RUN, không thay FE |

Full vẫn FAIL;18 lỗi nền cùng exact IDs/message, không chỉ cùng tổng. Chạy lại
full sau thay đổi reselection cuối, không lặp để né lỗi.18 lỗi nền nằm ngoài
phạm vi, được liệt kê [theo ID](../bao_cao/context602/TEST_ID_COMPARISON.md).

DOCX thật3 nguồn: format validator PASS; raw hash giữ. Native reconciliation
xác minh5 paragraph/24 fragments, bảng126/85 blocks giữ đầy đủ;0 body đổi không
giải thích được. Canonical S1/S2 giảm unit do nối paragraph, S3 giữ nguyên.
Chưa render Office/hình/layout và chưa chứng nhận full Quality Gate nguồn.
Cẩm nang canonical1301 sections phân thành3 trang,19 selector calls xác định,
0LLM; không phải ingestion/model E2E.

## ModelOps thật và đối chiếu theo câu

Giữ Luna/model/config/nguồn PDF/source revision12/index staging/timeout30s,
không reindex/publish. Hai bộ chạy tuần tự; sau app/test đã ổn định và full cuối.

- Frozen64 cuối:59/60 tri thức,49/50 positive,10/10 negative,4/4social,
  140/140 exact citations,0runtime;147Luna usage/0fallback. P07/P08/P16 PASS;
  còn P10 do audit/verifier bất đồng applicability chú thích. Historical601
  57/60, gains3/loss1, không phải causal ablation. Lượt trung gian60258/60 giữ
  riêng, không ghép kết quả hoặc retry câu cuối để tăng điểm.
- Ba DOCX nhiều năm: source wiki3/3ready,14trang,7compiler calls; bộ12 đạt6/12
  so6014/12,23/23 exact citations. PASS M01/M04/M05/M06/M07/M11; FAIL M02/M03
  timeout, M08 scope-condition disagreement, M09/M10 thiếu coverage hai nguồn,
  M12 chưa hoàn thành year-role inference. QA127usage success/0fallback không
  có nghĩa hai request timeout đã PASS. M04 giữ draft ở câu hỏi/citation title,
  body chưa nhắc lại; giới hạn hiển thị được công khai khi chấm.

Lượt64 dùng candidate `rag_service.ask`, có vector/ModelOps thật; bộ12 dùng
adapter canonical/BM25 local, không facts/vector. Không gọi cả hai là published
HTTP/browser E2E. Rubric draft Codex, không human holdout/judgeLLM. P13 có audit
prompt76.323tokens trong usage: không thể suy Qwen32K đủ. Chưa quy lỗi cho context
window hoặc thay model để che lỗi.

## Bàn giao, dọn dữ liệu và giới hạn

Postcheck sau cả hai bộ: nguồn/revision/index/model/config/code và toàn vector
payload khớp,2943points/0retrievable,0test thread/message/gap; usage/audit giữ.
Seals read-only và cleanup helper exit0. DB test602 đã drop sau xác minh đúng
tên/comment nonce và kiểm lại không còn. Storage tạm còn giữ theo chính sách
bảo vệ; không tắt policy hoặc dùng đường xóa khác. Không xóa dữ liệu vận hành.

Đã cập nhật báo cáo thiết kế/schema/triển khai/kiểm chứng/đối chiếu ID/nhiều nguồn,
quy trình17, index nhật ký, WORK_LOG, PROJECT_CONTEXT và snapshot602. Kiểm liên
kết, UTF-8/LF, schema khớp mã và diff có phạm vi trước bàn giao. Không commit,
stage,push,reset,reindex,publication,restart,deploy hoặc đổi model/config.

Đợt1/2 đã có mã và bằng chứng kiểm chứng, **chưa APPROVED toàn RAG**. Các khoảng
hở P10/M08,coverage nhiều nguồn,deadline,year roles và full payload budget cần
được xử lý ở phần kế tiếp có test; compiler tổng hợp/persistence/lifecycle mới
vẫn là thiết kế, chưa tự bắt đầu đợt3.

- [Kiểm chứng và lệnh/giới hạn](../bao_cao/context602/VALIDATION_REPORT.md)
- [Đối soát12 câu](../bao_cao/context602/MULTI_SOURCE_EVALUATION.md)
- [Thiết kế đợt2](../bao_cao/context602/COMPILATION_DESIGN.md)
- [Snapshot602](../memory/snapshots/2026-10-22_session_602.md)
