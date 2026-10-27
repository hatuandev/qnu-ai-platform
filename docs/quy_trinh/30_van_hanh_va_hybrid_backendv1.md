# 30 — Vận hành và hybrid retrieval backendV1

Mở rộng sau luồng [hậu OCR/Compiler](29_noi_hau_ocr_review_va_sua_compiler_backendv1.md):

1. Đọc trạng thái job và usage qua operations; tiến độ lấy từ trang/chunk đã có.
2. Khi queue gián đoạn, tạo preview rồi chấp nhận giao lại job queued/hết lease.
   Worker giữ quyền/checkpoint; failed/uncertain không được resend ngầm.
3. Tạo evidence backup theo workspace, kiểm checksum rồi tải ZIP. Nguồn/raw giữ
   vô thời hạn; chỉ xóa backup hết hạn sau preview/acceptance và audit.
4. Sau publication/index, search chọn dense hoặc FTS + dense/RRF và rerank.
   Rerank lấy model/credential/capacity/quota động qua ModelOps.
5. Đánh giá cùng snapshot, query và tập ứng viên; lưu nhãn, metrics, errors và
   giới hạn. Kết quả thử chức năng không phê duyệt nội dung hoặc chất lượng.

Chi tiết API: [operations](../../backendV1/docs/operations.md),
[hybrid/evaluation](../../backendV1/docs/hybrid-evaluation.md),
[review có cấu trúc](../../backendV1/docs/compiler-review.md).

Chỉ backendV1; workspace là biên giới quyền theo ngoại lệ của v1. Không áp kiến
trúc/quyền này sang backend cũ. Migration0014 chỉ được áp khi đã xác nhận DB đích.
