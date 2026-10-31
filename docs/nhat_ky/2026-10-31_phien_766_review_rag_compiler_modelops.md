# Phiên 766 — Review RAG, Compiler và ModelOps hiện tại

Ngày 2026-10-31. Người dùng yêu cầu review ba phần hiện tại. Phạm vi là `backendV1/` và E2E V1 đang dùng, không suy kết luận sang `backend/` cũ. Đọc mã tại HEAD `01f682ed`, các diff chưa commit, PROJECT_CONTEXT và skill clean code/RAG pipeline/ingestion/ModelOps. Giữ nguyên thay đổi của người dùng và các phiên 763–765. Không sửa logic, cấu hình DB, prompt version, nguồn, index hoặc checkpoint; không restart, reindex, publish hay gọi model thật.

## Trạng thái kiến trúc đã đối chiếu

| Phần | Luồng hiện có | Đánh giá trong phạm vi review |
| --- | --- | --- |
| RAG | Kiểm workspace/collection, publication/revision/hash → dense + PostgreSQL simple FTS → RRF → rerank theo policy → context → answer → citation/current-source validation; tùy chọn verification | Có ranh giới nguồn và quyền; giữ relevance/prompt v5, projection bảng giữ raw và cấu trúc. Chưa đạt gate hồi quy scope/context hiện tại. Simple FTS không đồng nghĩa BM25 hoặc learned sparse BGE. |
| Compiler | Đơn vị nội dung/bảng → planner xét input/output → scheduler có giới hạn → raw/JSON/Markdown từng node → refinement cha–con khi xác định truncated → ghép thứ tự → review → publication gate | Đúng hướng xử lý tài liệu lớn, giữ kết quả đã xong và không resend uncertain. Review có ledger request/token trước dispatch, literal assessment và artifact/coverage. Thời gian review hiện là cửa sổ mỗi claim. |
| ModelOps | Catalog/grant/default; key mã hóa; discovery/import capacity; per-model budget; routing trước dispatch; key lease/cooldown/fence; quota/usage | 31 kiểm tra tích hợp resilience đạt. Giới hạn token, reasoning và quota vẫn là ba cơ chế khác nhau; có gap trace reasoning và settlement rerank. |

## Phát hiện cần xử lý

### P2 — Ngân sách context bị bỏ qua ở cấu hình mặc định

`backendV1/qnu/domains/rag/answer/context.py:40–42` trả về ngay khi `context_window=0`, trước khi tính/kiểm `context_max_bytes` ở dòng69–75. UI mô tả trường này là giới hạn JSON evidence gửi model, còn giá trị window0 chỉ tắt lấy đoạn lân cận. Probe tổng hợp đặt giới hạn256byte nhưng trả nguyên evidence10.057byte và status disabled.

Tác động: cấu hình ngân sách không giới hạn được evidence chính; model context/quota vẫn có kiểm riêng nên không phải bypass trần model. Câu hỏi có top_k lớn có thể tiếp tục tốn input hoặc bị từ chối ở tầng ModelOps. Đề xuất kiểm ngân sách evidence chính trước nhánh tắt expansion, ghi bytes_used cả khi window0; không âm thầm cắt nội dung.

### P2 — Rerank làm mất usage đã được provider báo trong phản hồi lỗi

`backendV1/qnu/domains/knowledge/index/hybrid.py:113–115` settle `None` cho mọi exception. Adapter `providers/failures.py::tag_failure` có thể đã đính kèm `usage_tokens` xác định. Probe chạy hàm rerank thật, chỉ thay I/O bằng fake: lỗi có usage_tokens0 nhưng settlement nhận None. `usage/service.py` giữ reservation khi None là đúng cho trường hợp chưa biết; sai nằm ở việc bỏ số đo của caller.

Tác động: lỗi có usage xác định vẫn giữ token dự phòng, làm cạn quota sớm. Đề xuất giữ số đo hợp lệ (kể cả0) từ lỗi, unknown mới giữ None; regression cả zero/positive/missing và cancellation. Rà soát tương tự các caller embedding trước khi mở rộng sửa.

### P2 — Cấu hình reasoning chưa nằm trong danh tính/trace của câu trả lời RAG

`backendV1/qnu/domains/modelops/public_api.py:73–85` không đưa reasoning policy/directive vào configuration_hash. `answer/service.py` dùng hash này để kiểm thay đổi trước/sau model; AnswerTrace chưa có reasoning directive/hash riêng. Probe cùng endpoint/model/limits, thay server_default bằng directive verified cho answer: wire parameter đổi nhưng configuration_hash giữ nguyên và trace không có trường reasoning.

