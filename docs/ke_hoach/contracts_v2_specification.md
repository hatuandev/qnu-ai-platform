# ĐẶC TẢ KỸ THUẬT API CONTRACTS V2 & KIỂM KÊ HỆ THỐNG (INVENTORY & MIGRATION MAP)

- **Tài liệu đính kèm**: Kế hoạch Triển khai Quy trình "Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn"
- **Phiên thực hiện**: Phiên #286 (Pha 0 / Phiên 1)
- **Áp dụng cho**: Phân hệ Kho Tài Liệu (`/documents`), Kho Tri Thức (`/knowledge`), Background Jobs và Hybrid RAG

---

## 1. Kiểm Kê Hệ Thống Hiện Tại & Bản Đồ Chuyển Đổi (Inventory & Legacy Map)

### 1.1. Bảng cơ sở dữ liệu (Database Tables)

| Bảng Hiện Tại (V1) | Trạng Thái V1 | Bảng Mục Tiêu (V2) | Vai Trò & Thay Đổi Trong V2 |
|---|---|---|---|
| `repository_documents` | Đã có từ Phiên #283; lưu `parsed_markdown`, SHA-256 deduplication, metadata NĐ 30. | `repository_documents` | Trở thành thực thể tài liệu logic; thêm `current_revision_id`, `latest_revision_no`, `status` (`active/archived`), `row_version`. |
| *(Chưa có)* | Chưa có | `document_revisions` | Lưu trữ từng phiên bản nội dung nguồn bất biến (`canonical_markdown`, `source_hash`, `quality_report`, `status`, `idempotency_key`). |
| `knowledge_documents` | Bảng tài liệu riêng của từng collection; lưu trực tiếp tệp hoặc liên kết `repository_document_id`. | `knowledge_bindings` | Thay thế mô hình `KnowledgeDocument` bằng `KnowledgeBinding` (quản lý quan hệ collection ↔ repository document, `desired_source_revision_id`, `active_index_revision_id`, `active_epoch`, `sync_status`). |
| *(Chưa có)* | Chưa có | `knowledge_vector_generations` | Quản lý từng thế hệ không gian vector của collection (`embedding_provider_id`, `embedding_model_name`, `dimension`, `epoch`). |
| *(Chưa có)* | Chưa có | `knowledge_index_revisions` | Lưu trữ artifact RAG bất biến sinh từ source revision ở vùng Staging trước khi kích hoạt (`status`, `config_snapshot`, counts). |
| *(Chưa có)* | Chưa có | `knowledge_index_activations` | Bảng nhật ký append-only ghi lại toàn bộ lịch sử kích hoạt và rollback con trỏ CAS (`epoch`, `from_revision`, `to_revision`, `reason`). |
| `knowledge_chunks` | Thuộc về `knowledge_documents`; chưa có khóa revision. | `knowledge_chunks` | Bổ sung `binding_id`, `source_revision_id`, `index_revision_id`, `content_hash`, TSVECTOR generated column. |
| `knowledge_facts` | Thuộc về `knowledge_documents`; chưa có khóa revision. | `knowledge_facts` | Bổ sung `binding_id`, `source_revision_id`, `index_revision_id`, `fact_hash`. |
| `job_records` | Bảng quản lý async jobs chung; chưa có checkpoint theo phase. | `job_records` | Bổ sung `resource_type`, `resource_id`, `phase`, `idempotency_key`, `heartbeat_at`, `checkpoint_metadata`. |

---

### 1.2. Bản đồ chuyển đổi API Endpoints

