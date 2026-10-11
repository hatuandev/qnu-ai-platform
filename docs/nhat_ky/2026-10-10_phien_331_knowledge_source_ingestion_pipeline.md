# NHẬT KÝ LÀM VIỆC — PHIÊN #331
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Ngày thực hiện**: 2026-10-10  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Thực Hiện Phiên 4 Kế Hoạch 12 — Di Chuyển Pipeline Bóc Tách Sang Domain Knowledge, Quản Lý Nguồn Tri Thức, Tái Sử Dụng Artifact ("Parse Once, Embed Many") & Tác Vụ Nạp Bất Đồng Bộ ARQ Worker

---

### 1. Bối Cảnh & Yêu Cầu Kỹ Thuật (Phiên 4 / Kế Hoạch 12)
- Theo kiến trúc ADR-012 và lộ trình 8 phiên của Kế hoạch 12:
  - **Phiên 2** đã đưa Kho tài liệu (`RepositoryDocument`, `DocumentRevision`) về thuần lưu trữ (Document Vault, `status="stored"`).
  - **Phiên 3** đã triển khai Candidate Diffing & Import Batch Engine quản lý việc chọn và tạo batch nạp snapshot một chiều.
  - **Phiên 4 (Phiên này)**: Hiện thực hóa việc xử lý từng mục nạp (`KnowledgeImportItem`) trong batch:
    1. Đọc file từ MinIO (`app.core.storage.storage_service`).
    2. Snapshot tệp và metadata sang domain Knowledge (`KnowledgeSourceRevision`).
    3. Di chuyển toàn bộ pipeline: Native Document Parsers (PDF, DOCX, XLSX) / Vision OCR Engine / Vietnamese Normalizer (Unicode NFC) / Quality Gate (`evaluate_revision_quality`) sang service bóc tách tri thức `SourceIngestionService`.
    4. Tối ưu hóa "Parse Once, Embed Many": Lưu trữ và tái sử dụng `artifact_key` (`SHA256(origin_file_hash + ":" + parser_profile + ":v1")`) để chống bóc tách lặp lại cùng một tệp.
    5. Xây dựng ARQ worker task bất đồng bộ `task_knowledge_source_ingestion` hỗ trợ tracking tiến độ, huỷ hợp tác (cooperative cancellation) và tích hợp `JobRecord`.
    6. Mở rộng 4 REST API endpoints quản lý nguồn tri thức: lấy chi tiết nguồn, lịch sử revisions, hiệu đính nội dung markdown thủ công, phê duyệt/từ chối bóc tách.
    7. **Bất biến Zero-Writeback**: Không bao giờ ghi ngược metadata bóc tách (`issued_date`, `document_number`, `parse_status`) sang Kho tài liệu gốc `RepositoryDocument`.

---

### 2. Các Tệp Đã Thay Đổi & Tạo Mới

1. **`backend/app/modules/knowledge/services/source_ingestion_service.py`** (Tạo mới):
   - `SourceIngestionService`:
     - `process_import_item(db, item_id, ocr_engine)`: Điều phối toàn bộ luồng bóc tách nguồn tri thức từ `KnowledgeImportItem`.
     - `get_source(db, collection_id, source_id, ...)`: Truy vấn thực thể nguồn (`KnowledgeBinding`) kèm active revision và lịch sử.
     - `get_source_revisions(db, collection_id, source_id, ...)`: Danh sách revision theo thứ tự `revision_no desc`.
     - `update_revision_content(...)`: Cho phép hiệu đính Markdown và re-evaluate Quality Gate tự động.
     - `review_source_revision(...)`: Cho phép cán bộ phê duyệt thủ công (`approved` -> `ready`, `rejected` -> `failed`).
   - Tối ưu hóa `artifact_key`: Kiểm tra trong DB xem đã có `KnowledgeSourceRevision` nào thành công với cùng `artifact_key` chưa; nếu có thì tái sử dụng trực tiếp `canonical_markdown` và `quality_report` mà không tốn tài nguyên parse/OCR lại.
   - Thống kê tiến độ tự động: Cập nhật `batch.queued_count`, `batch.processing_count`, `batch.completed_count`, `batch.review_required_count`, `batch.failed_count` và trạng thái batch terminal (`completed`, `review_required`, `partial_failed`).

2. **`backend/app/modules/knowledge/schemas.py`**:
   - Bổ sung các DTOs V3:
     - `UpdateSourceContentRequest`: Nhận `content: str` hiệu đính.
     - `ReviewSourceRevisionRequest`: Nhận `decision: "approved" | "rejected"` và `comment`.
     - `KnowledgeSourceDetailResponse`: Trả về thông tin nguồn kèm `active_revision` và `revisions`.

3. **`backend/app/workers/tasks.py`**:
   - Thêm worker task `task_knowledge_source_ingestion(ctx, job_id: str)`:
     - Tích hợp `JobRecord` (`status`, `progress`, `meta_data`).
     - Hỗ trợ kiểm tra hủy tác vụ `is_job_cancelled`.
     - Xử lý từng `item_id` từ `job.meta_data["import_item_ids"]` hoặc `job.meta_data["item_id"]`.
     - Báo cáo lỗi trung thực chuẩn RFC 7807 khi phát sinh ngoại lệ.

