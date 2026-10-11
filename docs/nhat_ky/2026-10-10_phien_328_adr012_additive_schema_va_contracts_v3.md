# NHẬT KÝ PHIÊN LÀM VIỆC SỐ 328
**Ngày thực hiện**: 2026-10-10
**Kỹ sư thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**: Thực Hiện Phiên 1 Kế Hoạch 12: Ban Hành ADR-012, API Contracts V3 & Additive Database Migration Bóc Tách Ranh Giới Kho Tài Liệu Và Kho Tri Thức

---

## 1. Bối Cảnh & Mục Tiêu Phiên 1

Theo [Kế Hoạch 12 (docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md)](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md), hệ thống tiến hành tách rời hoàn toàn:
- **Kho Tài Liệu**: Là kho lưu trữ tệp thuần túy (Storage Repository), chỉ lưu file gốc MinIO/S3, tính SHA-256 chống trùng, quản lý metadata danh mục; tuyệt đối không bóc tách/OCR hay chunking ngầm.
- **Kho Tri Thức**: Sở hữu 100% Document Intelligence (Parse/OCR, Unicode NFC, Quality Gate, Hiệu đính, Chunking, Structured Facts, Embedding đa thế hệ, Qdrant).
- **Nguyên lý "Parse Once, Embed Many"**: Tách biệt `KnowledgeSourceRevision` (Markdown sạch) và `KnowledgeChunkSet` (chunks + facts) khỏi các `Vector Generations` để khi đổi mô hình embedding không phải OCR/parse lại.

Mục tiêu Phiên 1 là thiết lập nền tảng kiến trúc (ADR-012), khai báo các model SQLAlchemy mới, viết migration Alembic additive (chỉ thêm, không drop dữ liệu legacy), định nghĩa Pydantic DTOs và viết regression unit test xác minh.

---

## 2. Chi Tiết Các Thay Đổi & Giải Pháp Kỹ Thuật

### 2.1. Ban Hành Kiến Trúc ADR-012
Tạo tệp [`docs/adr/ADR-012-decouple-storage-repository-and-knowledge-document-intelligence.md`](../adr/ADR-012-decouple-storage-repository-and-knowledge-document-intelligence.md):
- Supersede Quyết định 1, 2, 3 của ADR-011 (chuyển parser/OCR sang Knowledge, thay `document_revisions` chứa markdown bằng `repository_file_revisions` thuần tệp, bãi bỏ liên kết nhóm nguồn lâu dài `KnowledgeGroupSource`).
- Bảo toàn các bất biến đắt giá: Staging index, Parity Gate, CAS Atomic Pointer Swap, RetrievalSnapshot Pinning, Rollback $O(1)$, Retention Window, Idempotency và Tenant Isolation.
- Bãi bỏ Foreign Key CASCADE giữa Documents và Knowledge: Xóa file ở Kho tài liệu không làm hỏng dữ liệu snapshot tri thức đang phục vụ RAG.

### 2.2. Khai Báo Data Models SQLAlchemy Mới
1. **Trong `app/modules/documents/models.py`**:
   - `RepositoryFileRevision` (`repository_file_revisions`): Lưu phiên bản tệp gốc nguyên bản (`document_id`, `revision_no`, `source_file_name`, `source_size_bytes`, `source_hash`, `source_storage_path`).
   - Thêm quan hệ `RepositoryDocument.file_revisions`.
