# Phiên 589 — Trang tri thức nguyên văn đạt, chatbot chưa nghiệm thu

Đã áp dụng lựa chọn LLM chọn nội dung/server trích nguyên văn. PDF revision12
ks_rev_993a7ad91b32/index idx_rev_6bf0d6f86b1b: wiki ready11 trang (1 source,
2 entity,8 concept), đủ327 units,431 trích đoạn,1915 refs exact;7 Luna/0 fallback.
Staging327chunks415facts,2943points/0retrievable; canonical/source hash giữ nguyên,
HTTPGET200 ready; không publish. Year-role annotation trống, không giả đã xác minh.
Focused109 và147 PASS, Ruff15 PASS; full cuối 3.086 PASS/18 FAIL/17 SKIP, exit1,
exact18 IDs/cause giữ,60 test mới PASS, code seals khớp. Có lượt bị ngắt không PASS.
Benchmark frozen64 nhận63 kết quả, P06 gián đoạn/không replay; điểm bảo thủ50/60
(83,33%),positive40/50,negative10/10,social4/4,citations98/98; chưa đạt85%.
GainF04; lossesP01/P03/P06/P11/P13/P14; commonFAILP05/P07/P09/P10.
Wiki mở trang ở4câu nhưng lỗi trước hoàn tất (provider502 hoặc extra_forbidden).
Không claimwiki giúp tăngđiểm.86Luna benchmark success log/0fallback, no context error.
PostcheckPASS; model/config/oldrevisions/vector/source giữ,0testthreads/messages/gaps.
DBtest đã dọn đúngowner; Storagetemp giữ do policy khôngbypass. No commit/push,
publish/restart/deploy/modelchanges; chưa làmưu tiên4–6. ChưaAPPROVED toànluồng.

## Phạm vi và bằng chứng

Compiler budget/transport/context closure và chế độ extractive v3; router giữ
fact-first, reader mở whole-section theo ngân sách. Không sửa parser hoặc FE.
Giữ thay đổi chưa commit Context587–588. Đọc báo cáo để xem phương pháp,
các lượt v2 thất bại, lệnh/checks thực chạy và giới hạn đánh giá.

[Báo cáo đối chiếu](../bao_cao/context589/IMPLEMENTATION_AND_VALIDATION.md).

## P06 bổ sung, giữ bộ chính nguyên trạng

P06 phiên mới PASS,5/5 citations,5 phản hồi Luna/0 fallback. Tính bổ sung:51/60=85%,
positive41/50=82%, chưa đạt43/50; không gọi đây là một lượt64 không gián đoạn.
Đủ64 câu duy nhất đã có kết quả qua các đoạn chạy. Bộ chính50/60, P06 interrupted
giữ nguyên để không che gián đoạn. Không đổi gold, model, source/index hoặc publish.
