# NHẬT KÝ LÀM VIỆC — PHIÊN #286
**Thời gian**: 2026-10-07 | **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**: Thực Hiện Phiên 1 (Pha 0) Kế Hoạch 11: Khóa Quyết Định Kiến Trúc ADR-011, Kiểm Kê Hệ Thống Hiện Tại & Ban Hành Đặc Tả API Contracts V2 Cho Quy Trình "Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn".

---

## 1. Bối Cảnh & Mục Tiêu Phiên 1

Tiếp nối sự thành công của phân hệ Kho Tài Liệu Tập Trung (`/documents`) tại các phiên #283, #284 và #285, hệ thống bước vào giai đoạn tái cấu trúc quy mô lớn theo **Kế Hoạch 11** ([`docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md)).

Mục tiêu cốt lõi của **Phiên 1 (Pha 0)** là:
1. **Khóa bất biến kiến trúc (Architectural Invariants Lock)** qua tài liệu Architecture Decision Record (ADR) chính thức.
2. **Kiểm kê toàn diện hệ thống hiện tại (System Inventory & Legacy Mapping)**: đối chiếu giữa thực trạng V1 và kiến trúc đích V2 trên cả 4 thành phần: Bảng CSDL, API Endpoints, Qdrant Vector Payloads, và Worker Jobs.
3. **Ban hành đặc tả kỹ thuật API Contracts V2**: Quy chuẩn hóa request/response DTOs, headers idempotency, HTTP status codes (`202 Accepted` vs `200 OK`), mã lỗi RFC 7807, và ma trận Feature Flags / Kill Switches an toàn.

---

## 2. Các Kết Quả Hoàn Thành Trong Phiên

### 2.1. Phê Chuẩn & Ban Hành ADR-011
Đã tạo lập tài liệu kiến trúc chuẩn quốc tế: [`docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md`](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md):
- **Quyết định 1**: Kho Tài Liệu là Nguồn Sự Thật Duy Nhất (Single Source of Truth) quản lý tệp gốc, checksum SHA-256, chuỗi các phiên bản nội dung bất biến (`document_revisions`), bóc tách Markdown, page manifest và metadata NĐ 30.
- **Quyết định 2**: Kho Tri Thức chuyển sang mô hình liên kết `knowledge_bindings`, loại bỏ hoàn toàn luồng upload trực tiếp độc lập.
- **Quyết định 3**: Quản lý không gian vector qua `knowledge_vector_generations` độc lập; thay đổi mô hình Embedding sẽ sinh generation mới, không làm ô nhiễm vector cũ.
- **Quyết định 4**: Xây dựng chỉ mục tại vùng Staging độc lập (`knowledge_index_revisions`); chỉ kích hoạt khi vượt qua **Parity Gate** (so khớp 100% giữa PostgreSQL chunks và Qdrant vectors).
- **Quyết định 5**: Kích hoạt nguyên tử bằng thao tác đổi con trỏ **Atomic Pointer Swap CAS** (`active_epoch`), cho phép **Rollback tức thì (0ms)** về phiên bản cũ mà không cần re-embed.
- **Quyết định 6**: Cưỡng chế mọi kênh RAG (Dense, Sparse, Facts, Neighbors, Citations) phải đọc từ một **`RetrievalSnapshot`** thống nhất, triệt tiêu 100% lỗi ảo giác trích dẫn lệch pha (Mixed Citations Hallucination).
- **Khóa cứng Mười Bất Biến Bắt Buộc (The 10 Invariants)** của hệ thống.

### 2.2. Ban Hành Đặc Tả API Contracts V2 & Báo Cáo Kiểm Kê
Đã tạo lập tài liệu: [`docs/ke_hoach/contracts_v2_specification.md`](../ke_hoach/contracts_v2_specification.md):
1. **Bảng đối chiếu 9 bảng CSDL**: `repository_documents`, `document_revisions`, `knowledge_bindings`, `knowledge_vector_generations`, `knowledge_index_revisions`, `knowledge_index_activations`, `knowledge_chunks`, `knowledge_facts`, `job_records`.
2. **Bản đồ chuyển đổi 12 API Endpoints**: Chi tiết các API tiếp nhận tài liệu bất đồng bộ (`POST /documents/upload` $\rightarrow$ `202 Accepted`), API quản lý revision (`GET/PATCH /documents/{id}/revisions`), API liên kết Kho Tri Thức (`POST /collections/{id}/bindings`), API đồng bộ và rollback (`POST /bindings/{id}/rollback`).
3. **Nâng cấp Qdrant Payload V2**: Bổ sung `point_id` deterministic UUID5 (`generation:revision:chunk_id`), `binding_id`, `source_revision_id`, `index_revision_id`, `vector_generation_id`, `tenant_id`, `workspace_id`.
4. **Quy chuẩn Header & Mã lỗi RFC 7807**: Cưỡng chế header `Idempotency-Key`, kiểm tra `request_hash`, chuẩn hóa các mã lỗi `IDEMPOTENCY_KEY_CONFLICT`, `PARITY_CHECK_FAILED`, `ACTIVE_EPOCH_MISMATCH`.
5. **Ma trận Feature Flags & Kill Switch**: Khai báo 6 cờ cấu hình môi trường (`KNOWLEDGE_REVISION_WRITES_ENABLED`, `RAG_REVISION_READ_MODE=legacy|shadow|revisioned`, `RAG_ATOMIC_ACTIVATION_ENABLED`, `RAG_CACHE_EPOCH_ENABLED`, `RAG_REVISION_GC_ENABLED`, `MAX_RETAINED_INDEX_REVISIONS_PER_BINDING=2`).

---

## 3. Danh Sách Tệp Đã Tạo Mới / Cập Nhật

1. [`docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md) — Tài liệu Architecture Decision Record ADR-011 chính thức.
2. [`docs/ke_hoach/contracts_v2_specification.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/contracts_v2_specification.md) — Đặc tả API Contracts V2, Inventory Map & Feature Flags.
3. [`docs/nhat_ky/2026-10-07_phien_286_chot_adr011_va_api_contracts_v2_tiep_nhan_mot_lan_xuat_ban_an_toan.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/nhat_ky/2026-10-07_phien_286_chot_adr011_va_api_contracts_v2_tiep_nhan_mot_lan_xuat_ban_an_toan.md) — Nhật ký làm việc phiên #286.

---

## 4. Kế Hoạch Cho Phiên Kế Tiếp (Phiên 2 / Pha 1)

Sẵn sàng bước vào **Phiên 2**: Thiết kế migration Alembic tạo bảng `document_revisions` và mở rộng các trường `current_revision_id`, `latest_revision_no`, `row_version` trên `repository_documents` theo đúng chuẩn mở rộng an toàn (Expand-and-Contract, không gây gián đoạn dữ liệu hiện tại).
