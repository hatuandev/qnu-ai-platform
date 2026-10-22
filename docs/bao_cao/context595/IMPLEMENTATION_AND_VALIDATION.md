# Context595 — Hoàn thiện mục3–6 của review Context593

Ngày22/10/2026. Người dùng giao xử lý tiếp bốn mục: vai trò năm, tập tham chiếu nhiều
đối tượng/bảng, phân bổ navigation budget, cache khi budget/policy/source đổi.
Giữ nguyên model/source/index/Quality Gate/publication; không commit/push/restart/deploy.
Đây không phải triển khai ưu tiên wiki4–6 của roadmap cũ hoặc đồ thị xuyên nguồn.

## Thay đổi

1. **Vai trò thời gian:** kiểm độc lập calendar/academic/data/publication/effective/event,
   giá trị/range và liên kết năm với chủ thể khi đối chiếu nhiều chủ thể. Không còn chỉ so
   tập chữ số. Referent gắn sai role hoặc quote không phân biệt được role cùng số bị chặn.
   Đường tắt đổi năm không tự sửa năm học/ban hành/hiệu lực. Nhánh legacy cũng giữ role.
2. **Tập tham chiếu:** nhiều giá trị cùng field không tự coi là conflict. Tập hợp phải có
   căn cứ trong user syntax và quote từng phần; câu sửa một đối tượng vẫn thay đối tượng
   cũ. So sánh hai chủ thể được user yêu cầu rõ có thể lấy căn cứ từ hai lượt khác nhau.
   Locator gắn tài liệu chứa nó: tráo Bảng4/Bảng5 giữa hai nguồn bị từ chối dù đủ tên.
   Không từ điển tên ngành/mã, không suy mã từ tên, không dùng assistant làm bằng chứng.
3. **Budget:** bỏ hai bước chia ba cứng. Các trang thực sự được model chọn dùng chung
   ngân sách; ưu tiên từng section hoàn chỉnh và giữ dependency closure, loại section
   vượt giới hạn thay vì cắt mất điều kiện. Caller truyền tổng context budget; allocator
   dành chỗ cho canonical evidence, packing cuối vẫn giữ cổng ngân sách tổng.
4. **Cache:** giữ nội dung/selection riêng với view phụ thuộc ngân sách. Mỗi hit tái kiểm
   quote, ID/revision/hash/nội dung, các reference và dependency rồi đóng gói theo budget/
   policy hiện tại. Giảm/tăng budget không gọi lại model hoặc reset call counter. Snapshot/
   plan/candidate mode khác không dùng cache cũ. Policy tắt sẽ xóa view hiển thị.

File ứng dụng: `conversation_time.py` mới; sửa `conversation_scope.py`,
`conversation_resolution.py`, `intent_contracts.py`, `wiki_context.py`,
`evidence_pipeline.py`. Test mới `test_context_extension_595.py`.

Mô hình vẫn chọn điều hướng qua ModelOps; nó không chứng minh quyền hoặc tự duyệt nguồn.
Không mở rộng cửa sổ lịch sử8userturn/12referent hoặc độ sâu đồ thị lưu trữ.
Tên/quan hệ mơ hồ, ví dụ hai bảng cùng tên nhưng không chỉ rõ tài liệu, vẫn có thể hỏi lại.
Đây là kiểm chứng literal/role/set theo cấu trúc ngôn ngữ hỗ trợ, không phải bộ hiểu mọi
cách diễn đạt tự nhiên. Bảo toàn các guard P1 của Context594.

## Kết quả cuối cùng

**Đã triển khai guard/budget/cache của mục3–6; chưa nghiệm thu toàn bộ chất lượng RAG.**

| Kiểm tra | Kết quả thực chạy | Exit code / bằng chứng |
|---|---|---|
| Baseline trước sửa, fixture đúng ngưỡng | 7FAIL/3PASS, tái hiện R04–R08 | 1; [JUnit đỏ](../../../backend/storage/context595/checks/baseline-corrected.xml) |
| Focused,10file | **381PASS**, gồm43regression mới | 0; [JUnit cuối](../../../backend/storage/context595/checks/focused-final.xml) |
| Ruff7file | **PASS** | 0; [receipt](../../../backend/storage/context595/checks/ruff.json) |
| Full Pytest | **3.238PASS/18FAIL/17SKIP**,23subtestsPASS | **1, full vẫn FAIL**; [JUnit](../../../backend/storage/context595/checks/full-acceptance.xml) |
| So baseline594 | 43test mới PASS,0lỗi mới/thiếu ID/đổi cause | 0; [đối chiếu từng ID](../../../backend/storage/context595/checks/full-acceptance-comparison.json) |
| Replay11 trang thật,339canonicalblocks | **11/11 mở được**, hạ2000chars đạt, action không lặp | 0; [summary](../../../backend/storage/context595/wiki-replay/summary.json) |
| Router+Luna,4synthetic | **4/4PASS**,5usage/12.569input/2.022output,0fallback | 0; [summary](../../../backend/storage/context595/scope-live/summary.json) |
| Frozen64 thật | **51/60 tri thức (85%)**,41/50positive (82%),10/10negative,4/4social | runner0/scorer**1**/postcheck0; [summary](../../../backend/storage/context595/acceptance/summary.json) |
| Thử lại riêng5lỗi lease, tuần tự | **5/5PASS**,24/24citations;14Luna usage/42.568input/1.110output,0fallback | runner0/postcheck0; [summary riêng](../../../backend/storage/context595/provider-retry/summary.json) |

