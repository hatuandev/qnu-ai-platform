# Nhật Ký Phiên #286 — Xây Dựng Kế Hoạch “Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn”

## 1. Thông tin phiên

- **Thời gian**: 2026-10-07 17:51 (UTC+7)
- **Phạm vi**: Phân tích và lập kế hoạch kiến trúc cho Kho tài liệu → Kho tri thức.
- **Loại thay đổi**: Tài liệu thiết kế; chưa thay đổi mã nguồn, schema hoặc runtime.

## 2. Mục tiêu

- Chuyển Kho tài liệu thành nguồn sự thật duy nhất cho tệp, metadata, OCR/parse và nội dung chuẩn hóa.
- Chuyển Kho tri thức sang mô hình binding + index revision bất biến.
- Loại bỏ rủi ro xử lý tệp trùng, delete-before-index và trộn revision trong RAG.
- Lập lộ trình triển khai có migration, backfill, testing, canary, rollback và acceptance criteria rõ ràng.

## 3. Công việc đã hoàn thành

- Khảo sát luồng Kho tài liệu, Kho tri thức, ingestion, vector indexing, retrieval, jobs và giao diện liên quan.
- Chốt kiến trúc đích:
  - `RepositoryDocument` quản lý tài liệu logic.
  - `DocumentRevision` quản lý bản nguồn bất biến.
  - `KnowledgeBinding` quản lý quan hệ tài liệu–collection.
  - `KnowledgeIndexRevision` quản lý artifact RAG bất biến.
  - `KnowledgeIndexActivation` quản lý lịch sử publish/rollback.
  - `KnowledgeVectorGeneration` tách biệt các không gian embedding.
- Thiết kế pipeline bất đồng bộ, Quality Gate, parity gate và atomic activation.
- Đề xuất RetrievalSnapshot dùng chung cho dense, sparse, facts, neighbors và citations.
- Xây dựng API V2, mô hình job idempotent, transactional outbox và cache theo epoch.
- Lập chiến lược expand-and-contract, backfill ngoài Alembic, shadow retrieval và canary theo collection.
- Lập ma trận kiểm thử, observability, runbook, rủi ro và acceptance criteria.

## 4. Tệp thay đổi

- `docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`: tài liệu kế hoạch chính.
- `docs/ke_hoach/README.md`: bổ sung kế hoạch số 11 vào danh mục.
- `docs/nhat_ky/README.md`: bổ sung phiên #286.
- `docs/memory/PROJECT_CONTEXT.md`: cập nhật snapshot phiên gần nhất và quyết định kiến trúc.
- `docs/WORK_LOG.md`: bổ sung dòng tiến trình phiên #286.

## 5. Quyết định kiến trúc

1. Kho tài liệu là nguồn sự thật của file và canonical content.
2. Kho tri thức chỉ tiếp nhận revision `ready` thông qua binding.
3. Revision nguồn và index artifact đã `ready` là bất biến.
4. PostgreSQL active pointer là nguồn sự thật của dữ liệu đang phục vụ.
5. Không xóa artifact cũ trước khi artifact mới vượt qua parity và được kích hoạt.
6. Đồng bộ mặc định là thủ công; revision mới chỉ tạo trạng thái `update_available`.
7. Mọi kênh retrieval phải dùng cùng một snapshot revision.
8. Model/provider được phân giải động từ ModelOps; không hardcode.

## 6. Kết quả kiểm tra

- Đã rà soát cấu trúc và liên kết của các tài liệu Markdown được cập nhật.
- Không chạy Ruff, Pytest hoặc Vite build vì phiên này chỉ thay đổi tài liệu, không thay đổi mã nguồn hay cấu hình runtime.
- Trạng thái triển khai: **mới hoàn tất kế hoạch; chưa triển khai schema, backend, frontend hoặc migration**.

## 7. Bài học và lưu ý cho phiên kế tiếp

- Cần bắt đầu bằng ADR, inventory và API contract V2 trước khi viết migration hoặc giao diện.
- Không được thực hiện backfill có I/O ngoài trong Alembic.
- Phải giữ feature flags và kill switch trong toàn bộ giai đoạn canary.
- Cần kiểm chứng concurrency “toàn old hoặc toàn new” trước khi cutover production.

## 8. Bước tiếp theo đề xuất

Triển khai Phiên 1 của kế hoạch: tạo ADR, inventory chi tiết các contract hiện tại, chốt enum/state machine và đóng băng API V2 để chuẩn bị migration additive.
