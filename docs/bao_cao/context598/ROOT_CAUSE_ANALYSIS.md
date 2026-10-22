# Context598 — Nguyên nhân P06 và X09

Ngày 22/10/2026. Chỉ phân tích lượt64 mã chốt Context597, không sửa ứng dụng,
không gọi lại LLM/DB hoặc chạy benchmark. Mã hiện tại khớp toàn bộ1.244 seal
app/test/frontend của lượt đó. Báo cáo không thay kết quả58/60 hoặc nhãn benchmark.

## Kết luận

Hai câu có đủ nguồn trong canonical Markdown/Structured JSON và context thực tế.
Lỗi quan sát nằm ở **đánh giá bằng chứng và vòng phục hồi**, không có dấu hiệu mất
nội dung của hai câu khi bóc tách hoặc context overflow. Không cần sửa parser hoặc
reindex để xử lý các nguyên nhân đã xác định ở đây.

| Ca | Câu hỏi và đáp án cần có | Nguồn |
|---|---|---|
| P06 | E-A áp dụng hồ sơ thiết bị nhóm A kế hoạch2027; gia hạn tối đa15 ngày làm việc từ hạn ban đầu, có thông báo kiểm định trùng đợt khóa và quyết định P.ĐT; không đổi chỉ tiêu SV hoặc áp sang nhóm B. | Trang18, Phụ lụcII.1 và hàngE-A của Bảng10. Bốn gold spans đều có trong context. |
| X09 | Với B=80,C=90,đủ90% minh chứng nhưng thiếuA, không thể xác định Q chính xác; phải ghi Chưa đủ điều kiện tính, không gánA=0. | Trang14, mục14.1; gold span39965:40394 có trong context. |

## P06 — Một ý bị loại và vòng sửa bỏ sót việc lấy lại ý đó

Chuỗi quan sát từ trace:

1. Retrieval/reranking lấy được hàngE-A, xếp đầu danh sách rerank. Hàng có đủ bốn
   cột, trong đó ô cuối ghi không tác động chỉ tiêu SV hoặc nhóm B. Header của cột
   là “Điều kiện loại trừ”. Canonical, JSON, context và header/cell đều có nội dung.
2. Bộ kiểm chứng ban đầu xác nhận cả bốn phần câu hỏi đã được bao phủ.
3. Whole-claim audit lại loại `c4.body0.1`: cho rằng reference xác nhận hàngE-A
   nhưng chưa chứng minh cột này là điều kiện loại trừ. Đây là phán đoán về vai trò
   cột; câu hỏi thực tế chỉ cần biết ngoại lệ có đổi chỉ tiêu SV không. Dữ kiện ô
   trả lời trực tiếp câu hỏi ấy. Không có binding rejection trong lượt này.
4. Cùng lúc audit yêu cầu bổ sung câu mở đầu rằng mọi điều kiện của ngoại lệ phải
   được thỏa mãn. Repair đi nhánh `source_condition_completion`, giữ ba claim còn
   hợp lệ và thêm điều kiện này; claimE-A đã bị audit loại không được giữ.
5. Sau sửa, điều kiện đã đủ, nhưng topic “Thay đổi chỉ tiêu sinh viên” chuyển thành
   false. Trace chỉ ghi một round repair và một SourcePassageProposal; không có
   vòng chọn lại nguồn để phục hồi phần SV còn thiếu. Hệ thống từ chối toàn câu.

**Hai nguyên nhân phân biệt được:**

- Model audit hiểu quá chặt/nhầm vai trò header với nội dung ô, làm mất một phần
  bằng chứng đúng. Không có bằng chứng header đã bị rơi khỏi payload: probe giữ
  nguyên header/cell qua bind_quote và compact reference_catalog.
- Vòng repair tập trung vào condition gaps. Ở `prose_fallback.py:278`, round tiếp
  theo dừng nếu không còn gap/qualifier mới, kể cả khi topic coverage chưa đủ.
  Predicate này được chạy offline từ AST mã hiện tại. Nó là khoảng hở thật với
  trạng thái “đã bổ sung điều kiện nhưng mất một ý trả lời”.

