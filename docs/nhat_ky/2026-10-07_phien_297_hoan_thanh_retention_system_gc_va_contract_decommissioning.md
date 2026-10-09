# NHẬT KÝ LÀM VIỆC — PHIÊN #297 (Phiên 12 / Kế Hoạch 11)
## Hoàn Thành Retention, System-Wide Artifact Garbage Collection & Contract Migration Loại Bỏ Legacy An Toàn (ADR-011)

- **Ngày thực hiện**: 2026-10-07
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Thuộc kế hoạch**: [Kế hoạch Triển khai Quy trình Tiếp nhận Một lần — Xuất bản Tri thức An toàn (Kế hoạch 11)](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) & [ADR-011](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md)
- **Mục tiêu phiên**:
  1. **Enforce Single Source of Truth & Cưỡng chế Deprecation**: Khóa hoàn toàn luồng nạp trực tiếp cũ `upload_document` khi `KNOWLEDGE_ALLOW_DIRECT_UPLOAD=False` bằng mã lỗi chuẩn RFC 7807 `DIRECT_UPLOAD_DEPRECATED_USE_CENTRAL_REPOSITORY`, điều hướng 100% luồng nghiệp vụ qua Kho Tài Liệu Tập Trung (`/documents/intake` $\rightarrow$ Quality Gate $\rightarrow$ Knowledge Binding).
  2. **System-wide Artifact Garbage Collection**: Xây dựng cơ chế dọn dẹp hàng loạt toàn hệ thống `collect_garbage_system_wide` hỗ trợ chế độ mô phỏng Dry-run và thực thi tự động theo chính sách `retention_revisions` của từng kho tri thức.
  3. **ARQ Worker Background Task**: Đăng ký `task_knowledge_garbage_collection` trong `tasks.py`, `arq_worker.py` và `jobs/service.py` cho phép vận hành dọn dẹp định kỳ không đồng bộ.
  4. **System Decommissioning Audit**: Xây dựng endpoint kiểm kê toàn trường `GET /knowledge/decommissioning/audit` đo lường tỷ lệ áp dụng V2 (`v2_adoption_rate_pct`), số tài liệu legacy còn lại và trạng thái phân bố các chế độ đọc RAG.
  5. **Frontend Contract Finalization**:
     - Cập nhật `CollectionHeader`: Nút hành động chính chuyển thành `+ Thêm Từ Kho` (điều hướng sang trang Master-Detail `/add-documents`), nút Direct Upload cũ chuyển vào tùy chọn phụ `[Legacy V1]`.
     - Cập nhật `CollectionDetailPage`: Đặt tab mặc định là `bindings` (chuẩn V2 ADR-011), tab tài liệu cũ gắn nhãn `Tài liệu (Legacy V1)`.
     - Bổ sung types và API client: `runSystemWideGarbageCollection`, `getSystemDecommissioningAudit`.
  6. **Đạt 100% Quality Gate**: 25/25 tests Pytest V2 passed, Ruff 0 lỗi, Biome linter 0 lỗi, TypeScript typecheck 0 lỗi.

---

### 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Trước Phiên 12:
- Dù kiến trúc V2 đã hoàn thành cutover ở Phiên 8 và Canary Policy ở Phiên 11, endpoint nạp trực tiếp cũ (`/collections/{id}/upload`) vẫn mở dưới dạng compatibility façade. Điều này dẫn tới nguy cơ người dùng tiếp tục bypass Kho Tài Liệu Tập Trung, vi phạm Bất biến 1 của ADR-011 (*Kho Tài Liệu Tập Trung là Nguồn Sự Thật Duy Nhất*).
- Garbage Collection chỉ mới hỗ trợ gọi đơn lẻ theo từng `collection_id`, thiếu khả năng quét dọn tự động toàn hệ thống (System-wide GC) và thiếu background worker task trong ARQ.
- Chưa có công cụ kiểm kê tập trung để ban lãnh đạo CNTT theo dõi tỷ lệ chuyển đổi từ V1 sang V2 trên toàn trường.
- Giao diện người dùng vẫn ưu tiên tab `documents` cũ và nút chính vẫn là `Nạp tài liệu` trực tiếp thay vì luồng thêm từ Kho tài liệu tập trung.

---

### 2. Các Thay Đổi Kiến Trúc & Triển Khai Codebase

#### 2.1. Backend Architecture (4-File Modular Monolith)

