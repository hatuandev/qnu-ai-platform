# Context596 — Vì sao điểm RAG giảm sau khi hoàn thiện ngữ cảnh?

Ngày 22/10/2026. Phạm vi: phân tích kết quả và mã hiện tại; chưa sửa ứng dụng.

## Kết luận

Điểm giảm là có thật, nhưng không thể quy cả chín câu lỗi cho phần mở rộng liên kết.
Năm câu lỗi vận hành trước khi có đáp án; bốn câu còn lại bộc lộ bất ổn ở chọn đoạn,
bảo toàn tham chiếu và kiểm chứng ngữ nghĩa. Có một thay đổi ngữ cảnh quan sát được
ở P07; chưa có thí nghiệm đối chứng đủ để kết luận đó là nguyên nhân duy nhất.

Không thấy bằng chứng PDF bị bóc tách lại sai hoặc thiếu cửa sổ context trong lượt này.
Nguồn canonical, revision, chỉ mục, model và toàn bộ cấu hình benchmark không đổi.

| Kết quả lịch sử thực chạy | Context591 | Context595 |
|---|---:|---:|
| Câu tri thức | 59/60 — 98,33% | 51/60 — 85% |
| Câu có đáp án trong nguồn | 49/50 — 98% | 41/50 — 82% |
| Câu âm tính | 10/10 | 10/10 |
| Giao tiếp xã hội | 4/4 | 4/4 |
| Lỗi vận hành | 0 | 5 |

F03 từ FAIL thành PASS. Chín câu từ PASS thành FAIL là N17, N18, N19, N20, M05,
F08, P07, P12, P15; vì vậy tổng điểm giảm tám câu. Ngưỡng positive cần ít nhất43/50,
nên Context595 vẫn FAIL. Lượt thử lại riêng năm lỗi vận hành đạt5/5, nhưng **không**
ghép vào điểm64 hoặc coi là một lượt64 đạt mới.

## Đối chiếu nguyên nhân từng nhóm

| Câu | Nguyên nhân trực tiếp có bằng chứng | Quan hệ với thay đổi vừa làm |
|---|---|---|
| N17/N18/N19/N20/M05 | Provider bị bỏ qua với `key_lease_unavailable`, trả `ALL_PROVIDERS_UNAVAILABLE`. Thử lại tuần tự cùng câu/lịch sử đạt5/5. | Có nhiễu do Codex chạy synthetic ModelOps đồng thời benchmark. Chưa chứng minh độc lập ai giữ lease từng thời điểm; không phải bằng chứng đáp án hoặc parser sai. |
| F08 | Referent metric không hiện nguyên cụm trong query viết lại; cả proposal và bounded repair đều bị `VALUE_NOT_IN_STANDALONE_QUERY`. | Hợp đồng literal đã gây lỗi ở Context592/594. Các guard và schema được mở rộng làm đường đi này nhạy hơn với cách LLM diễn đạt. Chưa cô lập tác động riêng của Context595. |
| P07 | Đáp án bỏ điều kiện áp dụng ngoại lệ E-B nhưng vẫn được đánh dấu `VERIFIED_CLAIM_COVERAGE`. | Context đóng gói đã đổi; điều kiện vẫn hiện diện. Khoảng hở thực nằm ở xác định điều kiện bắt buộc và kiểm tra độ đầy đủ, không chỉ retrieval. |
| P12 | Fallback đã lấy đúng đoạn công thức; audit vẫn báo thiếu định nghĩa/thang điểm Q/A/B/C sau vòng bổ sung, rồi từ chối. | Tập context IDs và mã fallback/audit giống lượt591. Không đi qua wiki; chưa chứng minh do thay đổi budget/cache. |
| P15 | Selector chọn nguyên đoạn có hai ngày cần hỏi nhưng kèm thông tin lịch sử/ngày kết thúc kỳ; verifier loại các claim vì có nội dung ngoài câu hỏi. Repair vẫn chọn quá rộng. | Tập context IDs và mã fallback/audit giống lượt591. Là bất ổn chọn phạm vi câu và xử lý claim nhiều mệnh đề. |

### 1. Lỗi vận hành làm phép đo bị nhiễu

Trong Context595, Codex đã chạy bốn ca router/ModelOps phụ cùng lúc lượt64. Đây là
cách bố trí thí nghiệm chưa phù hợp khi cả hai dùng chung cơ chế cấp suất gọi khóa.
Log xác nhận năm lần `key_lease_unavailable`; retry tách riêng, chạy tuần tự đạt5/5.
Những quan sát này ủng hộ giả thuyết tranh suất gọi, nhưng không xác định được lease
holder từng request và không loại trừ mọi trạng thái khóa khác bằng log hiện có.

