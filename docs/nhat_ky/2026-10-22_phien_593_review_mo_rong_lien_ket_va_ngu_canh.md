# Phiên593 — Review mở rộng liên kết và ngữ cảnh

Context593: review mở rộng ngữ cảnh/liên kết, chưa sửa app. Tái hiện8 trường hợp thành6 nhóm: coverage chủ thể/nguồn và điều kiện/ngoại lệ (P1); role năm học, nhiều đối tượng/bảng, chia budget wiki (P2); cache khi đổi budget (P3, chưa chứng minh caller hiện tại hạ budget). Hai control đúng, offline exit0, 1235 code seals giữ, 0LLM/DB/network. Full/live hiện tại NOT RUN; 8/8 và full3139PASS/18FAIL/17SKIP là lịch sử592. Không reindex/publish/restart/commit/push.

Người dùng yêu cầu review những điểm quan trọng cần mở rộng cho trường hợp khác.
Áp dụng clean-code, RAG pipeline/evaluation, đọc code/diff/tests thật. Không sửa
app/test, không thêm quan hệ vào nguồn. Probe trích hàm AST và contracts hiện tại,
guardrail thật, fixtures tổng quát; không gọi LLM/DB. Bản đầu harness thiếu globals
exit1, sửa riêng harness và chạy hoàn chỉnh exit0; giữ receipt lỗi đầu.

Phân biệt guard chấp nhận sai query với chatbot thực sự trả sai: chưa chạy E2E.
Hai P1 cần xử lý trước tăng số liên kết. P3 cache là guard cho ngân sách động;
chưa chứng minh runtime hiện tại thay budget trong cùng request.

[Báo cáo và kế hoạch ưu tiên](../bao_cao/context593/REVIEW_AND_EXTENSION_PLAN.md).
