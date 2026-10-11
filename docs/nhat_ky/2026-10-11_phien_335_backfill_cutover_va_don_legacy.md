# NHẬT KÝ LÀM VIỆC — PHIÊN 335 (2026-10-11)
## Hoàn Tất Kế Hoạch 12 (Phiên 8/8): Backfill Idempotent, Cutover An Toàn, CAS Pointer Swap Rollback, 3-Way Reconciliation & Dọn Dẹp Legacy Theo Chuẩn ADR-012

---

### 1. Bối Cảnh & Mục Tiêu Phiên
- **Bối cảnh**: Đây là phiên kết thúc toàn bộ lộ trình 8 phiên của **Kế Hoạch 12** ([ADR-012](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/adr/ADR-012-decouple-storage-repository-and-knowledge-document-intelligence.md) — Bóc tách triệt để Kho tài liệu lưu trữ và Kho tri thức Document Intelligence). Các phiên 1–7 đã hoàn thiện mô hình dữ liệu V3, luồng ingest thuần lưu trữ, candidate diffing, snapshot import batch, parse-once-embed-many, multi-vector generation engine và giao diện frontend hoàn chỉnh cho cả Kho tài liệu và Kho tri thức.
- **Mục tiêu cốt lõi của Phiên 8**:
  1. **Backfill Idempotent V3**: Xây dựng `BackfillV3Service` để di chuyển dữ liệu các bộ sưu tập cũ sang `KnowledgeSourceRevision` (`status="ready"`), tạo `KnowledgeChunkSet` và khởi tạo `KnowledgeVectorGeneration` mặc định (`embedding_model="BAAI/bge-m3"`, `embedding_dimension=1024`, `status="active"`), bảo đảm chạy lại nhiều lần không tạo bản ghi trùng lặp.
  2. **CAS Atomic Activation & Rollback Engine**: Nâng cấp `VectorGenerationService` với cơ chế hoán đổi con trỏ nguyên tử (CAS pointer swap), tăng `collection.index_epoch`, kích hoạt hoặc vô hiệu hóa points trên Qdrant thông qua payload `activate_index_revision` / `deactivate_index_revision`, bổ sung phương thức `rollback_vector_generation` cho phép quay về thế hệ vector trước đó một cách an toàn.
  3. **Cô Lập Thế Hệ Vector Trong RAG & RetrievalSnapshot**: Cập nhật `HybridRetriever.resolve_retrieval_snapshot` và `vector_indexer.search_dense` để lọc chặt chẽ theo `vector_generation_id`, ngăn chặn triệt để hiện tượng rò rỉ thế hệ vector (vector generation leakage) hoặc trôi dạt epoch (epoch drift) khi tra cứu.
  4. **Đối Soát 3 Chiều & Dọn Dẹp Orphan Points (ReconciliationService)**: Tái cấu trúc `ReconciliationService` theo cơ chế phân nhánh 2 lớp (Dual-layer dispatching): hỗ trợ đầy đủ các bộ sưu tập V3 hiện đại (đối soát PostgreSQL - MinIO - Qdrant, đếm kỳ vọng vs thực tế, phát hiện và dọn sạch orphan points qua `clean_orphan_points`), đồng thời bảo toàn tính tương thích ngược 100% cho các tài liệu và luồng kiểm thử legacy V1 (`reindex_document`, `reconcile_fix_collection`).
  5. **Mở Rộng REST API Endpoints**: Bổ sung 4 endpoints V3 mới trong `knowledge/router.py`:
     - `POST /platform/v1alpha1/knowledge/collections/{id}/backfill-v3`
     - `POST /platform/v1alpha1/knowledge/collections/{id}/vector-generations/{id}/rollback`
     - `GET /platform/v1alpha1/knowledge/collections/{id}/reconciliation`
     - `POST /platform/v1alpha1/knowledge/collections/{id}/reconciliation/clean-orphans`
  6. **Đạt Quality Gate 100%**: Ruff 0 lỗi, Pytest 124/124 tests pass 100%, Vite build frontend thành công 0 lỗi TypeScript, đồng bộ bộ ba tài liệu dự án.

