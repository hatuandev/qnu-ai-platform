# Phiên759 — Qwen hết output khi chưa có nội dung Compiler

## Yêu cầu và chẩn đoán

- User gửi log phiên `1da945adac7c`, chọn QNU `qwen3.8-27b-q4`; provider/setup/model probes/navigation/admissions-upload/admissions-extraction đạt, PDF8trang. `admissions-compilation` thất bại sau3.3phút.
- Đọc Git/diff, PROJECT_CONTEXT và skill clean-code/ModelOps/ingestion; giữ nguyên thay đổi757/758 chưa commit.
- Đọc DB/artifact theo cấu hình riêng của phiên, không in credential hoặc raw corpus/prompt.
- Run `cmp_9efc601ec91f`: planner v5, concurrency2, root4, output8192, refinement đã bật depth4/nodes124/time1500. Reasoning directive lưu `null`.
- Node1: prompt32036/completion8192/total40228, finish_reason length, content0ký tự, reasoning26189ký tự; node2: prompt38930/completion8192/total47122, length, content0, reasoning25827ký tự. Tổng87350token gồm input, không phải87350token output.
- Lỗi ban đầu là output budget đã dùng hết khi Qwen còn suy luận. Lỗi phục hồi trong code là `refinement.diagnose()` đòi cả length và content khác rỗng, nên trảFalse cho cả hai raw; `create_children()` không tạo node con và job dừng. Không phải lỗi key, kết nối, thiếu context đầu vào hoặc OCR.

## Thay đổi

- `backendV1/qnu/domains/knowledge/compilation/refinement.py`: chẩn đoán theo tín hiệu xác định `finish_reason=length`, kể cả chưa có content. Không suy từ HTTP422, lỗi mạng hoặc output malformed; không dùng reasoning làm dữ liệu nguồn hay bản nháp.
- Giữ nguyên thuật toán chia ownership, depth/nodes/time, raw/usage cha và JSON/MD links. Không sửa ModelOps, output mặc định8192, timeout, reasoning policy hoặc checkpoint.
- `tests/unit/test_compiler_truncation_759.py`: reasoning_content/reasoning chỉ có suy luận vẫn refinable; malformed/HTTPtext không được coi truncated.
- `tests/unit/test_compiler_refinement_751.py`: cập nhật quy tắc length-only, vẫn từ chối stop và HTTPtext.
- `tests/integration/test_compiler_refinement_751.py`: chạy cùng kiểm chứng HTTP/SQL/artifact/usage cho parent content dở dang và parent chỉ có reasoning.

## Kiểm chứng

| Lệnh/cwd | Kết quả |
|---|---|
| BackendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit/test_compiler_truncation_759.py -q --basetemp ../tmp/pytest-red-759 --tb=short` trước sửa | Exit1,2FAIL/4PASS; đúng2reasoning-only case không vào refinement |
| BackendV1: pytest unit truncation759/refinement751/projection746/parallel746/review_refinement755/review_budget757, `-q --basetemp ../tmp/pytest-focused-759 --tb=short` | Exit0,63PASS,2.81s |
| BackendV1: Ruff trên4file Python của phiên759 | Exit0,PASS |
| Harness `scripts/run_isolated_tests.py`: integration751 `test_truncated_parent_builds_child_pairs_and_aggregates_usage` (2case), `test_permanently_truncated_single_unit_stops_with_bounded_calls`, `test_uncertain_child_is_never_resent_or_reported_as_known_usage` | Exit0,4PASS,24.36s; PostgreSQL riêng đã drop/sentinel giữ nguyên, egress nonloopback bị chặn |
| BackendV1: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --basetemp ../tmp/pytest-all-759 --tb=short` | Exit1,522PASS/1FAIL,32.50s |

Lỗi nền giữ nguyên exact ID `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, invalid_identity tại `workspaces/access.py:39`. Full suite vẫn FAIL, không skip/sửa ngoài scope.

Integration dùng model HTTP loopback giả, không chứng minh Qwen thật đã hoàn thành sau sửa. Live E2E/Qwen sau sửa **NOT RUN**; không ngắt/restart cửa sổ serve của user hoặc tự gửi lại request model. Không đổi kết quả job lỗi cũ thành PASS.

## Chạy tiếp

- User Ctrl+C đúng cửa sổ serve, chạy lại `.\test-v1-e2e.ps1 serve`, chờ E2E live.
- Cửa sổ khác: `.\test-v1-e2e.ps1 run admissions-compilation --headed --recover`.
- `--recover` là đường phục hồi hiện có: tạo lượt mới từ OCR đã xong, giữ lượt lỗi trong lịch sử; nếu đủ điều kiện, runner chọn output theo trần ModelOps cho recovery (có thể cao hơn8192), không đổi cấu hình model/server. Phiên759 chưa sửa chính sách recovery đó.
- Không cleanup/init/upload/OCR lại. Nếu vẫn lỗi, giữ checkpoint/raw để xác định node, depth/budget và output; không lặp mù đến khi xanh.
- P2 cộng dồn thời gian review758 không thuộc lỗi Compiler này và chưa sửa.
