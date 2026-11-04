# 24 — Chỉ mục và tìm kiếm dense backendV1

Phạm vi: `backendV1/`, tiếp sau [duyệt/xuất bản](23_phien_ban_va_xuat_ban_backendv1.md).
Workspace là biên giới quyền của v1 theo ngoại lệ AGENTS; không thay cơ chế của `backend/`.

## Điều kiện đầu vào

Document có phiên bản đang xuất bản, receipt hợp lệ và nguồn/revision/hash còn
đúng. ModelOps có provider embedding đang hoạt động, credential mã hóa, grant
workspace, default hoặc provider được chọn, dimension/capacity và quota.
Qdrant/Redis/storage là cấu hình hạ tầng server, không lấy URL từ model hoặc body.

## Thứ tự nghiệp vụ

1. Editor/admin yêu cầu indexing bằng Idempotency-Key. Server chụp publication,
   chia đoạn và nhóm bảng giữ citation/ô/header/span/footnote từ snapshot gốc;
   lưu run/input/chunk và audit trước dispatch.
   Chỉ mục mới lấy tiêu đề nguồn có căn cứ cho đoạn và bảng của cả hai chế độ
   biên soạn. Nếu một đoạn tổng hợp nhiều mục, giữ tiêu đề biên soạn của đoạn.
   Với bảng sát ngân sách, giữ tiêu đề trong metadata để bảo toàn nhóm hàng.
   Chỉ mục v5 bỏ bản sao chữ trùng nguyên văn với các hàng của bảng đã bóc tách
   khi đoạn chỉ dẫn đúng bảng đó. Đoạn có metadata riêng, dẫn chứng khác hoặc
   nội dung bổ sung vẫn được lập chỉ mục theo đoạn.
2. Worker ARQ kiểm quyền/nguồn/model, reserve quota, gọi embedding theo batch.
   Raw response có hash, vector staging và usage receipt được giữ bền vững.
3. Ghi vào Qdrant generation riêng, xác nhận hoàn thành, kiểm lại snapshot,
   lưu manifest rồi kích hoạt. Generation mới lỗi giữ active generation cũ.
4. Người có quyền tìm trong collection và document scope tùy chọn. Chỉ tài liệu
   còn hợp lệ mới vào filter trước TopK; query dùng đúng model/config của index.
5. Sau embedding kiểm lại quyền/publication; đối chiếu hit với SQL/manifest,
   trả đoạn/bảng và citation revision/page/block. Thu hồi hoặc nguồn đổi loại
   nội dung; publication mới cần generation mới. Lỗi hạ tầng trả lỗi rõ.

Job mất delivery được reconcile; mất lease có fencing. Batch embedding chưa rõ
kết quả chuyển `uncertain`, không tự gọi lại. Batch đã lưu vector có thể upsert
lại cùng ID sau lỗi vector. Không tự xóa history/raw hoặc active generation.

## Kiểm chứng và bước sau

Live BGE-M3 trên server người dùng chỉ định đã qua ModelOps/ARQ/Qdrant/search
với dữ liệu mẫu: vector1024,2chunk, bảng150 và citation đúng, withdraw chặn kết quả
và không gọi embedding thêm. OCR/chat mẫu giả lập; chưa nghiệm thu chất lượng
corpus thật. Mã hiện tại là dense retrieval, chưa hybrid/rerank hoặc RAG answer.

Cần migration0009 và cấu hình ModelOps trong môi trường phục vụ trước khi vận hành;
phiên này chỉ áp DB thử. Không restart/deploy hoặc publish/index tài liệu thật.

[API/vận hành](../../backendV1/docs/dense-indexing.md) ·
[Báo cáo647](../bao_cao/context647/REVIEW.md).
