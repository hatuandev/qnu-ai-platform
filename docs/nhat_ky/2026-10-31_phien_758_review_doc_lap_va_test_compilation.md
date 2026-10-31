# Phiên 758 — Review độc lập và kiểm chứng bản sửa757

## Phạm vi

- Người dùng yêu cầu review và test sau khi triển khai prompt xử lý ba finding756.
- Đọc AGENTS, PROJECT_CONTEXT, diff thực tế và skill clean-code/backend/ModelOps. HEAD `c7dcda7a`; các thay đổi757 chưa commit, giữ nguyên.
- Phiên này không sửa logic sản phẩm. Thêm hai regression integration tại `backendV1/tests/integration/test_review_budget_758.py` và nhật ký/memory.
- Giữ phiên live `f2b0e64738c1`, không cleanup/init/upload lại, không đổi key/model/capacity.

## Kết luận review

Ba lỗi cũ đã có xử lý: ledger ngân sách tại ranh giới gửi request, messages gửi đúng hash replay với prompt v3/legacy v2, decode và validation cùng một ranh giới lỗi có refinement hữu hạn. Kiểm chứng trọng tâm và hai negative case qua HTTP/PostgreSQL đều đạt.

### P2 còn lại — Trần thời gian reset mỗi lần resume

- `review/refinement.py:145` chỉ tính `utcnow() - execution_started_at`.
- `review/service.py:289` đặt `execution_started_at` mới khi resume, không cộng thời gian xử lý của claim trước.
- Vì vậy `max_seconds` là trần từng execution claim, chưa là trần tổng thời gian thực thi review qua resume như prompt yêu cầu.
- Probe in-memory dùng cùng đường `_execute_segments`, trần60s và clock giả tăng31s/request: claim1 gửi2request rồi dừng sau62s; claim2 reset mốc như service hiện tại lại gửi thêm2request, tổng124s xử lý. Không tính thời gian laptop tắt vào probe này.
- `test_time_ceiling_is_per_execution_and_a_resume_starts_a_fresh_window` đang cố ý xác nhận hành vi reset; không chứng minh yêu cầu tổng thời gian. Cần lưu thời gian xử lý cộng dồn qua các claim (định nghĩa rõ thời gian dừng/offline), giữ bất biến khi resume. Phiên758 chỉ ghi finding, chưa sửa.

## Kiểm chứng đã thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Cwd backendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_compiler_review_budget_757.py tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_review_keyed_655.py tests/unit/test_review_literal_751.py tests/unit/test_migration_baseline_661.py -q --basetemp ../tmp/pytest-review-758 --tb=short` | Exit0, **58 PASS**, 3.34s |
| Cwd backendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --basetemp ../tmp/pytest-all-758 --tb=short` | Exit1, **516 PASS / 1 FAIL**, 26.39s |
| Cwd backendV1: `scripts/run_isolated_tests.py tests/integration/test_compiler_review_segments_750.py tests/integration/test_review_literal_751.py tests/integration/test_review_schema_655.py -q --tb=short` | Exit0, **6 PASS**, 67.74s; DB riêng đã drop, sentinel giữ nguyên |
| Cwd backendV1: `scripts/run_isolated_tests.py tests/integration/test_review_budget_758.py -q --tb=short` | Exit0, **2 PASS**, 13.36s; DB riêng đã drop, sentinel giữ nguyên |
| Cwd frontendV1: Vitest admission recovery/provider selection/progress budget/capacity735 | Exit0, **32 PASS**, 4 files |
| Cwd frontendV1: `npm run test:e2e:typecheck` | Exit0, PASS |
| Cwd frontendV1: `npx biome check e2e/stages/admissions-recovery.ts e2e/stages/workflow.spec.ts tests/admissions-recovery.test.ts` | Exit0, PASS |
| Cwd frontendV1: `npm run build` | Exit0, PASS; warning bundle/config Vite còn tồn tại |
| Cwd backendV1: Ruff review module + unit files757/755/744 và integration758 | Exit0, PASS |
| Root: `powershell -NoProfile -File ./test-v1-e2e.ps1 run compilation --headed` | Exit0, **1 PASS**, 10.4s tổng; test3.8s, tái sử dụng review hoàn tất |
| HTTP live POST review mới trên cùng bản nháp thử | HTTP200, completed, 3/3 phần, 15.59s; verdict needs_attention, 5findings |

Full unit vẫn FAIL đúng ID nền: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, `invalid_identity` tại `workspaces/access.py:39`. Không sửa/skip assertion.

Hai integration758 dùng API/service thật, Postgres thật và model HTTP loopback giả. Review chạy mặc định concurrency2. Trần request1 chỉ có1request review đến adapter; trần token1 không có request nào đến adapter. Không thay transaction/khóa hoặc mock DB để đạt kết quả.

Integration dùng harness tạo DB `qnu_v1_test_*`, key test riêng và chặn egress nonloopback; chỉ dùng địa chỉ PostgreSQL của phiên live làm admin tạo DB tạm, không sao chép dữ liệu hoặc credential LLM.

## Phân biệt kết quả E2E và chất lượng bản nháp

- E2E hiện tại kiểm review completed, endpoint report thành công và body có dữ liệu; không yêu cầu finding_count0. Vì vậy compilation PASS không có nghĩa bản nháp không còn nhận xét hoặc đã được phép publish.
- Report E2E mới: `tmp/v1-e2e/f2b0e64738c1/runs/compilation-1793427979855562300/html`.
- Để kiểm tra thật thay vì chỉ replay, gọi POST review mới `rvw_fa001f399977` trên run `cmp_af9ff45d717e`, idempotency key riêng phiên758, giữ cấu hình4096/structured output/ModelOps hiện có. Không sửa checkpoint để chuyển sang review mới.
- Kết quả: usage19972token tổng; source14/draft8 đều được đánh giá; leaf3completed, failed0/uncertain0. Model không truncated hoặc sai keyed contract trong lượt mới.
- Report mới có5findings, verdict `needs_attention`; report checkpoint trước đó cũng có5findings. Nhóm nhận xét gồm nguồn/tiêu đề chưa được thể hiện, heading bị đánh giá unsupported và các phát biểu thiếu dữ liệu cần đối chiếu. Đây không phải năm lỗi chính tả. Chưa kết luận mọi finding đều đúng; cần rà căn cứ/context và bản nháp. Không tự loại finding hoặc duyệt xuất bản.
- Metadata an toàn của lượt mới ở `tmp/v1-e2e/f2b0e64738c1/independent-review-758.json`; không chép raw/corpus/prompt/secret vào docs.

## Bàn giao

- Dừng serve do agent mở bằng Ctrl+C, xác minh API56266 và frontend56267 đã đóng. Giữ containers, dữ liệu và checkpoint.
- Phần request/token/hash/contract recovery đã vượt các kiểm chứng nêu trên; còn findingP2 thời gian cộng dồn và5nhận xét chất lượng cần xem xét.
- Publication/admissions toàn luồng không chạy trong phiên758. Chưa tuyên bố toàn nền tảng PASS.
- Khi tiếp tục: mở `./test-v1-e2e.ps1 serve`; không cleanup/init. Rà finding trước khi quyết định xuất bản.
