# Phiên 767 — Sửa bốn P2 và fixture RAG, kiểm chứng không chọn kết quả qua retry

Ngày2026-10-31. Người dùng giao sửa bốn P2 của review766 và fixture RAG, rồi test lại; không retry model để làm xanh. Giữ diff763–766 và dữ liệu phiên đang phục vụ. Áp dụng skill clean code/backend/RAG pipeline/ModelOps/ingestion. Không thay provider, capacity, quota, assistant, prompt hoặc index đang chạy; không restart hay gọi model thật. Thay đổi source V1, test và tài liệu, không sửa `backend/` cũ.

## Thay đổi

1. `rag/answer/context.py`: tính và kiểm ngân sách JSON evidence chính trước nhánh window0/no_hits. Có `bytes_used` cả khi expansion tắt; toàn bộ chunk/structure vẫn giữ, vượt trần trả422 `answer_context_budget_exceeded` trước chat. Đây là cận trên byte, không phải số token. Trần ModelOps vẫn độc lập.
2. `knowledge/index/hybrid.py`: lỗi AppException có usage token nguyên hợp lệ (0..10^15) được settle đúng số đó. Missing/không hợp lệ/cancellation giữ None. Giữ mã lỗi và không resend; không tự giải phóng reservation lịch sử thiếu căn cứ.
3. `modelops/public_api.py::ChatRuntime.inference_configuration_hash`: thêm danh tính inference theo task và exact reasoning trace/policy hash. `answer/service.py` dùng hash này trong reservation và guard trước/sau inference; `AnswerTrace` có `reasoning` và `inference_configuration_hash`. Configuration hash cũ giữ nguyên để không làm mất tương thích compiler/index/history. Không ghi lại trace của kết quả cũ. Prompt text không đổi, PROMPT_VERSION giữv5.
4. `compilation/review/refinement.py` và `review/service.py`: ngân sách thời gian cộng các claim đang chạy, đóng claim bằng finished_at để thời gian dừng không bị tính thêm. Resume giữ phần đã dùng, không cấp lại trần; exhausted bị chặn trước claim/model mới. Review cũ thiếu ledger dùng cận trên từ created_at đến lúc dừng, ghi basis `legacy_wall_clock_upper_bound/v1`; không coi những lần chạy không còn dấu vết là0. Trần request/token và completed/raw artifacts giữ nguyên. Không bật lại timeout300s, không hủy model đang chờ hoàn tất; đây là guard trước dispatch/refinement tiếp theo.
5. `tests/integration/rag_support_672.py`: tạo4paragraph có text phân biệt để không bị merge dedup; xác nhận đủ4đoạn trước gán annotation. Negative metadata kiểm đúng mã lỗi và xác nhận dữ liệu gốc đăng ký201 sau ca âm, không tạo trùng document key trước khi thử lỗi.

Các file test liên quan: unit767 mới, review budget757, API answers648, hybrid655, review budget758, scope/context672 và fixture672. Chưa thay E2E admissions-chat.ts của người dùng. Cập nhật tài liệu rag-answers/compiler-review và hướng dẫn PDF thật.

## Bằng chứng trước/sau sửa

