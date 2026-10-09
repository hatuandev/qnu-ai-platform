# NHẬT KÝ LÀM VIỆC — PHIÊN #296 (Phiên 11 / Kế Hoạch 11)
## Hoàn Thành Triển Khai Cơ Chế Phân Giải Động Chính Sách Canary Serving & Quản Lý Lưu Trữ Retention Window (ADR-011)

- **Ngày thực hiện**: 2026-10-07
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Thuộc kế hoạch**: [Kế hoạch Triển khai Quy trình Tiếp nhận Một lần — Xuất bản Tri thức An toàn (Kế hoạch 11)](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) & [ADR-011](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md)
- **Mục tiêu phiên**:
  1. Xây dựng cơ chế phân giải động chính sách Canary phục vụ RAG per-collection (`read_mode`: `"system"`, `"revisioned"`, `"shadow"`, `"legacy"`), cho phép cuốn chiếu an toàn từng kho tri thức riêng biệt mà không ảnh hưởng toàn hệ thống.
  2. Triển khai cấu hình cửa sổ lưu trữ bản superseded (`retention_revisions`: 2..10) để bảo vệ khả năng hoàn tác tức thì Instant Rollback $O(1)$.
  3. Mở rộng Backend: Hoàn thiện DTOs, Service Facade, Router endpoints `GET /collections/{id}/canary/policy` và `PUT /collections/{id}/canary/policy`, tích hợp lưu vết `last_gc_report` trong `collection_metadata`.
  4. Mở rộng Frontend UI: Tích hợp Sub-tab 3 "Chính Sách Canary & Lưu Trữ" trong `CollectionParityAuditTab`, gồm Card Canary Serving Mode, Card Rollback Retention, Card Last GC History và Dialog Artifact Garbage Collection mô phỏng/thực thi.
  5. Đạt 100% kiểm thử: Pytest 18/18 tests passed, Ruff 0 lỗi, Biome linter 0 lỗi, TypeScript typecheck 0 lỗi.

---

### 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Trước Phiên 11:
- Cấu hình chế độ đọc RAG (`read_mode`) phụ thuộc tĩnh vào biến môi trường hệ thống `settings.RAG_REVISION_READ_MODE`. Mọi kho tri thức đều phải chạy chung một chế độ (hoặc cùng `revisioned`, hoặc cùng `shadow`, hoặc cùng `legacy`).
- Thiếu cơ chế Canary Rollout mềm dẻo cho phép quản trị viên thử nghiệm chế độ `shadow` hoặc `revisioned` trên một kho tri thức cụ thể (ví dụ Kho Tuyển Sinh) trước khi áp dụng đại trà toàn trường.
- Số lượng phiên bản lịch sử được bảo lưu (`retention_revisions`) bị gán cứng mặc định là 2 trong mã nguồn, chưa cho phép người dùng tùy chỉnh linh hoạt theo quy mô từng kho.
- Giao diện người dùng chưa có khu vực quản lý tập trung chính sách Canary và kích hoạt tác vụ Dọn dẹp chỉ mục cũ (Artifact Garbage Collection) kèm theo việc quan sát báo cáo lịch sử GC gần nhất.

---

### 2. Các Thay Đổi Kiến Trúc & Triển Khai Codebase

#### 2.1. Backend Architecture (4-File Modular Monolith)

1. **Schemas DTOs (`backend/app/modules/knowledge/schemas.py`)**:
   - `CanaryPolicyResponse`: Đại diện phản hồi chính sách gồm `collection_id`, `read_mode`, `system_read_mode`, `effective_read_mode`, `retention_revisions`, và `last_gc_report`.
   - `UpdateCanaryPolicyRequest`: Payload cập nhật gồm `read_mode` (`"system" | "revisioned" | "shadow" | "legacy"`) và `retention_revisions` ($1 \le N \le 10$).

2. **Canary Service (`backend/app/modules/knowledge/services/canary_service.py`)**:
   - `get_collection_canary_policy`: Đọc `canary_policy` từ `collection_metadata`, phân giải động `effective_read_mode` và đính kèm `last_gc_report`.
   - `update_collection_canary_policy`: Cập nhật cấu hình nguyên tử vào `collection_metadata`, ghi log kiểm toán.

3. **Garbage Collection Service (`backend/app/modules/knowledge/services/gc_service.py`)**:
   - Sau khi thực thi dọn dẹp thành công, tự động lưu toàn bộ nội dung `GarbageCollectionReport` vào `col.collection_metadata["last_gc_report"]`.
   - Gom toàn bộ thao tác cập nhật trạng thái revision, xóa chunks/facts và lưu metadata vào 1 transaction DB duy nhất (Single Atomic Commit).

4. **Dynamic Resolution trong HybridRetriever (`backend/app/modules/rag/retriever.py`)**:
   - Cập nhật `search_sparse_fts` và `search_dense`: Phân giải động `effective_read_mode` từ `canary_policy` của từng collection. Nếu cấu hình là `"system"`, tự động fallback về `settings.RAG_REVISION_READ_MODE`.
   - Chế độ `"revisioned"`: Lọc nghiêm ngặt 100% `KnowledgeChunk.index_revision_id.in_(active_revs)`.
   - Chế độ `"shadow"` / `"legacy"`: Cho phép truy xuất cả chunks legacy unindexed nhằm mục đích đối soát hoặc dự phòng khẩn cấp.

