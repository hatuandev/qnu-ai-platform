# Phiên597 — Ổn định điều kiện nguồn và benchmark RAG

Ngày 22/10/2026, nhánh `v1.0.1`. Thực hiện đề xuất Context596, giữ thay đổi chưa
commit có trước. Không đổi model/nguồn/index/Quality Gate, không reindex, publish,
restart, deploy hoặc commit/push.

## Phạm vi và phương pháp

Mười file ứng dụng RAG, ba file test mới và một test592 được cập nhật. Giữ các
điều kiện nguồn đã xác minh qua vòng sửa; đọc quan hệ nguồn độc lập; tách đúng
primary quote khỏi context nền; phục hồi exact source rồi kiểm chứng lại.
Mỗi trích đoạn có ID riêng, không gộp mọi nhánh trong một block thành một target.
Fact dẫn xuất không có offset không trở thành clause canonical. Tham chiếu text
tự nhiên chấp nhận khác biệt trình bày có kiểm soát, mã/URL/quote vẫn giữ chặt.

Chi tiết file, nguyên nhân, các lượt đỏ và lệnh thật nằm trong
[báo cáo nghiệm thu](../bao_cao/context597/IMPLEMENTATION_AND_VALIDATION.md).
Luồng cập nhật tại [quy trình16](../quy_trinh/16_trang_tri_thuc_va_doc_nguon.md).

## Kết quả

<!-- SESSION_RESULTS_START -->
Mã chốt: **765 focused PASS**, Ruff14 PASS; **37 regression mới PASS**.
Full Pytest **FAIL**:3275PASS/18FAILnền/17SKIP,23subtestsPASS; exactIDs/nguyên nhân
khớp595, không lỗi pytest mới hoặc thiếuID không giải thích. Cwd backend; exit0
cho focused/Ruff, exit1 cho full; receipt và đối chiếu ở báo cáo liên kết.

Lượt64 cuối: **58/60tri thức=96,67%**, positive49/50,negative9/10,social4/4,
mục tiêu85%PASS. F08/P07/P12/P15 đềuPASS; cònFAIL **P06/X09**. P06 bị audit loại
phần chứng minh không tác động chỉ tiêuSV; X09 chỉ từ chối số chung sau numeric
guard90 và source review bắt thêm thangQ, chưa giải thích thiếuA. Không coi mọi
abstention làPASS. Không có runtime error;141/141citations resolve;148Luna calls,
0fallback, p95tri thức50,847s. Chưa nghiệm thu100% hoặc production readiness.

Các lượt64 trước:53/60,58/60,57/60 giữ riêng; probeP10/P13/P16=3/3 cũng giữ riêng,
không ghép vào điểm cuối. Có nine-ID gains và hai losses so595, ghi từng ID trong
báo cáo. Nhãn draft source-rubric, không gọi judgeLLM hoặc đổi frozen rubric.
PostcheckPASS: source/model/code/vector/lịch sử revision giữ,0chat/thread/gap.
<!-- SESSION_RESULTS_END -->

## An toàn và giới hạn

DB/MinIO/Qdrant local development được xác minh. Pytest dùng DB owner/nonce riêng,
Storage tạm và endpoint ngoại vi127.0.0.1:1; không migrate DB dùng chung. Cả bốn DBtest
đã dọn đúng owner/nonce. Storage giữ vì kiểm duyệt tự động trước đó đã chặn xóa theo policy; không thử vòng tránh.
Usage audit được giữ; benchmark không tạo chat/thread/gap để dọn.

Candidate RAG service thật với actor có quyền; không phải published HTTP/browser
E2E. Nhãn draft source-rubric do Codex đối soát, chưa là human holdout. Không gọi
judge LLM, không ghép retry. FE build/lint và retrieval ablation NOT RUN.

<!-- SESSION_HANDOFF_START -->
Đã hoàn thành đợt triển khai và phép đo cùng model/nguồn, đạt ngưỡng85% được giao;
hai câu cònFAIL được bàn giao công khai. Không tiếp tục thay mã/chạy lại để chọn
điểm cao hơn. Chưa publish hoặc restart services. Muốn cải thiện tiếp cần thí nghiệm
riêng ở audit vai trò hàngP06 và nhánh thiếu đầu vào/numeric guardX09, giữ Quality Gate.
<!-- SESSION_HANDOFF_END -->
