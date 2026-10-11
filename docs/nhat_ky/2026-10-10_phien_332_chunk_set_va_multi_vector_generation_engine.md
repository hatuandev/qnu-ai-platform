# NHẬT KÝ LÀM VIỆC — PHIÊN #332
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Ngày thực hiện**: 2026-10-10  
**Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Thực Hiện Phiên 5 Kế Hoạch 12 — Materialize KnowledgeChunkSet Độc Lập ("Parse Once, Chunk Once, Embed Many"), Multi-Vector Generation Engine, Parity Gate & CAS Atomic Activation Pointer Swap

---

### 1. Bối Cảnh & Yêu Cầu Kỹ Thuật (Phiên 5 / Kế Hoạch 12)
- Theo kiến trúc ADR-012 và lộ trình 8 phiên của Kế hoạch 12:
  - **Phiên 4** đã di chuyển toàn bộ pipeline bóc tách văn bản sang domain Knowledge (`SourceIngestionService`), snapshot tài liệu một chiều sang `KnowledgeSourceRevision` và tái sử dụng artifact qua SHA-256 hash.
  - **Phiên 5 (Phiên này)**: Hiện thực hóa nguyên lý *"Parse Once, Chunk Once, Embed Many"*:
    1. **Tách tầng Chunk Set độc lập**: Materialize `KnowledgeChunkSet` (`chunk_strategy`, `chunk_config`, `config_hash`, `chunk_count`, `token_count`, `storage_path`) gắn với `KnowledgeSourceRevision`. Khi cấu hình chunking không đổi, tái sử dụng 100% chunk set mà không phân đoạn lại.
    2. **Multi-Vector Generation Engine**: Quản lý nhiều thế hệ vector song song (`KnowledgeVectorGeneration`) cho cùng một bộ sưu tập tri thức (`collection_id`). Hỗ trợ cấu hình `embedding_provider`, `embedding_model`, `vector_dimension`, `distance_metric` phân giải động qua ModelOps DB (tuân thủ Tôn chỉ 6 & 9, Zero-Env hardcoded credentials).
    3. **Không gọi lại Parser / Vision OCR khi Re-embedding**: Khi sinh index vector cho mô hình embedding mới (ví dụ từ OpenAI sang BAAI/bge-m3 hoặc Qwen), hệ thống đọc trực tiếp chunks từ manifest của `KnowledgeChunkSet`, tuyệt đối không đụng đến Parser hay OCR.
    4. **Parity Gate Verification**: Bắt buộc đối soát 100% số lượng points được upsert vào Qdrant khớp với số chunks trong `KnowledgeChunkSet` (`actual_points == chunk_set.chunk_count`). Nếu có sự sai lệch dù chỉ 1 điểm, đánh dấu index revision `failed` và từ chối chuyển thế hệ sang `ready`.
    5. **CAS Atomic Activation Pointer Swap**: Khi kích hoạt một thế hệ vector (`POST /collections/{id}/vector-generations/{gen_id}/activate`), thực hiện nguyên tử:
       - Kiểm tra 100% active sources của collection đã có index revision `ready` hoặc `active` ở thế hệ này.
       - Chuyển thế hệ vector mục tiêu thành `active`, các thế hệ `active` cũ thành `retired`.
       - Cập nhật con trỏ `collection.active_vector_generation_id = target_generation.id`.
       - Tăng số hiệu epoch của collection (`collection.index_epoch = collection.index_epoch + 1`).
    6. **Mở rộng 5 REST API endpoints**:
       - `GET /collections/{collection_id}/vector-generations`
       - `POST /collections/{collection_id}/vector-generations`
       - `POST /collections/{collection_id}/vector-generations/{generation_id}/build`
       - `POST /collections/{collection_id}/vector-generations/{generation_id}/activate`
       - `GET /collections/{collection_id}/sources/{source_id}/chunk-sets`

---

### 2. Các Tệp Đã Thay Đổi & Tạo Mới

1. **`backend/app/modules/knowledge/services/chunk_set_service.py`** (Tạo mới):
   - `ChunkSetService`:
     - `compute_config_hash(chunk_strategy, chunk_config)`: SHA-256 hash chuẩn tắc từ chiến lược và cấu hình phân đoạn (bỏ qua các key metadata nội bộ bắt đầu bằng `_`).
     - `get_or_create_chunk_set(db, source_revision, ...)`: Kiểm tra chunk set đã tồn tại với `config_hash` tương ứng; nếu chưa có thì chạy `ChunkStrategyFactory.create(...)`, tạo các chunk với metadata đầy đủ, lưu manifest vào `chunk_config["_manifest"]` phục vụ multi-embedding tức thì mà không cần round-trip I/O phụ.
     - `get_chunk_set(db, chunk_set_id)`: Truy vấn chi tiết chunk set.
     - `list_chunk_sets_for_source(db, source_revision_id)`: Danh sách tất cả chunk sets của một revision nguồn.

