# 27 — Rà soát văn bản hậu OCR backendV1

Đầu vào là OCR đã hoàn tất với bản gốc bất biến. Đầu ra là phiên bản văn bản
người dùng đã sửa, có Markdown/JSON đồng bộ và mapping về nguồn ban đầu.

Người dùng đọc đoạn → kiểm tra chính tả → xem gợi ý → sửa theo gợi ý hoặc tự sửa
→ lưu → đọc/tải bản sửa. Gợi ý không tự ghi dữ liệu. Màn hình sẽ trình bày văn bản
thay cho mã; theo xác nhận người dùng, giao diện làm sau, đợt này chỉ backendV1.

Backend kiểm quyền, version/hash và trước/sau; tạo cả JSON lẫn Markdown trên
BlobStore rồi xác minh trước khi commit. Lỗi một tệp giữ phiên bản hiện tại;
sửa đồng thời gây conflict thay vì ghi đè. Mỗi lần lưu có lịch sử, idempotency và audit.

ModelOps chat phát hiện ứng viên lỗi trong phạm vi người dùng chọn, có usage,
trace và trạng thái durable. Gợi ý sai schema/span/nguồn bị chặn; hạ tầng lỗi
được báo đúng. Cần giữ bản người dùng đang soạn khi lưu lỗi và không auto retry model.

Không ghi đè OCR gốc, không suy đã kiểm ảnh hoặc đã đúng chính tả, không thay
Compiler/publication/index đang ghim bằng chứng cũ. Từ [quy trình29](29_noi_hau_ocr_review_va_sua_compiler_backendv1.md),
Compiler chọn được số text version cụ thể; omission/0 dùng gốc, không tự lấy latest.

[Contract và quy tắc giao diện](../../backendV1/docs/ocr-text-review.md) ·
[Báo cáo651](../bao_cao/context651/REVIEW.md).
