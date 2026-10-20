# Context565 — Kiểm thử và regression

## Môi trường

Đã xác minh development và DB/MinIO/Qdrant loopback trước chạy. Pytest dùng DB nonce riêng với ownership comment,49tables, Storage riêng; MinIO/Qdrant/Redis test trỏ loopback port1. Không migration hoặc auto-seed DB dùng chung. Source/config audit dùng transaction READ ONLY.

Runtime thật dùng actor development admin hiện hành và snapshot published; chỉ tạo các hội thoại kiểm thử thuộc phạm vi cho phép. Hash trước/sau của5collections/23bindings/2source revisions/27indexes/5assistants/13provider configs khớp.

## Lệnh và receipts

Từ repo root, Python venv đã có, không cài dependency:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context565/isolation.json --audit-file backend/storage/context565/safety.json --evidence-dir backend/storage/context565/tests --label focused-current tests/test_context565_entity_metric.py tests/test_temporal_fact_contract.py tests/test_facts.py tests/test_review536_findings.py tests/test_evidence_closure_564.py tests/test_qnu_serving.py tests/test_hybrid_chat_integration.py tests/test_hybrid_conversation.py tests/test_evidence_contracts_500.py tests/test_evidence_retrieval_regressions.py tests/test_qnu_fact_identity.py tests/test_excel_facts_ingestion.py tests/test_evidence_scope_452.py
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context565/isolation.json --audit-file backend/storage/context565/safety.json --evidence-dir backend/storage/context565/tests --label full-verified
```

Runner thực thi `pytest -q` với cwd `backend`, basetemp/JUnit riêng. Exact commands, exit codes và toàn test IDs nằm trong `backend/storage/context565/tests/*-run.json`, `*.xml`, `*.log`. Ruff kiểm17file app/test thuộc task; không sửa frontend nên frontend build NOT RUN.

| Gate | Kết quả | Exit | Ý nghĩa |
|---|---|---:|---|
| `baseline-focused` | NOT RUN | 4 | Sai tên file test; đã sửa invocation |
| `baseline-corrected` | 59 PASS | 0 | Trước sửa ứng dụng |
| `red` | 20 FAIL /5 PASS | 1 | Tái hiện entity/metric/row identity |
| `focused-first` | Collection ERROR | 2 | Import cycle do đặt helper dưới services eager package; đã chuyển helper thuần về knowledge root |
| `focused-second` | 82 PASS /2 FAIL | 1 | Phát hiện contract bare quantity cũ và diễn đạt tuyển sinh; xử lý có giải thích |
| `focused-third`, `closure-sql` | FAIL/ERROR | 1 | Fixture async bị khai báo thiếu fixture/result mock sai; receipts giữ, không tính nghiệm thu |
| `focused-final` | 203 PASS /2 FAIL | 1 | SQL test dùng pool qua loop khác; unknown-year check chặn conversion; đều đã sửa và tái kiểm |
| `narrative-red` | 1 FAIL | 1 | Code+năm không được ép narrative thành quantity |
| `followup-fix` | 116 PASS | 0 | Sau lỗi live current metric |
| `verification-sealed` | 249 PASS | 0 | Lịch sử trước bổ sung coverage/fallback/debug |
| `focused-current` | **253 PASS** | **0** | Gate focused cuối,10,48s |
| `full-final` | NOT COMPLETE | interrupted | Dừng trước khi coi là gate; rà soát method-vs-unit yêu cầu bổ sung |
| `full-sealed` | NOT COMPLETE | interrupted | Bị ngắt phiên trước JUnit, không dùng như full PASS; không còn process trước chạy lại |
| `full-current` | 2745PASS/20FAIL/17SKIP+23subtests | 1 | Có2newFAIL do orchestration fixtures thiếu strategy boundary, không gọi no-regression |
| `orchestration-compat` | 70PASS | 0 | Giữ expected, cập nhật mock ranh giới cho2unit tests; không làm bằng chứng E2E |
| `full-verified` | **2747PASS/18FAIL/17SKIP+23subtestsPASS** | **1** | Full gate vẫn FAIL;54addedPASS,0changed/removed;18failure IDs/causes giữ nguyên |
| Ruff17files | PASS | 0 | Không auto-fix toàn repo |
| Live app /TCP | 13/13 và8/8 +2scalar cuối đạt | 0 | Xem báo cáo E2E; kiểm lại23responses theo source coordinates |

## Baseline và contract

Context564 `full-final.xml` là baseline gần nhất đáng tin:2693PASS/18FAIL/17SKIP+23subtests. Working tree Context564 được giữ, không reset. Đối chiếu cuối theo test ID và failure cause, không chỉ tổng số.

Một test cũ được đổi contract công khai: bare `Số lượng` phải giữ nhãn nguồn/unknown, không sinh quota. Fixture/value giữ nguyên và thêm assertion chống tạo quota sai. [IMPLEMENTATION_REPORT](IMPLEMENTATION_REPORT.md) giải thích cụ thể; không coi expectation cũ là chứng cứ semantic đúng.

Các tests mới bao phủ normalization/candidates, code-name positions, quantity roles, pipeline selection, leading zero/case, SQL exact match trước LIMIT với nhãn metric cũ, source hash/revision/column/manifest, human override, unit/year unknown, cutoff method, current metric và canonical prose routing. [REGRESSION_IDS](REGRESSION_IDS.md) chứa IDs và nguyên nhân lỗi nền.

## Kiểm tra riêng các lỗi nền liên quan fact lookup

`test_tools.py::test_fact_layer_lookup_tool_found` và `test_universal_tools.py::test_fact_layer_lookup_tool` gọi `tools/builtin/fact_lookup_tool.py`, không đi qua `rag.facts.FactLayer` vừa sửa. Tests không tạo fixture nguồn/facts mà đòi dữ liệu ngành có sẵn trong `col_admissions`. Trong DB test cô lập, tool trả status success nhưng found=false; lỗi nền là giả định dữ liệu test chưa được seed. Không sao chép corpus thật vào test DB chỉ để làm các tests này xanh.

`test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` và hai dispatcher tests khác thiếu collection seed trong môi trường cô lập. Đây không phải bằng chứng scalar chat AM-0007 thất bại; chat E2E riêng đã đối chiếu nguồn thật và đạt. Mặc dù vậy, chúng vẫn giữ trạng thái FAIL trong full gate, không được bỏ khỏi báo cáo.

Qua đọc mã, builtin fact tool có SQL riêng, không tái dùng snapshot/metric resolver này. Task không nghiệm thu đường agentic tool đó; nếu dùng nó cho số liệu chính thức thì cần kiểm chứng publication/source scope riêng. Không tuyên bố mọi đường truy xuất fact của platform đã đạt chỉ từ việc sửa chat RAG.

## Cleanup và giới hạn

14hội thoại và6gap records kiểm thử đã dọn, usage audit giữ. DB test đã dọn; xóa runtime Storage riêng bị kiểm duyệt tự động chặn **blocked by policy**. Giữ runtime, không bypass hoặc đổi cách xóa; evidence và usage audit giữ lại. Evidence private được giữ cho đối soát.

Mock/source fixture/SQL tests không chứng minh upstream thật; ASGI spies chỉ chuyển tiếp service gốc; TCP xác nhận backend đang chạy. Chưa benchmark85%, tải đồng thời/SLA hoặc production. Không model/source/index/publication/restart/deploy/commit/push.
