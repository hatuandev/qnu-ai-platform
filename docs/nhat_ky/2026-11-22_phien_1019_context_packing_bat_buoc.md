# Phiên 1019 — Bảo toàn dẫn chứng bắt buộc khi đóng gói câu trả lời

## Phạm vi và thay đổi

- Bước 1 áp dụng cho Backend V1. Thay đổi trong `packing.py` chỉ cho phép loại chunk mở rộng đã phân loại tùy chọn, kể cả khi trace có cả nhãn tùy chọn lẫn bắt buộc cho cùng một ID. Khi đã tỉa hết mà bằng chứng còn lại vẫn vượt ngân sách, hàm trả lỗi 422 `answer_context_budget_exceeded` qua `AppException`.
- `service.py` chuyển lỗi lên bộ xử lý AppException hiện có. Hỏi đáp đồng bộ trả Problem Details. Luồng thực thi hội thoại lưu mã lỗi rồi ném tiếp theo hợp đồng hiện có.
- Hai nhóm hồi quy kiểm tra giữ đủ chunk gốc và `clause` sau khi tỉa hết tùy chọn, và trả 422 khi các chunk bắt buộc vẫn vượt ngân sách. Có thêm ca vượt ngân sách chỉ với các chunk gốc.

## Kiểm chứng

Các lệnh Python chạy từ `backendV1`. Unit tests dùng cấu hình URL test cô lập, bộ kiểm chứng 422 dùng ASGI trong tiến trình.

| Kiểm tra | Kết quả |
|---|---|
| `uv run --no-sync pytest -q tests/unit/test_rag_context_908.py` trước khi sửa mã | Exit 1, 32 đạt và 3 lỗi. Hai ca clause (`include_optional=False/True`) và một ca nhiều chunk gốc không nhận được AppException. |
| Cùng lệnh sau sửa | Exit 0, 35 đạt. |
| `uv run --no-sync pytest -q` với các tệp unit còn lại nhập `qnu.domains.rag.answer` | Exit 1, 520 đạt và 17 lỗi. Cùng 17 ID tái hiện khi nạp hàm packing từ HEAD trước sửa vào tiến trình test riêng. |
| `uv run --no-sync ruff check` và `uv run --no-sync ruff format --check` trên hai tệp Python thay đổi | Exit 0 cho cả hai lệnh. |
| Kiểm tra ASGI với hàm đóng gói và bộ xử lý AppException thật | Exit 0, HTTP 422, `application/problem+json`, đúng mã và thông báo. |
| `uv run --no-sync python scripts/run_isolated_tests.py tests/integration/test_answers_api_648.py::test_answer_budget_window_zero_is_checked_before_chat -q --tb=line` | Exit 0, 1 đạt. Route thật trả đúng mã 422 trước khi chạy adapter sinh câu trả lời. Harness đã xóa PostgreSQL test và kiểm chứng sentinel nguyên vẹn. |
| `uv run --no-sync python scripts/run_isolated_tests.py tests --ignore=tests/e2e --ignore=tests/live -q --tb=line` | Dừng lượt chạy rộng sau 179 giây, khi log đã có lỗi và chưa chạy hết. Harness đã xóa PostgreSQL test và kiểm chứng sentinel nguyên vẹn. |
| `uv run --no-sync python scripts/run_isolated_tests.py tests/integration/test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data -q --tb=short` | Exit 1, 4 đạt và 4 lỗi. Chạy riêng nhóm chứa các ca lỗi đầu tiên của lượt rộng để lấy kết quả chi tiết. |
| Chạy lại nhóm đầu ra model với hàm đóng gói từ commit `35e43332` nạp trong tiến trình thử | Exit 1, cùng 4 ca đạt và cùng 4 ID lỗi. Ca thứ năm đạt chỉ xác nhận đã nạp hàm trước sửa. Hai PostgreSQL test của nhóm này đã được dọn và sentinel được kiểm chứng. |

### 17 ca lỗi tái hiện trước sửa

- `test_answer_cache_956.py` có 12 ca. Hàm giả `Harness._pack` chưa nhận `conversation_memory`.
  - `test_identical_request_reuses_the_cached_generation`
  - `test_changed_scope_or_question_never_reuses_an_answer[change0–change4]` (5 ID)
  - `test_changed_index_generation_or_evidence_never_reuses_an_answer`
  - `test_changed_chat_runtime_never_reuses_an_answer`
  - `test_abstained_generation_is_not_cached`
  - `test_unsupported_observed_answer_is_not_cached`
  - `test_cache_disabled_or_unavailable_never_blocks_an_answer`
  - `test_corrupt_cached_generation_falls_back_to_the_model`
- `test_rag_recall_941.py` có 2 ca sai danh sách ID hợp nhất từ câu hỏi nhiều vế.
  - `test_each_question_clause_keeps_its_own_retrieved_top_k`
  - `test_shared_evidence_between_clauses_is_deduplicated`
- `test_rag_table_family_954.py` có 3 ca. Hàm giả `attach` chưa nhận `bundles`.
  - `test_count_question_reads_the_parent_family_even_with_only_table_hits`
  - `test_metric_value_question_keeps_the_retrieved_table_fragment_only`
  - `test_family_expansion_takes_what_fits_and_reports_the_rest`

### Bốn ca lỗi trong nhóm kiểm tra đầu ra model

Các ID dưới đây thuộc `test_answers_api_648.py::test_invalid_answer_is_an_error_not_no_data`.

- `[foreign_citation-answer_citation_invalid]`, `[uncited-answer_response_invalid]` và `[schema-answer_response_invalid]` ghi nhận hai lượt gọi adapter trong khi kiểm thử mong một lượt.
- `[inline_citation-answer_response_invalid]` nhận `answer_citation_invalid` thay cho mã mà kiểm thử mong đợi.