1. **Cấu Hình Feature Flag (`backend/app/core/config.py`)**:
   - `KNOWLEDGE_ALLOW_DIRECT_UPLOAD: bool = False`: Chốt chặn bảo vệ Decommissioning. Mặc định là `False` để chặn đứng nạp trực tiếp vào kho tri thức, buộc người dùng đi qua Kho Tài Liệu V2.

2. **Schemas DTOs (`backend/app/modules/knowledge/schemas.py`)**:
   - `SystemGarbageCollectionRequest`: Tham số cấu hình dọn dẹp toàn hệ thống (`dry_run`, `default_keep_revisions`).
   - `SystemGarbageCollectionReport`: Thống kê chi tiết số kho quét, số binding, số revisions/chunks/facts/points giải phóng.
   - `SystemDecommissioningAuditReport`: Báo cáo tỷ lệ chuyển đổi V2, số tài liệu legacy, số lượng kho ở các chế độ đọc (`revisioned`, `shadow`, `legacy`).

3. **Garbage Collection Service (`backend/app/modules/knowledge/services/gc_service.py`)**:
   - `collect_garbage_system_wide`: Quét qua toàn bộ kho tri thức, đọc chính sách `retention_revisions` riêng của từng kho và thực thi/mô phỏng dọn dẹp an toàn.
   - `audit_system_decommissioning`: Tổng hợp số liệu legacy vs V2 toàn hệ thống phục vụ báo cáo quản trị.

4. **ARQ Worker Background Task (`backend/app/workers/tasks.py` & `arq_worker.py` & `jobs/service.py`)**:
   - Khai báo và đăng ký `task_knowledge_garbage_collection` cho phép scheduler/cronjob định kỳ kích hoạt GC mà không nghẽn luồng HTTP request.

5. **Enforce Deprecation & REST Endpoints (`backend/app/modules/knowledge/router.py`)**:
   - `upload_document`: Kiểm tra `settings.KNOWLEDGE_ALLOW_DIRECT_UPLOAD`. Nếu `False`, chặn ngay với HTTP 400 kèm mã lỗi RFC 7807 `DIRECT_UPLOAD_DEPRECATED_USE_CENTRAL_REPOSITORY`.
   - `POST /api/v1/knowledge/gc/system-wide`: Chạy Garbage Collection toàn hệ thống.
   - `GET /api/v1/knowledge/decommissioning/audit`: Báo cáo tiến độ di trú toàn trường.

#### 2.2. Frontend UI/UX Architecture

1. **TypeScript Types & API Client (`frontend/src/types/knowledge.ts` & `frontend/src/services/knowledge-api.ts`)**:
   - Thêm `SystemGarbageCollectionRequest`, `SystemGarbageCollectionReport`, `SystemDecommissioningAuditReport`.
   - Bổ sung methods `runSystemWideGarbageCollection`, `getSystemDecommissioningAudit`.

2. **CollectionHeader (`frontend/src/components/knowledge/collection-header.tsx`)**:
   - Nút hành động chính: **`+ Thêm Từ Kho`** (màu Academic Teal Primary, icon `FileStack`), điều hướng sang trang Master-Detail `/add-documents`.
   - Nút `Gắn Nhanh` (mở dialog popup).
   - Nút `Nạp trực tiếp (Legacy)`: Chuyển vào menu phụ với nhãn `[Legacy V1]` và hướng dẫn dùng Kho Tài Liệu V2.

3. **CollectionDetailPage (`frontend/src/features/knowledge/collection-detail-page.tsx`)**:
   - Đổi tab mặc định thành `bindings` (chuẩn V2 ADR-011).
   - Đặt tab `bindings` lên vị trí số 1 trong `TabsList`.
   - Tab cũ đổi nhãn thành `Tài liệu (Legacy V1)`.
   - Đấu nối `onAddDocuments` chuyển hướng mượt mà sang `/knowledge/:collectionId/add-documents`.

---

### 3. Kết Quả Kiểm Thử Toàn Diện