2. **`backend/app/modules/knowledge/services/vector_generation_service.py`** (Tạo mới):
   - `VectorGenerationService`:
     - `list_vector_generations(db, collection_id)`: Lấy danh sách các thế hệ vector theo thứ tự thời gian.
     - `create_vector_generation(db, collection_id, req, actor)`: Tạo thế hệ vector mới với trạng thái `building`, tự động phân giải embedding model và dimension từ ModelOps DB (`model_catalog_service.get_model_catalog`).
     - `build_generation_for_source(db, collection_id, generation_id, source_id, ...)`:
       - Lấy hoặc tạo `KnowledgeChunkSet` cho active revision của nguồn.
       - Đọc chunks từ `chunk_set.chunk_config["_manifest"]` (hoặc CSDL).
       - Gọi embedding adapter sinh vectors.
       - Upsert vector points vào Qdrant với payload chứa `generation_id`, `source_revision_id`, `chunk_set_id`.
       - **Parity Gate**: Đếm số points thực tế trong Qdrant qua `vector_indexer.client.count`. Nếu khớp thì đánh dấu `KnowledgeIndexRevision` trạng thái `ready`; nếu không khớp thì đánh dấu `failed` và ghi nhận chi tiết lỗi.
     - `build_all_sources_for_generation(db, collection_id, generation_id, ...)`: Build tuần tự/lô cho toàn bộ active sources của collection. Đánh dấu thế hệ `ready` khi 100% sources thành công.
     - `activate_vector_generation(db, collection_id, generation_id, actor)`: CAS pointer swap nguyên tử, cập nhật `active_vector_generation_id`, retire thế hệ cũ, bump `index_epoch`.

3. **`backend/app/modules/knowledge/schemas.py`**:
   - Bổ sung các DTOs V3 cho Vector Generations:
     - `CreateVectorGenerationRequest`: Tên thế hệ, provider, model, dimension, metric, strategy, config.
     - `KnowledgeVectorGenerationResponse`: Thông tin thế hệ, trạng thái (`building`, `ready`, `active`, `retired`), số tài liệu/chunks đã lập chỉ mục.
     - `ActivateVectorGenerationResponse`: Kết quả kích hoạt kèm `activated_generation_id`, `previous_active_generation_id`, `new_epoch`, `activated_at`.
     - `BuildVectorGenerationRequest`: Danh sách `source_ids` tùy chọn để build cục bộ hoặc toàn phần.
     - `BuildVectorGenerationResponse`: Kết quả build theo từng source (`status`, `points_indexed`, `parity_verified`).

4. **`backend/app/modules/knowledge/router.py`**:
   - Khai báo 5 endpoints REST API chuẩn RESTful cho Vector Generations và Chunk Sets:
     - `GET /collections/{collection_id}/vector-generations`: Danh sách các thế hệ vector.
     - `POST /collections/{collection_id}/vector-generations`: Khởi tạo thế hệ vector mới.
     - `POST /collections/{collection_id}/vector-generations/{generation_id}/build`: Kích hoạt build vector cho các nguồn.
     - `POST /collections/{collection_id}/vector-generations/{generation_id}/activate`: CAS atomic pointer swap kích hoạt thế hệ vector.
     - `GET /collections/{collection_id}/sources/{source_id}/chunk-sets`: Danh sách chunk sets của nguồn.

5. **`backend/tests/test_knowledge_chunk_set_and_vector_generation.py`** (Tạo mới):
   - Bộ test gồm 6 kịch bản kiểm thử sâu:
     1. `test_chunk_set_materialization_and_reuse`: Phân đoạn và tái sử dụng chunk set thành công khi `config_hash` không đổi.
     2. `test_chunk_set_rejects_unready_source_revision`: Từ chối tạo chunk set nếu source revision chưa đạt trạng thái `ready`.
     3. `test_reembed_model_does_not_call_parser_or_ocr`: Khẳng định 100% không gọi lại parser hay OCR khi sinh index cho model embedding mới.
     4. `test_parity_gate_failure_marks_revision_failed`: Parity gate phát hiện lệch points và đánh dấu index revision `failed`.
     5. `test_vector_generation_lifecycle_and_cas_activation`: Vòng đời đầy đủ `building` -> `ready` -> `active` -> `retired` và atomic epoch bump.
     6. `test_http_routes_vector_generations`: Xác thực 5 endpoints HTTP router hoạt động trơn tru.

---

### 3. Kết Quả Kiểm Thử & Đo Lường Chất Lượng

- **Unit & Acceptance Tests**:
  - `pytest -v backend/tests/test_knowledge_chunk_set_and_vector_generation.py`: **6/6 passed 100%** trong 3.44s.
- **Regression Test Toàn Bộ Domain Kho & Tri Thức**:
  - Chạy đồng thời 7 test suites liên quan:
    - `test_knowledge_chunk_set_and_vector_generation.py` (6 tests)
    - `test_knowledge_source_ingestion.py` (6 tests)
    - `test_knowledge_candidate_and_import_batch.py` (6 tests)
    - `test_knowledge_v3_schema.py` (7 tests)
    - `test_document_repository_workflow.py` (26 tests)
    - `test_document_repository.py` (6 tests)
    - `test_document_revisions_lifecycle.py` (10 tests)
  - **Kết quả: 67/67 PASSED (100%)** trong 4.56s.
- **Linter & Code Quality**:
  - `uv run ruff check .`: **0 lỗi** (9/9 cảnh báo đã được auto-fix sạch sẽ).

---

### 4. Bài Học Rút Ra & Bước Tiếp Theo
- **Bài học kỹ thuật**:
  - Việc lưu `_manifest` trong `chunk_config` của `KnowledgeChunkSet` giúp loại bỏ hoàn toàn chi phí query đệ quy bảng chunks khi thực hiện multi-embedding cho nhiều model khác nhau, duy trì tốc độ nạp cực nhanh.
  - Parity Gate kết hợp với CAS atomic activation bảo đảm tính toàn vẹn 100% của không gian vector, loại bỏ hoàn toàn nguy cơ RAG tìm kiếm trên một index chưa hoàn tất hoặc bị mất mát points.
- **Bước tiếp theo (Phiên 6 của Kế hoạch 12)**:
  - Tinh gọn giao diện Frontend Kho tài liệu (`/documents`): biến thành Document Vault thuần lưu trữ, xóa bỏ các tab hay nút parse/OCR/re-index khỏi kho tài liệu, chỉ giữ lại tính năng upload, preview, phân nhóm và metadata hành chính.
