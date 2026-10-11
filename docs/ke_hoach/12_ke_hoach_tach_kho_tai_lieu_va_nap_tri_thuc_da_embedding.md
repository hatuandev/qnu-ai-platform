# Kế Hoạch Tách Kho Tài Liệu Thuần Lưu Trữ Và Pipeline Nạp Tri Thức Đa Embedding

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Dự án | QNU AI Platform |
| Phạm vi | Kho tài liệu, Kho tri thức, OCR/parser, chunking, ModelOps, PostgreSQL, Qdrant, RAG và giao diện quản trị |
| Trạng thái | Đề xuất đã thống nhất về nghiệp vụ, sẵn sàng triển khai theo phiên |
| Ngày lập | 2026-10-10 |
| Quyết định chính | Kho tài liệu chỉ lưu và quản lý tệp; Kho tri thức chủ động nhập snapshot, bóc tách, chuẩn hóa, chunk, facts và embedding |
| Chiến lược nhập | Snapshot thủ công, không tạo liên kết nhóm nguồn lâu dài và không tự đồng bộ ngầm |
| Chiến lược vector | Bóc tách một lần, tái sử dụng Markdown/chunk set để tạo nhiều thế hệ embedding |

---

## 2. Tóm tắt quyết định nghiệp vụ

### 2.1. Kho tài liệu là kho tệp thuần túy

Kho tài liệu chịu trách nhiệm:

- Tạo các kho logic như Tuyển sinh, Đào tạo, Công tác sinh viên.
- Tải lên và lưu tệp gốc trên MinIO/S3.
- Tính SHA-256, chống trùng trong tenant/workspace.
- Quản lý tên, loại tệp, dung lượng và metadata danh mục do người dùng nhập.
- Xem trước tệp gốc, tải xuống, thay thế phiên bản tệp và xóa tệp.
- Quản lý tài liệu thuộc kho nào.

Kho tài liệu **không** chịu trách nhiệm:

- OCR, parser PDF/DOCX/XLSX.
- Chuẩn hóa Markdown hoặc Unicode từ nội dung.
- Quality Gate, hiệu đính, duyệt/từ chối kết quả bóc tách.
- Chunking, facts, embedding hoặc Qdrant.
- Hiển thị Kho tri thức nào đang “gắn” tài liệu.
- Theo dõi trạng thái xử lý của Kho tri thức.
- Tự động đồng bộ thay đổi thành viên nhóm sang Kho tri thức.

### 2.2. Kho tri thức sở hữu toàn bộ Document Intelligence

Kho tri thức chịu trách nhiệm:

- Chủ động chọn một hoặc nhiều tệp từ Kho tài liệu.
- Tạo snapshot bất biến của tệp và metadata tại thời điểm nhập.
- Bóc tách nội dung, OCR ảnh/scan, nhận dạng bố cục và bảng biểu.
- Chuẩn hóa Unicode NFC và Markdown sạch.
- Trích xuất metadata hành chính từ nội dung mà không ghi ngược về Kho tài liệu.
- Quality Gate, hiệu đính và phê duyệt nội dung chuẩn hóa.
- Chunking, Structured Facts và citation metadata.
- Tạo embedding theo model được chọn động từ ModelOps.
- Dựng staging index, parity gate, atomic publish và rollback.
- Lưu nội dung chuẩn hóa/chunks/facts/audit trong PostgreSQL; lưu vector và payload tìm kiếm trong Qdrant.

### 2.3. “Không liên kết” được hiểu đúng

- Không tồn tại liên kết nhóm nguồn lâu dài giữa `DocumentGroup` và `KnowledgeCollection`.
- Kho tài liệu không có cột hoặc màn hình biết Kho tri thức nào đang sử dụng tệp.
- Kho tri thức được phép giữ provenance một chiều như `origin_document_id`, `origin_file_hash`, `origin_group_id` để chống nhập trùng và hiển thị trạng thái.
- Provenance không dùng foreign key cascade từ Knowledge sang Documents; xóa tài liệu khỏi Kho tài liệu không được làm mất nguồn đã xuất bản trong Kho tri thức.
- Khi nhập, Kho tri thức tạo snapshot file riêng hoặc một artifact content-addressed có vòng đời độc lập.

