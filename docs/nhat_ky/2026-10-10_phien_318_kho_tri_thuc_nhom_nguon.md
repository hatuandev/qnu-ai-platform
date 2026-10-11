# Nhật Ký Phiên #318 — Hoàn Thiện Quy Trình Kho Tri Thức Liên Kết Nhóm Nguồn Lâu Dài & Tinh Gọn Giao Diện

- **Thời gian**: 2026-10-10
- **Phiên làm việc**: #318
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Hoàn thiện quy trình Kho tri thức theo kiến trúc mới: Kho tài liệu quản lý file, phiên bản và Nhóm tài liệu; Kho tri thức liên kết một hoặc nhiều Nhóm tài liệu làm nguồn lâu dài (`KnowledgeGroupSource`); phát hiện biến động nhóm qua `membership_hash` SHA-256 ổn định; tinh gọn giao diện 4 tab loại bỏ toàn bộ luồng trùng lặp và thuật ngữ di trú/kỹ thuật.

---

## 1. Bối Cảnh & Vấn Đề Giải Quyết

Trước phiên #318:
1. `attach_document_group()` chỉ tạo snapshot một lần; Kho tri thức không lưu được quan hệ liên kết lâu dài với Nhóm tài liệu. Khi Nhóm tài liệu có thêm văn bản mới hoặc phát hành phiên bản mới, Kho tri thức không tự động phát hiện được.
2. Giao diện Kho tri thức có nhiều nút thao tác trùng lặp (`Gắn Nhanh`, `Nạp Nhanh (Modal)`, `Tài liệu (Legacy V1)`, `Reindex Vector`, `GC`, `Đối soát & Canary V2`) làm phân tán trải nghiệm người dùng nghiệp vụ và để lộ các thuật ngữ kỹ thuật/di trú (`V1/V2`, `ADR-011`, `Canary`, `GC`, `Epoch`, `Atomic Pointer Swap`, `Parity Gate`).
3. Trạng thái và số liệu header còn bị gán cứng hoặc đọc từ `KnowledgeDocument` Legacy thay vì tính toán động từ active index revisions và group sources thực tế.

---

## 2. Kiến Trúc & Giải Pháp Triển Khai

### 2.1. Backend Data Model & Migration
- **Model mới `KnowledgeGroupSource`** (`app/modules/knowledge/models.py`):
  - Các trường: `id`, `collection_id`, `document_group_id`, `sync_policy`, `chunk_strategy`, `status`, `last_synced_at`, `last_membership_hash`, `tenant_id`, `workspace_id`, `created_at`, `updated_at`.
  - Composite Unique Constraint: `(collection_id, document_group_id)`.
  - Trạng thái nguồn chuẩn hóa: `empty`, `up_to_date`, `updates_available`, `syncing`, `review_required`, `ready`, `failed`, `detached`.
- **Thêm cột `group_source_id`** vào `KnowledgeBinding` để truy vết nguồn gốc nhóm của từng binding.
- **Alembic Additive Migration** (`backend/alembic/versions/20261010_knowledge_group_sources.py`):
  - Tạo bảng `knowledge_group_sources` kèm foreign keys, unique constraint và indexes.
  - Bổ sung cột nullable `group_source_id` vào `knowledge_bindings`.
  - Giữ an toàn 100% dữ liệu hiện có và tính tương thích ngược với Inspector.

### 2.2. Thuật Toán Phát Hiện Thay Đổi (Differential Categorization)
- **Thuật toán tập hợp 6 phân loại**:
  - `added`: Tài liệu mới trong nhóm có revision `ready` mà chưa có active binding trong collection.
  - `updated`: Tài liệu đã bound nhưng có revision mới (`rev.id != binding.source_revision_id`).
  - `removed`: Đã có binding gắn với group source nhưng tài liệu không còn nằm trong nhóm (`doc_id not in group_doc_map`). Chuyển sang trạng thái `removed/pending_detach`.
  - `unchanged`: Đã bound và revision trùng khớp.
  - `not_ready`: Tài liệu có trong nhóm nhưng revision chưa hoàn thành bóc tách (`pending`, `parsing`).
  - `failed`: Revision bị lỗi bóc tách (`failed`, `cancelled`).
- **Membership Hash ổn định (Bất biến thứ tự)**:
  - Sắp xếp `sorted((doc_id, rev_id))` trước khi nối chuỗi định dạng `doc_id:rev_id|...`.
  - Băm SHA-256 thành chuỗi hex 64 ký tự. Đảm bảo độc lập 100% với thứ tự thêm dữ liệu.

