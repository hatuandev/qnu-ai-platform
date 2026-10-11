# NHẬT KÝ LÀM VIỆC — PHIÊN #334
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Ngày thực hiện**: 2026-10-11  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Thực Hiện Phiên 7 Kế Hoạch 12 — Frontend Kho Tri Thức Hoàn Chỉnh (Ingestion Hub UI, Bulk Candidate Selection 100+ Tệp, Multi-Vector Generation Selector, Realtime Import Batch Tracker & Source Detail Lifecycle Theo Chuẩn ADR-012)

---

### 1. Bối Cảnh & Yêu Cầu Kỹ Thuật (Phiên 7 / Kế Hoạch 12)
- Tiếp nối lộ trình 8 phiên của Kế hoạch 12 và quyết định kiến trúc ADR-012:
  - **Phiên 6** đã tinh gọn hoàn toàn Frontend Kho tài liệu thành Storage Vault thuần túy (loại bỏ UI bóc tách, reparse, markdown, quality gate và gỡ bỏ nút/dialog đẩy một chiều sang Knowledge).
  - **Phiên 7 (Phiên này)**: Hiện thực hóa giao diện Kho tri thức hoàn chỉnh, làm chủ toàn bộ vòng đời nạp tri thức và đa vector:
    1. **Bổ sung Types & API Client V3**: Đồng bộ 100% schema backend V3 sang Frontend TypeScript:
       - `CandidateGroupItem`, `RepositoryCandidateItem`, `CandidateListResponse`.
       - `KnowledgeImportBatchCreateRequest`, `KnowledgeImportItemResponse`, `KnowledgeImportBatchResponse`.
       - `KnowledgeSourceDetailResponse`, `KnowledgeSourceRevisionResponse`.
       - `KnowledgeVectorGenerationResponse`, `CreateVectorGenerationRequest`, `BuildVectorGenerationResponse`, `ActivateVectorGenerationResponse`.
       - `KnowledgeChunkSetResponse`.
    2. **Tái thiết kế Trang Nạp Tài Liệu (`AddDocumentsPage` tại `/knowledge/:collectionId/add-documents`)**:
       - Duyệt tài liệu ứng viên từ API `getCandidateDocuments` và `getCandidateGroups`.
       - Hiển thị trực quan **trạng thái 2 chiều (2-Dimensional Status Badges)**:
         + `source_state`: `not_imported` ("Chưa nạp"), `current` ("Đã nạp"), `update_available` ("Có bản mới"), `processing` ("Đang nạp"), `failed` ("Lỗi nạp").
         + `vector_state`: `not_indexed` ("Chưa index"), `indexed` ("Đã index"), `indexing` ("Đang index"), `index_failed` ("Lỗi index").
       - Công cụ chọn hàng loạt (Bulk Selection 100+ files): Nút tiện ích "Chọn chưa nạp", Checkbox header chọn tất cả, Checkbox Radix UI từng dòng.
       - Panel Cấu hình Nạp:
         + Chọn Thế hệ Vector đích (`listVectorGenerations`, tự động highlight generation active).
         + Chọn Cấu hình bóc tách OCR (`standard`, `vision_ocr`, `layout_analysis`).
         + Chọn Chiến lược phân đoạn (`ClauseBasedChunker`, `SemanticChunker`, `FixedSizeChunker`).
       - Sticky Bottom Action Bar: Hiển thị số lượng tài liệu đã chọn, nút "Bỏ chọn" và nút "Nạp X Tài Liệu Vào Kho Tri Thức".
    3. **Component Theo Dõi Đợt Nạp (`ImportBatchModal`)**:
       - Tự động poll trạng thái đợt nạp qua `getImportBatch(collectionId, batchId)`.
       - Hiển thị thanh tiến trình hoàn thành (`Progress`), thống kê đếm (Tổng số, Đang xử lý, Thành công, Lỗi, Cần duyệt).
       - Bảng danh sách tài liệu con với trạng thái và nút "Thử lại các mục lỗi" (`retryFailedImportItems`), nút "Hủy đợt nạp" (`cancelImportBatch`).
    4. **Tái thiết kế Trang Chi Tiết Nguồn Tri Thức (`SourceDetailPage` tại `/knowledge/:collectionId/sources/:sourceId`)**:
       - Đọc dữ liệu từ `getKnowledgeSource` và `listSourceChunkSets`.
       - Snapshot provenance: Tệp gốc, mã băm SHA-256, revision hiện hành.
       - 4 Tabs chuyên sâu:
         + `content`: Xem trước Markdown chuẩn đã bóc tách, hỗ trợ chế độ "Hiệu đính Markdown" và lưu thay đổi (`updateSourceRevisionContent`).
         + `quality`: Báo cáo đánh giá chất lượng Quality Gate, điểm số, danh sách vi phạm cấu trúc, modal phê duyệt/từ chối thủ công (`reviewSourceRevision`).
         + `chunks`: Danh sách các tập đoạn cắt (`KnowledgeChunkSet`) độc lập (Parse once, Chunk once, Embed many).
         + `revisions`: Lịch sử các bản sửa đổi bóc tách nội dung.