---

## 3. Quy trình người dùng đích

### 3.1. Lưu 100 tài liệu tuyển sinh

```text
Kho tài liệu
  → Tạo kho “Tuyển sinh”
  → Tải 100 tệp
  → MinIO + SHA-256 + metadata danh mục
  → Hoàn tất ngay, không tạo job OCR/parser
```

### 3.2. Nạp 100 tài liệu vào Kho tri thức

```text
Kho tri thức “Tư vấn tuyển sinh”
  → Nạp tài liệu
  → Chọn Kho tài liệu “Tuyển sinh”
  → Xem 100 tệp và trạng thái so với Kho tri thức hiện tại
  → Chọn tất cả “Chưa có” và “Cần cập nhật”
  → Chọn cấu hình OCR/parser, chunking và thế hệ embedding BGE-M3
  → Xác nhận nhập
  → Pipeline chạy bất đồng bộ theo từng tệp
  → Quality Gate / hiệu đính nếu cần
  → Chunk + Facts
  → Embed vào Qdrant staging
  → Parity Gate
  → Xuất bản nguyên tử
```

### 3.3. Trạng thái trên màn hình chọn tài liệu

Tách hai chiều trạng thái để tránh hiểu sai khi hỗ trợ nhiều model:

**Trạng thái nguồn:**

- `Chưa có`: chưa có snapshot của tài liệu trong collection.
- `Đã có`: `origin_document_id` và SHA-256 hiện tại khớp snapshot đang có.
- `Cần cập nhật`: cùng tài liệu nguồn nhưng SHA-256 đã thay đổi.
- `Đang xử lý`: snapshot đang được parse/OCR/chuẩn hóa.
- `Lỗi`: lần xử lý nguồn gần nhất thất bại.

**Trạng thái vector theo model/generation đang chọn:**

- `Đã lập chỉ mục`.
- `Chưa lập chỉ mục`.
- `Đang lập chỉ mục`.
- `Lỗi lập chỉ mục`.

Ví dụ một tệp có thể đồng thời mang nhãn `Đã có` và `Chưa có BGE-M3`. Đây là trường hợp chỉ cần embedding, tuyệt đối không OCR lại.

### 3.4. Quy tắc chọn hàng loạt

- “Chọn tất cả” mặc định chỉ chọn `Chưa có`, `Cần cập nhật`, hoặc `Chưa lập chỉ mục` cho generation đang chọn.
- Tài liệu `Đã có` và đã index đúng generation không được xử lý lại.
- Batch 100 tệp cho phép thành công một phần; lỗi một tệp không rollback 99 tệp còn lại.
- Mỗi item có retry độc lập và toàn batch có nút “Thử lại lỗi”.

---

## 4. Kiến trúc đích

```text
DocumentGroup
  └── RepositoryDocument
        └── RepositoryFileRevision (chỉ tệp gốc)
                │ snapshot import, một chiều
                ▼
KnowledgeBinding / KnowledgeSource
  └── KnowledgeSourceRevision
        ├── Canonical Markdown + manifests + Quality Gate (PostgreSQL)
        └── KnowledgeChunkSet
              ├── Structured Facts (PostgreSQL)
              ├── Vector Generation BGE-M3 (Qdrant)
              ├── Vector Generation Qwen3 (Qdrant)
              └── Vector Generation khác (Qdrant)
```

### 4.1. Nguyên tắc “parse once, embed many”

Khóa tái sử dụng artifact:

```text
source_artifact_key = SHA-256(
  source_file_hash
  + parser_profile_hash
  + normalizer_version
)

chunk_set_key = SHA-256(
  knowledge_source_revision_id
  + chunk_strategy
  + chunk_config_hash
)

vector_artifact_key = SHA-256(
  chunk_set_id
  + provider_id
  + model_name
  + dimension
  + distance_metric
)
```