Ngưỡng benchmark hiện tại yêu cầu đồng thời ít nhất51/60tri thức và43/50positive.
Lượt64 này đạt cổng tri thức nhưng **chưa đạt cổng positive**. Không thay rubric hoặc
cộng5retry để suy thành56/60. Nhãn là draft source-rubric do Codex đối soát, không phải
holdout người dùng đã duyệt. Không gọi judgeLLM; các adjudication ghim hash đáp án.

### Đối chiếu đúng bốn finding

| Review593 | Guard/kiểm chứng | Trạng thái |
|---|---|---|
| R04: mất năm học khi đổi năm | Explicit/inherited academic role, publication/effective/event/data role, tráo năm hai chủ thể, role referent sai, router hỏi lại | Đã sửa; regression PASS; T01Luna thật PASS |
| R05/R06: hai giá trị cùng field bị conflict | Hai ngành, mã, cơ quan, bảng; hai lượt có yêu cầu so sánh; giữ nguồn của locator; thiếu/tráo thành viên vẫn chặn | Đã sửa; regression PASS; M01/M02/M03Luna thật PASS |
| R07: section phù hợp bị chia ba loại sớm | Single large section, selected pages share budget, partial view nguyên section, reserve canonical closure, cycle/shared note | Đã sửa; regression PASS; replay nguồn thật11/11 |
| R08: cache trả quá budget mới | Shrink/grow, policy disable/change, text/hash/index/snapshot đổi, mất reference/closure, counter không reset | Đã sửa; regression PASS; replay2000chars đúng |

Replay dùng DB/source thật ở transaction read-only, model action là fixture: **không**
chứng minh LLM chọn trang đúng. Bốn ca synthetic dùng ModelOps thật, chỉ routing: **không**
chứng minh trả lời đúng nguồn. Lượt64 là authenticated candidate RAG thật ghim snapshot,
không HTTP/browser E2E hay assistant đã xuất bản. Không chạy dense/hybrid/rerank ablation
hoặc suy Hit@K/Recall@K từ điểm đáp án.

### Chín FAIL trong lượt64

| IDs | Kết quả và nguyên nhân quan sát | Xử lý trong phiên |
|---|---|---|
| N17,N18,N19,N20,M05 | Provider bị skip `key_lease_unavailable`, báo `ALL_PROVIDERS_UNAVAILABLE` | Giữ FAIL gốc; sau khi dừng lượt model phụ, thử riêng tuần tự5/5PASS; không tắt lease guard |
| F08 | Referent metric không giữ nguyên cụm trong standalone, cả lần đầu và bounded repair; router hỏi lại | Giữ FAIL; không hạ literal guard hoặc đoán bị riêng hoa/thường |
| P07 | Câu trả lời thiếu điều kiện chậm chữ ký do cơ sở tạm đóng, nhật ký và xác nhận giảng viên cùng kỳ | Condition vẫn có trong final context, không phải bằng chứng parser mất dữ liệu; chưa sửa answer-audit ngoài phạm vi |
| P12,P15 | `VISIBLE_ANSWER_NOT_SUPPORTED`, nhánh `fact_hybrid`/prose fallback, không dùng wiki | Giữ FAIL, không coi từ chối là PASS cho câu có căn cứ |

[Phân tích bằng chứng](../../../backend/storage/context595/acceptance/failure-analysis.json)
và [từng label](../../../backend/storage/context595/acceptance/labels-final.json).
Mã nguồn/hashes/test không đổi trong các lượt nghiệm thu.

So bộ64 lịch sử591: cùng nguồn/model/config/query/rubric, gainF03; lossN17/N18/N19/
N20/M05/F08/P07/P12/P15; không commonFAIL. [Bảng so sánh](../../../backend/storage/context595/acceptance/baseline-comparison.json).
Chưa có ablation chứng minh mọi loss do code;5lease failures có nhiễu vận hành và những
lượt model khác nhau có thể chọn câu/claim khác. F03 vẫn75SV/page6; F08 từng thất bại
literal từ các lượt trước, không được coi test cũ xanh là bảo đảm model luôn tuân thủ.
P12/P15 không đi qua nhánh wiki đang sửa, không quy lỗi đó cho cache hoặc context32K.

