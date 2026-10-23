# Context606 — Kết quả kiểm chứng

## Phạm vi và môi trường

Đã kiểm ENV development, DB loopback, MinIO/Qdrant loopback trước regression. Test dùng hai database được tạo riêng với tên qnu_test_context606_… và nonce ownership comment, schema chỉ ở DB test; LocalStorage riêng. Network guard cho regression chặn endpoint ngoài DB test/local listener; endpoints hạ tầng thay bằng127.0.0.1:1. Không migration hoặc reset DB ứng dụng.

DB1 dùng baseline/full; DB2 dùng compiler API fixtures và focused lifecycle. Một số focused chạy khi compiler đang chạy trên DB2 nhưng dùng collection UUID riêng và cleanup có scope, không reset global hoặc collection compiler. Fake model ở regression; inference thật dùng riêng session ModelOps cấu hình Qwen, không chép key/provider credential vào DB test. Một inactive defaults metadata row được sao chép để test mocked handler cũ có cấu hình typed hợp lệ; không cho phép inference bằng row đó.

## Regression và gate

| Lượt | Kết quả thực chạy | Exit | Ghi chú |
|---|---|---:|---|
| Baseline full |3520PASS/18FAIL/17SKIP,+23subtestPASS,583,27s |1| Snapshot app đầu606, không gồm file test606 mới |
| Entity graph trước sửa |5FAIL |1| Thiếu validator local entity graph |
| Output packing trước sửa |1FAIL |1|12primary trong một packet thay vì cap4 |
| Scalar error codes trước sửa |4FAIL |1| Mã value_error chung thay vì mã actionable |
| Wire alias trước sửa |10FAIL |1| Chưa có restore/alias, adapter chưa giải mã; không phải10lỗi ngữ nghĩa độc lập |
| Focused trước alias cuối |159PASS,63,71s |0| Code trước wire alias, lưu riêng |
| Focused cuối |169PASS,73,57s |0|31test606 +138test liên quan; một warning Qdrant offline từ guard |
| Scoped Ruff cuối |10files PASS |0|6app/4test |

Có các full trung gian3533/18/17 và3537/18/17 được giữ đúng code version, không dùng thay final. Một lượt release-full đã INTERRUPTED sau khi xác minh đúng PID/parent/command pytest riêng để cập nhật fixture số packet; không ghép thành PASS. Hai lượt focused output đầu có5 và1lỗi fixture đếm cố định3packet; đã thay bằng kiểm coverage/reuse theo packet thực, không giảm yêu cầu behavior.

Final full code cuối: **3551PASS/18FAIL/17SKIP,+23subtestPASS**,14warnings,587,09s,exit1. So baseline3520/18/17:31test mới PASS;0failure ID mới,0cause đổi,0ID mất,0lỗi nền được sửa. Full vẫn FAIL.

Baseline/final theo exact test ID và message tại [TEST_ID_COMPARISON](TEST_ID_COMPARISON.md). Full suite còn lỗi nền phải báo FAIL, không dùng focused PASS để ghi đè.

## Qwen thật và nguồn thật

| Kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| Blind direction probe |PASS, mới5173→cũ4500; control đảo bị chặn | Một relation, không phê duyệt bundle604 |
| Ba coverage controls trước hướng dẫn |4/6đúng,2FAIL đều ngày nguồn để trống | Relevance phụ thuộc câu hỏi, không phải ba đoạn luôn unrelated |
| Cùng controls sau hướng dẫn |6/6 required_assertion | Hai request riêng cùng Qwen mỗi đoạn; không chứng nhận toàn bộ assertions |
| Unknown probe đầu |FAIL local entity graph; lượt sau FAIL empty draft/check | Bằng chứng đã lưu, không xóa lịch sử |
| Unknown probe v3 trước wire alias |PASS extraction/null và review complete,2calls | Chỉ một proof và code trước alias cuối |
| Wire alias cuối | Bóc tách đúng source_unspecified/null, persist unknown/null; toàn probe FAIL temporal_roles=false | Reviewer supported nhưng sai/không đạt phần thời gian, gate complete=false |
| Empty draft probe cuối |FAIL KNOWLEDGE_WIKI_INVALID cả initial+1correction | Model tạo item cho assertion không tồn tại; schema maxItems0 chặn đúng |

Ba full compiler dưới đây dùng cùng ba DOCX2024–2026,381noncontainer proofs từ parser602, source fixtures test/local; API create+read qua ASGI thật, actor local/dev, không browser E2E. Không fresh parse/full Quality Gate nguồn; không benchmark chatbot hoặc publication. Read jobHTTP200 không có nghĩa build thành công.

| Attempt / job | API | Lỗi | Thời gian |
|---|---:|---|---:|
| `live-qwen` / `kc_41d173ce3f694091bca7e438a8887c33` |503| MODEL_OUTPUT_BUDGET_EXHAUSTED ở PacketDraft, finish_reason length, output2500 |88.324,31ms |
| `live-qwen-output` / `kc_25d243b00b794133a075e79d50310f8e` |502| PacketDraft state/value không nhất quán sau một correction |67.019,01ms |
| `live-qwen-contract` / `kc_bc34b547578f4c368f704d4b06b1645c` |502| Empty PacketDraft rồi PacketCheck tạo3items trong maxItems0 |66.367,19ms |