- Đổi embedding model: tái sử dụng `KnowledgeChunkSet`, chỉ tạo vector generation mới.
- Đổi chunk strategy: tạo chunk set mới nhưng không OCR lại.
- Tệp nguồn thay đổi hoặc parser/normalizer thay đổi: tạo `KnowledgeSourceRevision` mới.
- Không hardcode từ vựng để nhận dạng bảng hoặc metadata; dùng thuật toán hình thái/cấu trúc theo AGENTS.md.

---

## 5. Điều chỉnh ADR-011 và mã hiện tại

ADR-011 hiện đã chốt parser/OCR/Canonical Markdown thuộc Kho tài liệu. Quyết định này không còn phù hợp với nghiệp vụ mới.

Kế hoạch triển khai phải tạo **ADR-012** với nội dung:

- Supersede Quyết định 1, 2, 3 và Bất biến `Referential Integrity` theo liên kết Documents–Knowledge của ADR-011.
- Giữ nguyên các phần tốt của ADR-011: immutable artifact, staging, parity gate, CAS atomic publish, RetrievalSnapshot, idempotency, tenant isolation, rollback và retention.
- Thay `DocumentRevision` chứa canonical content bằng `RepositoryFileRevision` thuần tệp và `KnowledgeSourceRevision` thuộc domain Knowledge.
- Thay persistent `KnowledgeGroupSource` bằng import batch snapshot thủ công.

Các thành phần hiện tại cần deprecate/cắt chuyển:

- `KnowledgeGroupSource`, `group_source_id`, `membership_hash`, `sync_policy` theo nhóm.
- `DocumentRevision.canonical_markdown`, `quality_report`, `parse_provenance` trong domain Documents.
- Job `task_document_revision_parse` được kích hoạt ngay sau upload.
- `/documents/{id}/reparse` và revision review/edit/retry APIs của Documents.
- UI Kho tài liệu: Markdown sạch, Quality Gate, hiệu đính, duyệt/từ chối, trạng thái bóc tách và “Kho tri thức đang gắn”.
- Điều kiện `DocumentRevision.status == ready` trong preview/import Knowledge.

Không xóa vật lý các cột/bảng legacy trong migration đầu tiên. Dùng additive migration, backfill, cutover rồi mới drop ở phiên dọn dẹp cuối.

---

## 6. Mô hình dữ liệu đề xuất

### 6.1. `repository_documents`

Giữ:

- `id`, tenant/workspace.
- `title`, `file_name`, `file_type`, `file_size_bytes`, `file_hash`.
- `storage_path` hoặc con trỏ phiên bản tệp hiện hành.
- Metadata danh mục: loại văn bản, số hiệu, cơ quan, ngày ban hành, ngày hiệu lực, tags.
- Trạng thái `active | archived` và audit timestamps.

Loại khỏi contract công khai sau cutover:

- `parse_status`.
- `ocr_engine`.
- `parsed_markdown`.
- `current_revision_id` nếu nó còn mang nghĩa “revision đã parse”.

### 6.2. `repository_file_revisions`

Phiên bản file gốc bất biến:

- `id`, `document_id`, `revision_no`.
- `source_file_name`, `source_file_type`, `source_size_bytes`.
- `source_hash`, `source_storage_path`.
- `created_by`, `created_at`.
- Không có canonical Markdown, OCR provenance hoặc Quality Gate.

Trong giai đoạn chuyển tiếp có thể backfill từ phần source fields của `document_revisions`.

### 6.3. `knowledge_import_batches`

- `id`, `collection_id`, tenant/workspace.
- `vector_generation_id` hoặc profile embedding mục tiêu.
- `parser_profile`, `chunk_strategy`, các config snapshot/hash.
- `idempotency_key`, `request_hash`.
- Counts: total, queued, processing, review_required, succeeded, failed, skipped.
- `status`: `queued | processing | review_required | ready_to_publish | completed | partial_failed | failed | cancelled`.
- Audit timestamps và người tạo.