Lượt64 dùng118Luna usage,881.237input/33.028output,0fallback;106/106citations resolve.
Max prompt quan sát23.623tokens; đây là quan sát của lượt này, không chứng minh context
window của model khác. Tất cả lượt dùng Luna chính; fallback Qwen trong DB giữ nguyên.

### Bằng chứng và lệnh

Cwd repo root; Python3.12 trong `backend/.venv`. Helper giữ command/cwd/exit code thật:

- `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context595_checks.py run --label baseline-corrected --baseline tests/test_context_extension_595.py`
- `context595_checks.py run --label focused-final` với10file ghi trong receipt/JUnit.
- `context595_gate.py` chạy full từ backend, DB/Storage/basetemp riêng;
  [receipt](../../../backend/storage/context595/checks/full-acceptance-run.json).
- `context595_compare.py full-acceptance`: exact test IDs/cause với594.
- `context595_acceptance_preflight.py` → `prepare.py` → `run.py` → `postcheck.py`
  → `score.py` (tiền tố đầy đủ `context595_acceptance_`), tất cả bằng Python trên.
- `context595_scope_live.py`:4ca mới qua router/ModelOps thật.
- `context595_wiki_replay.py`: real read-only source + fixture navigation.
- `context595_provider_retry_run.py`/`postcheck.py`:5retry riêng, cùng history trước mỗi
  request như lượt gốc; không thêm đáp án retry của câu trước vào history câu sau.

Frontend lint/build **NOT RUN** vì không sửa frontend. Đã chạy full64, không còn ghi
full64NOTRUN cho phiên này. [Seal và encoding](../../../backend/storage/context595/checks/source-hygiene.json).

## Các lượt trung gian và giới hạn vận hành

Test ban đầu có hai fixture kích thước không vượt ngưỡng mong muốn; sửa fixture5000 và
2500chars, chạy lại trên snapshot app trước sửa. Kết quả đỏ7FAIL/3PASS sau sửa fixture
mới là bằng chứng tái hiện budget/cache. Focused đầu4FAIL/139PASS; sau batch143PASS;
expanded170PASS; target-year139PASS/1FAIL (common year cuối cụm so sánh); sau sửa
376PASS,380PASS, cuối381PASS. Giữ toàn bộ JUnit/log, không đổi assertion để che lỗi app.

Lượt64 có N17/N18/N19/N20/M05 lỗi `ALL_PROVIDERS_UNAVAILABLE`; log xác nhận provider bị
skip vì `key_lease_unavailable`. Lượt synthetic chạy đồng thời có thể tranh suất gọi
khóa với benchmark; đây là hạn chế do cách bố trí thí nghiệm, không được quy cho nguồn,
context32K hoặc thay đổi retrieval. Không tắt lease policy, đổi model hoặc nới quota.
Các câu lỗi vẫn FAIL; không cộng kết quả retry vào điểm bộ64.

F08 bị chặn vì referent metric không còn nguyên cụm trong query, cả proposal và repair
đều có `VALUE_NOT_IN_STANDALONE_QUERY`. Đây là lỗi hợp đồng literal đã quan sát ở594;
không lưu rejectedquery nên không quy chắc riêng cho hoa/thường. Giữ hỏi lại an toàn,
không đổi guard hoặc model để tạo PASS.

## An toàn

DB/MinIO/Qdrant loopback development được kiểm chứng trước chạy. Pytest dùng DBtest
riêng có owner nonce, Storage local tạm, endpoint ngoài127.0.0.1:1 và không migration DB
chung. Live benchmark dùng authenticated candidate snapshot đã có, ghim exact revisions/
hashes và Luna-only trong phạm vi thí nghiệm, không thay fallback config DB. Chỉ giữ
ModelOps usage/lease audits thật; không tạo chat/thread/gap nguồn để dọn.

Storage test không thử xóa qua công cụ khác sau hạn chế cleanup cũ. Không ghi credential,
private prompt hoặc raw corpus vào báo cáo Git. DBtest `qnu_test_context595_2df667fab351` đã dọn sau đối chiếu owner nonce;
Storage tạm vẫn giữ theo chính sách, trạng thái `database_removed_storage_pending`.
Code seals khớp1.239file trước/sau full/live. [Task delta](../../../backend/storage/context595/checks/task-delta.json)
xác minh5appfile cũ đổi,1appfile mới; app ngoài scope giữ nguyên. Git chưa stage/commit/push.

Postcheck bổ sung đầu tái sử dụng nhãn completed_requests64 của helper cũ, trong khi
assert thực tế là5; sửa nhãn thành observed count5 và chạy lại read-only postcheck.
Giữ `provider-retry/postcheck-attempt-1.json` để truy vết, không thay kết quả request.

Kết luận bàn giao: chức năng guard/set/role/allocation/cache của4mục có regression và
kiểm chứng tương ứng. Chất lượng RAG tổng thể **chưa APPROVED** theo mục tiêu85%positive;
các lỗi answer-audit/prose/literal còn lại cần xử lý riêng trước khi tuyên bố đạt toàn bộ.