5. **Service Facade & REST API (`service.py` & `router.py`)**:
   - `KnowledgeService.get_collection_canary_policy` & `update_collection_canary_policy`.
   - Endpoints:
     * `GET /api/v1/knowledge/collections/{collection_id}/canary/policy`
     * `PUT /api/v1/knowledge/collections/{collection_id}/canary/policy`
     * `POST /api/v1/knowledge/collections/{collection_id}/gc`

#### 2.2. Frontend UI/UX Architecture

1. **TypeScript Types & API Client (`frontend/src/types/knowledge.ts` & `frontend/src/services/knowledge-api.ts`)**:
   - Bổ sung interface `CanaryPolicyResponse`, `UpdateCanaryPolicyRequest`, `GarbageCollectionRequest`, `GarbageCollectionReport`.
   - Mở rộng API client: `getCanaryPolicy`, `updateCanaryPolicy`, `runGarbageCollection`. Khử trùng lặp phương thức triệt để.

2. **Giao Diện `CollectionParityAuditTab` (`frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx`)**:
   - Mở rộng Sub-tab 3: **"Chính Sách Canary & Lưu Trữ"** (`Sliders` icon).
   - **Card Cấu hình Canary Serving Mode**:
     * Dropdown chọn `read_mode`: `system`, `revisioned`, `shadow`, `legacy`.
     * Badge hiển thị trực quan trạng thái đang chạy thực tế (`effective_read_mode`).
     * Box hướng dẫn ý nghĩa nghiệp vụ của từng chế độ đối với Trợ lý AI.
     * Cấu hình số bản superseded lưu lại cho Rollback ($N \in [1..10]$).
     * Nút "Lưu Thiết Lập Chính Sách" với phản hồi Toast và mutation state.
   - **Card Dọn Dẹp Chỉ Mục Cũ (Artifact Garbage Collection)**:
     * Cảnh báo bảo vệ Rollback an toàn (active + $N$ bản superseded được bảo vệ tuyệt đối).
     * Thẻ lịch sử dọn dẹp gần nhất (`last_gc_report`): Revisions pruned, Chunks xóa, Points Qdrant, thời điểm chạy.
     * 2 nút hành động: "Mô Phỏng Dry-Run" và "Dọn Dẹp Chỉ Mục Cũ".
   - **Dialog Artifact Garbage Collection**:
     * Tùy chọn chuyển đổi linh hoạt Dry-run / Thực thi và số lượng bản bảo lưu.
     * Bảng kết quả thống kê 4 ô chi tiết khi chạy xong.

---

### 3. Kết Quả Kiểm Thử Toàn Diện

| Thành Phần | Công Cụ Kiểm Thử | Kết Quả | Ghi Chú |
| :--- | :--- | :---: | :--- |
| **Backend Unit & E2E Tests** | Pytest 9.1.1 | **18/18 PASSED (100%)** | `test_publishing_v2_cutover_and_gc.py` (9 tests) & `test_publishing_v2_e2e_canary.py` (9 tests) |
| **Backend Code Quality** | Ruff Linter | **0 LỖI (All checks passed)** | Tuân thủ 100% chuẩn code PEP 8 & Clean Architecture |
| **Frontend Type Safety** | `tsc --noEmit` | **0 LỖI (Exit Code 0)** | 100% Type-safe React 19 + TanStack Query v5 |
| **Frontend Code Quality** | Biome Linter | **0 LỖI / 0 WARNINGS** | Tuân thủ quy chuẩn thẻ Radix, Lucide icons, `Number.parseInt(..., 10)` |

---

### 4. Các Tệp Đã Thay Đổi Trong Phiên

1. [`backend/app/modules/knowledge/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/schemas.py): Bổ sung DTOs `CanaryPolicyResponse` và `UpdateCanaryPolicyRequest`.
2. [`backend/app/modules/knowledge/services/canary_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/canary_service.py): Thêm methods quản lý chính sách per-collection canary policy.
3. [`backend/app/modules/knowledge/services/gc_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/gc_service.py): Lưu `last_gc_report` vào metadata và tối ưu Single Atomic Commit.
4. [`backend/app/modules/rag/retriever.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py): Phân giải động `effective_read_mode` từ collection canary metadata.
5. [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py): Bổ sung 2 facade methods cho Canary Policy.
6. [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py): Bổ sung 2 endpoints `GET` và `PUT /collections/{id}/canary/policy`.
7. [`backend/tests/test_publishing_v2_cutover_and_gc.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_publishing_v2_cutover_and_gc.py): Viết thêm test cases cho Canary Policy REST API và dynamic resolution.
8. [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts): Khai báo types `CanaryPolicyResponse`, `UpdateCanaryPolicyRequest`, `GarbageCollectionRequest`, `GarbageCollectionReport`.
9. [`frontend/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts): Bổ sung `getCanaryPolicy`, `updateCanaryPolicy`, chuẩn hóa `runGarbageCollection`.
10. [`frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx): Tích hợp Sub-tab 3 Canary Serving & Retention, Card Last GC Report, và Dialog Garbage Collection.
11. [`docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md): Cập nhật tiến độ Phiên 11 hoàn tất.

---

### 5. Kết Luận & Định Hướng Kế Tiếp

- **Tổng kết Phiên 11**: Hoàn thành xuất sắc toàn bộ 11 phiên trong lộ trình [Kế Hoạch 11](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md). Hệ thống xuất bản tri thức V2 của QNU AI Platform nay đã đạt chuẩn Production-Ready với khả năng phân giải Canary linh hoạt, kiểm định đối soát Parity Gate 100%, bảo vệ Rollback $O(1)$ và dọn dẹp chỉ mục an toàn.