### 6.4. `knowledge_import_items`

- `id`, `batch_id`.
- Snapshot provenance: `origin_document_id`, `origin_group_id`, `origin_file_revision_id`, `origin_file_hash`.
- Snapshot metadata: title, file name/type, catalog metadata.
- `knowledge_binding_id`, `knowledge_source_revision_id`, `index_revision_id`.
- `phase`: `snapshot | parse | normalize | validate | chunk | facts | embed | parity | publish`.
- `status`, progress, failure code/detail, retry count.
- Unique/idempotency theo batch và nguồn.

### 6.5. `knowledge_source_revisions`

- `id`, `binding_id`, `revision_no`.
- `origin_document_id` và source hash chỉ là provenance, không FK cascade.
- `snapshot_storage_path`, snapshot metadata JSONB.
- `canonical_markdown`, `canonical_hash`.
- `page_manifest`, `citation_metadata`, `parse_provenance`, `quality_report`.
- `parser_profile_hash`, `normalizer_version`.
- `status`: `queued | extracting | normalizing | validating | review_required | ready | failed | cancelled`.
- Unique `(binding_id, revision_no)` và artifact key để chống xử lý trùng.

### 6.6. `knowledge_chunk_sets`

- `id`, `source_revision_id`.
- `chunk_strategy`, `chunk_config`, `config_hash`.
- `chunk_count`, `fact_count`, `manifest_hash`.
- `status`: `building | ready | failed`.
- Unique `(source_revision_id, config_hash)`.

### 6.7. `knowledge_bindings` trong giai đoạn chuyển đổi

Giữ bảng để tránh phá RetrievalSnapshot và index history, nhưng đổi nghĩa thành một nguồn nội bộ của collection:

- Bỏ phụ thuộc FK cascade vào `repository_documents`.
- `repository_document_id` trở thành provenance `origin_document_id` hoặc thêm trường mới rồi backfill.
- Thay `source_revision_id` trỏ `document_revisions` bằng `active_source_revision_id` trỏ `knowledge_source_revisions`.
- `group_source_id` được deprecate rồi xóa.
- UI/API dùng thuật ngữ “Nguồn tri thức”, không hiển thị “Binding”.

### 6.8. Nhiều thế hệ embedding

Giữ và mở rộng `knowledge_vector_generations`:

- Model/provider/dimension được resolve động từ ModelOps DB.
- Một collection có thể có nhiều generation `building | ready | active | retired`.
- Chỉ một generation phục vụ truy vấn mặc định tại một thời điểm, vì query vector không được trộn giữa các không gian model.
- Chuyển generation phải đạt parity trên toàn bộ nguồn rồi đổi con trỏ collection bằng CAS.
- Các generation cũ giữ trong retention window để rollback.

`knowledge_index_revisions` phải tham chiếu:

- `knowledge_source_revision_id`.
- `chunk_set_id`.
- `vector_generation_id`.

Unique artifact theo `(binding_id, source_revision_id, chunk_set_id, vector_generation_id)` để retry không sinh trùng.

---

## 7. API contract đích

### 7.1. Kho tài liệu

```text
POST   /documents/intake
GET    /documents/groups
GET    /documents/groups/{group_id}/documents
GET    /documents/{document_id}
PATCH  /documents/{document_id}
GET    /documents/{document_id}/download
GET    /documents/{document_id}/preview-pdf
DELETE /documents/{document_id}
```

`POST /documents/intake` trả trạng thái `stored`, không tạo parse job.

Deprecate và sau cutover loại bỏ:

```text
POST  /documents/{id}/reparse
GET   /documents/{id}/revisions (contract parse cũ)
PATCH /documents/{id}/revisions/{revision_id}/content
POST  /documents/{id}/revisions/{revision_id}/review
POST  /documents/{id}/revisions/{revision_id}/retry
```