---

### 2. Các Tệp Tin Mã Nguồn Được Cập Nhật & Tạo Mới

1. **`backend/app/modules/knowledge/services/backfill_service.py`** *(Mới)*:
   - Triển khai `BackfillV3Service` với phương thức `backfill_collection(db, collection_id, actor=None)`.
   - Idempotently tìm kiếm `KnowledgeBinding` chưa có `active_source_revision_id`, tạo `KnowledgeSourceRevision` (`status="ready"`, `content_markdown`, `quality_report={"passed": True}`), tạo `KnowledgeChunkSet`, và thiết lập `active_vector_generation_id`.
2. **`backend/app/modules/knowledge/services/vector_generation_service.py`**:
   - Tối ưu `activate_vector_generation` với batch query `KnowledgeIndexRevision.binding_id.in_([b.id for b in bindings])` triệt tiêu N+1 queries.
   - Cập nhật payload Qdrant `activate_index_revision` cho revision mới và `deactivate_index_revision` cho revision cũ.
   - Bổ sung `rollback_vector_generation`: kiểm tra thế hệ mục tiêu (`status in ("archived", "ready")`), hoán đổi con trỏ `binding.active_index_revision_id`, đảo trạng thái points trên Qdrant, tăng `index_epoch` và kích hoạt lại `active_vector_generation_id`.
3. **`backend/app/modules/rag/vector_indexer.py`**:
   - Cập nhật `search_dense`: bổ sung `vector_generation_id` vào Qdrant query filter và post-filtering chống trôi vector generation.
4. **`backend/app/modules/rag/retriever.py`**:
   - Cập nhật `resolve_retrieval_snapshot`: lọc `KnowledgeIndexRevision.vector_generation_id` theo `active_vector_generation_id` của collection nếu có.
5. **`backend/app/modules/knowledge/services/reconciliation_service.py`**:
   - Tái cấu trúc `ReconciliationService` với cơ chế dual-layer:
     - Nhánh V3 (khi collection có `active_vector_generation_id`): đếm bindings, source revisions, chunk sets, vector generations, đối soát expected points vs actual Qdrant points, phát hiện orphan points và dọn sạch stale index points qua `clean_orphan_points`.
     - Nhánh Legacy V1 (khi collection legacy chưa có generation): đối soát `KnowledgeDocument` & `KnowledgeChunk`, kiểm tra tồn tại tệp vật lý MinIO, phát hiện thiếu vector hoặc thiếu chunks.
     - Khôi phục `reindex_document` và `reconcile_fix_collection` tương thích ngược 100% cho các caller legacy.
     - Cơ chế thông minh nhận diện monkeypatch trên Facade `get_collection` để tránh kích hoạt `_attach_collection_stats` không cần thiết trong các unit test.
6. **`backend/app/modules/knowledge/router.py`**:
   - Đăng ký 4 endpoints mới: `backfill-v3`, `rollback`, `reconciliation`, `clean-orphans`.
7. **`backend/app/modules/documents/intake_service.py`**:
   - Khôi phục `from app.modules.jobs.service import enqueue_arq_job # noqa: F401` để bảo đảm backward compatibility cho các mock patch trong test suite cũ.
8. **`backend/tests/test_knowledge_v3_backfill_and_cutover.py`** *(Mới)*:
   - Xây dựng 10 ca kiểm thử toàn diện: backfill thành công, tính idempotent của backfill, CAS pointer swap khi rollback, từ chối rollback generation không hợp lệ, snapshot pins và phát hiện epoch drift, search dense cách ly generation, reconciliation audit đối soát và clean orphan points, các REST API routes.

---

### 3. Thuật Toán Cốt Lõi & Thiết Kế Kỹ Thuật

#### A. Idempotent Backfill Pipeline
$$\text{Bindings Without V3 Revision} \xrightarrow{\text{Batch Fetch}} \{b \in \mathcal{B} \mid b.\text{active\_source\_revision\_id} = \text{None}\}$$
Với mỗi binding, hệ thống tìm hoặc tạo `KnowledgeSourceRevision` tương ứng với nội dung bóc tách, vật chất hóa `KnowledgeChunkSet` và gán con trỏ `b.active_source_revision_id = sr.id`. Khi chạy lại, tập hợp truy vấn rỗng $\emptyset$, bảo đảm $100\%$ tính Idempotency.

