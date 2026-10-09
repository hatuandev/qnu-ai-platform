# NHẬT KÝ LÀM VIỆC — PHIÊN #287
**Thời gian**: 2026-10-07 | **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**: Thực Hiện Phiên 2 (Pha 1) Kế Hoạch 11: Mở Rộng Schema CSDL & DTO Revisions Theo Chiến Lược Expand-and-Contract, Tạo Bảng `document_revisions`, Viết Migration Alembic Có Backfill An Toàn và Hoàn Thành Bộ Test Suite 100%.

---

## 1. Bối Cảnh & Mục Tiêu Phiên 2 (Pha 1)

Tiếp nối Phiên 1 (Pha 0) đã khóa cứng ADR-011 và Đặc tả API Contracts V2, Phiên 2 bước vào triển khai thực tế tầng dữ liệu (Data Persistence & Schema Layer) theo đúng kế hoạch [`docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md).

Mục tiêu cốt lõi của **Phiên 2 (Pha 1)** bao gồm:
1. **Thiết kế & Mở rộng Model SQLAlchemy ORM**: Khai báo model mới `DocumentRevision` và mở rộng `RepositoryDocument` với các trường phục vụ phiên bản hóa và cô lập đa khách thuê (`tenant_id`, `workspace_id`, `status`, `current_revision_id`, `latest_revision_no`, `row_version`, `catalog_metadata`).
2. **Thiết kế Migration Alembic Expand-and-Contract**: Viết file migration `20261007_document_revisions.py` với cơ chế **Safe Backfill** tự động chuyển đổi toàn bộ tài liệu hiện hữu trong `repository_documents` sang phiên bản đầu tiên (`revision_no = 1`), bảo đảm 0 downtime và không gây gián đoạn các luồng nghiệp vụ hiện tại.
3. **Khai báo DTO Pydantic V2**: Xây dựng đầy đủ các schemas `DocumentRevisionListItem`, `DocumentRevisionResponse`, `ReviewRevisionContentRequest`, `SubmitRevisionReviewRequest`, và `AsyncUploadDocumentResponse` (HTTP 202 Accepted).
4. **Kiểm thử Tự động & Linter**: Viết unit test suite `test_document_revisions_schema.py` kiểm tra toàn diện quan hệ ORM, ràng buộc khóa ngoại vòng, serialization Pydantic, và tính toàn vẹn của Alembic migration; đạt 100% tests pass và 0 lỗi Ruff linter.

---

## 2. Các Kết Quả Hoàn Thành Trong Phiên

### 2.1. Cập Nhật Model ORM SQLAlchemy (`backend/app/modules/documents/models.py`)
- **Mở rộng `RepositoryDocument`**:
  - Bổ sung `tenant_id` (`String(64)`), `workspace_id` (`String(64)`) phục vụ Bất biến 10 (Tenant Isolation).
  - Bổ sung `status` (`active`, `archived`).
  - Bổ sung `current_revision_id` trỏ tới `document_revisions.id` (với `post_update=True` để giải quyết triệt để phụ thuộc vòng Foreign Key).
  - Bổ sung `latest_revision_no` (`Integer`, default=0), `row_version` (`Integer`, default=1) cho kiểm soát tương tranh lạc quan (Optimistic Concurrency Control - OCC).
  - Bổ sung `catalog_metadata` (`JSONB`).
  - Thiết lập quan hệ hai chiều `revisions` (one-to-many, `cascade="all, delete-orphan"`) và `current_revision` (one-to-one pointer).
- **Thêm mới `DocumentRevision`**:
  - Mã định danh `id` tiền tố `rev_<hex12>`.
  - Khóa ngoại `document_id` trỏ về `repository_documents.id` (`ondelete="CASCADE"`).
  - `revision_no` kết hợp `(document_id, revision_no)` làm Unique Index.
  - Con trỏ phiên bản kế thừa `based_on_revision_id` và self-referential relationship `based_on`.
  - Bất biến tệp nguồn: `source_file_name`, `source_file_type`, `source_size_bytes`, `source_hash`, `source_storage_path`.
  - Nội dung chuẩn hóa: `canonical_markdown`, `canonical_hash`.
  - Cấu trúc bóc tách & Cổng chất lượng: `page_manifest` (`JSONB`), `citation_metadata` (`JSONB`), `parse_provenance` (`JSONB`), `quality_report` (`JSONB`).
  - Máy trạng thái: `status` (`queued | processing | validating | review_required | ready | failed | cancelled`), `failure_code`, `failure_detail`.
  - Idempotency & Concurrency: `idempotency_key`, `request_hash`, `lock_version`.
  - Dấu vết kiểm toán & Timestamps: `started_at`, `finished_at`, `created_by`, `created_at`, `updated_at`.

### 2.2. Xây Dựng Alembic Migration Có Backfill An Toàn (`backend/alembic/versions/20261007_document_revisions.py`)
- Kế thừa migration `20261007_document_repository`.
- **Thao tác `upgrade()`**:
  1. Thêm các cột mở rộng vào bảng `repository_documents` kèm chỉ mục tương ứng.
  2. Tạo bảng `document_revisions` kèm các khóa ngoại và composite indexes (`ix_doc_revisions_doc_rev_no`, `ix_doc_revisions_doc_status`, `ix_doc_revisions_source_hash`, `ix_doc_revisions_canonical_hash`, `ix_doc_revisions_idempotency`).
  3. Tạo ràng buộc khóa ngoại `fk_repository_docs_current_rev` từ `repository_documents.current_revision_id` sang `document_revisions.id`.
  4. **Cơ chế Safe Backfill tự động**: Quét toàn bộ bản ghi `repository_documents` hiện có trong database, tự động tạo bản ghi `document_revisions` tương ứng với `revision_no = 1`, kế thừa markdown, provenance và quality report; cập nhật ngược lại `current_revision_id` và `latest_revision_no = 1`.
- **Thao tác `downgrade()`**: Hạ cấp tuần tự an toàn (drop FK $\rightarrow$ drop bảng `document_revisions` $\rightarrow$ drop các cột mở rộng trên `repository_documents`).

### 2.3. Bổ Sung DTO Schemas Pydantic V2 (`backend/app/modules/documents/schemas.py`)
- Cập nhật `RepositoryDocumentListItem` và `RepositoryDocumentResponse`: Bổ sung `status`, `current_revision_id`, `latest_revision_no`, `catalog_metadata`.
- Bổ sung `DocumentRevisionListItem`: DTO thu gọn cho danh sách revisions và timeline lịch sử.
- Bổ sung `DocumentRevisionResponse`: DTO chi tiết chứa toàn bộ manifests, quality report và markdown.
- Bổ sung `ReviewRevisionContentRequest`: DTO hỗ trợ chuyên viên biên tập hiệu đính Markdown với validation không để trống.
- Bổ sung `SubmitRevisionReviewRequest`: DTO phê duyệt/từ chối bản sửa đổi.
- Bổ sung `AsyncUploadDocumentResponse`: DTO phản hồi tiếp nhận tài liệu bất đồng bộ HTTP 202 Accepted theo chuẩn ADR-011.

### 2.4. Kiểm Thử Unit Test Suite 100% Pass & Linter Sạch 0 Lỗi
- Tạo tệp kiểm thử chuyên biệt: `backend/tests/test_document_revisions_schema.py`.
- Bao phủ:
  - Khởi tạo model ORM `RepositoryDocument` và `DocumentRevision`.
  - Quan hệ hai chiều, self-referential lineage (`rev2.based_on == rev1`).
  - Serialization / Deserialization Pydantic DTOs V2 và validation error khi nội dung rỗng.
  - Tính toàn vẹn của tệp migration Alembic (kiểm tra `revision`, `down_revision`, `upgrade`, `downgrade`).
- **Kết quả Pytest**:
  ```
  tests\test_document_revisions_schema.py ... [ 33%]
  tests\test_document_repository.py ...... [100%]
  ======================== 9 passed, 1 warning in 3.49s =========================
  ```
- **Kết quả Ruff Linter**:
  ```
  uv run ruff check app/modules/documents/ alembic/versions/20261007_document_revisions.py tests/
  All checks passed! (0 lint errors)
  ```

---

## 3. Danh Sách Tệp Đã Tạo Mới / Cập Nhật

1. [`backend/app/modules/documents/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/models.py) — Khai báo model `DocumentRevision`, mở rộng `RepositoryDocument`.
2. [`backend/alembic/versions/20261007_document_revisions.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20261007_document_revisions.py) — Migration Alembic mở rộng bảng và backfill an toàn.
3. [`backend/app/modules/documents/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/schemas.py) — Bổ sung các DTO schemas Pydantic V2 cho Revisions và Async Upload.
4. [`backend/tests/test_document_revisions_schema.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_document_revisions_schema.py) — Test suite kiểm tra ORM models, relations, schemas và migration.
5. [`docs/nhat_ky/2026-10-07_phien_287_hoan_thanh_pha_1_schema_csdl_document_revisions_va_dto_v2.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/nhat_ky/2026-10-07_phien_287_hoan_thanh_pha_1_schema_csdl_document_revisions_va_dto_v2.md) — Nhật ký làm việc phiên #287.

---

## 4. Kế Hoạch Cho Phiên Kế Tiếp (Phiên 3 / Pha 2)

Sẵn sàng bước vào **Phiên 3 (Pha 2)**:
- Triển khai **Pipeline Tiếp Nhận Bất Đồng Bộ V2 & Cổng Đánh Giá Chất Lượng (Quality Gate)**:
  - Nâng cấp `DocumentRepositoryService.upload_document` sang cơ chế bất đồng bộ trả về `job_id` và HTTP 202 (`AsyncUploadDocumentResponse`).
  - Xây dựng Worker xử lý tài liệu nền (`intake_worker` / job pipeline).
  - Tích hợp bộ quy chuẩn chất lượng: độ đầy đủ văn bản, tỷ lệ bảng biểu, cảnh báo scan mờ/OCR lỗi.
  - Chuyển trạng thái sang `ready` (nếu đạt) hoặc `review_required` (nếu cần cán bộ hiệu đính).