**Giới hạn chẩn đoán:** final qualifier signature và conflict flag không được lưu
đầy đủ, nên chưa chứng minh tuyệt đối P06 đã rơi vào nhánh break cụ thể nào. Điều
đã thấy chắc chắn là: claimSV bị loại, chỉ chạy một round bổ sung điều kiện và
không có reselection cho topic còn thiếu. Không gọi lại model để đoán output cũ.

`source_dependency_reviews` không có ở P06: không quy lỗi này cho source-only
review hoặc cho việc nó yêu cầu thêm định nghĩa.

## X09 — Hai lớp chặn nối nhau, trong đó có yêu cầu thừa bị khóa lại

### 1. Lớp kiểm số

Decision gốc là `NUMERIC_GROUNDING_FAILED`, unsupported_numbers=[90].
`citation_guard.verify_numeric_grounding` so số trong đáp án với citation/facts/
candidates, còn query không được coi là nguồn. Vì vậy90 có thể bị chặn dù người
hỏi vừa đưa C=90 và90% minh chứng.

**Chưa thể kết luận guard đã chặn sai bản nháp gốc:** bản nháp trước numeric gate
không được lưu. Không biết90 lúc đó được nhắc như giả định của user hay bị model
biến thành kết quả Q. Nếu model trả Q=90 thì chặn là đúng.

Probe offline xác nhận ranh giới hiện tại:

| Văn bản kiểm thử tổng hợp | Numeric gate |
|---|---|
| Nhắc lại B=80,C=90 rồi nói thiếuA nên chưa đủ điều kiện tính | FAIL, số90 không có trong evidence đã chọn |
| Chỉ nêu thiếuA, chưa đủ điều kiện tính, không đặt biến thiếu bằng0 | PASS ở riêng gate số |
| Tự khẳng định Q=90, kể cả query có90 | FAIL |
| Sai cách: thêm toàn query vào evidence rồi khẳng định Q=90 | Riêng gate số sẽ PASS; vì vậy không được whitelist mọi số user nhập |

Đây là probe của gate số, không phải phép thử bypass toàn pipeline hay câu trả lời
thật của model. Gate này kiểm sự hiện diện số, không chứng minh metric/vai trò.

### 2. Fallback đã có lời giải thích đúng nhưng bị obligation thừa chặn

1. Fallback chọn được hai claim nguồn. Verifier xác nhận topic “có tính Q khi thiếuA
   không” là true; whole-answer audit complete=true. Các điều kiện thật về đầy đủ
   biến và không đặt0 đã được giữ.
2. SourceDependencyReview lại đánh `e4.c0` là required=true cho cả hai claim. Clause
   này chỉ định nghĩa Q và thang0–100; không phải điều kiện cần để nêu rằng thiếuA
   thì chưa thể tính Q.
3. `remember_conditions` kiểm canonical/span/hash và giữ clause đó thành nghĩa vụ
   bắt buộc. Contract hiện chủ yếu kiểm ID và cùng source, chưa chứng minh quan hệ
   ngữ nghĩa “clause này thật sự cần cho nhánh trả lời đang xét”.
4. Repair chép thêm định nghĩa Q. Verifier lại loại nó với lý do thangQ không trả
   lời việc có tính đượcQ khi thiếuA không. Ledger vẫn giữ yêu cầu, nên câu trả lời
   đúng về missing-input tiếp tục bị coi là chưa đủ.
5. Service quay về lời từ chối số liệu chung của numeric gate, không nêu thiếuA.
   Vì rubric đòi giải thích chính xác lý do không tính được, X09 vẫn FAIL.

Đây là **bất đồng giữa hai bộ kiểm tra**, cộng với việc một verdict required=true
được biến thành ràng buộc không thể tự mất. Cơ chế giữ điều kiện bảo vệ đúng các
ca tiền đề thật nhưP07; nhưng điều kiện bị đánh nhầm cũng bị giữ. Chỉ tăng số lần
prompt hoặc thêm context không giải quyết được cơ chế bất đồng này.

## Hướng sửa đề xuất theo nguyên nhân chung

