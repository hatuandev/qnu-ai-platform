# Context594 — Bảo toàn đối tượng, nguồn và điều kiện hội thoại

Phạm vi người dùng giao: sửa mục 1–2 (P1) của review Context593, trước khi mở rộng liên kết.
Không triển khai mục 3–6 hoặc ưu tiên wiki 4–6.

## Nguyên nhân và cách sửa

Guard cũ chỉ xác minh referent được model khai báo, không kiểm coverage của đối tượng/nguồn.
Kiểm phủ định chỉ đếm sự xuất hiện từ phủ định. Vì vậy, model có thể đổi chủ thể mà chỉ
chứng minh năm, đổi đích bị loại trừ, hoặc bỏ điều kiện của lượt trước.

Bổ sung `conversation_scope.py`: đọc các cấu trúc ngôn ngữ chỉ đối tượng, cơ quan, mã,
tài liệu và vị trí từ chính user turns; kiểm câu viết lại giữ đủ tên cùng quote đúng lượt.
Nguồn có URL phải giữ toàn bộ định danh, không chỉ cùng giao thức. Tên trích dẫn và mã
được giữ nguyên, không suy tên từ mã hoặc mở quyền đọc tài liệu.

Điều kiện được giữ nguyên cụm, gồm đích, phủ định lồng và toán tử AND/OR; kiểm cả phần
nối qua dấu chấm phẩy. Chỉ lệnh người dùng bỏ/thay rõ một cụm điều kiện được trích nguyên
văn mới được áp dụng; lệnh phủ định hoặc câu trích dẫn lệnh không là cho phép xóa lọc.
Khi xử lý thành công, câu truy vấn không nối lại phần điều kiện vừa được bỏ.

Nhánh legacy cũng kiểm tên/điều kiện bằng literal user text, không bắt nó dùng schema
tham chiếu mới. Nhánh hybrid vẫn yêu cầu referent có bằng chứng. Đường tắt đổi năm chỉ
được dùng nếu không bỏ qua một lượt user mới hơn. Một lần repair, cùng deadline20s,
không thêm vòng JSON retry; provider/quyền/cancellation giữ hành vi cũ.

Phương pháp thận trọng: câu diễn đạt lại không chứng minh được giữ nghĩa sẽ hỏi lại.
Giữ mọi điều kiện trong cửa sổ user hiện có; không tự bỏ điều kiện vì model chọn một
antecedent gần hơn. Đây không phải bộ phân tích mọi ngôn ngữ tự nhiên; chưa mở rộng tập
nhiều đối tượng, vai trò năm, lịch sử vô hạn, đồ thị xuyên nguồn hoặc wiki budget/cache.

## File thay đổi

- `backend/app/modules/rag/conversation_scope.py`: kiểm coverage tên/nguồn và điều kiện.
- `backend/app/modules/rag/conversation_resolution.py`: tích hợp guard/diagnostics,
  chống bypass legacy/literal-year, giữ original user request trong provenance.
- `backend/app/modules/rag/intent_contracts.py`: thêm role source, giữ schema cũ tương thích.
- `backend/tests/test_context_scope_integrity_594.py`: regression tổng quát, không dùng mã
  hay đáp án của PDF benchmark làm từ điển chạy thật.

## Kiểm chứng cuối batch

| Kiểm tra | Kết quả thực tế | Exit code / bằng chứng |
|---|---|---|
| Baseline trước sửa,22 ca ban đầu | 15 FAIL /7 PASS, tái hiện đúng lỗi | 1; [JUnit đỏ](../../../backend/storage/context594/checks/baseline-p1-corrected.xml) |
| Bổ sung URL/Boolean trước sửa batch2 | 6 FAIL /50 PASS | 1; [JUnit mở rộng đỏ](../../../backend/storage/context594/checks/extension-red.xml) |
| Focused cuối,7 tệp | **290 PASS** | 0; [JUnit](../../../backend/storage/context594/checks/focused-coverage.xml) |
| Ruff4file sửa | **PASS** | 0; [receipt](../../../backend/storage/context594/checks-final/ruff.json) |
| Full Pytest cuối | **3.195 PASS /18 FAIL /17 SKIP**,23 subtests PASS | **1, full vẫn FAIL**; [JUnit](../../../backend/storage/context594/checks-final/full-acceptance.xml) |
| Đối chiếu với Context592 | 56 test mới PASS; không ID lỗi mới/mất/đổi nguyên nhân | 0; [so sánh exact IDs/cause](../../../backend/storage/context594/checks-final/full-acceptance-comparison.json) |
| Luna/candidate8 câu F01–F08 | **8/8 PASS**, citations8/8,0runtime errors | runner0/scorer0/postcheck0; [summary](../../../backend/storage/context594/followup-final/summary.json) |
| Luna/router4 tình huống mới | **3/4 PASS**,C04FAIL và hỏi lại an toàn | 1; [summary](../../../backend/storage/context594/scope-live/summary.json) |
| Runtime/source/vector/model seals | PASS trước/sau,0retrievable; không publish | [postcheck sau cả4probe](../../../backend/storage/context594/followup-final/scope-postcheck.json) |

