# Phiên 908 — Thu gọn bảng, nối ngữ cảnh và kiểm chứng câu trả lời

Tiếp tục ba điểm tối ưu RAG sau Context907 khi người dùng mở lại Docker Desktop. Giữ nguyên các thay đổi KH16 đang có trong checkout; không reset dữ liệu ứng dụng, reindex, upload, xuất bản hoặc push. Khởi động lại các dependency của phiên E2E cũ; không khởi động hay ngắt app dev.

## Phương pháp và phạm vi sửa

1. `answer/table_selection.py` bổ sung lựa chọn hàng theo tên đối tượng xuất hiện nguyên dạng trong nguồn và câu hỏi đã làm rõ. Chỉ thu gọn câu hỏi giá trị đơn hoặc so sánh rõ ít nhất hai đối tượng, không thu hẹp câu liệt kê hoặc so sánh một đối tượng với toàn tập. Giữ tất cả cột/năm/điều kiện của hàng, nối bảng chỉ khi cùng publication và liên kết header đã niêm phong. Không khớp chắc chắn thì giữ toàn bảng. `cells.py`, `drafting.py`, `service.py` dùng catalog đã chọn để sinh và kiểm tra cell proof; ô bị loại khỏi prompt không thể được model tự chọn. Nguồn, bảng đầy đủ và geometry vẫn được giữ trên server.
2. `context.py` dùng câu hỏi đã làm rõ, lấy các đơn vị cấu trúc theo canonical source order, bỏ trần 20 đoạn phụ thuộc. `structure_context.py` v3 nối mảnh câu bị tách qua trang, giữ đoạn dẫn và các điểm điều kiện; heading, bảng, hình và điểm danh sách là ranh giới. Phần không có chunk vẫn được ghi thiếu, không tạo dẫn chứng giả. Bộ đóng gói bảo vệ phần cấu trúc bắt buộc; ngân sách caller và giới hạn vật lý vẫn áp dụng. `coverage.py` v2 phân biệt câu nối tiếp với phạm vi liệt kê đầy đủ; câu chỉ lấy kèm mà không dùng không tự biến thành yêu cầu còn thiếu.
3. `verification.py` v3 áp dụng chính sách reasoning của task answer qua ModelOps, chỉ khi đã khai báo và xác nhận. Hash kiểm cả cấu hình suy luận trước/sau gọi; thay cấu hình thì trả lỗi, không tự gửi lại. Prompt answer tăng v19 → v20.

Đo model thật phát hiện thêm lỗi của bước kiểm chứng: prompt cũ ghép/chuẩn hóa hàng bảng thành chuỗi dễ đọc, trong khi parser đòi quote khớp nguyên văn nguồn. Verifier nay nhận từng ô/đoạn/note nguyên dạng, không gửi geometry thừa. Giữ nguyên kiểm tra quote, số liệu, quyền và tình trạng xuất bản.

Fixture API trước đó hỏi “tuyển sinh” nhưng fake luôn chọn số thuộc hàng “trúng tuyển”. Sửa câu hỏi chung của fixture để khớp hàng mà assertion vốn kiểm; thêm ca riêng xác nhận hàng tuyển sinh không nhận số của hàng trúng tuyển. Cập nhật kỳ vọng phiên bản prompt/selection/coverage và fake verifier theo hợp đồng mới, không bỏ guard để làm xanh.

## Kiểm chứng