Mã inference gọi `acquire`, rồi skip provider nếu không có lease. Hàm này có thể trả
`busy` riêng, nhưng nhánh skip hiện gộp thành `key_lease_unavailable`. Do đó không được
diễn giải mã đó thành HTTP429, upstream timeout hoặc thiếu context. Policy Luna-only
của phép đo khiến không dùng provider khác; cấu hình fallback DB vẫn giữ nguyên.

### 2. F08: bảo toàn ý nghĩa đang phụ thuộc quá nhiều vào chuỗi ký tự

F08 hỏi chỉ tiêu SV2027 của chương trình đang nói tới. `referent_errors` kiểm bằng
`reference.value not in rewritten`, có phân biệt hoa/thường và khoảng trắng. Probe
tổng quát với cùng referent cho thấy `chỉ tiêu SV` đạt, còn đổi chữ đầu thành hoa
hoặc thêm một khoảng trắng bị chặn.

Đây là điểm nhạy có thể tái hiện, **không phải** bằng chứng rewrite F08 thật chỉ sai
hoa/thường: bản rewrite bị từ chối không được lưu. Lượt thật chỉ chứng minh metric
không được giữ đúng điều kiện literal. Hỏi lại an toàn hơn trả nhầm chỉ tiêu/số thực
ghi nhận, nhưng vẫn làm giảm khả năng trả lời câu có đủ căn cứ.

### 3. P07: có đủ nguồn vẫn có thể trả lời thiếu điều kiện

P07 hỏi cách thay chữ ký giấy, thời hạn và miễn kiểm tra an toàn của E-B. Đoạn điều
kiện ở trang18, unit `qnu:p0018_b0008`, span50205:50413, vẫn nằm trong11block cuối.
Đáp án lại thiếu điều kiện chậm chữ ký do cơ sở tiếp nhận tạm đóng, có nhật ký cá
nhân và xác nhận giảng viên cùng kỳ.

Replay offline bằng chính các claim cuối, manifest và hàm `audit_payload` hiện tại
xác nhận đoạn đó **cũng thuộc phạm vi source-condition audit**, không bị loại trước
audit. Tuy nhiên, cổng `condition_gaps` chỉ bắt buộc giữ câu khi check của model có
`required=true`. Với cùng đoạn bị bỏ sót: đặt false không sinh gap, đặt true sinh
gap `e5.c0`. Kết quả thật lưu `source_condition_gaps={}` và không chạy completion.
Đây là lỗ hổng phụ thuộc đánh giá applicability của LLM: kiểm literal sau đó không
thể cứu một điều kiện bị coi là không bắt buộc. Raw required flags không được lưu,
nên replay chứng minh cơ chế có thể xảy ra, chưa tái dựng đầy đủ verdict thật.

Ngữ cảnh cũng đã đổi: navigation3994→4347ký tự; cả hai lượt giữ11block nhưng lượt595
loại `facts:60d57ea0896fdfff1b9c` vì giới hạn nhóm block và thay bằng một đoạn khác.
Điều kiện canonical vẫn giữ. Thêm context làm thay thứ tự/biểu diễn bằng chứng có
thể đổi cách model chọn và audit; chưa có A/B để lượng hóa riêng tác động này.

### 4. P12: vòng bổ sung nguồn chưa giải quyết được sự bất đồng của audit

P12 hỏi công thức Q và điều kiện tính. Lượt591 và595 dùng đúng cùng sáu context IDs.
Lượt595 báo đủ hai topic chính nhưng audit yêu cầu định nghĩa và thang điểm bốn
biến. Server phục hồi bốn clause từ nguồn rồi kiểm lại; cuối cùng có6claim accepted,
không binding/verification errors, nhưng `audit_complete=false` và vẫn báo thiếu
định nghĩa/thang điểm. Fallback trả `PROSE_NOT_FULLY_VERIFIED`.

Nguyên nhân trực tiếp là quyết định audit không hoàn tất sau repair, không phải
không tìm được công thức. Trace chưa giữ toàn bộ claim/audit cuối của lượt thất bại,
nên chưa thể khẳng định mọi phần định nghĩa đã hiện đúng trong public draft hoặc
chỉ ra verdict nào nhận sai. Không nên tắt audit hay tự coi câu này đạt.

### 5. P15: đơn vị đoạn nguồn quá rộng cho câu hỏi hẹp

Hai mốc cần phân biệt là ngày ban hành mô phỏng18/10/2026 và ngày bắt đầu áp dụng
01/11/2026. Cả hai được verifier xác nhận có trong nguồn. Nhưng các đoạn model chọn
kèm ngày kết thúc kỳ đánh giá và dữ liệu không được hỏi; claim bị loại dù có hai
ngày đúng. Repair chọn lại đoạn vẫn chứa thông tin thừa nên không còn claim accepted.

