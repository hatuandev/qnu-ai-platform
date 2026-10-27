# 25 — Hỏi đáp có trích dẫn backendV1

Tiếp sau [index/search](24_index_va_tim_kiem_dense_backendv1.md), thuộc `backendV1/`.
Workspace là biên giới quyền của v1; không thay cơ chế hoặc code của backend cũ.

1. Người có quyền đọc gửi câu hỏi và phạm vi collection/document.
2. BE tìm bằng chứng từ active index, kiểm publication/nguồn/hash như search647.
3. Cấp ID evidence cho từng chunk, giữ ánh xạ nguồn tại server; gửi text/structure
   và ID vào prompt. Không cắt bảng âm thầm hoặc nhờ model tự tạo source location.
4. Model chat lấy động từ ModelOps trong danh sách được cấp, có capacity/quota.
   Model trả JSON từng ý cùng evidence IDs hoặc abstain khi thiếu căn cứ.
5. BE kiểm schema, ID citation và text thuần, kiểm lại quyền/publication/index/
   nguồn/model sau HTTP. Nguồn thay đổi thì bỏ đáp án, trả lỗi rõ.
6. Trả câu trả lời + statements + nguồn revision/page/path/hash + trace an toàn.

Chưa có lịch sử hội thoại, streaming hoặc cache. Mỗi POST là một lượt mới; không
retry model ngầm. Lỗi provider/quota/citation không biến thành không có dữ liệu.
Không có bằng chứng thì không gọi chat. Kiểm ID không thay thế kiểm chứng ngữ nghĩa.

Live BGE-M3/Qwen3.5-9B/Qdrant qua ModelOps trên dữ liệu mẫu PASS:2ý/1nguồn,
1.979token,2,891s, ô150 và ghi chú2023 giữ, revision đúng. OCR/Compiler mock;
chưa benchmark corpus thật hoặc thay đổi môi trường phục vụ. Không migration mới;
vẫn cần0009/config/index hợp lệ khi vận hành.

[API và giới hạn](../../backendV1/docs/rag-answers.md) ·
[Báo cáo648](../bao_cao/context648/REVIEW.md).
