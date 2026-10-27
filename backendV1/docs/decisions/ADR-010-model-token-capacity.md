# ADR-010 — Capacity theo endpoint/model, tách ngân sách tác vụ

Ngày 2026-10-26, Context641. Chỉ áp dụng backendV1.

1. ModelOps nhận `token_limits` có context dùng chung, input và output riêng. Các
   số nguyên dương không có trần8K/32K áp chung. API có input/output độc lập có thể
   không khai báo shared context; không cộng hai số để suy ra context mới.
2. Khai báo qua API quản trị có basis operator_configured. Unknown giữ null,
   không phải unlimited. Không chấp nhận cờ provider_reported/verified do client khai.
3. Profile lưu trong JSONB hiện có, ghim endpoint/model ở server. Thay đổi identity
   vô hiệu profile; đổi lại identity cũ không tự phục hồi. PATCH không có trường
   giữ nguyên; null tường minh xóa profile; khai báo lại xác nhận đích hiện hành.
4. Runtime gọi public API để kiểm quyền workspace/grant/capability/provider và lấy
   snapshot/configuration_hash. Giới hạn input/output và ngân sách tác vụ là ba
   đại lượng riêng; output tự tính chỉ dùng phần context còn lại và giới hạn model.
5. Đếm đầu vào phải theo đúng protocol, gồm ảnh/framing; unknown phải báo lỗi, không
   suy token ảnh từ Base64. Không cắt tài liệu hoặc clamp output tường minh để che lỗi.
6. OCR_MAX_OUTPUT_TOKENS là ngân sách mặc định của workflow, không phải capacity
   của model; gỡ trần validation32768. Mỗi runtime phải nối guard trước gửi request
   và kiểm truncated response; helper chưa được gọi không tự bảo vệ adapter.

Tự động discovery provider và token hóa ảnh thuộc điểm nối runtime riêng. Lượt này
không gọi provider thật, không đổi cấu hình DB phục vụ hoặc migration.

[Hợp đồng và điểm nối OCR](../model-capacity.md).