---

### 2. Các Tệp Đã Thay Đổi & Tạo Mới

1. **`frontend/src/types/knowledge.ts`**:
   - Bổ sung toàn bộ các DTOs V3: Candidate Groups/Documents, Import Batches/Items, Source Detail/Revisions, Chunk Sets và Vector Generations.

2. **`frontend/src/services/knowledge-api.ts`**:
   - Bổ sung 15 API client methods:
     - `getCandidateGroups`, `getCandidateDocuments`.
     - `createImportBatch`, `getImportBatch`, `retryFailedImportItems`, `cancelImportBatch`.
     - `getKnowledgeSource`, `listSourceRevisions`, `updateSourceRevisionContent`, `reviewSourceRevision`.
     - `listVectorGenerations`, `createVectorGeneration`, `buildVectorGeneration`, `activateVectorGeneration`.
     - `listSourceChunkSets`.

3. **`frontend/src/features/knowledge/components/import-batch-modal.tsx`** (Tạo mới):
   - Modal theo dõi tiến trình đợt nạp độc lập: polling realtime, Progress bar, KPI counters, danh sách tài liệu con, nút thử lại lỗi và hủy đợt nạp.

4. **`frontend/src/features/knowledge/add-documents-page.tsx`**:
   - Tái cấu trúc thành Ingestion Hub: Lọc theo nhóm, lọc trạng thái nguồn, tìm kiếm từ khóa, hiển thị badge 2 chiều, bulk selection 100+ tệp, cấu hình pipeline (Vector generation, OCR profile, Chunker) và Sticky Action Bar ở đáy.

5. **`frontend/src/features/knowledge/source-detail-page.tsx`**:
   - Tái thiết kế thành trang chi tiết nguồn tri thức theo ADR-012: Hiển thị snapshot provenance, tab Markdown chuẩn kèm editor hiệu đính, tab Quality Gate kèm kiểm duyệt thủ công, tab Chunk Sets và tab Lịch sử revisions.

---

### 3. Kết Quả Kiểm Thử & Quality Gate

1. **Backend**:
   - `uv run ruff check .`: **All checks passed!** (0 cảnh báo, 0 lỗi).
   - `pytest tests/test_knowledge_candidate_and_import_batch.py tests/test_knowledge_source_ingestion.py tests/test_knowledge_chunk_set_and_vector_generation.py -v`: **18/18 tests passed** (100%).
   - `pytest tests/test_knowledge_v3_schema.py -v`: **7/7 tests passed** (100%).

2. **Frontend**:
   - `npm run build` (`vite build && tsc --noEmit`): **Exit code 0** (0 lỗi TypeScript, 0 lỗi biên dịch, bundle đóng gói hoàn tất trong 2.98s).

---

### 4. Bài Học Rút Ra & Bước Tiếp Theo
- **Trải nghiệm nạp tri thức nhất quán**: Với trạng thái 2 chiều (Nguồn & Vector), cán bộ quản trị nhìn vào là biết ngay tài liệu nào đã có, tài liệu nào cần cập nhật bản mới và tài liệu nào chưa được lập chỉ mục vector trên model mục tiêu.
- **Parse once, chunk once, embed many được trực quan hóa đầy đủ**: Người dùng thấy rõ các chunk sets được lưu cố định và có thể chọn nạp vào bất kỳ thế hệ vector nào mà không tốn công bóc tách hay OCR lại.
- Sẵn sàng tiến hành **Phiên 8 Kế Hoạch 12**: Backfill nguồn đã publish sang `knowledge_source_revisions`, cutover workers/API và dọn dẹp các trường legacy.
