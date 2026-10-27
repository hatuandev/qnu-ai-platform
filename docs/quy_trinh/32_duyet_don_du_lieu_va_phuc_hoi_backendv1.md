# 32 — Duyệt review, dọn dẫn xuất, phục hồi và nghiệm thu backendV1

Chỉ áp dụng backendV1; workspace là biên quyền theo ADR v1. Không đổi schema hoặc
dữ liệu của backend legacy. Model không tự cấp quyền hoặc duyệt tài liệu.

## Duyệt bản biên soạn

Compiler → review hoàn tất của đúng nguồn/bản nháp → người duyệt đọc findings →
giải trình từng finding hoặc lưu bản sửa mới và review lại → preview ghim hash →
xác nhận duyệt → admin xuất bản/thay thế. Không có finding vẫn cần xác nhận đã đọc.
Review mới sau preview làm xác nhận cũ hết hiệu lực. Báo cáo gốc giữ nguyên.

## Dọn dữ liệu dẫn xuất

Admin yêu cầu preview → kiểm job đã kết thúc, tuổi tệp và toàn bộ references →
trả danh sách/hash/hạn dùng → admin xác nhận cùng idempotency key → lưu intent →
kiểm lại quyền/references/version → xóa có điều kiện → audit/receipt.
Giữ nguồn, raw, backup, tệp còn tham chiếu và namespace không biết owner. Lỗi giữ
pending để retry đúng key; không tự xóa theo lịch hoặc purge tài liệu nghiệp vụ.

## Sao lưu và phục hồi v1

Người vận hành có token quản trị dừng nhận ghi, chờ/hủy job → snapshot MVCC và
kiểm từng tệp → bundle được mã hóa/xác thực → chọn DB chưa tồn tại và kho trống →
xem trước đích/hash → xác nhận → migration mới → phục hồi rows có kiểu/tệp nguyên
bytes → dựng vector từ dữ liệu đã lưu, remap cả generation cũ → kiểm checksum,
credential và tìm kiếm → người vận hành chấp nhận rồi mới bật phục vụ.

Không tự khởi động worker, chuyển lưu lượng, ghi đè DB/kho nguồn hoặc chép khóa
master vào bundle. Legacy và queue/cache ngoài phạm vi; không resend uncertain.

## Sẵn sàng vận hành

Admin đọc readiness để kiểm DB/schema, Redis, dấu sống worker đúng queue, Qdrant,
nguồn đọc được và cấu hình OCR/chat/embedding qua ModelOps. Đây không phải bằng
chứng inference hoặc chất lượng. Chạy toàn luồng trong môi trường riêng và thử
phục hồi trước khi chuyển lưu lượng. Production cần cấu hình xác thực/reconcile
phù hợp; dev token trong lượt thử không thay thế nghiệm thu SSO.

[Review gate](../../backendV1/docs/publication-review-gate.md) ·
[Dọn dẫn xuất](../../backendV1/docs/storage-cleanup.md) ·
[Recovery](../../backendV1/docs/recovery.md) · [Readiness](../../backendV1/docs/readiness.md).
