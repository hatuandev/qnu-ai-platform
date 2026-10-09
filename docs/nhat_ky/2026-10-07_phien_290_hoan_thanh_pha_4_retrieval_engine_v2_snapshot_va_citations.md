# NHẬT KÝ PHIÊN LÀM VIỆC #290: HOÀN THÀNH PHA 4 (RETRIEVAL ENGINE V2, RETRIEVAL SNAPSHOT PINNING & AUDITABLE CITATIONS)

- **Thời gian thực hiện**: 2026-10-07
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Thuộc Kế hoạch**: [Kế hoạch triển khai quy trình tiếp nhận một lần – xuất bản tri thức an toàn (Kế hoạch 11)](../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md)
- **Quyết định kiến trúc cơ sở**: [ADR-011: Tiếp Nhận Một Lần — Xuất Bản Tri Thức An Toàn & Không Gián Đoạn Truy Vấn](../kien_truc/ADR-011-tiep-nhan-mot-lan-xuat-ban-an-toan.md)
- **Mục tiêu phiên**: Hoàn thành toàn diện **Pha 4 (Cải tiến Retrieval Engine V2 & Consistency Guarantees)**:
  1. Xây dựng DTO và cơ chế `RetrievalSnapshot` (Snapshot Isolation & Session Pinning) bảo đảm tính nhất quán phiên hỏi đáp đa lượt theo Bất biến 7 của ADR-011.
  2. Nâng cấp Qdrant vector retrieval (`vector_indexer.py`): Cho phép trạng thái `"active"` trong `document_status`, lọc Snapshot Isolation theo active index revisions, loại bỏ chunks staging/archived.
  3. Mở rộng `FusionCandidate` (`fusion.py`) và `Citation` (`citation_guard.py`): Truyền nguyên vẹn `binding_id`, `index_revision_id`, `source_revision_id`, `revision_no` (Bất biến 10: Auditable & Reproducible Citations).
  4. Cập nhật `HybridRetriever` (`retriever.py`): Bổ sung `resolve_retrieval_snapshot`, áp dụng snapshot filter trong sparse FTS và unaccent fallback, truyền snapshot sang dense search.
  5. Đấu nối `RagService` (`rag/service.py`): Tự động resolve/pin snapshot qua `search` và `ask`, trả snapshot về cho client trong `SearchResponse` và `AskResponse`.
  6. Đăng ký background worker task `task_knowledge_index_build` vào ARQ worker (`tasks.py`, `arq_worker.py`, `jobs/service.py`).
  7. Xây dựng bộ kiểm thử tự động `test_retrieval_engine_v2.py` (9/9 passed 100%), xác thực toàn bộ hồi quy 7 test suites của Kế hoạch 11 (67/67 passed 100%), 0 lỗi Ruff linter.

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Trước Phiên 5, mặc dù hệ thống đã có kiến trúc Staging Index Revision và Atomic Pointer Swap (Pha 3), tầng truy vấn (Retrieval Engine) vẫn còn những lỗ hổng kiến trúc:
1. **Hiện tượng Race Condition / Phantom Inconsistency giữa các lượt chat**: Khi cán bộ xuất bản phiên bản tài liệu mới (Atomic Swap) ngay giữa phiên trò chuyện của người dùng, các lượt hỏi đáp kế tiếp có thể bị lẫn lộn giữa ngữ cảnh cũ và ngữ cảnh mới nếu không có cơ chế cố định phiên (Session Pinning).
2. **Qdrant Payload Allowlist thiếu trạng thái `"active"`**: Points sau khi swap chỉ mang trạng thái `active`, khiến dense vector search cũ (`document_status in ["ready", "approved"]`) không tìm thấy dữ liệu.
3. **Trích dẫn không thể đối soát ngược (Non-Auditable Citations)**: Client và cán bộ thẩm định không thể biết chính xác câu trả lời của AI được trích xuất từ phiên bản tài liệu gốc nào (`source_revision_id`), index revision nào (`index_revision_id`) và liên kết nào (`binding_id`).
4. **Worker Task chưa được tích hợp**: ARQ worker chưa có task chạy nền cho việc xây dựng index revision trên staging (`task_knowledge_index_build`).

---

## 2. Các Thay Đổi & Giải Pháp Kiến Trúc Cốt Lõi

