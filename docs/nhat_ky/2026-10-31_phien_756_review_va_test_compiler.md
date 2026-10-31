# Phiên 756 — Review và test bản compiler/review sau vibe coding

## Phạm vi và hiện trạng

- Người dùng yêu cầu đọc lại code và thử test sau khi khởi động laptop. Chỉ review/kiểm chứng; chưa sửa logic ứng dụng, assertion hay cấu hình model.
- Đối chiếu Git tại `c7dcda7a`, PROJECT_CONTEXT và mã hiện tại; working tree sạch trước khi ghi nhật ký này.
- Phiên live `f2b0e64738c1` còn checkpoint. Docker engine phản hồi dù Windows service báo Stopped; trạng thái service không đủ chứng minh Docker không chạy.
- Khởi động lại đúng hạ tầng phiên bằng runner hiện có, mở `serve` do agent sở hữu; migration `0009 -> 0010_review_refinement` chạy thành công. Không cleanup/init, không thay key/model/capacity.

## Phát hiện có bằng chứng

1. **P1 — Giới hạn review không kiểm trước mỗi request.** `review/refinement.py:206` định nghĩa trần request/token/thời gian nhưng `check_limits()` chỉ được gọi tại `execution.py:369` khi chia node truncated. Vòng chạy các lá và `_run_segment` không áp trần tổng trước khi gọi model. Probe dùng `_setup_segmented_harness` của test755, 18 units, `max_requests=1`, `max_tokens=1`, model giả luôn trả hợp lệ 320 token: review vẫn completed sau **7 request, 2240 token**. Cần kiểm/đặt chỗ ngân sách tại ranh giới thực thi, bao gồm concurrency; không chỉ khi tạo con.
2. **P2 — Prompt replay được kiểm hash khác prompt gửi đi.** `parts.py:1149` dựng và kiểm prompt theo `scope.request_total`, nhưng dòng1185 trả messages theo `total` mới. Probe đổi total từ7 sang8: hash payload đúng, hash system prompt gửi đi khác `plan.prompt_sha256`, không bị từ chối. Khi refinement làm tăng số lá, trace không còn chứng minh đúng prompt đã gửi. Cần dùng cùng bộ messages cho hash và request.
3. **P2 — Phản hồi keyed sai bị kẹt ở received/uncertain.** `execution.py:716` gọi `decode_keyed` ngoài khối xử lý validation thất bại; dòng335 đánh dấu review uncertain khi đã gửi request. E2E thật trả dư đúng1 source assessment thuộc readonly context: nguồn owned12, trả13, thiếu0; draft đúng5. `finish_reason=stop`, completion3759/4096, nên lần này là lỗi hợp đồng, không phải cắt output. Node1 còn received, node2 completed, node3 pending; review uncertain/`compilation_review_invalid`. Khi resume, nhánh có raw đọc lại cùng phản hồi và decode lại, nên không tự tiến tiếp. Cần phân loại lỗi đã biết và có recovery hữu hạn giữ lịch sử; không bỏ validation hoặc tự xóa assessment dư để làm xanh test.

## Kiểm chứng đã chạy

Các đường dẫn dưới đây tương đối root repo; mọi lệnh không ghi cwd riêng chạy tại root.

| Kiểm tra | Kết quả |
|---|---|
| Cwd backendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_review_keyed_655.py tests/unit/test_review_literal_751.py tests/unit/test_migration_baseline_661.py -q --basetemp ../tmp/pytest-review-756 --tb=short` | Exit0, **41 PASS**, 3.57s |
| Cwd backendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --basetemp ../tmp/pytest-all-756 --tb=short` | Exit1, **499 PASS / 1 FAIL**, 37.95s; toàn suite vẫn FAIL |
| Integration qua `scripts/run_isolated_tests.py`: `test_compiler_review_segments_750.py`, `test_review_literal_751.py`, `test_review_schema_655.py` | Exit0, **6 PASS**, 64.54s; DB riêng đã drop, sentinel giữ nguyên, egress nonloopback bị chặn |
| Cwd frontendV1: `npx vitest run tests/admissions-recovery.test.ts tests/e2e-provider-selection.test.ts tests/progress-budget.test.ts tests/e2e-capacity-735.test.ts` | Exit0, **32 PASS**, 4 file |
| Cwd frontendV1: `npm run test:e2e:typecheck` | Exit0, PASS |
| Cwd frontendV1: `npm run build` | Exit0, PASS; có warning Vite về import/config và kích thước bundle |
| Cwd backendV1: `.venv/Scripts/python.exe -X utf8 -m ruff check qnu/domains/knowledge/compilation/review alembic/versions/0010_review_refinement.py tests/unit/test_compiler_review_refinement_755.py` | Exit0, PASS |
| Cwd frontendV1: `npx biome check e2e/stages/admissions-recovery.ts e2e/stages/workflow.spec.ts tests/admissions-recovery.test.ts` | Exit1, FAIL: assignment trong expression `workflow.spec.ts:418` và format dòng422; không autofix |
| `powershell -NoProfile -File ./test-v1-e2e.ps1 run compilation --headed` | Exit1, **FAIL**, 16.0s; POST reviews HTTP409 `compilation_review_invalid` |
| Hai probe in-memory request limit/replay hash, forensic read-only raw artifact | Exit0; kết quả cụ thể tại ba phát hiện trên; không ghi raw/corpus/secret vào nhật ký |

Lỗi full unit khớp exact ID nền đã ghi phiên755: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, `invalid_identity` tại `workspaces/access.py:39`. Chưa sửa trong scope này.

Report E2E: `tmp/v1-e2e/f2b0e64738c1/runs/compilation-1793425583695087200/html`. Review mới `rvw_1dacc6c225df`, run `cmp_af9ff45d717e`; giữ review lỗi cũ. Phiên này chỉ chạy lại compilation; các PASS trước có checkpoint nhưng không được ghi thành kết quả chạy mới.

## Bàn giao

- Đã dừng serve agent bằng Ctrl+C; xác minh API56266 và frontend56267 không còn lắng nghe. Giữ containers/data/checkpoint; DB test cô lập đã dọn riêng.
- **Chưa nghiệm thu toàn luồng.** Publication/chat sau compilation và admissions E2E: NOT RUN trong phiên này.
- Chưa cần test lại từ cleanup/init. Sửa ba phát hiện, bổ sung regression tại ranh giới gửi/replay/validation rồi mở lại `serve`, chạy `run compilation --headed` trên phiên hiện tại. Tránh lặp request live trước khi có recovery cho raw invalid.
- Các file thay đổi trong phiên756 chỉ là nhật ký, snapshot và ba index/memory; không sửa sản phẩm.