`resolve_proposal(..., separate_context=True)` lấy nguyên phần thân passage được
chọn; model không viết lại nội dung công khai. Cách này bảo vệ nguyên văn nhưng
nếu chọn whole passage quá rộng, một mệnh đề thừa có thể làm cả claim bị từ chối.
Lỗi cần xử lý ở phân tách/chọn span và vai trò body/context, không phải thêm mọi
ngữ cảnh lân cận hoặc bỏ điều kiện relevance của verifier.

## Những gì đã loại trừ và giới hạn kết luận

Đối chiếu JSON/hashes thực tế xác nhận:

- Cùng64query và rubric; cùng toàn bộ profile; canonical, SHA nguồn, revision và
  index giống nhau. Snapshot chỉ khác `created_at`, các trường ghim dữ liệu giống.
- Mã `prose_fallback.py`, `evidence_verification.py`, `evidence_indexed_audit.py`,
  `source_scope_audit.py`, `response_audit.py`, `evidence_passages.py` giống cả591,
  595 và file hiện tại. Mã inference cũng được đọc/đối chiếu, không có thay đổi595.
- P12/P15 dùng cùng context IDs với591 và không mở wiki. Các lời gọi structured
  trong bốn ca chất lượng trả hợp đồng hợp lệ; hợp lệ JSON không chứng minh đúng nghĩa.
- Lượt595 dùng Luna, không fallback; prompt lớn nhất quan sát23.623tokens. Không có
  chứng cứ context overflow ở chín FAIL, không liên quan giới hạn Qwen32K trong lượt này.
- 1.239file source/test/FE khớp seal595 trước/sau phân tích. Không thay mã hoặc dữ liệu.

Không có các lần chạy lặp/paired ablation cùng output model để quy tỷ lệ giảm cho
từng thay đổi mã. Cùng model và temperature không bảo đảm cùng selection/verdict.
Không nên gọi tất cả là ngẫu nhiên, cũng không nên coi mọi loss là regression đã
chứng minh do595. P07 thiếu điều kiện là lỗi thực; P12/P15 từ chối câu có nguồn cũng
là lỗi chất lượng cần xử lý, dù nhánh mã đó không đổi.

Unit tests chứng minh guard/contract với fixture. Replay trang thật có fixture
navigation chứng minh đóng gói. Chúng không thay thế nghiệm thu ổn định bằng LLM
thật; vì vậy381focused PASS không mâu thuẫn với live64 FAIL.

## Thứ tự xử lý đề xuất

1. Tách lượt model phụ khỏi benchmark; chạy tuần tự/có điều phối, giữ đúng phân loại
   lỗi busy/quota/provider. Không tăng quota, tắt lease hoặc đổi model để tạo điểm xanh.
2. Ưu tiên P07: điều kiện đã xác minh chi phối quyền/ngoại lệ cần trở thành nghĩa vụ
   coverage có nguồn; model không tự hủy nghĩa vụ đó. Không suy applicability chỉ
   từ đứng cạnh nhau. Bổ sung ca bỏ tiền đề, giữ ngoại lệ, bảng tóm tắt so với luật gốc.
3. P15/P12: chọn span vừa đủ, tách body/context và kiểm giữ nguyên các clause phục hồi
   với đúng chủ nguồn. Audit phải phân biệt thông tin thừa với điều kiện cần; không
   loại cả đáp án đúng hoặc thêm mọi định nghĩa lân cận một cách máy móc.
4. F08: đối chiếu cách trình bày tương đương có kiểm soát cho rewritten query, giữ
   nguyên quote/provenance; không bỏ kiểm mã, metric, vai trò năm, phủ định và scope.
5. Lưu thêm ID/flag/cause an toàn của selection/audit thất bại để đối soát chính xác;
   không log raw private prompt. Regression gồm cả cho qua sai và từ chối sai.
6. Sau batch được giao sửa: chạy lại nguyên64 tuần tự, cùng nguồn/model/rubric và
   đối chiếu từng ID. Không ghép retry, không hạ Quality Gate hoặc mở rộng context mù.

## Kiểm chứng phiên này

- Đã chạy từ repo root:
  `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context596_analysis.py`.
- Exit0: kiểm đối chiếu artifact, pure-function replay P07 và synthetic literal probes;
  1.239code seals giữ. Đây là kiểm chứng offline, **không** phải benchmark/test app PASS mới.
- Bằng chứng chọn lọc: [offline-analysis.json](../../../backend/storage/context596/offline-analysis.json).
- Không gọi LLM, DB, MinIO, Qdrant; không chạy lại64 hoặc full suite. Full3238PASS/
  18FAIL/17SKIP là kết quả lịch sử595, vẫn FAIL; phiên này full/live/FE NOT RUN.
- Chỉ bổ sung báo cáo/memory và helper phân tích; không sửa app, model, cấu hình,
  nguồn, index hoặc publication; không restart/deploy/commit/push. Không thử dọn
  Storage đang được policy bảo vệ.