Ba attempt xảy ra trước wire alias cuối, không có bundle606 hoàn thành; job được registry giữ uncertain, không resend cùng key/intent. Sau alias chỉ chạy probe hẹp mới, không lặp toàn ba nguồn vì probe đã chứng minh vẫn còn lỗi schema/temporal review. Không đổi output/context/call/time budget hoặc hạ validation để tạo kết quả đẹp.

Ledger ModelOps của các tag606:90records, toàn qwen3.5-9b,0fallback/Luna,255072prompt/24372completiontokens. Status success trong usage chỉ là inference/transport, không phải semantic/compiler PASS. Có61records của ba full attempts; các record còn lại thuộc probes, lịch sử trước/sau được giữ riêng. Không có đối chứng đủ để quy lỗi cho Token Saver,32K hoặc parser.

## Bảo toàn và dọn dữ liệu

Read-only seals cuối khớp đầu606:5collections,24bindings,12source revisions,37index revisions,5assistants,13model config rows. Raw ba DOCX giữ hash602. Qdrant2943points/full payload hash khớp snapshot602,0retrievable; không publish. App hash đối chiếu456file Python: chỉ6file đúng phạm vi thay đổi; phần còn lại giữ.

Cả hai database test606 đã được drop sau khi kiểm exact name, nonce ownership comment và khác DB cấu hình ứng dụng; readback không còn database. LocalStorage/bằng chứng giữ lại, không tuyên bố đã xóa Storage.

Storage606 và bằng chứng được giữ theo chính sách bảo vệ đã chặn xóa ở các lượt trước; không tắt policy hoặc thử đường vòng. Chưa thêm GC mới. Không tự duyệt, không writes source/index/vector/publication thật, không reindex/restart/config/model change/commit/push.

## Kết luận nghiệm thu

Wire alias và regression nội bộ đạt. Chưa APPROVED full compiler: model vẫn vi phạm schema trong trường hợp empty draft và kiểm thời gian chưa ổn định. Tiếp theo nên xử lý hợp đồng output của compiler tại ranh giới ModelOps hoặc tách review không có assertion sang yêu cầu coverage thích hợp; giữ kiểm null/nguồn và missed evidence. Chưa triển khai mở rộng đó trong606, chưa kết luận native schema upstream được hỗ trợ cho mọi contract.

Benchmark64, FE build, browser authenticated E2E và chatbot integration: NOT RUN trong606. Không ghép điểm Luna lịch sử thành điểm Qwen mới.

Receipts/JUnit/log ở `backend/storage/context606/checks/`, `live-checks/` và các thư mục probe/attempt. Report này không chứa raw prompt, credential hoặc toàn corpus.

## Lệnh chính đã chạy

Child commands thực chạy, cwd `D:\DuAnPhanMem\qnu-ai-platform\backend`:

```text
D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606\checks\baseline-code\run.py -q --ignore=tests/test_compilation_context_606.py --basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606-runtime-eeca1e846955\baseline-full --junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606\checks\baseline-full.xml
D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe -m pytest -q tests/test_compilation_context_606.py tests/test_compilation_semantics_604.py tests/test_compilation_engine_603.py tests/test_compilation_contracts_602.py tests/test_compilation_lifecycle_603.py tests/test_compilation_metadata_603.py tests/test_compilation_modelops_603.py tests/test_wiki_snapshot_integration_600.py tests/test_wiki_revision_reuse_600.py tests/test_wiki_revocation_600.py --basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606-runtime-94136633f3ff\focused-wire-alias --junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606\live-checks\focused-wire-alias.xml
D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe -m pytest -q tests --basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606-runtime-eeca1e846955\final-wire-full --junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context606\checks\final-wire-full.xml
```

Các helper từ root đã chạy: `context606_compare_tests.py`, `context606_checks.py seals --label final`, `context606_postcheck.py`, và cleanup của cả `context606_checks.py`/`context606_live_checks.py`.

Các helper probe/three compiler attempts có tên context606_direction_probe.py, context606_coverage_probe.py, context606_topic_controls.py, context606_topic_controls_after.py, context606_unknown_probe*.py, context606_live_qwen*.py, context606_wire_probe.py, context606_empty_probe.py; intent/metrics/usage/response giữ trong từng thư mục tương ứng. Chỉ probe hẹp sau alias cuối, không whole-build thứ4.

Command/args Pytest và Ruff đầy đủ, cwd, exit code nằm trong run.json tương ứng; child Pytest chạy cwd backend. Baseline đã truyền --ignore=tests/test_compilation_context_606.py như receipt, không tự sửa collection cuối. Không cần DB thật để đọc báo cáo/JUnit. Hai helper lỗi khởi động trước inference và một lệnh chọn test không được argparse hỗ trợ đã được sửa trước khi chạy; không tính chúng là test/model PASS.
