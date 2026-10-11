# NHẬT KÝ PHIÊN LÀM VIỆC SỐ 327

**Ngày thực hiện**: 2026-10-10  
**Kỹ sư thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Lập kế hoạch thay đổi ranh giới Kho tài liệu–Kho tri thức và prompt triển khai theo hướng parse một lần, embedding nhiều model.

## Kết quả

- Rà soát code hiện tại và xác nhận Kho tài liệu đang tạo parse job, canonical Markdown, Quality Gate và revision ready trước khi Knowledge index.
- Chốt Kho tài liệu là kho tệp thuần: MinIO, SHA-256, metadata danh mục và nhóm tài liệu.
- Chốt Kho tri thức sở hữu snapshot, OCR/parser, Unicode NFC, Markdown, Quality Gate, chunk set, facts, vector generations, Qdrant và RAG publishing.
- Chốt import snapshot một chiều, không duy trì `KnowledgeGroupSource` lâu dài và không ghi ngược trạng thái Knowledge vào Documents.
- Thiết kế trạng thái nguồn/vector tách biệt để hỗ trợ “đã có nguồn nhưng chưa có model embedding đang chọn”.
- Thiết kế nguyên tắc parse once/embed many và lộ trình 8 phiên additive migration → cutover → legacy cleanup.
- Bổ sung prompt tổng có thể dùng trực tiếp cho từng phiên vibe coding.

## Tệp thay đổi

- `docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`
- `docs/ke_hoach/README.md`
- `docs/nhat_ky/README.md`
- `docs/memory/PROJECT_CONTEXT.md`
- `docs/WORK_LOG.md`

## Kiểm tra

- Tài liệu Markdown được rà soát cấu trúc, liên kết và thuật ngữ.
- Không thay đổi mã nguồn, migration, dữ liệu runtime hoặc `qnu-sso` trong phiên lập kế hoạch.

## Quyết định kiến trúc cần thực hiện đầu tiên

Phiên triển khai đầu tiên phải tạo ADR-012 để supersede phần ranh giới domain của ADR-011; không được âm thầm sửa nội dung lịch sử của ADR-011 đã ACCEPTED.