Tác động: không phân biệt đầy đủ các lượt answer khác hợp đồng suy luận; thay policy trong lúc inference không bị phát hiện bởi guard hash này. Compiler/review có kiểm reasoning riêng, vì vậy không suy rộng rằng cả hai cũng thiếu fence tương tự. Đề xuất lưu exact directive/policy hash cho answer và kiểm lại tương ứng; cần bảo toàn replay/hash của run cũ khi thiết kế migration/version.

### P2 còn lại từ758 — Trần thời gian review không cộng dồn qua resume

`review/service.py:285–289` ghi execution_started_at mới, `review/refinement.py:145–154` tính elapsed từ đó. Probe budget60s: đã qua61s bị chặn, đổi timestamp đúng thao tác resume thì lại được phép. Test757 cũng đang chủ động chấp nhận cửa sổ mới mỗi execution; đây là hành vi đã được mã/test xác lập, không phải lỗi mới do phiên766.

Tác động: nếu max_seconds được dùng làm tổng ngân sách một review thì resume không giữ trần này. Trần request/token vẫn cộng dồn và được kiểm riêng, không có bằng chứng chúng bị reset. Đề xuất phân biệt cửa sổ một claim với ngân sách thực thi cộng dồn. Việc này khác yêu cầu bỏ timeout300s của từng phản hồi model; không tự bật lại timeout hay cắt request đang chạy trong phiên review này.

## Gate test và giới hạn đánh giá

1. Full unit: cwd `backendV1`, `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --tb=short --basetemp ../tmp/review766-unit-temp`: **533 PASS/1 FAIL**, exit1,31.96s. Exact failure nền: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, invalid_identity tạiworkspaces/access.py39. Tổng suite vẫn FAIL. Lượt đầu không đặt basetemp:509PASS/1FAIL/24ERROR do WinError5 thư mục Temp; đổi riêng thư mục test đã giải quyết24ERROR, không đổi quyền hệ thống hoặc test assertion.
2. Integration qua harness DB riêng: `scripts/run_isolated_tests.py tests/integration/test_modelops_resilience_695.py tests/integration/test_rag_scope_context_672.py tests/integration/test_review_budget_758.py -q --tb=short`. **37 PASS/1 FAIL/3 ERROR**, exit1,99.39s; harness108.97s. ModelOps31/31PASS, review2/2PASS, RAG4negativePASS và4case còn lạiFAIL/ERROR.
3. Cả4case RAG lỗi `retrieval_metadata_invalid`422: annotation trỏ đoạn không tồn tại. `tests/integration/rag_support_672.py::ParagraphChat` tạo4paragraph giống hệt, trong khi `segments._merge_sections` dedup theo heading/text/citations nên draft không có các vị trí mà annotation1/2 giả định. Positive scope/context/tamper chưa chạy được; negative cases có thể cùng bị chặn bởi fixture nên không lấy4PASS làm bằng chứng đủ. Cần sửa fixture tạo các đoạn phân biệt, xác nhận đăng ký hợp lệ trước negative mutation; không nới guard metadata của production.
4. Database `qnu_v1_test_2b1f010ab1394313` đãdrop; receipt xác nhận legacy sentinel preserved. External network bị harness chặn; fake HTTP loopback, Redis/cache namespace riêng. Log local `tmp/review766-integration.log`, full pytest log/result/receipt trong thư mục runtime của DB test.
5. Bốn probe tổng hợp trong `tmp/review766_probes.py` chạy exit0, xác nhận bốn hành vi nêu trên. Không dùng DB, model hoặc corpus thật. Probe rerank đã sửa kích thước dữ liệu tổng hợp sau lượt đầu bị capacity guard chặn; không sửa production để đạt probe.
6. Live inference/E2E mới, load test, benchmark chất lượng nhiều tài liệu: **NOT RUN**. Không chạy lại F15 hoặc19câu để chọn kết quả. Kết quả5case v5 của765 là lịch sử, không phải19/19 mới trong766. Verification off và benchmark label draft vẫn là giới hạn đánh giá; citation hợp lệ không tự chứng minh mọi diễn giải đúng.

## Ưu tiên bàn giao

Sửa context budget và settlement quota trước; bổ sung reasoning identity/trace; chốt semantics tổng thời gian review và sửa fixture scope/context. E2E ensureAssistant còn nuốt lỗi GET/PUT đã nêu từ762, cần dừng khi không xác nhận cấu hình thay vì tiếp tục; chưa sửa ở766. Sau sửa chạy hồi quy/API và một lượt benchmark mới cùng snapshot, cấu hình, prompt version; không retry theo gold hoặc gộp replay thành first-attempt.

Hiện chưa có cơ sở để đề xuất viết lại ba phân hệ. Kiến trúc chính đáp ứng hướng đã thống nhất; phần cần củng cố là tính nhất quán giữa giới hạn cấu hình, đo usage, trace và test gate.