### 2.3. Chính Sách Xóa An Toàn & Quy Trình Index/Publish
- Khi tài liệu bị loại khỏi nhóm: **Tuyệt đối không tự động detach hoặc xóa index ngay**. Preview gắn nhãn `removed` ("chờ xác nhận gỡ bỏ"). Chỉ detach khi người dùng đánh dấu `confirm_detach_removed=True` trong payload sync.
- Mặc định xuất bản có kiểm soát: Sau khi sync tạo index staging, chuyển sang trạng thái `review_required`. Người dùng kiểm tra đối soát trước khi bấm **Xuất bản** (gọi atomic pointer promotion chuyển `staging` -> `active`, không downtime).
- Nếu Index build thất bại: Trả lỗi chi tiết RFC 7807, giữ nguyên pointer `active_index_revision_id` cũ, không trả thành công giả.

### 2.4. Đơn Giản Hóa Giao Diện Frontend (Group-First Flow)
- **Header tinh gọn**:
  - Tên Kho tri thức, trạng thái động (`Trống`, `Đang đồng bộ`, `Chờ xuất bản`, `Có cập nhật`, `Sẵn sàng`, `Có lỗi`).
  - 4 chỉ số thực tế: Số nhóm nguồn, Tài liệu đã xuất bản, Tài liệu cần đồng bộ, Chunks đang hoạt động.
  - Duy nhất 1 CTA chính: **`Thêm nguồn`**.
  - Không hardcode model embedding hay provider ID; hiển thị cấu hình từ ModelOps hoặc "Theo mặc định hệ thống".
- **4 Tab chuẩn hóa**:
  1. `Nguồn tài liệu` (thay thế Liên kết V2 / Tài liệu Legacy): Thẻ và bảng các Nhóm tài liệu nguồn, badge trạng thái, nút `Đồng bộ` khi có cập nhật, nút `Xem` mở trang chi tiết nguồn.
  2. `Dữ liệu số` (Facts số).
  3. `Hoạt động` (Tiến trình jobs/ingestion).
  4. `Cấu hình` (Mô hình & Cấu hình).
- **Trang Thêm Nguồn (`/knowledge/:collectionId/add-documents`)**:
  - Mặc định: Chọn Nhóm tài liệu, xem trước khác biệt (Server-Side Preview Diff Breakdown) và xác nhận thêm nguồn.
  - Nâng cao: Tab "Chọn riêng" cho các tài liệu lẻ nếu nghiệp vụ cần.
- **Trang Chi Tiết Nguồn (`/knowledge/:collectionId/sources/:sourceId`)**:
  - Breadcrumb phân cấp rõ ràng, tổng quan tài liệu, bảng đối soát chi tiết từng tài liệu (`added`, `updated`, `removed`, `unchanged`, `not_ready`, `failed`).
  - Hộp kiểm xác nhận gỡ bỏ tài liệu `removed`. Nút `Đồng bộ`, nút `Xuất bản`, và nút `Gỡ nguồn`.
- **Ẩn hoàn toàn thuật ngữ kỹ thuật**: Loại bỏ V1/V2, ADR-011, Canary, GC, Epoch, Atomic Pointer Swap, Parity Gate khỏi người dùng thông thường.

---

## 3. Các Tệp Mã Nguồn Thay Đổi

### Backend
1. [`backend/app/modules/knowledge/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/models.py): Thêm model `KnowledgeGroupSource` và quan hệ `KnowledgeBinding.group_source_id`.
2. [`backend/alembic/versions/20261010_knowledge_group_sources.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20261010_knowledge_group_sources.py): Migration additive an toàn.
3. [`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py): Thêm DTOs `KnowledgeGroupSourceResponse`, `AttachGroupSourceRequest`, `PreviewGroupSourceDiffResponse`, `SyncGroupSourceRequest`, `SyncGroupSourceResponse`, `DetachGroupSourceRequest`, `CollectionSummaryMetrics`.
4. [`backend/app/modules/knowledge/services/group_source_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/group_source_service.py): Triển khai nghiệp vụ `GroupSourceService` (diff 6 tập, membership hash, sync, publish, detach, metrics).
5. [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py): Đăng ký 8 endpoints cho group sources và summary metrics.
6. [`backend/app/modules/knowledge/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/__init__.py): Export `KnowledgeGroupSource` và sắp xếp imports chuẩn Ruff.
7. [`backend/tests/test_knowledge_group_sources.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_knowledge_group_sources.py): Tạo mới 13 test cases bao phủ toàn bộ Phần 8.