### 7.2. Kho tri thức – chọn nguồn

```text
GET /knowledge/collections/{collection_id}/repository-candidates
    ?group_id={group_id}
    &vector_generation_id={generation_id}
    &search={query}
    &source_status={status}
```

Mỗi item trả:

- Metadata tài liệu.
- `source_state`.
- `vector_state` theo generation được chọn.
- `current_origin_hash`, `imported_origin_hash`.
- `knowledge_source_id` nếu đã có.
- `selectable` và `reason`.

### 7.3. Kho tri thức – import batch

```text
POST /knowledge/collections/{collection_id}/imports
GET  /knowledge/collections/{collection_id}/imports/{batch_id}
POST /knowledge/collections/{collection_id}/imports/{batch_id}/retry-failed
POST /knowledge/collections/{collection_id}/imports/{batch_id}/cancel
```

Request tạo batch chứa danh sách document IDs, cấu hình parser/chunker, vector generation mục tiêu và `Idempotency-Key`.

### 7.4. Kho tri thức – xử lý nguồn

```text
GET   /knowledge/collections/{collection_id}/sources/{source_id}
GET   /knowledge/collections/{collection_id}/sources/{source_id}/revisions
PATCH /knowledge/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/content
POST  /knowledge/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/review
POST  /knowledge/collections/{collection_id}/sources/{source_id}/retry
```

### 7.5. Vector generations

```text
GET  /knowledge/collections/{collection_id}/vector-generations
POST /knowledge/collections/{collection_id}/vector-generations
POST /knowledge/collections/{collection_id}/vector-generations/{generation_id}/build
POST /knowledge/collections/{collection_id}/vector-generations/{generation_id}/activate
```

Không nhận model name không được resolve qua ModelOps. Không đọc API key từ `.env`.

---

## 8. Pipeline worker

### 8.1. Pipeline nguồn

```text
snapshot source
→ parse native/OCR strategy
→ normalize Unicode NFC/Markdown
→ extract layout, tables, administrative metadata
→ Quality Gate
→ ready hoặc review_required
```

Worker: `task_knowledge_source_ingestion`.

### 8.2. Pipeline index

```text
ready KnowledgeSourceRevision
→ get-or-create KnowledgeChunkSet
→ chunks + facts PostgreSQL
→ resolve vector generation/model from ModelOps
→ embeddings
→ Qdrant staging points
→ parity gate
→ ready_to_publish
→ atomic activation
```

Worker theo từng item, batch orchestrator chỉ điều phối và tổng hợp. Không giữ transaction DB dài trong lúc OCR hoặc gọi embedding provider.

### 8.3. Retry và idempotency

- Retry parse dùng artifact key; nếu source artifact ready thì tái sử dụng.
- Retry embedding tái sử dụng chunk set ready.
- Không tăng counts hoặc tạo duplicate chunks/Qdrant points khi retry cùng request hash.
- Qdrant point ID xác định theo collection/source revision/chunk set/vector generation/chunk index.
- Lỗi từng item dùng RFC 7807 code ổn định và lưu vào `knowledge_import_items`.

---

## 9. Thiết kế giao diện

### 9.1. Kho tài liệu

Trang chi tiết tài liệu chỉ còn:

- Breadcrumb và metadata tệp.
- `Sửa`, `Tải xuống`, `Thay tệp`, `Xóa`.
- Tab/khối `Thông tin`, `Tệp gốc`, `Lịch sử tệp` nếu hỗ trợ phiên bản file.
- Không còn nút `Bóc tách lại`, `Markdown sạch`, Quality Gate, hiệu đính hoặc card “Kho tri thức đang gắn”.

Upload modal dùng microcopy:

> Tệp được lưu an toàn trong Kho tài liệu. Việc bóc tách và lập chỉ mục được thực hiện khi bạn nạp tệp vào Kho tri thức.

### 9.2. Kho tri thức

Header giữ một CTA chính **Nạp tài liệu**.

Trang `/knowledge/:collectionId/add-documents`:

- Bước 1: Chọn Kho tài liệu.
- Bước 2: Tìm kiếm, lọc và chọn tài liệu.
- Hai badge nguồn/vector rõ ràng.
- `Chọn tất cả chưa có`.
- Bước 3: Cấu hình parser/OCR, chunker và vector generation.
- Sticky action bar: số tài liệu chọn và nút **Nạp tài liệu**.
- Mobile sử dụng card/list responsive; desktop dùng Table bọc `overflow-x-auto`.

Trang chi tiết nguồn tri thức chuyển các chức năng cũ từ Documents sang:

- Tệp snapshot và provenance.
- Markdown chuẩn.
- Quality Gate.
- Hiệu đính, duyệt/từ chối, retry.
- Chunks/facts.
- Các index revisions theo từng vector generation.

Tái sử dụng primitives có sẵn; không dùng raw checkbox/button/select. Icon 100% Lucide và semantic OKLCH tokens.

---

## 10. Lộ trình triển khai theo 8 phiên

### Phiên 1 – ADR-012, contract và additive schema

Mục tiêu:

- Viết ADR-012 supersede phần ranh giới của ADR-011.
- Thêm bảng source revisions, chunk sets, import batches/items và các con trỏ cần thiết.
- Không drop cột/bảng cũ.
- Viết migration upgrade/downgrade idempotent và kiểm tra một Alembic head.

Acceptance:

- Migration chạy trên DB rỗng và DB hiện có.
- Tenant/workspace constraints đầy đủ.
- Không mất dữ liệu legacy.

### Phiên 2 – Simplify Kho tài liệu backend

Mục tiêu:

- Upload chỉ lưu file, metadata và raw file revision.
- Không tạo `document_revision_parse` job.
- API trả `stored` trung thực.
- Giữ compatibility adapter có cảnh báo deprecation nếu cần.

Acceptance:

- Upload 100 file không gọi parser/OCR/Qdrant.
- Dedupe/idempotency và MinIO compensation vẫn đúng.
- Xóa tài liệu không cascade dữ liệu Knowledge đã snapshot.

### Phiên 3 – Candidate diff và import batch

Mục tiêu:

- API duyệt nhóm/tài liệu từ phía Knowledge.
- Tính `source_state` và `vector_state` bằng ID/hash/generation.
- Tạo batch idempotent và item per document.

Acceptance:

- Hiển thị đúng `Chưa có`, `Đã có`, `Cần cập nhật`, `Chưa lập chỉ mục`.
- Gửi cùng Idempotency-Key không tạo batch/item trùng.
- Không tạo `KnowledgeGroupSource`.

### Phiên 4 – Knowledge source ingestion

Mục tiêu:

- Snapshot tệp và metadata vào domain Knowledge.
- Di chuyển parser/OCR/cleaner/Quality Gate sang service Knowledge.
- Worker bất đồng bộ, retry và partial failure.

Acceptance:

- Kho tài liệu không bị ghi ngược metadata bóc tách.
- Source revision ready/review_required/failed trung thực.
- OCR failure không trả fake content.

### Phiên 5 – Chunk set và multi-vector generation

Mục tiêu:

- Materialize chunk set/facts một lần.
- Build BGE-M3 và model khác từ cùng chunk set.
- Collection-level active generation CAS và retention.

Acceptance:

- Đổi model không gọi parser/OCR.
- Không trộn vector giữa model hoặc dimension khác nhau.
- Parity gate kiểm tra PostgreSQL/Qdrant chính xác.

### Phiên 6 – Frontend Kho tài liệu tinh gọn

Mục tiêu:

- Xóa UI bóc tách, revision canonical, Quality Gate và liên kết Knowledge.
- Cập nhật KPI/filter/status theo storage domain.
- Cập nhật upload microcopy.

Acceptance:

- Kho tài liệu chỉ thể hiện quản lý file/metadata.
- `npm run build` thành công.

### Phiên 7 – Frontend Kho tri thức hoàn chỉnh

