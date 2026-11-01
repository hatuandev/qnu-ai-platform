# Phiên789 — Điều kiện nối đoạn và trả lời hỗn hợp

Ngày2026-11-01. User yêu cầu tìm nguyên nhân F14/MX-05, sửa tiếp và chạy đủ9 câu model thật, không retry để làm xanh.

## Phạm vi và nguyên nhân

- F14: hai đoạn được xếp theo relevance, phần tiếp câu đứng trước phần mở đầu. Khi model chỉ dẫn đoạn bắt đầu giữa câu, bộ chấm không thấy đầy đủ chủ thể và điều kiện. Source có đủ dữ kiện; không phải thiếu output. Đây là vấn đề trình bày và hoàn thiện citation của văn bản đã ghim.
- MX-05: prompt buộc lookups có statements rỗng; backend bỏ toàn bộ prose nếu có lookup. Hợp đồng không biểu đạt tốt câu cần ô bảng và ý văn bản cùng lúc. Hai nguồn đã được retrieval đưa vào.
- Vòng kiểm chứng còn phát hiện reference clause trong câu nhiều ý bị tách mất antecedent; giải quyết bằng giữ câu hỏi gốc trong truy vấn nhánh có đại từ, không đoán entity/năm và giữ scope/filter/index.

## Cách sửa tổng quát

1. `source_text.py` giữ vị trí block theo thứ tự canonical, tính cả block không được dẫn và bảng để khoảng trống không tự thành quan hệ nối. `narrative.py` tạo nhóm đọc liên tiếp chỉ cùng document/version/publication/ocr; giữ từng citation/evidence owner, không thêm block mới. Payload và budget tính cả narrative_context, trace hash/số nhóm, source identity tường minh.
2. Đoạn bắt đầu chữ thường có block trước liền kề chưa kết thúc câu được thêm citation hỗ trợ từ evidence đã được truy xuất, cùng identity. Không áp khi có gap, kết thúc câu hoặc khác phiên bản; không thay văn bản gốc. ModelAnswer nguyên đầu vào không bị sửa tại chỗ.
3. Projectionv3 giữ statement chỉ dẫn paragraph khi có lookup; prose dẫn bảng vẫn bị bỏ, giá trị bảng được copy từ ô nguồn. Không nới cell/citation/plaintext/numeric guard. Cho phép trả lời hỗn hợp nguồn văn bản và bảng.
4. `PROMPT_VERSION=qnu.rag.answer/v13`; JSON Schema của request có enum citation paragraph cho statements, bảng phải đi qua lookups. Schema hash theo request vì danh sách evidence thay đổi. Guard backend vẫn từ chối provider không tuân thủ. Không dùng regex giá trị đáp án hay từ khóa ngành để trả lời hộ model.
5. Evaluator hỗ trợ text fact trên các block liền nhau, cùng published identity và đúng citation. Không gộp tùy tiện text khác tài liệu, không sửa gold hoặc expected values để làm xanh.

## Kiểm chứng

- Regression RED8FAIL/1PASS cho narrative order và mixed projection; sau sửa nhóm44PASS. Citation closure RED1FAIL14PASS, schema-source RED1FAIL15PASS, query antecedent RED→PASS. Nhóm cuối49PASS gồm composition/query/projection/cells.
- Fullunit cuối: **630PASS/1FAIL** nền716 (`test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`). Log `tmp/789-backend-unit-v13.log`. Lần chạy đầu cwdroot có thêm3 lỗi subprocess path; chạy đúng cwdbackendV1 chỉ còn lỗi nền.
- API/PostgreSQL/Qdrant cô lập:66PASS toàn batch; sau closure8PASS22deselected; sau schema theo nguồn3PASS27deselected. DB test riêng được drop. Log `tmp/verification789-integration.log`, `tmp/verification789-closure.log`, `tmp/verification789-schema.log`. Không gọi provider thật trong các test này.
- Frontend57targetedPASS, full591PASS33FAIL đúng33IDs baseline779, không thêm/bớt. Build/TS/Biome/Ruff/diffcheckPASS. Log `tmp/789-frontend-full.log`, `tmp/789-build.log`. Fullsuite vẫn FAIL, không gọi toàn bộ xanh.

## Cohort model thật và lịch sử

Mỗi lần chỉ chạy `scripts/run_admissions_retest.py --headed`, chín ID cố định, một dispatch/câu, không retry/fallback. Sau thay đổi mã có cohort mới riêng; không gộp kết quả giữa phiên bản, không âm thầm chạy lại cùng cấu hình.