### Frontend
1. [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts): Bổ sung TypeScript types cho group sources, diff preview, sync và collection summary metrics.
2. [`frontend/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts): Thêm 8 client API methods cho group sources và metrics.
3. [`frontend/src/components/knowledge/tabs/collection-group-sources-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/tabs/collection-group-sources-tab.tsx): Tab Nguồn tài liệu mới tinh gọn, hiển thị group source cards/table, nút Đồng bộ và Xem.
4. [`frontend/src/components/knowledge/collection-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/collection-header.tsx): Header tinh gọn 1 CTA duy nhất "Thêm nguồn", metrics động, loại bỏ hardcode model/provider.
5. [`frontend/src/features/knowledge/add-documents-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/knowledge/add-documents-page.tsx): Quy trình thêm nguồn Group-first mặc định kèm Server-Side Preview Diff.
6. [`frontend/src/features/knowledge/source-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/knowledge/source-detail-page.tsx): Trang chi tiết nguồn chuyên sâu đối soát từng tài liệu.
7. [`frontend/src/routes/knowledge.$collectionId.sources.$sourceId.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/routes/knowledge.$collectionId.sources.$sourceId.tsx): Route chuyên biệt cho chi tiết nguồn.
8. [`frontend/src/routes/knowledge.$collectionId.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/routes/knowledge.$collectionId.tsx): Cập nhật search schema tab hỗ trợ `sources`.
9. [`frontend/src/features/knowledge/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/knowledge/collection-detail-page.tsx): Tinh gọn thành 4 tab chính, loại bỏ các modal legacy và entry points trùng lặp.

---

## 4. Kết Quả Kiểm Thử (Quality Gates)

### 4.1. Backend
- **Ruff linter**:
  ```bash
  uv run ruff check .
  # Kết quả: All checks passed! (0 errors)
  ```
- **Pytest Suite (`test_knowledge_group_sources.py`)**:
  ```bash
  uv run --extra dev pytest -v tests/test_knowledge_group_sources.py
  # Kết quả: 13/13 passed in 2.71s
  ```
  - `test_membership_hash_order_independence`: PASSED
  - `test_attach_group_source_success`: PASSED
  - `test_attach_group_source_idempotent`: PASSED
  - `test_preview_categorization_diff`: PASSED
  - `test_revision_change_detected_as_updated`: PASSED
  - `test_removed_document_requires_confirmation_to_detach`: PASSED
  - `test_tenant_workspace_isolation`: PASSED
  - `test_index_build_error_fails_loudly`: PASSED
  - `test_validation_fail_retains_active_pointer`: PASSED
  - `test_publish_success_promotes_staging_to_active`: PASSED
  - `test_collection_summary_metrics_and_status`: PASSED
  - `test_non_existent_group_returns_404`: PASSED
  - `test_empty_group_source_status_is_empty`: PASSED
- **Pytest Regression Suite (`test_document_groups_and_knowledge_attach.py`)**:
  ```bash
  uv run --extra dev pytest -v tests/test_document_groups_and_knowledge_attach.py
  # Kết quả: 14/14 passed in 4.45s
  ```

### 4.2. Frontend
- **TypeScript Typecheck (`tsc --noEmit`)**:
  ```bash
  bun x tsc --noEmit
  # Kết quả: exit code 0 (0 errors)
  ```
- **Vite Build**:
  ```bash
  bun ./node_modules/vite/bin/vite.js build
  # Kết quả: built in 4.57s (exit code 0)
  ```

---

## 5. Kết Luận & Điểm Lưu Ý Cho Phiên Tiếp Theo
- Hệ thống Kho tri thức đã chuyển đổi hoàn toàn sang mô hình Group-First bền vững, có khả năng phát hiện thay đổi tự động, an toàn trước dữ liệu bị gỡ bỏ, và giao diện quản trị đạt chuẩn thẩm mỹ cao cấp của ĐH Quy Nhơn.
- Backward compatibility: Các endpoints backend legacy vẫn được duy trì nguyên vẹn cho các consumer cũ nhưng đã được ẩn hoàn toàn khỏi luồng UI thông thường.