| Endpoint Hiện Tại (V1) | Phương thức | Endpoint Mục Tiêu (V2) | Chiến Lược Chuyển Đổi (Strategy) |
|---|---|---|---|
| `/documents/upload` | `POST` | `/documents/upload` | Nâng cấp trả về `202 Accepted` kèm `job_id`, `revision_id` và hỗ trợ header `Idempotency-Key`. Giữ nguyên hỗ trợ multi-file upload. |
| `/documents` | `GET` | `/documents` | Giữ nguyên bộ lọc, hiển thị thêm thông tin `current_revision_status` và `bindings_count`. |
| `/documents/{id}` | `GET` | `/documents/{id}` | Mở rộng trả về danh sách lịch sử revisions và các Kho Tri Thức đang sử dụng. |
| `/documents/{id}/reparse` | `POST` | `/documents/{id}/revisions` | Thay thế thao tác reparse ghi đè bằng việc tạo một `DocumentRevision` mới kế thừa, không ảnh hưởng bản cũ đang dùng. |
| *(Chưa có)* | - | `PATCH /documents/{id}/revisions/{rev_id}/review-content` | Endpoint mới cho phép cán bộ chỉnh sửa / hiệu đính Markdown trước khi chốt duyệt. |
| *(Chưa có)* | - | `POST /documents/{id}/revisions/{rev_id}/submit-review` | Endpoint mới chốt duyệt revision sang trạng thái `ready`. |
| `/collections/{id}/documents` (Direct Upload) | `POST` | `/collections/{id}/documents` *(Legacy)* | Giữ làm **Compatibility Façade**: Tự động đưa file vào Kho Tài Liệu trước $\rightarrow$ đợi `ready` $\rightarrow$ tạo binding tự động. Sẽ deprecate sau khi cutover. |
| `/collections/{id}/attach-repository-documents` | `POST` | `/collections/{id}/bindings` | Thay thế việc clone document sang tạo bản ghi `knowledge_bindings` với `source_revision_id` cụ thể. |
| *(Chưa có)* | - | `GET /collections/{id}/available-documents` | Endpoint mới liệt kê các tài liệu nguồn có revision `ready` kèm bộ lọc loại văn bản và trạng thái binding. |
| `/collections/{id}/documents` | `GET` | `/collections/{id}/bindings` | Trả về danh sách bindings kèm trạng thái đồng bộ (`current`, `update_available`, `building`, `failed`). |
| *(Chưa có)* | - | `POST /bindings/{binding_id}/sync` | Endpoint mới kích hoạt build index revision mới từ source revision mới nhất. |
| *(Chưa có)* | - | `POST /bindings/{binding_id}/rollback` | Endpoint mới chuyển con trỏ CAS về revision trước đó ngay lập tức (0ms). |
| `/collections/{id}/reindex` | `POST` | `/collections/{id}/rebuild-generation` | Tái lập chỉ mục toàn bộ collection sang một `vector_generation` mới mà không làm gián đoạn retrieval hiện tại. |

---

### 1.3. Qdrant Payload Schema V1 vs V2

```json
// Qdrant Payload V1 (Hiện tại)
{
  "chunk_id": "chk_abc123",
  "document_id": "doc_xyz789",
  "collection_id": "col_admission",
  "text": "Nội dung trích đoạn...",
  "page_number": 1,
  "section": "Điều 15. Tiêu chuẩn xét tuyển"
}

// Qdrant Payload V2 (Mục tiêu - Đầy đủ Provenance & Revision Scoping)
{
  "point_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6", // UUID5 deterministic: generation_id + revision_id + chunk_id
  "chunk_id": "chk_abc123",
  "binding_id": "bnd_456def",
  "source_revision_id": "rev_001",
  "index_revision_id": "idx_rev_002",
  "vector_generation_id": "gen_bge_m3_v1",
  "collection_id": "col_admission",
  "tenant_id": "tenant_qnu",
  "workspace_id": "workspace_qnu",
  "text": "Nội dung trích đoạn...",
  "content_hash": "a1b2c3d4...",
  "page_number": 1,
  "section": "Điều 15. Tiêu chuẩn xét tuyển",
  "document_number": "2139/QĐ-ĐHQN",
  "issued_date": "2025-08-15"
}
```

---

## 2. Đặc Tả Chi Tiết API Contracts V2 (Schemas & DTOs)

### 2.1. Phân hệ Kho Tài Liệu Tập Trung (Document Repository V2)

#### `POST /documents/upload`
- **Mục đích**: Tiếp nhận một hoặc nhiều tệp vào Kho Tài Liệu, lưu trữ MinIO S3, tính toán SHA-256 deduplication và tạo job bóc tách bất đồng bộ.
- **Request Headers**:
  - `Idempotency-Key`: Chuỗi UUID định danh yêu cầu chống gửi trùng.
- **Request Body (Multipart Form)**:
  - `file`: UploadFile (PDF, DOCX, XLSX, TXT, MD).
  - `title`: Chuỗi tùy chọn (nếu để trống, AI tự trích xuất từ văn bản).
  - `document_type_code`: Chuỗi tùy chọn (mặc định AI tự nhận diện NĐ 30).
  - `issuing_authority`: Chuỗi tùy chọn (mặc định "Trường Đại học Quy Nhơn").
  - `auto_parse`: Boolean (mặc định `true`).