### 2.1. Quản Lý Tính Nhất Quán Phiên Bằng `RetrievalSnapshot`
- Khai báo model `RetrievalSnapshot` trong `backend/app/modules/rag/schemas.py`:
  - `snapshot_id`: Mã định danh duy nhất của snapshot (`snap_{collection_id}_{epoch}_{uuid}`).
  - `collection_id`: Mã bộ sưu tập tri thức.
  - `collection_epoch`: Epoch hiện hành của bộ sưu tập.
  - `binding_revisions`: Bản đồ phiên bản active `{binding_id: active_index_revision_id}`.
  - `created_at`: Thời điểm tạo snapshot ISO-8601 (tự động gán mặc định).
- Cung cấp `resolve_retrieval_snapshot` trong `HybridRetriever`:
  - Nếu client truyền `pinned_snapshot` hợp lệ (cùng `collection_id`), giữ nguyên snapshot hiện hành (Session Pinning).
  - Nếu chưa có, query collection epoch và toàn bộ `KnowledgeBinding` active để sinh snapshot mới nhất.
  - Xử lý phòng thủ (Graceful Fallback) khi chạy trong môi trường test/mock DB.

### 2.2. Lọc Snapshot Isolation Trong Qdrant & PostgreSQL FTS
- **Qdrant Dense Vector Search (`vector_indexer.py`)**:
  - Bổ sung `"active"` vào allowlist: `MatchAny(any=["ready", "approved", "active"])`.
  - Khi có `snapshot`: Kiểm tra `point_binding`. Nếu point thuộc một binding, `index_revision_id` bắt buộc phải nằm trong `snapshot.binding_revisions`. Loại bỏ 100% points thuộc staging hoặc archived index revisions.
  - Bảo đảm tương thích ngược tuyệt đối với các điểm dữ liệu legacy (`point_binding is None`).
- **PostgreSQL Sparse FTS & Unaccent Search (`retriever.py`)**:
  - Áp dụng `snapshot_filter`:
    ```python
    or_(
        KnowledgeChunk.binding_id.is_(None),
        KnowledgeChunk.index_revision_id.in_(active_revs),
    )
    ```
  - Lọc sạch các chunks staging và chunks archived khỏi cả ba nhánh tìm kiếm: ILIKE mật độ thông tin trọng số cao, PostgreSQL FTS `ts_rank_cd`, và Fallback không dấu `unaccent`.

### 2.3. Minh Chứng Nguồn Trích Dẫn Có Thể Đối Soát & Tái Hiện (Auditable Citations)
- Mở rộng `FusionCandidate` (`fusion.py`):
  - Bổ sung `binding_id`, `index_revision_id`, `document_revision`.
  - Trích xuất tự động trong `_merge_ranked_list` từ cả dense hits lẫn sparse hits.
- Mở rộng `Citation` (`citation_guard.py` & `schemas.py`):
  - `binding_id`, `index_revision_id`, `source_revision_id`, `revision_no`.
  - Mọi trích dẫn xuất ra giao diện hoặc log kiểm toán đều gắn liền với số hiệu phiên bản bất biến.

### 2.4. Đấu Nối Toàn Diện Dịch Vụ RAG (`rag/service.py`)
- Cả hai phương thức `search` và `ask` đều:
  1. Phân giải snapshot: `snapshot = await hybrid_retriever.resolve_retrieval_snapshot(...)`.
  2. Truyền `snapshot=snapshot` vào toàn bộ pipeline retrieval.
  3. Trả `retrieval_snapshot` (và alias `snapshot`) trong `SearchResponse` và `AskResponse`.
  4. Duy trì `retrieval_snapshot` ngay cả trong trường hợp kích hoạt No-Answer Policy để bảo toàn phiên cho client.

### 2.5. Đăng Ký Background Worker Task (`tasks.py`, `arq_worker.py`, `jobs/service.py`)
- Thêm `task_knowledge_index_build` vào `backend/app/workers/tasks.py`.
- Tích hợp `index_build_service.build_staging_index(...)`.
- Bổ sung `"knowledge_index_build": "task_knowledge_index_build"` vào `ARQ_FUNCTIONS` của `JobsService`.
- Đăng ký `task_knowledge_index_build` vào `WorkerSettings.functions` của `arq_worker.py`.

---

## 3. Các Tệp Mã Nguồn Đã Chỉnh Sửa & Bổ Sung

