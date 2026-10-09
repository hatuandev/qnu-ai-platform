# NHẬT KÝ LÀM VIỆC — PHIÊN #293 (2026-10-07)
## Thực Hiện Phiên 8 (Pha 7) Kế Hoạch 11: Hoàn Thành Cutover Sang V2, Đánh Dấu Deprecated Legacy APIs, Dịch Vụ Garbage Collection (GC) Có Bảo Vệ Rollback & Đóng Toàn Bộ Kế Hoạch 11

---

### 1. Thông Tin Phiên Làm Việc
- **Thời gian**: 2026-10-07 21:30 – 22:00 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect
- **Mục tiêu**: Triển khai trọn vẹn **Pha 7 (Cutover & Dọn Dẹp Legacy)** theo [Kế hoạch 11](../../docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và [ADR-011](../../docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md):
  1. Kích hoạt toàn diện Cutover sang V2: Đặt `RAG_REVISION_READ_MODE="revisioned"` làm mặc định hệ thống.
  2. Đánh dấu Deprecated các endpoints cũ (`/upload`, `/reindex`) với chuẩn OpenAPI và HTTP Headers `Deprecation`, `X-API-Deprecation-Warning`.
  3. Xây dựng dịch vụ **Artifact Garbage Collection (GC)** (`KnowledgeArtifactGCService`) với chính sách bảo lưu Rollback window an toàn (bảo lưu active + 2 bản superseded gần nhất).
  4. Cơ chế chặn rollback về revision đã pruned với mã lỗi RFC 7807 `REVISION_ALREADY_PRUNED`.
  5. Mở rộng endpoint `POST /knowledge/collections/{id}/gc` và tích hợp UI nút Dọn Chỉ Mục Cũ (GC) trên `CollectionBindingsTab`.
  6. Xây dựng Sổ tay Vận hành & Runbook Production [`cutover_and_operations_runbook.md`](../../docs/ke_hoach/cutover_and_operations_runbook.md).
  7. Xây dựng test suite `test_publishing_v2_cutover_and_gc.py` và kiểm thử hồi quy 100% Kế hoạch 11 (47/47 passed).

---

### 2. Các Thay Đổi Chi Tiết

#### 2.1. Cấu hình Hệ thống & Strict Revisioned Cutover (`app/core/config.py`, `rag/retriever.py`)
- Cập nhật biến môi trường cốt lõi trong `Settings`:
  * `RAG_REVISION_READ_MODE: str = "revisioned"`: Chuyển hoàn toàn chế độ đọc sang V2 Snapshot Isolation.
  * `KNOWLEDGE_REVISION_WRITES_ENABLED: bool = True`: Chỉ cho phép ghi qua pipeline V2 (Staging Index Build & Atomic Activation).
  * `KNOWLEDGE_GC_RETENTION_REVISIONS: int = 2`: Bảo lưu mặc định 2 bản index revision lịch sử gần nhất cho mỗi tài liệu để rollback tức thì.
- Cập nhật `HybridRetriever.search_with_snapshot`:
  * Khi `RAG_REVISION_READ_MODE == "revisioned"`, hệ thống nghiêm ngặt lọc chunks: nếu Snapshot có danh sách `active_index_revision_ids`, chỉ truy xuất các chunk có `index_revision_id` nằm trong danh sách này. Nếu không có revision active nào, trả về tập rỗng (Zero Leak).

#### 2.2. Deprecation Policy Chuẩn Cho Legacy Endpoints (`knowledge/router.py`)
- Đánh dấu `deprecated=True` trong OpenAPI spec cho các endpoints:
  * `POST /knowledge/collections/{collection_id}/upload`
  * `POST /knowledge/collections/{collection_id}/reindex`
  * `POST /knowledge/documents/{document_id}/reindex`
- Thêm HTTP Response Headers chuẩn RFC:
  * `Deprecation: @2026-10-07`
  * `X-API-Deprecation-Warning: This endpoint is deprecated and scheduled for removal. Please migrate to V2 Document Intake and Knowledge Bindings APIs.` (Sử dụng 100% chuỗi ASCII chuẩn để tránh lỗi `UnicodeEncodeError` của HTTP server).

#### 2.3. Dịch Vụ Garbage Collection (GC) Có Bảo Vệ Rollback (`knowledge/services/gc_service.py`, `schemas.py`)
- Khai báo DTOs:
  * `GarbageCollectionRequest`: `retention_revisions: int = 2`, `dry_run: bool = False`.
  * `GarbageCollectionReport`: `collection_id`, `dry_run`, `retention_window`, `revisions_inspected`, `revisions_pruned`, `chunks_deleted`, `facts_deleted`, `vector_points_deleted`, `pruned_revision_ids`.
- Triển khai `KnowledgeArtifactGCService.collect_garbage`:
  * Nhóm các index revisions theo từng binding.
  * Phân loại:
    - Bắt buộc bảo vệ: Revision đang `active` và $N$ bản `superseded` mới nhất (xếp theo `created_at desc`).
    - Đối tượng cần dọn: Các bản `superseded` cũ nằm ngoài retention window, cùng toàn bộ các bản `failed` hoặc `cancelled`.
  * Khi `dry_run=True`: Trả về dự báo số lượng bản ghi và vector points sẽ bị xóa mà không tác động DB.
  * Khi thực thi thật (`dry_run=False`):
    - Chuyển `status = "pruned"` trên bảng `knowledge_index_revisions`.
    - Xóa các bản ghi `KnowledgeChunk` và `KnowledgeFact` tương ứng với `index_revision_id`.
    - Gọi Qdrant xóa toàn bộ vector points mang `index_revision_id` tương ứng qua `delete_points_by_index_revision`.
    - Ghi log JSON có cấu trúc phục vụ kiểm toán hệ thống.

#### 2.4. Xóa Vector Points Theo Revision Trên Qdrant (`rag/vector_indexer.py`)
- Bổ sung hàm `delete_points_by_index_revision(collection_id, index_revision_id) -> int`:
  * Sử dụng Qdrant Filter: `Must(FieldCondition(key="index_revision_id", match=MatchValue(value=str(index_revision_id))))`.
  * Đếm số points trước khi xóa và thực hiện lệnh `delete` an toàn theo batch.

#### 2.5. Cơ Chế Chặn Rollback Bản Đã Bị Dọn (`knowledge/services/index_build_service.py`)
- Cập nhật `IndexBuildService.rollback_index_revision`:
  * Kiểm tra nếu target revision có `status == "pruned"`, lập tức ngắt lệnh và ném exception `AppException(status_code=400, code="REVISION_ALREADY_PRUNED", message="Cannot rollback to revision that has already been pruned by garbage collection.")`.
  * Nếu target revision có `status == "superseded"` (vẫn còn trong retention window), cho phép hoán đổi con trỏ nguyên tử $O(1)$ khôi phục lại trạng thái `active`.

#### 2.6. Mở Rộng Facade, Router & Giao Diện Quản Trị Frontend
- Backend Router: Bổ sung endpoint `POST /knowledge/collections/{collection_id}/gc` gọi qua `KnowledgeService.collect_garbage`.
- Frontend Types (`frontend/src/types/knowledge.ts`): Bổ sung `GarbageCollectionRequest`, `GarbageCollectionReport`.
- Frontend API Client (`frontend/src/services/knowledge-api.ts`): Bổ sung hàm `runGarbageCollection(collectionId, params)`.
- Frontend UI (`frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx`):
  * Thêm nút "Dọn Chỉ Mục Cũ (GC)" (icon `Trash2`, outline button) trên Action Toolbar.
  * Thêm Dialog xác nhận "Dọn dẹp chỉ mục cũ (Garbage Collection)": hiển thị cảnh báo an toàn, giải thích rõ cơ chế bảo lưu 2 bản rollback gần nhất và cho phép chạy Thử nghiệm (Dry Run) hoặc Xóa thật.

#### 2.7. Ban Hành Sổ Tay Vận Hành & Runbook Production (`docs/ke_hoach/cutover_and_operations_runbook.md`)
- Ban hành tài liệu vận hành chi tiết bao gồm:
  1. Kiến trúc tổng quan Cutover V2.
  2. Bảng ma trận Feature Flags & Kill Switches.
  3. Quy trình Cutover từ V1 sang V2 không gián đoạn dịch vụ.
  4. Sổ tay vận hành hàng ngày (Giám sát Observability, SLIs/SLOs, Parity Mismatch, Outbox Backlog).
  5. Quy trình xử lý sự cố khẩn cấp (Emergency Runbook: Rollback $O(1)$, Kích hoạt Kill Switch fallback).
  6. Quy trình bảo trì & dọn dẹp định kỳ (Artifact GC cron schedule).

---

### 3. Kết Quả Kiểm Thử Toàn Diện (Quality Gate)

#### 3.1. Test Suite Pha 7 Mới (`test_publishing_v2_cutover_and_gc.py`)
- `test_cutover_read_mode_revisioned_zero_leak`: PASSED (Đảm bảo snapshot filter loại bỏ 100% revision không active).
- `test_legacy_endpoints_deprecation_headers`: PASSED (Kiểm tra OpenAPI `deprecated=True` và HTTP response headers).
- `test_garbage_collection_dry_run`: PASSED (Dự báo chính xác số lượng revision/chunks/vectors cần dọn).
- `test_garbage_collection_execution_pruning`: PASSED (Xóa sạch DB chunks/facts, xóa Qdrant points, đổi status pruned).
- `test_rollback_protection_allowed_within_retention`: PASSED (Rollback thành công $O(1)$ về bản superseded còn lưu).
- `test_rollback_protection_blocked_for_pruned_revision`: PASSED (Chặn đứng rollback về bản pruned với mã `REVISION_ALREADY_PRUNED`).
- `test_gc_api_endpoint`: PASSED (Endpoint REST API `/gc` phản hồi chuẩn HTTP 200).
- **Kết quả: 7/7 tests PASSED 100% trong 3.95s**.

#### 3.2. Kiểm Thử Hồi Quy Toàn Bộ Kế Hoạch 11
- `test_document_revisions_schema.py`: 9 passed
- `test_document_revisions_lifecycle.py`: 7 passed
- `test_knowledge_publishing_v2.py`: 6 passed
- `test_retrieval_engine_v2.py`: 9 passed
- `test_publishing_v2_e2e_canary.py`: 9 passed
- `test_publishing_v2_cutover_and_gc.py`: 7 passed
- **Tổng cộng: 47/47 tests PASSED 100%**.

#### 3.3. Kiểm Tra Mã Nguồn (Linter)
- Ruff Linter Backend: `All checks passed! (0 errors)`.
- HTTP Headers Encoding: 100% ASCII compliance, triệt tiêu lỗi `UnicodeEncodeError`.

---

### 4. Tổng Kết Toàn Diện Kế Hoạch 11
Sau 8 phiên làm việc chuyên sâu liên tục (từ Phiên 1 #286 đến Phiên 8 #293), dự án **QNU AI Platform** đã hoàn thành xuất sắc 100% các mục tiêu kiến trúc của **Kế hoạch 11 ("Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn")** và tuân thủ tuyệt đối 10 Bất biến cốt lõi của **ADR-011**:

| Pha | Phiên | Nội Dung Triển Khai | Trạng Thái |
|---|---|---|---|
| **Pha 0** | #286 | Chốt ADR-011, Inventory Map 9 Tables/12 Endpoints & API Contracts V2 | **100% Hoàn Thành** |
| **Pha 1** | #287 | Schema CSDL `document_revisions`, Migration Safe Backfill & DTOs V2 | **100% Hoàn Thành** |
| **Pha 2** | #288 | Async Intake Service (202 Accepted), Quality Gate Engine & Revision Service | **100% Hoàn Thành** |
| **Pha 3** | #289 | Schema Knowledge Bindings, Staging Index Build & Parity Gate Zero-Downtime | **100% Hoàn Thành** |
| **Pha 4** | #290 | Retrieval Engine V2, RetrievalSnapshot Pinning (Bất biến 7) & Auditable Citations | **100% Hoàn Thành** |
| **Pha 5** | #291 | Giao diện Quản trị Frontend Revisions & Knowledge Bindings V2 (Biome & Build 0 lỗi) | **100% Hoàn Thành** |
| **Pha 6** | #292 | Legacy Data Backfill, Shadow Retrieval Verification & Bộ Kiểm thử E2E Canary | **100% Hoàn Thành** |
| **Pha 7** | #293 | Cutover V2, Deprecated Legacy APIs, Garbage Collection Service & Runbook Vận Hành | **100% Hoàn Thành** |

---

### 5. Cam Kết Bất Biến & Bài Học Vận Hành
1. **Triệt tiêu 100% "Delete-Before-Index"**: Mọi tài liệu cập nhật đều được dựng chỉ mục trong vùng đệm staging; chatbot chỉ phục vụ bản mới sau khi vượt qua Parity Gate 100% và hoán đổi con trỏ nguyên tử (Atomic Pointer Swap).
2. **Khả năng Rollback Tức Thì trong $O(1)$**: Người dùng có thể quay lại phiên bản trước đó trong nháy mắt mà không cần nạp lại tài liệu hay tính toán lại vector embedding.
3. **An toàn Bộ nhớ & Chi phí Hạ tầng**: Dịch vụ Artifact GC định kỳ dọn sạch vector và chunks dư thừa nhưng vẫn giữ vững cửa sổ an toàn (retention window) cho các tình huống khẩn cấp.