4. **`backend/app/workers/arq_worker.py` & `backend/app/modules/jobs/service.py`**:
   - Đăng ký `task_knowledge_source_ingestion` vào danh sách hàm thực thi của ARQ Worker.
   - Đăng ký mapping job type `"knowledge_source_ingestion"` sang hàm ARQ tương ứng trong `ARQ_FUNCTIONS`.

5. **`backend/app/modules/knowledge/router.py`**:
   - Bổ sung 4 endpoints REST API quản lý nguồn tri thức:
     - `GET /collections/{collection_id}/sources/{source_id}`: Chi tiết nguồn và lịch sử revision.
     - `GET /collections/{collection_id}/sources/{source_id}/revisions`: Danh sách lịch sử revision.
     - `PATCH /collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/content`: Hiệu đính nội dung Markdown.
     - `POST /collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/review`: Phê duyệt/Từ chối revision cần duyệt.

6. **`backend/tests/test_knowledge_source_ingestion.py`** (Tạo mới):
   - Xây dựng 6 kịch bản kiểm thử toàn diện:
     - `test_process_import_item_clean_source_ready_and_zero_writeback`: Kiểm tra tài liệu bóc tách sạch đạt `ready`, bảo đảm 100% không ghi ngược sang `RepositoryDocument`.
     - `test_process_import_item_empty_file_fails_honestly`: Kiểm tra tệp rỗng fail trung thực với mã `FILE_CONTENT_EMPTY` và RFC 7807 (Zero Fake Content).
     - `test_process_import_item_artifact_reuse_parse_once_embed_many`: Kiểm tra cơ chế tái sử dụng `artifact_key` bỏ qua bóc tách lặp lại.
     - `test_source_content_editing_and_human_review`: Kiểm tra hiệu đính markdown và luồng review approved/rejected.
     - `test_worker_task_knowledge_source_ingestion`: Kiểm tra ARQ task bất đồng bộ tích hợp JobRecord.
     - `test_http_routes_source_management`: Kiểm tra đầy đủ 4 REST API endpoints.

---

### 3. Kết Quả Kiểm Thử & Đảm Bảo Chất Lượng

- **Pytest New Suite**:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_knowledge_source_ingestion.py -v
  # Kết quả: 6 passed, 0 failed trong 3.51s
  ```
- **Pytest Regression Suites (Toàn bộ 6 test files liên quan đến Knowledge V3 & Documents)**:
  ```bash
  .venv\Scripts\python.exe -m pytest tests/test_knowledge_candidate_and_import_batch.py tests/test_knowledge_source_ingestion.py tests/test_knowledge_v3_schema.py tests/test_document_repository_workflow.py tests/test_document_repository.py tests/test_document_revisions_lifecycle.py -v
  # Kết quả: 61 passed, 1 warning (Qdrant test server version) trong 4.06s (100% PASSED)
  ```
- **Ruff Code Linter**:
  ```bash
  .venv\Scripts\python.exe -m ruff check app/modules/knowledge/ app/workers/ app/modules/jobs/ tests/test_knowledge_source_ingestion.py
  # Kết quả: All checks passed! 0 warnings, 0 errors.
  ```

---

### 4. Bài Học Kỹ Thuật Rút Ra
1. **Khớp Chữ Ký Ngoại Lệ DomainException**:
   - `DomainException.__init__` nhận `message`, `code`, `status_code`, `detail`. Không truyền `error_code` như một kwarg riêng để tránh `TypeError`. Khi trích xuất mã lỗi từ `exc`, sử dụng `getattr(exc, "code", getattr(exc, "error_code", "INGESTION_ERROR"))`.
2. **Độ Nhạy của Quality Gate đối với Mật Độ Ký Tự**:
   - Quality Gate kiểm tra ngưỡng mật độ ký tự trên mỗi trang `chars_per_page < 60` (`critically_low_text_density`). Khi kiểm thử luồng clean document, cần cung cấp chuỗi văn bản thực tế đầy đủ ngữ cảnh để bảo đảm vượt qua bài kiểm tra chất lượng tự động.
3. **Mocking SQLAlchemy Scalars**:
   - Khi mock `AsyncSession.execute`, đối với truy vấn `scalars().first()`, cần đảm bảo khi `scalar is None`, `mock.scalars.return_value.first.return_value = None` để tránh trả về mock object truthy dẫn đến logic nhánh rẽ sai lệch.

---

### 5. Kế Hoạch Tiếp Theo (Phiên 5)
- **Phiên 5 Kế Hoạch 12**: Xây dựng mô hình và service sinh Chunk Set và Multi-Vector Generation:
  - Khởi tạo `KnowledgeChunkSet` cho từng nguồn tri thức theo chiến lược chunking (`ClauseBasedChunker`, `SemanticChunker`, `TableAwareChunker`).
  - Hỗ trợ đa mô hình embedding độc lập theo cấu hình ModelOps (`collection.embedding_model`).
  - Tách bạch trạng thái vector độc lập (`indexing`, `indexed`, `failed`).