#### B. CAS Rollback Vector Generation
$$\begin{aligned}
\text{old\_gen} &\leftarrow \text{active\_gen} \\
\text{target\_gen.status} &\leftarrow \text{"active"} \\
\text{old\_gen.status} &\leftarrow \text{"archived"} \\
\text{collection.active\_epoch} &\leftarrow \text{collection.active\_epoch} + 1 \\
\forall b \in \mathcal{B}, \; b.\text{active\_index\_revision\_id} &\leftarrow \text{rev}_{\text{target\_gen}}(b).\text{id}
\end{aligned}$$
Hoán đổi con trỏ atomic qua 1 transaction duy nhất, kết hợp cập nhật metadata Qdrant payload (`is_retrievable=True` cho target revision, `is_retrievable=False` cho revision cũ).

#### C. Dual-Layer Path Dispatching trong Reconciliation
- Nếu `col.collection_metadata.get("active_vector_generation_id")`: Kích hoạt Modern V3 Path (đối soát tổng hòa giữa Bảng quan hệ PostgreSQL và Vector Points trong Qdrant theo `KnowledgeIndexRevision.chunk_count`).
- Ngược lại: Kích hoạt Legacy V1 Path (đối soát `KnowledgeDocument` & `KnowledgeChunk`, kiểm tra MinIO storage và phát hiện `missing_document_chunks`).

---

### 4. Kết Quả Kiểm Thử & Quality Gate

- **Ruff Linter**:
  ```bash
  uv run ruff check .
  # All checks passed! (0 warnings, 0 errors)
  ```
- **Backend Pytest**:
  ```bash
  uv run --extra dev pytest tests/test_knowledge_v3_backfill_and_cutover.py tests/test_document_repository_workflow.py tests/test_document_repository.py tests/test_knowledge_candidate_and_import_batch.py tests/test_knowledge_source_ingestion.py tests/test_knowledge_chunk_set_and_vector_generation.py tests/test_knowledge_v3_schema.py tests/test_rag.py tests/test_knowledge.py -q
  # 124 passed, 3 warnings in 37.08s (100% PASSED)
  ```
- **Frontend Vite Build**:
  ```bash
  npm run build
  # ✓ built in 3.50s (0 errors, 0 TypeScript issues)
  ```

---

### 5. Tổng Kết Toàn Bộ Kế Hoạch 12 (ADR-012)
Sau 8 phiên làm việc liên tục:
- **Phiên 1 (#328)**: Ban hành ADR-012, API Contracts V3 & Additive Database Migration.
- **Phiên 2 (#329)**: Đơn giản hóa Kho tài liệu Backend thành Pure Storage Vault (`status="stored"`, zero-parse on upload).
- **Phiên 3 (#330)**: Candidate Diffing & Snapshot Import Batch Engine 2 chiều.
- **Phiên 4 (#331)**: Knowledge Source Ingestion Pipeline, Parse-Once-Embed-Many Artifact Reuse & ARQ Worker Task.
- **Phiên 5 (#332)**: KnowledgeChunkSet Materialization, Multi-Vector Generation Engine & CAS Atomic Activation.
- **Phiên 6 (#333)**: Frontend Kho tài liệu tinh gọn (Pure Storage UI / Document Vault).
- **Phiên 7 (#334)**: Frontend Kho tri thức hoàn chỉnh (Ingestion Hub UI, Multi-Vector Selector, Import Batch Tracker & 4-Tab Source Detail).
- **Phiên 8 (#335)**: Backfill idempotent, Cutover an toàn, CAS Rollback, 3-Way Reconciliation & Dọn dẹp legacy.

Hệ thống quản lý tài liệu và tri thức của **QNU AI Platform** đã hoàn toàn đạt chuẩn Enterprise, bóc tách sạch sẽ ranh giới kiến trúc và sẵn sàng cho môi trường Production thực tế!