| Thành Phần | Công Cụ Kiểm Thử | Kết Quả | Ghi Chú |
| :--- | :--- | :---: | :--- |
| **Backend Phiên 12 Test Suite** | Pytest 9.1.1 | **7/7 PASSED (100%)** | `test_publishing_v2_decommissioning_and_system_gc.py` (Chặn direct upload, system-wide GC dry-run/exec, worker task, audit API) |
| **Backend Toàn Bộ V2 Regression Tests** | Pytest 9.1.1 | **25/25 PASSED (100%)** | Kết hợp cả 3 test suites: `decommissioning`, `cutover_and_gc`, `e2e_canary` |
| **Backend Code Quality** | Ruff Linter | **0 LỖI (All checks passed)** | Tuân thủ 100% chuẩn code PEP 8 & Clean Architecture |
| **Frontend Type Safety** | `tsc --noEmit` | **0 LỖI (Exit Code 0)** | 100% Type-safe React 19 + TanStack Query v5 + TanStack Router |
| **Frontend Code Quality** | Biome Linter | **0 LỖI / 0 WARNINGS** | Tuân thủ tokens OKLCH, chuẩn Radix UI, Biome formatter |

---

### 4. Các Tệp Đã Thay Đổi Trong Phiên

1. [`backend/app/core/config.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py): Thêm `KNOWLEDGE_ALLOW_DIRECT_UPLOAD: bool = False`.
2. [`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py): Thêm `SystemGarbageCollectionRequest`, `SystemGarbageCollectionReport`, `SystemDecommissioningAuditReport`.
3. [`backend/app/modules/knowledge/services/gc_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/gc_service.py): Thêm `collect_garbage_system_wide` và `audit_system_decommissioning`.
4. [`backend/app/workers/tasks.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/workers/tasks.py): Khai báo ARQ worker task `task_knowledge_garbage_collection`.
5. [`backend/app/workers/arq_worker.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/workers/arq_worker.py): Đăng ký `task_knowledge_garbage_collection` vào `WorkerSettings`.
6. [`backend/app/modules/jobs/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/jobs/service.py): Đăng ký mapping job type `knowledge_garbage_collection`.
7. [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py): Bổ sung 2 facade methods cho System GC và Decommissioning Audit.
8. [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py): Cưỡng chế chặn direct upload và mở 2 endpoints `/gc/system-wide`, `/decommissioning/audit`.
9. [`backend/tests/test_publishing_v2_decommissioning_and_system_gc.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_publishing_v2_decommissioning_and_system_gc.py): Test suite kiểm thử toàn diện Phiên 12 (7 unit tests).
10. [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts): Bổ sung TypeScript interfaces cho System GC và Audit.
11. [`frontend/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts): Bổ sung methods `runSystemWideGarbageCollection`, `getSystemDecommissioningAudit`.
12. [`frontend/src/components/knowledge/collection-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/collection-header.tsx): Tái cấu trúc action buttons ưu tiên `+ Thêm Từ Kho` V2.
13. [`frontend/src/features/knowledge/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/knowledge/collection-detail-page.tsx): Đổi tab mặc định sang `bindings`, đổi nhãn `Tài liệu (Legacy V1)`.
14. [`docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md): Cập nhật tiến độ hoàn tất 100% trọn vẹn cả 12 phiên.

---

### 5. Kết Luận & Tổng Kết Kế Hoạch 11

- **Kế hoạch 11 đã chính thức hoàn thành trọn vẹn 100% qua 12 phiên làm việc liên tục**.
- Toàn bộ 10 bất biến của [ADR-011](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md) đã được hiện thực hóa ở mức độ hoàn hảo:
  1. *Kho Tài Liệu Tập Trung là Nguồn Sự Thật Duy Nhất*: Đã cưỡng chế loại bỏ luồng nạp trực tiếp cũ.
  2. *Phiên Bản Nội Dung Bất Biến*: `DocumentRevision` v1, v2 với kiểm định Quality Gate tự động.
  3. *Liên Kết Độc Lập*: `KnowledgeBinding` và `KnowledgeVectorGeneration`.
  4. *Staging Indexing*: Không còn hiện tượng Delete-Before-Index.
  5. *Cổng Kiểm Định Parity Gate*: So khớp 100% DB vs Vector DB trước khi kích hoạt.
  6. *Hoán Đổi Con Trỏ Nguyên Tử CAS*: Promote trong $O(1)$ kèm epoch counter.
  7. *RetrievalSnapshot Nhất Quán*: Zero Revision Leak giữa các lượt hỏi đáp đa vòng.
  8. *Instant Zero-Reindex Rollback*: Hoàn tác tức thì trong $< 1$ giây.
  9. *Dynamic Canary & Retention Policy*: Cho phép cuốn chiếu từng kho tri thức an toàn.
  10. *Trích Dẫn Minh Chứng Đầy Đủ Provenance*: Auditable Citations tới từng revision cụ thể.