- Toàn bộ unit: **881 passed**, 4 cảnh báo, 22,39 giây, exit0. Cwd `backendV1`; lệnh `.venv/Scripts/python.exe -m pytest tests/unit -q --basetemp=../tmp/pytest-rag908-last-unit`; log `tmp/rag908-last-unit.log`.
- API regression cuối batch: **60 ca khác nhau đạt** qua hai nhóm. Lượt `rag908-regression3.log` hoàn tất 22 ca thuộc `test_rag_context_908.py`, `test_answer_coverage_861.py`, `test_rag_verification_policy_672.py`, `test_answer_review_p6.py`, rồi gặp assertion phiên bản prompt cũ trong nhóm answer API. Lượt tiếp phát hiện assertion selection cũ; cập nhật hai kỳ vọng sang v20/v2. Lệnh cuối từ root với `QNU_TEST_WINDOWS_SELECTOR_LOOP=true`: `.\backendV1\.venv\Scripts\python.exe backendV1/scripts/test_database.py tests/integration/test_answers_api_648.py tests/integration/test_rag_scope_context_672.py -vv --tb=short` đạt **38 passed**, 2 cảnh báo,305,16 giây,exit0. Receipt `qnu_v1_test_141bb17a07e64cac`: `db_dropped=true`, `legacy_sentinel_preserved=true`,315,61 giây toàn harness. Lượt trước `qnu_v1_test_6238d81bd5584996` vẫn là FAIL23passed/1failed, không đổi lịch sử thành PASS; 1 answer API đã đạt ở đó được kiểm lại trong lượt38.
- Ruff scoped17file và whitespace scoped đạt, exit0. Memory908 UTF-8 không BOM/LF, liên kết index được kiểm tồn tại. Diff toàn repo còn CRLF/trailing whitespace ở `knowledge/preparation/router.py` ngoài phạm vi, không tự sửa.
- Full Pytest đã thử trên DB cô lập: lượt đầu chưa hoàn tất; lượt fail-fast sau đó **1 failed, 6 passed** do fixture hỏi khác metric (đã sửa và chạy regression). **Full suite hiện NOT COMPLETED**, không tuyên bố toàn backend PASS. Các receipt của lượt đã kết thúc xác nhận DB test được dọn, sentinel legacy giữ nguyên.
- FE/build và benchmark KH16 đầy đủ: **NOT RUN** trong phiên này; không có thay đổi FE mới từ tác vụ này.

## Đo Qwen thật

Artifact cục bộ, không đưa corpus/phản hồi vào Git: `tmp/v1-user-workflow-eval/ctx-opt-20261109/` (`context-comparison.json`, `live-full-pipeline.json`, `grading.json`, `live-verification.json`, `live-verification-v3.json`). Giữ index hiện hành `idx_beee9142147d`; gọi full `answer()` gồm retrieval BGE, Qdrant, rerank, context và kiểm nguồn hiện hành bằng actor có quyền. Không lập chỉ mục lại.

Áp dụng policy off đúng profile đã khai báo cho Qwen vào **ModelOps của phiên E2E** qua service có quyền, không đổi DB app dev/model mặc định. Mỗi câu/mỗi cấu hình có một lần gửi; không retry làm xanh.

- 8 câu F01/F02/F03/F06/F09/F11/F12/F13: chấm rule nhãn draft **7 PASS / 1 FAIL**. Không thay thế nghiệm thu người thật.
- Median prompt: **3.596 token**; cohort v19 lưu trước đó **12.093,5 token** (giảm khoảng 70,3%). Median full RAG **6,3985 giây**, riêng generation **2,172 giây**. Cohort cũ chỉ đo frozen-evidence generation và reasoning mặc định; không suy tốc độ cải thiện nhân quả từ hai ranh giới/config khác nhau. So offline cùng hit snapshot cho thấy payload các câu chọn hàng giảm rõ; câu liệt kê F13 giữ toàn bảng.
- **F13 vẫn FAIL**: Qwen từ chối tổng hợp điều kiện dù trace có đủ 6/6 đơn vị liên quan, gồm phần nối trang. 13.194 prompt token; full12,25 giây. Vấn đề còn ở khâu tổng hợp/đánh giá đủ căn cứ của model/prompt; không kết luận thiếu nguồn hay sửa compiler khi không có bằng chứng. Giữ nguyên kết quả lỗi.
- Verifier v2 thực gọi gặp `answer_verification_invalid` do quote hàng tổng hợp; kết quả lỗi giữ lại. Sau sửa v3, cohort verifier riêng dùng lại câu trả lời F02 đã lưu, không sinh lại answer: **supported**, 1.008 prompt token, 3,25 giây, reasoning off đã áp dụng, một lần gửi.

## Việc còn lại

Cần giải quyết riêng F13 bằng hợp đồng tổng hợp điều kiện chung, sau đó đo cohort mới một lần/câu; không dùng retry hay nhãn draft để tuyên bố chất lượng toàn bộ. KH16/pilot và full backend chưa được nghiệm thu. Không cần xóa tài liệu/reindex vì thay đổi cách đóng gói prompt.