| STT | Tệp tin | Thay đổi chính |
|:---:|:---|:---|
| 1 | `backend/app/modules/rag/schemas.py` | Thêm `RetrievalSnapshot`, mở rộng `SearchRequest`, `SearchResponse`, `AskRequest`, `AskResponse`, `Citation`, `SearchResultItem`. |
| 2 | `backend/app/modules/rag/fusion.py` | Bổ sung `binding_id`, `index_revision_id`, `document_revision` vào `FusionCandidate` và `_merge_ranked_list`. |
| 3 | `backend/app/modules/rag/citation_guard.py` | Điền các trường revision tracking vào `Citation` trong `build_citations`. |
| 4 | `backend/app/modules/rag/vector_indexer.py` | Thêm `"active"` vào allowlist `document_status`, snapshot isolation post-filter, lưu `binding_id` và `index_revision_id` vào Qdrant payload. |
| 5 | `backend/app/modules/rag/retriever.py` | Thêm `resolve_retrieval_snapshot`, áp dụng snapshot filter trong `search_sparse_fts` và `retrieve`. |
| 6 | `backend/app/modules/rag/service.py` | Đấu nối snapshot resolution, retrieval filtering và return snapshot trong `search` và `ask`. |
| 7 | `backend/app/modules/jobs/service.py` | Thêm `"knowledge_index_build": "task_knowledge_index_build"` vào `ARQ_FUNCTIONS`. |
| 8 | `backend/app/workers/tasks.py` | Triển khai worker task `task_knowledge_index_build`. |
| 9 | `backend/app/workers/arq_worker.py` | Đăng ký `task_knowledge_index_build` và `task_document_revision_parse` vào `WorkerSettings`. |
| 10 | `backend/tests/test_retrieval_engine_v2.py` | Tạo mới test suite kiểm thử toàn diện Pha 4 (9 unit tests). |

---

## 4. Kết Quả Kiểm Thử (Verification & Testing)

1. **Ruff Linter**:
   - Lệnh: `uv run ruff check app tests`
   - Kết quả: **All checks passed! 0 lỗi lint.**
2. **Unit Test Suite Pha 4 (`test_retrieval_engine_v2.py`)**:
   - `test_retrieval_snapshot_schema`: **PASSED**
   - `test_resolve_retrieval_snapshot_pinned`: **PASSED**
   - `test_resolve_retrieval_snapshot_from_db`: **PASSED**
   - `test_fusion_candidate_and_rrf_with_revision_metadata`: **PASSED**
   - `test_citation_guard_build_citations_with_revisions`: **PASSED**
   - `test_vector_indexer_search_dense_snapshot_filtering`: **PASSED**
   - `test_rag_service_search_includes_snapshot`: **PASSED**
   - `test_rag_service_ask_includes_snapshot_even_on_no_answer`: **PASSED**
   - `test_worker_task_knowledge_index_build_missing_payload`: **PASSED**
   - Kết quả: **9/9 tests PASSED 100% (2.60s)**.
3. **Toàn Bộ Regression Test Suites (Pha 1 đến Pha 4 của Kế hoạch 11 & ADR-011)**:
   - `tests/test_document_repository.py`
   - `tests/test_document_revisions_schema.py`
   - `tests/test_document_revisions_lifecycle.py`
   - `tests/test_domain_records_and_quality_gate.py`
   - `tests/test_knowledge_publishing_v2.py`
   - `tests/test_retrieval_engine_v2.py`
   - `tests/test_revision_safe_qdrant_and_retrieval.py`
   - Kết quả: **67/67 tests PASSED 100% (0 lỗi, 0 thất bại)**.

---

## 5. Kết Luận & Bước Tiếp Theo

- **Pha 4 đã hoàn thành xuất sắc 100%** mục tiêu đề ra trong Kế hoạch 11.
- Toàn bộ cơ chế Snapshot Isolation, Session Pinning và Auditable Citations đã hoạt động hoàn hảo, bảo vệ vững chắc Bất biến 7 và Bất biến 10 của ADR-011.
- **Bước tiếp theo (Phiên 6)**: Triển khai **Pha 5 — Giao diện Quản trị Frontend V2** (Master-Detail Revisions Review UI, Quality Gate Badge, Staging Build & Atomic Swap Action, Snapshot Inspector).