Mục tiêu:

- Trang Nạp tài liệu theo deep route đã có.
- Bulk selection 100+ file, status badges, model generation selector.
- Batch progress, source detail, review Markdown và retry.

Acceptance:

- Có thể nhập 100 file; tài liệu đã có không bị chọn lại mặc định.
- Source tồn tại nhưng thiếu generation hiển thị đúng.
- Refresh/deep link không mất trạng thái.
- `npm run build` thành công.

### Phiên 8 – Backfill, cutover và dọn legacy

Mục tiêu:

- Backfill nguồn đã publish sang `knowledge_source_revisions`.
- Cutover workers/API/frontend.
- Sau thời gian xác minh mới drop `KnowledgeGroupSource`, parse fields và endpoints Documents cũ.
- Reconciliation PostgreSQL–MinIO–Qdrant và GC orphan snapshots.

Acceptance:

- RetrievalSnapshot không rò revision/generation.
- Rollback hoạt động.
- Không còn runtime path tạo parse job trong Documents.
- Ruff, Pytest, frontend build và migration checks đạt.

---

## 11. Chiến lược kiểm thử theo rủi ro

### Test-first bắt buộc

- Migration/backfill và FK/cascade.
- Idempotency batch/item.
- Tenant/workspace isolation.
- Retry không sinh trùng chunks/vectors.
- Collection generation CAS và parity gate.
- Xóa tài liệu repository không làm mất tri thức đã snapshot.

### Code trước, test một lần cuối phiên

- DTO/API CRUD thông thường.
- UI picker, badge, progress, microcopy.
- Tách component và route.

### Bộ kiểm thử trọng tâm

- Upload repository: file được lưu nhưng parser/worker không được gọi.
- Import 100 item: partial success, retry failed only.
- Candidate diff: new/current/update/model-missing.
- Parse once/embed many: parser call count không tăng khi tạo generation thứ hai.
- ModelOps unavailable: RFC 7807, không mock embedding.
- Qdrant failure: active generation cũ vẫn phục vụ.
- Empty extraction: `EMPTY_EXTRACTED_TEXT`, không publish.
- Full RAG citation: source revision, trang, section và vector generation đồng pha.

Final gates:

```bash
uv run ruff check .
uv run --extra dev pytest -v
cd frontend && npm run build
```

---

## 12. Những điều tuyệt đối không làm

- Không hardcode BGE-M3 hoặc provider ID trong runtime; model chọn từ ModelOps DB.
- Không tự động OCR khi upload vào Kho tài liệu.
- Không tạo quan hệ group-source lâu dài.
- Không viết ngược metadata bóc tách vào RepositoryDocument.
- Không cascade delete Knowledge khi xóa tài liệu repository.
- Không OCR lại khi chỉ đổi embedding model.
- Không ghi vector model mới vào Qdrant generation cũ.
- Không xóa active artifacts trước khi staging/parity hoàn tất.
- Không dùng mock/fallback giả khi OCR, DB, ModelOps hoặc Qdrant lỗi.
- Không drop legacy schema trong cùng migration tạo schema mới.
- Không đụng tới repository `qnu-sso`.

---

## 13. Definition of Done tổng thể

- Kho tài liệu upload xong ở trạng thái lưu trữ, không parse.
- Giao diện Kho tài liệu không còn chức năng bóc tách hoặc liên kết Knowledge.
- Kho tri thức có nút **Nạp tài liệu**, chọn theo kho và hỗ trợ bulk 100+ file.
- Mỗi candidate hiển thị chính xác trạng thái nguồn và vector generation.
- Parser/OCR/normalizer/Quality Gate chạy trong Knowledge.
- Markdown/chunks/facts nằm trong PostgreSQL; vector/payload nằm trong Qdrant.
- Một source/chunk set có thể tạo nhiều vector generations mà không OCR lại.
- Model/provider/dimension được resolve động từ ModelOps.
- Batch idempotent, retry an toàn, partial failure trung thực.
- Atomic publish, RetrievalSnapshot, rollback và retention vẫn hoạt động.
- Migration/backfill không mất dữ liệu và chỉ còn một Alembic head.
- Toàn bộ quality gates đạt, không có lỗi TypeScript/Biome/Ruff và không có regression trong RAG.