- **Response (`202 Accepted`)**:
```json
{
  "document_id": "rep_doc_a1b2c3d4e5f6",
  "revision_id": "rev_01j8k9m0n1p2",
  "revision_no": 1,
  "file_name": "quyet_dinh_2139.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "job_id": "job_doc_parse_789xyz",
  "status": "queued",
  "deduplicated": false,
  "created_at": "2026-10-07T11:45:00Z"
}
```

#### `GET /documents/{id}/revisions`
- **Mục đích**: Lấy danh sách lịch sử toàn bộ các phiên bản nội dung của tài liệu.
- **Response (`200 OK`)**:
```json
{
  "document_id": "rep_doc_a1b2c3d4e5f6",
  "current_revision_id": "rev_01j8k9m0n1p2",
  "revisions": [
    {
      "id": "rev_01j8k9m0n1p2",
      "revision_no": 1,
      "status": "ready",
      "canonical_hash": "c4ca4238a0b923820dcc509a6f75849b...",
      "page_count": 2,
      "table_count": 2,
      "quality_report": {
        "status": "passed",
        "mojibake_score": 0.0,
        "unrecognized_chars_ratio": 0.0,
        "table_integrity_score": 1.0
      },
      "created_at": "2026-10-07T11:45:00Z"
    }
  ]
}
```

#### `PATCH /documents/{id}/revisions/{revision_id}/review-content`
- **Mục đích**: Cho phép cán bộ chỉnh sửa nội dung Canonical Markdown (chỉ áp dụng khi revision đang ở trạng thái `review_required` hoặc `processing`).
- **Request Body**:
```json
{
  "canonical_markdown": "# Quy định tuyển sinh mới...",
  "notes": "Chỉnh sửa lại bảng điểm chuẩn khối A00"
}
```
- **Response (`200 OK`)**: Trả về `DocumentRevisionResponse` cập nhật.

---

### 2.2. Phân hệ Kho Tri Thức (Knowledge Publishing V2)

#### `GET /collections/{id}/available-documents`
- **Mục đích**: Liệt kê các tài liệu nguồn có revision `ready` để quản trị viên Kho Tri Thức lựa chọn gắn vào collection.
- **Query Params**:
  - `search`: Chuỗi tìm kiếm.
  - `document_type_code`: Lọc theo mã loại văn bản NĐ 30.
  - `already_bound`: `true | false | all` (lọc các tài liệu đã gắn hoặc chưa gắn vào kho này).
- **Response (`200 OK`)**:
```json
{
  "items": [
    {
      "repository_document_id": "rep_doc_a1b2c3d4e5f6",
      "title": "Ban hành quy chế tổ chức đào tạo đại học năm học 2025 - 2026",
      "document_number": "2139/QĐ-ĐHQN",
      "document_type_code": "quyet_dinh",
      "latest_ready_revision_id": "rev_01j8k9m0n1p2",
      "latest_ready_revision_no": 1,
      "issued_date": "2025-08-15",
      "is_bound_to_this_collection": false,
      "current_binding_id": null
    }
  ],
  "total": 1
}
```

#### `POST /collections/{id}/bindings`
- **Mục đích**: Gắn danh sách tài liệu từ Kho Tài Liệu vào collection và kích hoạt quá trình dựng index revision ở vùng Staging.
- **Request Body**:
```json
{
  "selections": [
    {
      "repository_document_id": "rep_doc_a1b2c3d4e5f6",
      "source_revision_id": "rev_01j8k9m0n1p2",
      "chunk_strategy": "ClauseBasedChunker",
      "auto_activate": true
    }
  ]
}
```
- **Response (`202 Accepted`)**:
```json
{
  "accepted": [
    {
      "binding_id": "bnd_99887766",
      "repository_document_id": "rep_doc_a1b2c3d4e5f6",
      "source_revision_id": "rev_01j8k9m0n1p2",
      "index_revision_id": "idx_rev_55443322",
      "job_id": "job_idx_build_112233",
      "status": "building"
    }
  ],
  "rejected": []
}
```

#### `POST /bindings/{binding_id}/rollback`
- **Mục đích**: Quay ngược tức thì (0ms) về phiên bản index revision liền trước đó.
- **Request Body**:
```json
{
  "reason": "Phát hiện lỗi sai lệch số liệu trong bản sửa đổi mới"
}
```
- **Response (`200 OK`)**:
```json
{
  "binding_id": "bnd_99887766",
  "active_index_revision_id": "idx_rev_00112233",
  "active_epoch": 2,
  "action": "rollback",
  "message": "Đã hoàn tác thành công về Index Revision trước đó."
}
```

