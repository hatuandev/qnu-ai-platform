# Kiểm tra sẵn sàng và nghiệm thu backendV1

`GET /platform/v1alpha1/workspaces/{workspace_id}/operations/readiness` dành cho
admin, dùng resolver workspace và `private, no-store`. Phản hồi chỉ có trạng thái,
ID model/provider và mã lỗi an toàn, không có credential hay prompt.

Kiểm tra quan sát được: DB ở schema `0003_rag_policy_metadata`, kết nối Redis,
worker đúng queue/schema/code còn heartbeat, Qdrant phản hồi và đọc được nguồn có hash
đã ghim. Phân giải OCR/chat/embedding qua ModelOps kiểm grant, capability, key và
capacity hiện hành; không hardcode model hoặc endpoint vào đường xử lý nghiệp vụ.
Quota tháng phải được cấu hình tường minh, không khóa và còn ngân sách; thiếu cấu
hình hoặc limit 0 không thành ready. Limit null chỉ là unlimited khi có hàng cấu
hình thật; reservation chưa rõ vẫn được trừ khỏi ngân sách khả dụng.

`ready=true` chỉ nói các dependency và cấu hình hiện tại đã đạt. API luôn để
`live_inference_verified=false`, vì GET này không gửi nội dung tài liệu tới model.
`production_auth_configured` và `reconcile_enabled` được báo riêng; không coi
dev login hoặc thiếu reconcile là đã nghiệm thu production. Hệ thống trống chưa
có nguồn để đọc thử giữ storage chưa kiểm chứng, không tạo PASS giả.

Worker ghi heartbeat TTL 90 giây, gia hạn 30 giây trên namespace queue/cache v1;
shutdown xóa đúng dấu của worker đó. Worker queue khác không làm queue hiện tại
thành ready. Schema heartbeat lấy từ DB thực tại startup và kèm phiên bản code.

## Nghiệm thu môi trường riêng

1. Chọn DB/queue/storage riêng, áp migration head, cấu hình xác thực và ModelOps
   đúng quyền; không sao chép key vào file cấu hình LLM tạm.
2. Chạy API/ARQ worker, kiểm readiness. Production tắt dev gate, cấu hình SSO và
   reconcile; token phải đến từ môi trường xác thực hợp lệ.
3. Upload PDF/DOCX → revision → OCR → sửa text nếu cần → Compiler → review.
4. Người duyệt dùng [review gate](publication-review-gate.md), rồi xuất bản và index.
5. Hỏi đáp có nguồn; kiểm lại binding/revision/hash khi nguồn bị thu hồi hoặc thay.
6. Thử dừng chatbot/hủy job/khôi phục; kiểm phản hồi muộn không được nhận lại.
7. Thử [dọn dẫn xuất](storage-cleanup.md), [backup/restore](recovery.md) vào đích mới
   và hỏi lại dữ liệu đã phục hồi trước khi chuyển lưu lượng.

Lượt nghiệm thu Context666 đã dùng API HTTP thật, dev token của môi trường riêng,
Redis/ARQ, PostgreSQL, Local storage và Qdrant thật. Nemotron/Qwen/BGE-M3/BGE rerank
chạy trên server AI người dùng đã cho phép; PDF 2 trang đã qua toàn luồng và phục
hồi. Quyết định duyệt là thao tác thử được cho phép trong DB riêng, không là duyệt
chất lượng hay xuất bản corpus phục vụ. Readiness đạt khi worker đang chạy; worker,
DB và vector thử được dọn sau lượt chạy.