---

## 14. Prompt tổng để Vibe Coding

```text
Bạn đang làm việc trong repository:
D:\DuAnPhanMem\qnu-ai-platform

Hãy đọc và tuân thủ đầy đủ:
- AGENTS.md
- docs/ke_hoach/12_ke_hoach_tach_kho_tai_lieu_va_nap_tri_thuc_da_embedding.md
- docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md
- .agents/skills/qnu-clean-code-architect/SKILL.md
- .agents/skills/qnu-knowledge-ingestion/SKILL.md
- .agents/skills/qnu-backend-architect/SKILL.md
- .agents/skills/qnu-frontend-architect/SKILL.md

Mục tiêu kiến trúc bắt buộc:
1. Kho tài liệu chỉ lưu file gốc, SHA-256, metadata danh mục và nhóm tài liệu; tuyệt đối không OCR, parse, chuẩn hóa Markdown, Quality Gate, chunk, facts hoặc embedding.
2. Kho tri thức chủ động nhập snapshot tài liệu từ Kho tài liệu; không tạo liên kết DocumentGroup–KnowledgeCollection lâu dài và không ghi ngược trạng thái vào Kho tài liệu.
3. Kho tri thức sở hữu KnowledgeSourceRevision, Markdown chuẩn, Quality Gate, chunks, facts, vector generations, staging/parity/publish và rollback.
4. Parse/OCR một lần, tái sử dụng KnowledgeChunkSet để embedding bằng nhiều model. Đổi embedding model không được gọi parser/OCR lại.
5. Model/provider/dimension phải resolve động từ ModelOps DB; cấm hardcode BGE-M3, provider ID hoặc API key.
6. PostgreSQL lưu canonical Markdown/chunks/facts/audit; Qdrant chỉ lưu vectors và payload phục vụ retrieval.
7. Giữ nguyên các bất biến tốt của ADR-011: staging, parity gate, CAS atomic activation, RetrievalSnapshot, idempotency, tenant isolation và rollback.
8. Không sửa qnu-sso.

Cách thực thi:
- Chỉ thực hiện đúng MỘT phiên trong Mục 10 mà tôi chỉ định; không làm tràn sang phiên sau.
- Đọc code hiện tại trước, tận dụng service/component có sẵn, không tạo file quái vật.
- Với migration, idempotency, tenant isolation, CAS và dữ liệu: viết regression test tái hiện bất biến trước khi sửa.
- Với code nghiệp vụ/UI thông thường: hoàn thành code theo một batch, sau đó viết/cập nhật test và chạy quality gate một lần ở cuối để làm nhanh.
- Dùng additive migration trước; không drop legacy schema trước phiên cutover.
- Mọi lỗi nghiệp vụ trả RFC 7807 AppException, không nuốt lỗi hoặc mock fake-success.
- UI dùng shadcn/Radix primitives hiện có, Lucide icons, semantic OKLCH tokens, responsive và deep routing.

Sau khi hoàn thành:
- Rà diff để bảo đảm không có thay đổi ngoài phạm vi.
- Chạy các test trọng tâm của phiên.
- Nếu có backend: chạy Ruff và Pytest phù hợp; phiên final chạy full suite.
- Nếu có frontend: chạy npm run build.
- Cập nhật docs/nhat_ky, docs/memory/PROJECT_CONTEXT.md và docs/WORK_LOG.md theo AGENTS.md.
- Báo cáo tệp thay đổi, migration, test đã chạy, kết quả và rủi ro còn lại.
```

Khi sử dụng prompt, nối thêm một dòng cuối:

```text
Phiên cần thực hiện: Phiên N – <tên phiên trong Mục 10>.
```