---

## 3. Quy Chuẩn Headers, Mã Lỗi RFC 7807 & Idempotency

### 3.1. Ràng buộc Header `Idempotency-Key`
- Mọi API tạo dữ liệu (`POST /documents/upload`, `POST /collections/{id}/bindings`, `POST /bindings/{id}/sync`) chấp nhận header `Idempotency-Key: <UUID>`.
- Hệ thống băm toàn bộ payload (`request_hash = SHA256(body)`).
- Nếu gặp cùng `Idempotency-Key` và cùng `request_hash`: Trả về kết quả ban đầu (HTTP 200/202).
- Nếu gặp cùng `Idempotency-Key` nhưng `request_hash` khác: Trả lỗi `409 IDEMPOTENCY_KEY_CONFLICT`.

### 3.2. Mã lỗi chuẩn hóa RFC 7807 (`AppException`)

```json
{
  "type": "https://api.qnu.edu.vn/errors/parity-check-failed",
  "title": "Kiểm tra tính toàn vẹn chỉ mục thất bại",
  "status": 422,
  "code": "PARITY_CHECK_FAILED",
  "detail": "Số lượng vector trong Qdrant (12) không khớp với số chunks trong PostgreSQL (15).",
  "instance": "/bindings/bnd_99887766/activate",
  "invalid_params": [
    { "name": "vector_count_delta", "reason": "Missing 3 vectors in Qdrant staging" }
  ]
}
```

Các mã lỗi nghiệp vụ bắt buộc:
- `IDEMPOTENCY_KEY_CONFLICT` (HTTP 409)
- `REVISION_NOT_READY` (HTTP 400): Nguồn chưa đạt `ready` nên không thể tạo binding.
- `PARITY_CHECK_FAILED` (HTTP 422): Không vượt qua Parity Gate.
- `ACTIVE_EPOCH_MISMATCH` (HTTP 409): Xung đột cạnh tranh con trỏ CAS khi hai cán bộ cùng duyệt.
- `VECTOR_GENERATION_INCOMPATIBLE` (HTTP 400): Mô hình embedding không tương thích với generation hiện hành.

---

## 4. Bảng Cấu Hình Feature Flags & Kill Switch

| Tên Biến Môi Trường (Feature Flag) | Giá Trị Mặc Định | Mô Tả & Tác Dụng Bảo Vệ |
|---|---|---|
| `KNOWLEDGE_REVISION_WRITES_ENABLED` | `true` | Bật/tắt ghi dữ liệu theo mô hình Revision V2 (cho phép rollback về luồng cũ nếu gặp sự cố). |
| `RAG_REVISION_READ_MODE` | `legacy` $\rightarrow$ `shadow` $\rightarrow$ `revisioned` | Chế độ đọc của RAG Retrieval: `legacy` (đọc bảng cũ), `shadow` (đọc bảng cũ nhưng chạy ngầm đối soát V2), `revisioned` (đọc chính thức theo con trỏ active revision). |
| `RAG_ATOMIC_ACTIVATION_ENABLED` | `true` | Kích hoạt cơ chế đổi con trỏ nguyên tử CAS và Parity Gate. |
| `RAG_CACHE_EPOCH_ENABLED` | `true` | Bổ sung `index_epoch` vào Semantic Cache Key chống đọc cache rác. |
| `RAG_REVISION_GC_ENABLED` | `false` | Bật/tắt tiến trình dọn dẹp vector/chunks cũ (mặc định tắt trong giai đoạn canary để bảo toàn dữ liệu rollback). |
| `MAX_RETAINED_INDEX_REVISIONS_PER_BINDING` | `2` | Giới hạn số lượng index revision lưu giữ cho mỗi binding (1 active + 1 previous). |

---

## 5. Kết Luận & Kế Hoạch Tiếp Theo

Tài liệu này đóng vai trò là **Hợp Đồng Kỹ Thuật (Contract Baseline)** ràng buộc toàn bộ các bước triển khai tiếp theo:
- **Phiên #287 (Pha 1)**: Viết migration Alembic tạo bảng `document_revisions` và mở rộng các cột liên quan trên `repository_documents`.
- **Phiên #288 (Pha 2)**: Hiện thực hóa Async Document Intake (`202 Accepted`) và Quality Gate bóc tách Markdown.
