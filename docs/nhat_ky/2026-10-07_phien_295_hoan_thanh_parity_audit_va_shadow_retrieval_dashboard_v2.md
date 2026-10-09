# NHẬT KÝ LÀM VIỆC — PHIÊN #295 (2026-10-07)
## Thực Hiện Phiên 10 Kế Hoạch 11: Hoàn Thành Bảng Điều Khiển Kiểm Định Đối Soát Parity Gate & Shadow Retrieval Dashboard V2 (ADR-011)

---

### 1. Thông Tin Phiên Làm Việc
- **Thời gian**: 2026-10-07 22:15 – 22:35 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect
- **Mục tiêu**: Thực hiện mục tiêu **Phiên 10** theo lộ trình [Kế hoạch 11](../../docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và [ADR-011](../../docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md):
  1. Xây dựng **Bảng Điều Khiển Kiểm Định Đối Soát Parity Gate & Shadow Retrieval V2** (`CollectionParityAuditTab`):
     - Bento Grid 4 KPIs: Tỷ lệ Parity Gate toàn kho (%), Số tài liệu khớp chuẩn (`active-parity-ok`), Số tài liệu lệch vector (`needs-rebuild`), Số tài liệu chờ intake (`pending-intake`).
     - Sub-tab 1: Bảng Kiểm Kê Parity Danh Mục Tài Liệu — tìm kiếm tức thì, bộ lọc phân loại, hiển thị số chunks DB vs điểm vectors Qdrant, lý do lệch và nút liên kết tới Binding Detail.
     - Sub-tab 2: Trình Thử Nghiệm Shadow Retrieval Độc Lập — so khớp song song kết quả V1 Legacy vs V2 Snapshot Isolation, đo lường độ trễ delta ($p95$), độ tương đồng Jaccard và xác nhận huy hiệu **Zero Revision Leak** (0 rò rỉ phiên bản).
     - Dialog Di Trú An Toàn (Backfill to V2): Tùy chọn chiến lược phân đoạn mặc định (`ClauseBasedChunker`), cờ `force_rebuild` và báo cáo kết quả chi tiết.
  2. Mở rộng Frontend Types & API Client:
     - Khai báo các interface: `LegacyAuditReport`, `LegacyAuditItem`, `BackfillRequest`, `BackfillReport`, `BackfillItemResult`, `ShadowRetrievalRequest`, `ShadowRetrievalReport`.
     - Bổ sung 3 methods trong `knowledgeApi`: `auditCollectionCanary`, `backfillCollectionCanary`, `runShadowRetrievalTest`.
  3. Tích hợp Tab "Đối Soát & Canary V2" vào `CollectionDetailPage`:
     - Bổ sung `"audit"` vào `CollectionDetailTab`.
     - Chuyển hướng trực tiếp khi cán bộ nhấn nút "Đối Soát" trên thanh `CollectionHeader` sang Tab `audit`.
  4. Đảm bảo Quality Gate:
     - Backend: 9/9 tests `test_publishing_v2_e2e_canary.py` PASSED 100%, Ruff 0 lỗi.
     - Frontend: Biome linter 0 lỗi, TypeScript typecheck (`tsc --noEmit`) 0 lỗi.

---

### 2. Các Thay Đổi Chi Tiết

#### 2.1. Mở Rộng Frontend Types (`frontend/src/types/knowledge.ts`)
- Khai báo các interfaces chuẩn hóa khớp 100% với Pydantic DTOs backend:
  * `LegacyAuditItem`: `document_id`, `document_title`, `repository_document_id`, `binding_id`, `active_index_revision_id`, `db_chunks_count`, `qdrant_points_count`, `classification` (`'active-parity-ok' | 'needs-rebuild' | 'pending-intake'`), `discrepancy_reason`.
  * `LegacyAuditReport`: `collection_id`, `total_documents`, `active_parity_ok_count`, `needs_rebuild_count`, `pending_intake_count`, `parity_ratio`, `items`, `audited_at`.
  * `BackfillRequest`: `force_rebuild: boolean`, `default_chunk_strategy: string`.
  * `BackfillItemResult`: `document_id`, `binding_id`, `index_revision_id`, `chunks_tagged`, `facts_tagged`, `classification`, `status`.
  * `BackfillReport`: `collection_id`, `documents_processed`, `bindings_created`, `index_revisions_created`, `chunks_tagged`, `facts_tagged`, `collection_epoch`, `status`, `items`, `completed_at`.
  * `ShadowRetrievalRequest`: `query: string`, `top_k: number`.
  * `ShadowRetrievalReport`: `collection_id`, `query`, `v1_result_count`, `v2_result_count`, `overlap_count`, `jaccard_similarity`, `latency_v1_ms`, `latency_v2_ms`, `latency_delta_pct`, `retrieval_revision_leak_total`, `leak_detected`, `v1_chunk_ids`, `v2_chunk_ids`, `tested_at`.

#### 2.2. Mở Rộng API Client (`frontend/src/services/knowledge-api.ts`)
- Bổ sung 3 methods gọi các endpoints Canary backend:
  * `auditCollectionCanary(collectionId: string): Promise<LegacyAuditReport>`: Gọi `POST /knowledge/collections/{id}/canary/audit`.
  * `backfillCollectionCanary(collectionId: string, payload?: BackfillRequest): Promise<BackfillReport>`: Gọi `POST /knowledge/collections/{id}/canary/backfill`.
  * `runShadowRetrievalTest(collectionId: string, payload: ShadowRetrievalRequest): Promise<ShadowRetrievalReport>`: Gọi `POST /knowledge/collections/{id}/canary/shadow-test`.

#### 2.3. Xây Dựng Component Tab `CollectionParityAuditTab`
- **Vị trí**: [`frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx`](../../frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx).
- **Thiết kế & Tính năng nổi bật**:
  * **Header Toolbar**: Tiêu đề trực quan, mô tả rõ vai trò kiểm định Parity Gate so khớp DB vs Vector, nút "Kiểm Kê Lại (Audit)" (icon `RefreshCw`), nút "Di Trú Backfill" (icon `FolderSync`) và nút "Chạy Shadow Test" (icon `Zap`).
  * **Bento Grid 4 KPI Metrics**:
    1. *Tỷ Lệ Parity Toàn Kho*: Hiển thị % khớp tuyệt đối kèm thanh `Progress`, đổi màu xanh Teal khi đạt 100% và màu hổ phách khi có lệch số liệu.
    2. *Khớp Tuyệt Đối (OK)*: Đếm số lượng tài liệu `active-parity-ok` / tổng số tài liệu.
    3. *Cần Tái Dựng (Needs Rebuild)*: Cảnh báo số lượng tài liệu có DB chunks lệch với vector points trong Qdrant.
    4. *Chờ Intake / Rỗng (Pending Intake)*: Đếm số tài liệu chưa được nạp hoặc 0 chunks.
  * **Sub-tab 1: Bảng Kiểm Kê Danh Mục Parity**:
    - Ô tìm kiếm tức thì theo tên văn bản, document ID hoặc binding ID.
    - Bộ lọc trạng thái: Tất cả, Khớp chuẩn, Lệch vector, Chờ intake.
    - Bảng chi tiết: Tên tài liệu, DB Chunks, Qdrant Points (in đậm màu cam nếu lệch), Huy hiệu phân loại, Chi tiết lý do và Nút "Chi tiết" chuyển sang trang `BindingDetailPage`.
  * **Sub-tab 2: Trình Thử Nghiệm Shadow Retrieval Test**:
    - Ô nhập câu hỏi thử nghiệm tùy ý hoặc 3 chip câu hỏi mẫu về quy chế tuyển sinh, học phí, điều kiện tốt nghiệp.
    - Bộ chọn `top_k` (3, 5, 10) và nút thực thi có spinner `shadowMutation`.
    - Thẻ An Toàn Tuyệt Đối: **"XÁC NHẬN AN TOÀN TUYỆT ĐỐI — ZERO REVISION LEAK"** nếu `retrieval_revision_leak_total === 0` và `!leak_detected`.
    - 3 Cards chỉ số: Độ trễ V1 vs V2 kèm % chênh lệch delta, Điểm tương đồng Jaccard và Số kết quả overlap.
    - Bảng so khớp 2 cột trực quan: Cột V1 Legacy vs Cột V2 Snapshot Isolation với danh sách chunk IDs.
  * **Dialog Di Trú Dữ Liệu An Toàn (Backfill to V2)**:
    - Giải thích rõ cơ chế Idempotent & Safe (không xóa dữ liệu phục vụ).
    - Lựa chọn chiến lược phân đoạn: `ClauseBasedChunker` (chuẩn NĐ 30 & Quy chế ĐH Quy Nhơn), `SemanticChunker`, `RecursiveCharacterChunker`.
    - Switch tùy chọn `force_rebuild` và hiển thị tóm tắt kết quả sau khi hoàn tất.

#### 2.4. Tích Hợp Vào `CollectionDetailPage`
- **Tệp**: [`frontend/src/features/knowledge/collection-detail-page.tsx`](../../frontend/src/features/knowledge/collection-detail-page.tsx).
- Cập nhật kiểu `CollectionDetailTab` trong [`frontend/src/components/knowledge/types.ts`](../../frontend/src/components/knowledge/types.ts) bổ sung tab `"audit"`.
- Cập nhật handler `handleOpenReconcile` trên Header: khi người dùng nhấn nút "Đối Soát", hệ thống tự động chuyển mượt sang Tab "Đối Soát & Canary V2".
- Bổ sung `TabsTrigger` cho `"audit"` (icon `ShieldCheck`) và `TabsContent` render component `CollectionParityAuditTab`.

---

### 3. Kết Quả Kiểm Định Chất Lượng (Quality Gate)

| Bộ Kiểm Tra | Mục Tiêu | Kết Quả | Ghi Chú |
|---|---|:---:|---|
| **Backend Pytest** | [`tests/test_publishing_v2_e2e_canary.py`](../../backend/tests/test_publishing_v2_e2e_canary.py) | **9/9 PASSED (100%)** | Bao gồm `test_legacy_audit_and_classification`, `test_idempotent_legacy_backfill`, `test_shadow_retrieval_zero_leak_and_latency` |
| **Backend Ruff Linter** | `ruff check app tests` | **0 Lỗi (100%)** | `All checks passed!` |
| **Frontend Biome Linter** | `biome check src/types/ src/services/ src/components/ src/features/` | **0 Lỗi, 0 Warning** | 100% chuẩn a11y, format chuẩn |
| **Frontend TypeScript** | `bun x tsc --noEmit` | **0 Lỗi Typecheck** | Exit code 0, 0 lỗi biên dịch |

---

### 4. Bảng Tổng Hợp Tệp Mã Nguồn Đã Thay Đổi / Tạo Mới

| STT | Tệp | Trạng thái | Mô tả |
| :---: | :--- | :---: | :--- |
| 1 | `frontend/src/types/knowledge.ts` | Cập nhật | Bổ sung TypeScript types cho Canary Audit, Backfill và Shadow Retrieval |
| 2 | `frontend/src/services/knowledge-api.ts` | Cập nhật | Bổ sung 3 API methods: `auditCollectionCanary`, `backfillCollectionCanary`, `runShadowRetrievalTest` |
| 3 | `frontend/src/components/knowledge/types.ts` | Cập nhật | Mở rộng kiểu `CollectionDetailTab` thêm tab `"audit"` |
| 4 | `frontend/src/components/knowledge/tabs/collection-parity-audit-tab.tsx` | **Tạo mới** | Giao diện Dashboard Đối soát Parity Gate, Kiểm kê danh mục và Shadow Retrieval Tester |
| 5 | `frontend/src/features/knowledge/collection-detail-page.tsx` | Cập nhật | Tích hợp Tab `"audit"` và kết nối nút Đối soát trên Header |

---

### 5. Kết Luận & Hướng Tiếp Theo
- **Kết luận**: Phiên 10 theo Kế hoạch 11 đã hoàn tất 100%. Nền tảng hiện có đầy đủ bộ công cụ trực quan để cán bộ quản trị kiểm kê tính toàn vẹn Parity Gate, thực hiện di trú an toàn (Idempotent Backfill) và đo lường đối soát trực tiếp Shadow Retrieval với bảo đảm tuyệt đối Zero Revision Leak.
- **Tiến độ tổng thể Kế hoạch 11**: Đã hoàn thành xuất sắc 10/10 phiên (100% mục tiêu kiến trúc và giao diện).