| Cohort | Phiên bản | Kết quả |
|---|---|---|
| `admissions-retest9-1793520124806705500` | v11 |6PASS3FAIL: F14/BC24-08 factproof,MX-02 abstain |
| `admissions-retest9-1793520731185091000` | v12 |7PASS2FAIL: F14 cell_selection_required,MX-02 abstain |
| `admissions-retest9-1793521145475121600` | v13 |8PASS0FAIL1UNCERTAIN,9dispatched0NOT_RUN,exit1 |

Cả hai cohort đầu đều đủ9, exit1, không NOT_RUN/UNCERTAIN. Audit DB: mỗi cohort9conv/9turn/9key/9chat, toànattempt1; usage394428 và382738 quan sát. Lượt v12 có13embedding/rerank do giữ nguyên câu referential trước khi sửa v13; không gọi retry.

BC24-08 ở v11 trả đúng số người theo câu hỏi nhưng gold còn đòi số trường: ghi nhận không khớp độ chi tiết nhãn/câu hỏi, giữ FAIL chứ không đổi nhãn. V12 đã PASS; không lấy kết quả này thay cho kết quả v13.

Giữ phiên93faa11f0caf, assistantrev2/output16384/evidence98304byte/answeroff, ba tài liệu/index179chunks cũ. Không cleanup/init/compile/review/publish/reindex/đổiModelOps. Các restart chỉ nạp mã vào API/worker/FE của cùng phiên được giao test.

Lượt v13 bị ngắt các tiến trình API/test sau khi F13/F14 đã lưu PASS và I25-04 đã dispatch. DB vẫn ghi running, server.json vẫn true dù process/port không còn; vì vậy nhận định tạm thời “model chậm” được rút lại sau khi kiểm tra process. Không chứng minh được nguyên nhân tiến trình mất từ phía app/host/user. Không có provider completion nên không coi là model FAIL hoặc tokenlimit, không tính usage bằng0.

Khôi phục serve cùng phiên, đối chiếu I25-04 qua DB read-only (đúng conversation/question/key, một turn), giữ `UNCERTAIN` ở report, không sửa DB turn hoặc gửi lại. Bản tiếp tục tạm thời chỉ gửi sáu ID NOT_RUN còn lại, kiểm fingerprint bằng seed cũ, giữ F13/F14 và uncertain, final assertion vẫn exit1. Đây là tiếp tục một cohort, không gộp PASS từ hai cohort v11/v12. Mã tiếp tục, seed trước ngắt và audit được giữ trong thư mục report; runner chính không thêm auto-retry/auto-resume. Thời gian I25-04 không quan sát được, ghi null.

| Câu v13 | Kết quả | Client latency quan sát |
|---|---|---:|
| F13 |PASS|24.3s|
| F14 |PASS|19.7s|
| I25-04 |UNCERTAIN — process_interrupted_uncertain|null|
| I25-05 |PASS|19.3s|
| BC24-05 |PASS|14.2s|
| BC24-08 |PASS|14.7s|
| MX-02 |PASS|26.6s|
| MX-05 |PASS|22.9s|
| MX-10 |PASS|24.1s|

Audit cuối:9conversation/9turn/9key, mỗi conversation một turn, đúng question/key, một chat reservation/câu.14embedding/14rerank/9chat;8chat có execution hoàn tất attempt1/codeok, một chat I25-04 vẫn reserved/usageunknown. Tổng usage đã quan sát360131 token,1unknown không cộng thành chi phí0. Hệ thống không có đủ bằng chứng tổng latency model của cohort bị ngắt. Hash checkpoint và5artifact lịch sử theo manifest không đổi. Báo cáo `retest9-answers.json`, audit `tmp/audit789-v13.json`, log `tmp/789-remaining.log`; thư mục root report là đường dẫn bảng bên trên.

Đã đọc tám phản hồi hoàn tất: F14 nêu đủ mức học lực/ngưỡng/ngoại lệ với hai source; MX-05 chọn ô hai tài liệu; không tái diễn citation/table-prose guard ở tám câu này. Không gọi đây là nghiệm thu9/9 hoặc thay full53. F14/MX-05 đã chứng minh PASS trong cùng bảnv13, còn I25-04 cần đối soát provider hoặc một lần chạy mới có chủ đích sau này; không retry trong task này để làm xanh.

Serve cuốiẩn38788/API64624/FE64625, backendhash `ae4616a1e4be8e89ea3c84ec6f809c51b96c9533f2b588c1f7df05e8047c2146`. Không đổi source/index/ModelOps. Ba cohort đã dùng tổng1,137,297 token quan sát (394428+382738+360131), còn1usageunknown; chi phí phải giữ cả các lượt chưa đạt, không chỉ báo lượt cuối.
