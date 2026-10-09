# NHẬT KÝ LÀM VIỆC — PHIÊN #289
**Dự án**: QNU.AI Platform (Trường Đại Học Quy Nhơn)

**Ngày thực hiện**: 2026-10-07
**Nội dung trọng tâm**: Thực Hiện Phiên 4 (Pha 3) Kế Hoạch 11: Kiến Trúc Knowledge Publishing V2, Staging Index Build & Parity Gate, Triệt Tiêu 100% Anti-Pattern "Delete-Before-Index" & Pass 100% Test Suite

---

## 1. Mục Tiêu Phiên Làm Việc

Theo lộ trình tại [Kế hoạch 11](../../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md) và quyết định kiến trúc [ADR-011](../../ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md#quyet-dinh-kien-truc-chinh-adr-011), mục tiêu cốt lõi của Phiên 4 (Pha 3) là:
1. **Thiết kế Schema CSDL Knowledge Publishing V2**:
   - Mở rộng `knowledge_collections`: thêm trường `index_epoch` (Integer, default=1).
   - Mở rộng `knowledge_chunks` và `knowledge_facts`: bổ sung `binding_id` và `index_revision_id` để phân lập phạm vi theo revision thay vì chỉ theo document phẳng.
   - Tạo mới 4 bảng thực thể:
     - `knowledge_vector_generations`: Quản lý không gian vector độc lập (Vector Space Invariance, dimension, model, epoch).
     - `knowledge_bindings`: Quản lý quan hệ liên kết M:N giữa Kho Tài Liệu Trung Tâm (`RepositoryDocument`) và Kho Tri Thức (`KnowledgeCollection`).
     - `knowledge_index_revisions`: Artifact bất biến được xây dựng độc lập trong môi trường Staging trước khi thăng cấp.
     - `knowledge_index_activations`: Nhật ký kiểm toán audit ghi nhận mọi lần hoán đổi con trỏ nguyên tử (promote, rollback, rebuild).
2. **Alembic Migration V2**:
   - Viết migration `20261007_knowledge_publishing_v2.py` kế thừa `20261007_document_revisions`.
3. **Pydantic DTO Schemas V2**:
   - Bổ sung các DTO: `AvailableRepositoryDocumentItem`, `AvailableRepositoryDocumentsResponse`, `BindingSelectionItem`, `CreateKnowledgeBindingsRequest`, `CreateKnowledgeBindingsResponse`, `KnowledgeBindingResponse`, `KnowledgeIndexRevisionResponse`, `BuildStagingIndexRequest`, `IndexActivationRequest`, `IndexActivationResponse`.
4. **Service Layer V2**:
   - `BindingService` (`binding_service.py`): Tra cứu tài liệu khả dụng trong kho trung tâm kèm trạng thái bound/unbound và tạo binding an toàn.
   - `IndexBuildService` (`index_build_service.py`): Xây dựng staging index revision, chunking, tính hash, nạp point Qdrant ở chế độ `is_retrievable=False` (staging).
   - **Parity Gate**: So khớp 100% giữa số chunks DB, số vector points Qdrant và chuỗi băm tính toán trước khi đánh dấu `ready`.
   - **Atomic Pointer Swap**: Hoán đổi con trỏ nguyên tử `active_index_revision_id` và tăng `active_epoch` (+1), chuyển cờ `is_retrievable=True` trên vector database, triệt tiêu hoàn toàn downtime và anti-pattern xóa điểm trước khi nạp điểm mới (*Zero Delete-Before-Index*).
5. **Đấu Nối Router Facade & API Endpoints**:
   - Tích hợp 8 endpoint V2 vào `knowledge/router.py` và Facade `KnowledgeService`.
6. **Kiểm Thử & Đảm Bảo Chất Lượng**:
   - Viết test suite `test_knowledge_publishing_v2.py` gồm 12 bài test toàn diện đạt 100% pass.
   - Chạy kiểm tra hồi quy tổng thể cả 4 test suite (28/28 tests passed).
   - Đảm bảo 0 lỗi Ruff linter.

---

## 2. Các Tệp Mã Nguồn Đã Thay Đổi & Tạo Mới

| STT | Đường Dẫn Tệp | Hành Động | Vai Trò & Chức Năng |
|---|---|---|---|
| 1 | `backend/app/modules/knowledge/models.py` | Cập nhật | Mở rộng `KnowledgeCollection.index_epoch`, `KnowledgeChunk.binding_id/index_revision_id`, `KnowledgeFact.binding_id/index_revision_id`; Thêm 4 ORM models V2 (`KnowledgeVectorGeneration`, `KnowledgeBinding`, `KnowledgeIndexRevision`, `KnowledgeIndexActivation`) với eager Python `__init__` defaults. |
| 2 | `backend/alembic/versions/20261007_knowledge_publishing_v2.py` | Tạo mới | Migration Alembic mở rộng cột và tạo 4 bảng CSDL mới với composite unique constraints và indexes. |
| 3 | `backend/app/modules/knowledge/schemas.py` | Cập nhật | Bổ sung 9 Pydantic DTO models phục vụ đàm thoại API V2 cho Binding, Staging Build, Parity Gate và Activation. |
| 4 | `backend/app/modules/knowledge/services/binding_service.py` | Tạo mới | Dịch vụ nghiệp vụ quản lý liên kết tài liệu vào bộ sưu tập tri thức (`get_available_documents`, `create_bindings`, `list_bindings`, `get_binding`, `detach_binding`). |
| 5 | `backend/app/modules/knowledge/services/index_build_service.py` | Tạo mới | Dịch vụ staging build, tích hợp Parity Gate so khớp 100%, và atomic pointer swap promotion. |
| 6 | `backend/app/modules/knowledge/service.py` | Cập nhật | Mở rộng Unified Facade `KnowledgeService`, inject `binding_service` và `index_build_service`. |
| 7 | `backend/app/modules/knowledge/router.py` | Cập nhật | Bổ sung 8 HTTP REST endpoints mới theo chuẩn OpenAPI RESTful. |
| 8 | `backend/tests/test_knowledge_publishing_v2.py` | Tạo mới | Unit test suite 12 bài kiểm thử phủ sóng toàn diện Models, Service, Parity Gate, Atomic Swap và HTTP Routes. |

---

## 3. Thuật Toán & Cơ Chế Kỹ Thuật Nổi Bật

### 3.1. Triệt Tiêu 100% Anti-Pattern "Delete-Before-Index" (Bất Biến 3 ADR-011)
- **Vấn đề trong V1**: Quy trình cũ luôn gọi `vector_indexer.delete_by_document(...)` TRƯỚC KHI sinh vector mới. Nếu quá trình sinh vector, kết nối mạng hoặc embedding provider gặp sự cố (timeout, hết quota, crash), tài liệu lập tức bị biến mất khỏi hệ thống tra cứu RAG, gây ra "downtime dữ liệu" nghiêm trọng.
- **Giải pháp V2**:
  1. Khi một bản ghi `KnowledgeIndexRevision` được khởi tạo, nó nhận trạng thái `building`.
  2. Các điểm vector mới được nạp vào Qdrant với payload chứa `is_retrievable = False` và `document_status = "staging"`.
  3. Mọi truy vấn RAG của người dùng đang chạy hoàn toàn không nhìn thấy các điểm staging này và tiếp tục phục vụ trên index revision cũ mà không gián đoạn 1 micro-giây nào.

### 3.2. Cổng So Khớp Tính Toàn Vẹn Parity Gate
- Trước khi một index revision được cho phép chuyển sang trạng thái `ready`, hệ thống bắt buộc chạy qua **Parity Gate**:
  - So sánh: $N_{\text{db\_chunks}} = N_{\text{qdrant\_points}} = N_{\text{point\_ids}}$.
  - Kiểm tra xác thực tính nguyên vẹn của chuỗi băm nội dung `chunk_hash`.
  - Kết quả kiểm toán được lưu bất biến vào JSONB `parity_report` kèm dấu thời gian `checked_at`.
  - Nếu số điểm không khớp, revision lập tức bị gắn trạng thái `failed` với mã lỗi `PARITY_GATE_MISMATCH`, không bao giờ được phép đưa vào phục vụ.

### 3.3. Hoán Đổi Con Trỏ Nguyên Tử (Atomic Pointer Swap)
- Khi thực hiện `promote_index_revision`:
  1. Chỉ cho phép các revision đạt trạng thái `ready` (hoặc `building` trong quy trình auto-activate hợp lệ).
  2. Cập nhật con trỏ `binding.active_index_revision_id = target_rev.id` và tăng `binding.active_epoch += 1`.
  3. Đánh dấu revision cũ thành `archived`.
  4. Ghi một bản ghi bất biến vào `KnowledgeIndexActivation` phục vụ kiểm toán hoặc rollback tức thì.
  5. Cập nhật payload của các điểm mới thành `is_retrievable = True` và `document_status = "active"`.
  6. Các điểm cũ chỉ được dọn dẹp an toàn sau khi việc thăng cấp đã thành công mỹ mãn.

---

## 4. Kết Quả Kiểm Thử (Verification & Testing)

### 4.1. Unit Test Suite Knowledge Publishing V2
Chạy lệnh kiểm thử độc lập cho tính năng V2:
```bash
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_knowledge_publishing_v2.py -v
```
**Kết quả**: **12 passed / 12 tests (100% PASS)** trong 45.72s:
- `test_models_v2_instantiation_defaults`: PASSED
- `test_chunk_and_collection_expansion_fields`: PASSED
- `test_get_available_documents_success`: PASSED
- `test_create_bindings_success`: PASSED
- `test_create_bindings_already_bound_skips`: PASSED
- `test_create_bindings_missing_revision_fails`: PASSED
- `test_build_staging_index_success`: PASSED
- `test_build_staging_index_empty_text_fails`: PASSED
- `test_promote_index_revision_atomic_pointer_swap`: PASSED
- `test_promote_index_revision_invalid_status_rejects`: PASSED
- `test_api_get_available_documents`: PASSED
- `test_api_create_bindings_endpoint`: PASSED

### 4.2. Kiểm Thử Hồi Quy Toàn Bộ Chuỗi V2 (Full Regression Test Suite)
Chạy đồng thời toàn bộ 4 test suite của 3 phiên liên tiếp:
```bash
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_document_repository.py backend/tests/test_document_revisions_schema.py backend/tests/test_document_revisions_lifecycle.py backend/tests/test_knowledge_publishing_v2.py -v
```
**Kết quả**: **28 passed / 28 tests (100% PASS)** trong 69.67s.

### 4.3. Kiểm Tra Linter Ruff
```bash
backend\.venv\Scripts\ruff.exe check backend/app/modules/knowledge/ backend/app/modules/documents/ backend/tests/test_knowledge_publishing_v2.py
```
**Kết quả**: **All checks passed! (0 lỗi lint, 0 cảnh báo).**

---

## 5. Kết Luận & Sẵn Sàng Cho Pha Kế Tiếp

Phiên 4 (Pha 3) đã hoàn thành xuất sắc 100% mục tiêu kiến trúc backend cho Knowledge Publishing V2. Toàn bộ nền tảng dữ liệu Staging Index, Parity Gate, Atomic Pointer Swap đã sẵn sàng cho:
- **Phiên 5 (Pha 4)**: Cải tiến Retrieval Engine V2 (`retriever.py`, snapshot pinning, session consistency) và Background Workers (re-indexing định kỳ, async bulk promotion).