Full baseline592 là3.139PASS/18FAIL/17SKIP. Danh sách từng test, status và cause có trong
artifact so sánh, không chỉ so tổng số. Bộ test còn18 lỗi nền nên không tuyên bố full PASS.

### Phạm vi regression

56 ca mới bao phủ đổi/ngầm thêm đối tượng, thiếu proof, mất cơ quan/locator, nguồn mới
có cùng Bảng4, toàn bộ URL và tên tài liệu trích dẫn, không lấy assistant làm căn cứ;
đổi A/B, mất lọc nhiều lượt, AND/OR, phủ định lồng, substring target, điều kiện dương,
ngày/ngưỡng và tiếng Anh; bỏ/thay nguyên cụm rõ ràng và từ chối lệnh mơ hồ/phủ định;
legacy rewrite, đường tắt năm và kiểm router không tạo request retrieval khi scope sai.

Các test đối chiếu trọng tâm:

- R01 → `test_unproven_scope_is_rejected[invented-subject/omitted-proof/changed-source]`.
- R02 → `test_unproven_scope_is_rejected[swapped-exclusion]` và nhóm Boolean-tail.
- R03 → `test_unproven_scope_is_rejected[lost-inherited-filters/lost-multiturn-filter]`.
- Ranh giới router → `test_invalid_scope_never_becomes_a_retrieval_request_after_repair`,
  `test_repair_restores_complete_scope_using_only_user_turns`,
  `test_explicit_removal_is_not_reintroduced_into_the_retrieval_query`.

Các ID parametrized đầy đủ nằm ở JUnit; tên rút gọn trên chỉ chỉ nhóm hành vi.

### Thử thật và giới hạn

Bộ8 giữ nguyên questions/rubric/gold spans/fact IDs/source revision/index với Context592.
Cuối batch có6Luna usage,14.778input/2.219output tokens,0fallback. F03 vẫn75SV/page6.
Hai lượt sửa reference đã được chấp nhận ở F07/F08. Không gọi judgeLLM, không ghép điểm
với bộ64 Context591; **full64 hiện tại NOT RUN**. Đây là authenticated candidate service,
chưa HTTP/browser E2E hoặc assistant đã xuất bản.

Bốn tình huống synthetic gọi ModelOps thật, chỉ kiểm routing, không retrieval:

| ID | Tình huống | Kết quả |
|---|---|---|
| C01 | Đổi metric nhưng giữ điều kiện và loại trừ kế thừa | PASS sau bounded repair |
| C02 | Thêm loại trừ hiện tại, giữ ngành và năm | PASS sau bounded repair |
| C03 | Giữ tài liệu, bảng, ngành, trường và năm | PASS ngay |
| C04 | Bỏ một điều kiện được trích nguyên cụm | **FAIL**; hỏi lại, không chuyển sang retrieval |

Bốn ca dùng7Luna usage/17.077input/2.470output,0fallback. C04 cả hai proposal bị lỗi
`VALUE_NOT_IN_STANDALONE_QUERY` ở metric. Quote và giá trị referent có căn cứ, nhưng
cụm giá trị không được giữ nguyên trong câu viết lại. Bản proposal bị từ chối không
được lưu; **không đủ chứng minh lỗi riêng do hoa/thường**. Nhận định hoa/thường trong
commentary đã được đính chính. Không gọi lại để thay kết quả hay hạ kiểm tra literal.
Regression không dùng LLM đã chứng minh nhánh bỏ điều kiện đúng hoạt động; C04 chưa
chứng minh thành công bằng model thật, không được gộp thành4/4 hoặc coi mock là E2E.