2. **Trong `app/modules/knowledge/models.py`**:
   - `KnowledgeSourceRevision` (`knowledge_source_revisions`): Lưu nội dung Markdown chuẩn hóa, page manifest, citation metadata, Quality Gate report trong miền Knowledge.
   - `KnowledgeChunkSet` (`knowledge_chunk_sets`): Lưu tập chunks và facts độc lập với vector model (`chunk_strategy`, `chunk_config`, `config_hash`, `chunk_set_key`).
   - `KnowledgeImportBatch` (`knowledge_import_batches`): Điều phối các batch nạp snapshot từ Kho tài liệu vào Kho tri thức.
   - `KnowledgeImportItem` (`knowledge_import_items`): Quản lý tiến trình xử lý từng tài liệu trong batch (tránh all-or-nothing, hỗ trợ partial failure & retry).
   - Mở rộng quan hệ:
     - `KnowledgeBinding.active_source_revision_id` và quan hệ `active_source_revision`, `source_revisions`.
     - `KnowledgeIndexRevision.source_revision_v2_id` và `chunk_set_id`, quan hệ `source_revision_v2`, `chunk_set`.
     - `KnowledgeCollection.import_batches`.

### 2.3. Additive Alembic Migration
Tạo file [`backend/alembic/versions/20261010_decouple_storage_and_knowledge_v3.py`](../../backend/alembic/versions/20261010_decouple_storage_and_knowledge_v3.py):
- `revision: 20261010_decouple_storage_and_knowledge_v3`
- `down_revision: 20261010_knowledge_group_sources`
- Sử dụng `inspect(bind)` để bảo đảm tính idempotent 100% (an toàn khi chạy lại nhiều lần).
- Tạo 5 bảng mới: `repository_file_revisions`, `knowledge_source_revisions`, `knowledge_chunk_sets`, `knowledge_import_batches`, `knowledge_import_items`.
- Bổ sung 3 cột liên kết vào bảng hiện có: `knowledge_bindings.active_source_revision_id`, `knowledge_index_revisions.source_revision_v2_id`, `knowledge_index_revisions.chunk_set_id`.
- Cung cấp hàm `downgrade()` đầy đủ.
- Bảo đảm duy nhất 1 Alembic HEAD (`20261010_decouple_storage_and_knowledge_v3 (head)`).

### 2.4. Pydantic DTOs & Schemas V3
1. **`app/modules/documents/schemas.py`**:
   - `RepositoryFileRevisionItem`, `RepositoryFileRevisionResponse`.
2. **`app/modules/knowledge/schemas.py`**:
   - `KnowledgeSourceRevisionResponse`, `KnowledgeChunkSetResponse`.
   - `KnowledgeImportBatchCreateRequest`, `KnowledgeImportItemResponse`, `KnowledgeImportBatchResponse`.
   - `RepositoryCandidateItem`, `CandidateListResponse` (hỗ trợ lọc 2 chiều `source_state` và `vector_state`).

---

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)

1. **Unit Test Suite Mới (`test_knowledge_v3_schema.py`)**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_knowledge_v3_schema.py -v`
   - Kết quả: **7/7 passed in 0.52s (100% đạt)**.
2. **Regression Test Suites Liên Quan**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_knowledge_group_sources.py backend/tests/test_document_repository_workflow.py backend/tests/test_knowledge_publishing_v2.py`
   - Kết quả: **72 passed, 1 skipped in 4.53s (100% đạt, zero regression)**.
3. **Linter Quality Gate (Ruff)**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m ruff check backend/app/modules/documents/models.py backend/app/modules/documents/schemas.py backend/app/modules/knowledge/models.py backend/app/modules/knowledge/schemas.py backend/alembic/versions/20261010_decouple_storage_and_knowledge_v3.py backend/tests/test_knowledge_v3_schema.py`
   - Kết quả: **All checks passed! (0 lỗi)**.
4. **Kiểm Tra Alembic HEAD**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads`
   - Kết quả: `20261010_decouple_storage_and_knowledge_v3 (head)` (duy nhất 1 head).

---

## 4. Trạng Thái & Công Việc Tiếp Theo (Next Steps)

- **Trạng thái**: **HOÀN THÀNH 100% PHIÊN 1 KẾ HOẠCH 12**.
- **Kế hoạch phiên tiếp theo**: **Phiên 2 – Simplify Kho tài liệu backend** (cắt bỏ việc tự động sinh parse job khi upload, trả trạng thái `stored` trung thực, bảo đảm xóa tệp không cascade tri thức).