- RED trước sửa: `tests/unit/test_rag_modelops_budgets_767.py -q --tb=short --basetemp ../tmp/767-red`:7FAIL/5PASS,exit1,2.61s. Tái hiện window0 vượt trần/thiếubytes_used, mấtusage0/37, thiếu task fingerprint, reset/mất cộng dồn thời gian và tính nhầm thời gian dừng.
- Sau sửa batch đầu: cùng unit767 +review budget757/refinement755:43PASS,exit0,2.78s. Sau đó thêm biên invalid token lớn, resume nhiều claim và legacy clock; các case này nằm trong full unit cuối.
- Full unit: `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --tb=short --basetemp ../tmp/767-unit-final`, cwdbackendV1: **548PASS/1FAIL**,exit1,30.23s. Lỗi nền giữ đúng ID `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, invalid_identity tạiworkspaces/access.py39. Không sửa assertion/guard này ngoài phạm vi. Tổng unit gate vẫn FAIL.
- Ruff scoped14file source/test:PASS/exit0. Diff whitespace, UTF-8/LF và liên kết tài liệu kiểm riêng. Không chạy FE build vì không thay frontend trong767.

## Kiểm tra tích hợp và sự cố test được giữ nguyên

Chạy một batch6file qua `scripts/run_isolated_tests.py`, external network bị chặn, provider HTTP loopback giả lập, DB/cache namespace riêng. Không gửi corpus cho provider thật. Lệnh tests gồm modelops_resilience695, rag_scope_context672, review_budget758, answers_api648, hybrid655 và compiler_review_segments750; `-q --tb=short`, cwdbackendV1.

Lượt rộng đầu: **76PASS/4FAIL**,exit1,466.49s; harness474.45s. Breakdown:

| Nhóm | PASS | FAIL |
| --- | ---: | ---: |
| ModelOps resilience695 | 31 | 0 |
| Scope/context672 | 4 | 4 |
| Review budget758 | 2 | 0 |
| Answers648 | 25 | 0 |
| Hybrid/rerank655 | 12 | 0 |
| Review segments750 | 2 | 0 |

Bốn FAIL là test negative metadata mới được bổ sung đối chứng: tôi đã đặt POST đăng ký hợp lệ trước ca âm, tạo trùng document key và khiến3case trả409 `compiled_document_key_exists`; case global_data_year bị Pydantic chặn422 `validation_error`, không phải mã domain mà assertion mới ban đầu đòi. Sửa đúng cách chuẩn bị test: thử ca âm trước, kiểm mã cụ thể, sau đó đăng ký dữ liệu gốc để chứng minh fixture hợp lệ và ca âm không tạo dữ liệu. Không nới production metadata guard hoặc chấp nhận tùy ý một mã lỗi.

Sau thay đổi test này, chỉ chạy lại toàn file scope/context672 trên DB riêng: **8PASS**,exit0,50.04s; harness69.0s. Không chạy lại các nhóm đã đạt khi source hành vi của chúng không đổi. Không cộng thành tuyên bố có một lượt80/80PASS; lượt rộng đầu vẫn76/4 và báo cáo được giữ nguyên.

Receipt xác nhận hai DB `qnu_v1_test_210bb95dbca74a0c` và `qnu_v1_test_a5f8547895744e03` đãdrop, legacy sentinel preserved. Log local `tmp/fix767-integration.log`, `tmp/fix767-rag-fixture.log`; log chi tiết/JUnit/receipt ở storage/context636 tương ứng.

## Những gì regression đã kiểm

- Window0 chặn256byte với evidence10K, không crop; trace có bound trong trường hợp vừa trần.
- Rerank429 fake: chỉ1HTTP/ca; usage0và37 settle failed và không giữ reserve, missing usage vẫn unknown/giữ reserve. Invalid/bool/cancellation unit không bị biến thành0.
- Answer reasoning: ModelOps API lưu policy, wire có đúng directive và trace có hash; thay policy sau reservation chặn trước chat/settle0; thay trong lúc inference loại kết quả sau đúng1request. Không retry lấy đáp án khác.
- Review resume đã hết tổng thời gian: cùng idempotency key không thêm request, giữ execution token cũ/statusfailed. Request/token ceiling và parent–child/raw recovery regressions vẫn đạt. Những request lặp trong negative idempotency test chứng minh không dispatch, không phải retry model để chọn kết quả.
- Scope đúng trước TopK ở dense/hybrid/rerank, chỉ cùng publication/metadata khi expansion; dữ liệu sửa sai hoặc thiếu human acknowledgement vẫn bị chặn.

## Giới hạn và chạy tiếp

Live inference,19câu PDF thật và full suite ngoài unit/phạm vi6file: **NOT RUN**. Không suy những test fake provider thành chất lượng OCR/LLM thật. Không thay nhãn draft hoặc semantic_review của benchmark. Không chạy lại F15 hay thay checkpoint để làm xanh.

Muốn chạy E2E bằng mã mới cần người dùng mở lại serve; không cleanup/init hoặc upload/OCR/index lại chỉ để nạp code. Guard byte hiện được áp thật: trợ lý top20 còn ngân sách mặc định16000byte có thể bị `answer_context_budget_exceeded`. Cần chọn ngân sách context có căn cứ cho retrieval trong cấu hình được duyệt hoặc giảm top_k; không tăng context model/quota để che lỗi. Không tự đổi DB của phiên đang phục vụ trong767.