Đây là giới hạn độ ổn định của hợp đồng literal ở model, không có bằng chứng guard
mất điều kiện hoặc nạp dữ kiện sai trong C04. Mục1–2 đã có guard và regression cho các
gap review; không tuyên bố toàn bộ hội thoại/6 mục review đều được nghiệm thu.

### Các lượt trung gian được giữ

- Baseline đầu14FAIL/8PASS có fixture changed-source vô tình chứa ref Sigma không ở
  nguồn; bỏ ref dư trong fixture, chạy bản code trước sửa lại thành15FAIL/7PASS.
- Focused đầu1FAIL/213PASS vì ranh giới `program` cắt tên `Program0`; sửa word boundary.
- Focused-routing1FAIL/232PASS do đổi mã lỗi legacy filter; giữ thứ tự guard cũ, không sửa assertion.
- Focused-expanded231PASS; focused-final279PASS; focused-release283PASS; cuối290PASS.
- Live8 đầu8/8,8/8citations,5Luna usage/0fallback; sau đó phát hiện URL/Boolean-tail,
  nên giữ như kết quả trung gian và thử lại8 câu trên đúng code cuối.
- Full đầu dừng~42% do gap mới: **INTERRUPTED**, không coi là full đã hoàn tất.
  Chỉ dừng process tree của helper Context594 sau khi xác minh PID/command line;
  không restart/dừng BE,worker,FE hoặc dịch vụ người dùng.
- DBtest đầu được dọn theo owner nonce; final dùng DBtest mới để tránh dư dữ liệu.

### Lệnh đã chạy

Cwd repo root, Python3.12 của `backend/.venv`. Helper giữ nguyên command/cwd/exitcode:

- `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context594_checks.py run --label baseline-p1-corrected --baseline tests/test_context_scope_integrity_594.py`
- `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context594_checks.py run --label focused-coverage tests/test_context_scope_integrity_594.py tests/test_context_reference_repair_592.py tests/test_hybrid_conversation.py tests/test_hybrid_intent_routing.py tests/test_conversation_acts.py tests/test_wiki_navigation.py tests/test_rag_reliability_591.py`
- `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context594_final_gate.py`:
  gọi Pytest từ backend với basetemp/Storage/DB riêng; [receipt](../../../backend/storage/context594/checks-final/full-acceptance-run.json).
- `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context594_compare.py full-acceptance`
- `context594_final_preflight.py` → `context594_final_prepare.py` → `context594_final_run.py`
  → `context594_final_postcheck.py` → `context594_final_score.py`, cùng Python ở trên.
- `context594_scope_live.py` và `context594_scope_postcheck.py`:4probe thật; không retry batch uncertain.
- `backend/.venv/Scripts/ruff.exe check backend/app/modules/rag/conversation_scope.py backend/app/modules/rag/conversation_resolution.py backend/app/modules/rag/intent_contracts.py backend/tests/test_context_scope_integrity_594.py`

Frontend lint/build và full64 **NOT RUN**, vì không sửa frontend và chỉ nghiệm thu phạm vi hội thoại.

## Bảo vệ và giới hạn

DB/MinIO/Qdrant local đã xác minh. Pytest dùng DBtest riêng, Storage local tạm,
endpoint ngoài bị trỏ127.0.0.1:1; không migration DB dùng chung. Live dùng candidate có
quyền và snapshot server xác minh, giữ ModelOps audit thật, không HTTP/browser E2E.

Giữ model Luna chính/Qwen dự phòng, PDF/canonical/revision/index/hash, Quality Gate và
publication. Không reindex, xuất bản, restart, deploy, stage, commit hoặc push.
Storage test giữ lại theo hạn chế cleanup đã có; không thử lại xóa qua công cụ khác.


Hai DBtest `qnu_test_context594_adeebc2dea4e` và `qnu_test_context594_2bfb4133c170` đã
xóa sau đối chiếu tên/owner nonce; runtime Storage còn, trạng thái
`database_removed_storage_pending`. Không thử lại thao tác xóa Storage bị chặn ở phiên trước.
Usage/lease audit thật giữ nguyên. Code seals trước/sau full/live khớp1237file;
[task delta](../../../backend/storage/context594/checks-final/task-delta.json) xác nhận chỉ
hai appfile cũ đổi và thêm một helper module,428 appfile khác giữ nguyên.
[Kiểm encoding](../../../backend/storage/context594/checks-final/source-hygiene.json): UTF-8noBOM/LF,
không replacement char, không tên/mã của benchmark trong appcode vừa sửa.
