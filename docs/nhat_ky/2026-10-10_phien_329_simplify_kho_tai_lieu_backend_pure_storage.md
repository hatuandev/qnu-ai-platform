# NHẬT KÝ PHIÊN LÀM VIỆC #329: ĐƠN GIẢN HÓA KHO TÀI LIỆU BACKEND THÀNH THUẦN LƯU TRỮ (ADR-012 PHIÊN 2)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Thời gian thực hiện**: 2026-10-10  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Thực hiện **Phiên 2 của Kế Hoạch 12** ([`docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md`](../ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md)): Chuyển đổi module Kho tài liệu (`documents`) thành kho lưu trữ thuần túy (*Storage Repository / Document Vault*). Cắt bỏ hoàn toàn việc ép buộc kích hoạt parse job tự động khi upload, trả về trạng thái `status="stored"` với `job_id=None`, đồng thời ngắt coupling khi xóa tài liệu khỏi kho lưu trữ đối với dữ liệu Tri thức đã nạp.

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Theo thiết kế kiến trúc tại **ADR-012** (đã ban hành ở Phiên #328), hệ thống giải quyết dứt điểm nghịch lý kép giữa Kho tài liệu và Kho tri thức:
- **Kho tài liệu** đóng vai trò là kho lưu trữ trung tâm (*Document Vault*), lưu trữ nguyên vẹn tệp gốc trên MinIO/S3, cấp định danh duy nhất và quản lý số phiên bản tệp gốc (`RepositoryFileRevision`).
- Quá trình upload/intake tệp vào Kho tài liệu chỉ cần lưu tệp và ghi nhận bản ghi với trạng thái `stored`, **không kích hoạt bóc tách (parse) nặng nề** hay đẩy job vào worker hàng đợi ARQ. Việc bóc tách và tạo embedding thuộc quyền sở hữu của **Kho tri thức** theo nguyên lý *"Parse once, embed many"*.
- Khi xóa mềm tài liệu trong Kho tài liệu (`delete_document`), hệ thống tuân thủ mô hình **Snapshot Import một chiều**: tài liệu đã được nạp sang Kho tri thức là bản sao độc lập, việc xóa tệp trong kho lưu trữ không xóa hay làm hỏng dữ liệu đang phục vụ truy vấn RAG trong Kho tri thức.

---

## 2. Chi Tiết Các Thay Đổi Kiến Trúc & Mã Nguồn

### 2.1. Module Revision (`backend/app/modules/documents/revision_service.py`)
- Mở rộng hàm `create_initial_revision` hỗ trợ tham số `initial_status: str = "stored"`.
- Tạo đồng thời `RepositoryFileRevision` (`revision_no=1`, `source_hash`, `source_storage_path`) cùng lúc với `DocumentRevision` để đảm bảo hợp đồng Additive Schema V3 mà không phá vỡ logic kế thừa.

### 2.2. Module Intake Bất Đồng Bộ (`backend/app/modules/documents/intake_service.py`)
- Mở rộng `VALID_REVISION_STATUSES` bổ sung giá trị `"stored"`.
- Khi tiếp nhận tệp tải lên mới:
  - Khởi tạo `RepositoryDocument` với `parse_status = "stored"`.
  - Khởi tạo revision ban đầu với `initial_status = "stored"`.
  - **Cắt bỏ hoàn toàn**: Không tạo `JobRecord(job_type="document_revision_parse")`, không đẩy tác vụ `task_document_revision_parse` vào ARQ worker qua `enqueue_arq_job`.
  - Trả về `AsyncUploadDocumentResponse(..., status="stored", job_id=None, deduplicated=False)`.
- Giữ dòng `from app.modules.jobs.service import enqueue_arq_job  # noqa: F401` để bảo toàn tính tương thích mock cho các unit tests kế thừa.

### 2.3. Service Kho Tài Liệu (`backend/app/modules/documents/service.py`)
- `upload_document`: Gán `parse_status = "stored"`, tạo initial revision với `status="stored"`, loại bỏ lệnh gọi `parse_and_cache_document` tự động.
- `delete_document`: Xóa bỏ việc truy vấn và kiểm tra `doc.knowledge_documents`, thực hiện soft-delete độc lập trên `RepositoryDocument` mà không làm ảnh hưởng đến các bản ghi trong Kho tri thức.
- `get_stats`: Cập nhật thống kê `parsed_documents` tính cả tài liệu có `parse_status.in_(["stored", "parsed"])`, đồng thời tính số lượt sử dụng thông qua `KnowledgeBinding`.

### 2.4. Cập Nhật Bộ Kiểm Thử (Unit & Lifecycle Tests)
- [`backend/tests/test_document_repository_workflow.py`](../../backend/tests/test_document_repository_workflow.py):
  - Cập nhật các kịch bản kiểm thử intake (`test_02`, `test_07`, `test_12`, `test_http_route_intake_idempotency_header`) để kỳ vọng `status="stored"` và `job_id is None`.
  - Bổ sung 2 acceptance tests cho ADR-012:
    - `test_adr012_batch_upload_stored_status_and_zero_parse_invocations`: Xác nhận upload hàng loạt tệp trả về `status="stored"` và 0 lần gọi bóc tách/job worker.
    - `test_adr012_delete_repository_document_decoupled_from_knowledge`: Xác nhận việc xóa mềm `RepositoryDocument` không gây lỗi và tách biệt hoàn toàn với Knowledge.
- [`backend/tests/test_document_repository.py`](../../backend/tests/test_document_repository.py):
  - Cập nhật `test_document_repository_upload_and_storage_lifecycle` và `test_document_repository_auto_detect_nd30_metadata` phù hợp với hợp đồng `status="stored"`.
- [`backend/tests/test_document_revisions_lifecycle.py`](../../backend/tests/test_document_revisions_lifecycle.py):
  - Cập nhật `test_intake_service_upload_new_document` và `test_api_intake_and_revisions_routes` kiểm tra `res.status == "stored"` và `job_id is None`.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Python Linter (`ruff`)**:
   ```bash
   .venv\Scripts\python.exe -m ruff check app/modules/documents/ tests/test_document_repository_workflow.py tests/test_document_repository.py tests/test_document_revisions_lifecycle.py
   # All checks passed! (0 lỗi linter)
   ```

2. **Kiểm Thử Toàn Diện Các Suite Liên Quan (`pytest`)**:
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_document_repository_workflow.py tests/test_document_repository.py tests/test_document_revisions_lifecycle.py tests/test_document_revisions_schema.py tests/test_knowledge_v3_schema.py -v
   # Kết quả: 52 passed, 1 warning in 4.50s (100% pass)
   ```
   - `test_document_repository_workflow.py`: 29/29 tests PASSED
   - `test_document_repository.py`: 6/6 tests PASSED
   - `test_document_revisions_lifecycle.py`: 7/7 tests PASSED
   - `test_document_revisions_schema.py`: 3/3 tests PASSED
   - `test_knowledge_v3_schema.py`: 7/7 tests PASSED

---

## 4. Kế Hoạch Tiếp Theo (Phiên 3)

Sẵn sàng chuyển sang **Phiên 3 của Kế Hoạch 12**:
- Xây dựng API và service phía Knowledge để:
  - **Candidate Diffing**: So sánh diff giữa Kho tài liệu (`RepositoryDocument` / `RepositoryFileRevision`) và Kho tri thức (`KnowledgeSourceRevision` / `KnowledgeBinding`).
  - **Batch Import**: Nạp batch snapshot từ Kho tài liệu sang Kho tri thức với các tùy chọn chunking (`ClauseBasedChunker`, `SemanticChunker`) và embedding profile riêng biệt của từng Collection.
