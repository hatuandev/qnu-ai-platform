# Phiên 768 — Ngân sách context và 19 câu với model thật

Ngày 2026-10-31. Phạm vi người dùng cho phép: cấu hình ngân sách context phù hợp và chạy mới đủ 19 câu, không retry để làm xanh kết quả.

## Cấu hình

Đối chiếu quyền actor, collection, bản xuất bản và manifest chỉ mục hiện tại trước khi cấu hình. Trợ lý admissions `ast_c122f8de4b84` được cập nhật qua API, có kiểm tra revision: `context_max_bytes` từ **16000 lên 57344 byte**, revision **3 → 4**. Các trường khác giữ nguyên: candidate 50, top 20, window 0, output 4096 và verification off.

Chỉ mục có 46 chunks. Tổng kích thước evidence JSON của 20 chunks lớn nhất cho cận trên **51391 byte**; thêm 10% rồi làm tròn theo 4096 được **57344 byte**. Kiểm tra cả prompt/persona/câu hỏi cho cận input bảo thủ 60807, cộng output 4096 thành 64903, nằm trong context 131072 của model Qwen đã chọn. Byte là đơn vị ngân sách evidence, không phải số token thực đo. Không đổi capacity model, quota, provider, nguồn hoặc chỉ mục.

## Thực thi và kết quả

Chạy backend hiện tại qua HTTPX ASGITransport cùng lifespan, xác thực thật, DB/Qdrant và các adapter provider thật; không giả actor hoặc model. Đây là kiểm thử API, không phải chạy Playwright/UI. Không ngắt hoặc khởi động lại cửa sổ serve của người dùng.

Tạo 19 conversations và 19 turns mới, mỗi câu gửi đúng một lần. Cùng bộ câu hỏi, prompt `qnu.rag.answer/v5`, cấu hình inference và manifest chỉ mục xuyên suốt. Audit DB xác nhận mỗi capability embedding/rerank/chat có **19 executions, tất cả attempt 1, code ok**. Không dùng đáp án cũ hoặc phục hồi câu sai.

**FAIL: 16 PASS / 3 FAIL / 0 NOT_RUN**, thời gian 228.297 giây (~3 phút 48 giây), exit 1.

| Câu | Kết quả quan sát |
| --- | --- |
| F06 | `model_abstained` |
| F09 | `model_abstained` |
| F15 | `numbers_mismatch`: trả điều kiện chung tốt/giỏi và 18.00 hoặc 8.50; rubric yêu cầu ngoại lệ khá và 16.50 hoặc 6.50 |

Các câu khác đạt kiểm tra tự động; F17–F19 từ chối đúng theo rubric. API hoàn tất cả 19 turns không có nghĩa cả 19 câu trả lời đạt. Chưa kết luận nguyên nhân duy nhất bên trong model cho ba câu sai; không sửa hoặc hỏi lại trong phiên này.

Không có lỗi vượt token/context/quota. Evidence thực tế tối đa **49819 byte**, input thực đo tối đa **21908 token**. Tổng usage của ba capability là **1088242 token**. Quota giữ 10000000; tokens used 7038355 → 8126597, reserved giữ 123455; không phát sinh unknown reservation mới hoặc giải phóng reservation lịch sử.

Một preflight thiết lập ban đầu dừng trước mọi model POST vì cộng dự phòng cả 19 câu (2925962) thay vì reserve/settle từng câu tuần tự (quota còn 2838190). Sửa riêng script cục bộ để kiểm tra đủ một lượt tối đa, giữ ledger kiểm tra từng request. Resume chỉ cho thư mục chưa có dispatch, kiểm tra DB có 0 turns của đợt này và tạo khóa độc quyền. Không có request model nào được gửi lại.

## Bằng chứng và giới hạn

- [Kết quả từng câu](../../tmp/admissions-once-768/admissions-answers.json), [manifest](../../tmp/admissions-once-768/manifest.json), [dispatches](../../tmp/admissions-once-768/dispatches.json), [audit](../../tmp/admissions-once-768/audit.json). Artifacts nằm cục bộ trong tmp bị ignore; không đưa corpus/đáp án thô vào Git.
- PDF 8 trang giữ hash `236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45`; index `idx_876119b2d82a`, manifest `068b1421875efb11b28f712345631a320f3872a4801d36928fbc9059d361b098` không đổi.
- Bộ nhãn `floor2026-v1` vẫn `draft_agent_read_pdf_not_human_approved`; semantic review độc lập **NOT_RUN**. 16/19 là nghiệm thu tự động của đợt này, không phải chứng nhận chất lượng production.
- Không đổi mã ứng dụng, reindex, OCR, compile, publish, checkpoint hoặc restart. Không chạy lại unit/integration trong phiên cấu hình này; full unit phiên 767 còn FAIL nền source_purge_716 (548 PASS / 1 FAIL), không chuyển thành PASS.
- Serve cũ chưa nạp các sửa mã trước đó. Nếu người dùng chạy CLI tiếp, cần tự mở lại serve để nạp mã hiện tại; không cleanup/init nếu muốn giữ nguồn đã xuất bản.

Việc tiếp theo nếu được giao: phân tích retrieval/evidence và câu trả lời đầu tiên của F06/F09/F15, sửa theo cấu trúc tổng quát rồi chạy một cohort mới có định danh riêng. Giữ nguyên kết quả FAIL của cohort này.