| Ưu tiên | Thay đổi tối thiểu cần nghiên cứu/triển khai | Bảo vệ phải giữ |
|---|---|---|
| 1 — Repair coverage | Theo dõi riêng missing answer facets và missing source conditions. Sau bổ sung điều kiện, nếu vẫn thiếu một phần câu hỏi thì cho phép chọn lại đúng bằng chứng đó trong budget hiện có; giữ các claim an toàn và kiểm chứng lại. Ghi rõ lý do dừng. | Không tự chấp nhận claim đã bị audit loại; không lặp vô hạn hoặc bỏ tiền đề để lấy điểm. |
| 2 — Audit hàng bảng | Tách chứng minh cấu trúc do server kiểm (ô/hàng/header/span) với kiểm applicability của model. Kiểm câu trả lời theo nội dung ô và đối tượng hàng; không biến nhãn cột thành một yêu cầu chứng minh ngoài câu hỏi. Cần giữ cả body và applicable conditions. | Quote nguyên văn không tự chứng minh mọi scope; vẫn chặn nhầm hàng, nhóm, năm và mâu thuẫn nguồn. Không sửa header nguồn chỉ để dễ audit. |
| 3 — Obligation applicability | Phân biệt đề xuất dependency với dependency đã đủ bằng chứng cho đúng action/facet/nhánh. Giữ kiểu quan hệ và proof link; xử lý một lần có giới hạn khi hai audit bất đồng trước khi coi yêu cầu mới là nghĩa vụ bất biến. | Không xóa ledger hoặc mặc định tin verifier cuối. Nếu chưa giải được bất đồng thì trả lỗi kiểm chứng có nguyên nhân rõ; không giả thiếu dữ liệu nguồn. |
| 4 — Vai trò số và missing-input | Phân biệt số giả định user, số nguồn và kết quả tính. Khi nguồn quy định thiếu input không được tính, ưu tiên giải thích thiếu input bằng chính rule; không cần nhắc lại các số giả định. Nếu cần nhắc, phải giữ vai trò/quote của giả định, không biến thành fact. | Không whitelist số trong query, không tự gán thiếu=0, không tạo Q khi chưa đủ input. |

Regression nên có: mất một facet sau bổ sung điều kiện; sai header/nhầm hàng;
nguồn có header khó hiểu nhưng ô trả lời rõ; nhánh thiếu input không cần glossary;
tiền đề thật vẫn bắt buộc; audit bất đồng; user giả định số nhưng không cho phép
model trả số đó như fact; thiếu input có và không có phương án thay thế theo nguồn.

## Bằng chứng và giới hạn

- Phân tích response/diagnostics/gold/manifest đã đóng băng của597. So sánh các
  lượt trước thấy P06/X09 từng PASS, rồi FAIL; không quy tất cả cho sampling hoặc
  coi chênh lệch nhiều code batch là causal ablation.
- Đã chạy từ repo root: `backend/.venv/Scripts/python.exe -X utf8
  .antigravity-bridge/validation/context598_analysis.py`, exit0.
  [Receipt](../../../backend/storage/context598/analysis-run.json),
  [9 nhóm probe](../../../backend/storage/context598/offline-analysis.json).
- Toàn bộ1.244 file app/test/FE vẫn khớp seal597. Không sửa ứng dụng, cấu hình,
  nguồn hoặc dữ liệu; không reindex/publish/restart/commit/push.
- 0 LLM calls, 0 DB calls, 0 kết nối mạng thành công. Socket guard chặn một
  request kiểm tra version Qdrant khi import module; không có egress thực hiện.
- Full Pytest/live64/FE checks **NOT RUN** trong phiên phân tích này. Điểm58/60 và
  full3275PASS/18FAILnền/17SKIP là kết quả lịch sử597, không phải PASS mới.
- Chưa replay actual model draft hoặc kết luận lại hiệu quả sửa: chỉ có trace,
  source hiện hữu, code reading và pure-function/predicate probes. Nhãn benchmark
  vẫn là draft source-rubric; không thay rubric hoặc hợp thức hóa hai câuFAIL.
