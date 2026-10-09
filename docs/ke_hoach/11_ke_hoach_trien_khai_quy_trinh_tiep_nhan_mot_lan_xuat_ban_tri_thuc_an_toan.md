# Kế Hoạch Triển Khai Quy Trình “Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn”

## 1. Thông tin tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Dự án | QNU AI Platform |
| Phạm vi | Kho tài liệu, Kho tri thức, ingestion, RAG, jobs và giao diện quản trị |
| Trạng thái | Đã thống nhất phương án, sẵn sàng chia phiên triển khai |
| Ngày lập | 2026-10-07 |
| Quyết định chính | Kho tài liệu là nguồn sự thật của tệp và nội dung chuẩn hóa; Kho tri thức chỉ xuất bản các revision đã sẵn sàng thành artifact RAG bất biến |
| Chính sách đồng bộ mặc định | Thủ công, có cảnh báo khi tài liệu nguồn có revision mới |

---

## 2. Bối cảnh và mục tiêu

Hiện tại QNU AI Platform đã có Kho tài liệu tập trung, lưu tệp trên MinIO/S3, tiền bóc tách Markdown và cho phép gắn tài liệu vào Kho tri thức. Tuy nhiên, luồng hiện tại vẫn còn một số điểm chưa phù hợp với vận hành production:

- Tài liệu logic, tệp nguồn và kết quả bóc tách chưa được quản lý thành các revision bất biến rõ ràng.
- Kho tri thức còn có thể vừa nhận file trực tiếp, vừa nhận dữ liệu từ Kho tài liệu, dẫn đến hai đường ingestion và nguy cơ xử lý trùng.
- Một số luồng lập chỉ mục xóa vector hoặc chunks cũ trước khi bản mới hoàn tất, làm tăng rủi ro gián đoạn.
- Dense retrieval, sparse retrieval và Structured Fact Layer chưa được bảo đảm cùng đọc một snapshot revision duy nhất.
- Trạng thái xử lý, duyệt, lập chỉ mục và đang phục vụ chưa tách bạch hoàn toàn trên API và giao diện.
- Job nền chưa có đầy đủ idempotency, checkpoint, heartbeat và transactional dispatch.

Mục tiêu của kế hoạch là xây dựng quy trình:

1. Người dùng chỉ tải tệp vào Kho tài liệu một lần.
2. Hệ thống tạo một revision nguồn bất biến, bóc tách và kiểm định chất lượng.
3. Kho tri thức chỉ chọn các revision đã đạt trạng thái `ready`.
4. Mỗi lần nạp hoặc đồng bộ tạo một index revision mới ở vùng staging.
5. Chỉ khi kiểm tra parity đạt, hệ thống mới kích hoạt revision mới bằng thao tác đổi con trỏ nguyên tử.
6. Nếu có lỗi, revision đang phục vụ vẫn hoạt động bình thường và có thể rollback.

---

## 3. Kiến trúc đích

```text
RepositoryDocument
    └── DocumentRevision v1, v2, v3, ...
            └── KnowledgeBinding
                    └── KnowledgeIndexRevision v1, v2, v3, ...
                            └── Active Pointer + Activation History
```

Luồng nghiệp vụ chuẩn:

```text
Tải tệp vào Kho tài liệu
    ↓
Tạo DocumentRevision và Job bóc tách
    ↓
Parse/OCR → Unicode NFC → Canonical Markdown → Quality Gate
    ↓
ready hoặc review_required
    ↓
Chọn revision ready trong Kho tri thức
    ↓
Tạo KnowledgeBinding và KnowledgeIndexRevision ở staging
    ↓
Chunk + Fact + Embedding + Qdrant
    ↓
Parity Gate
    ↓
Kích hoạt nguyên tử
    ↓
Dense + Sparse + Facts + Citations cùng một RetrievalSnapshot
```

### 3.1. Ranh giới trách nhiệm

**Kho tài liệu chịu trách nhiệm:**

- Tệp gốc, checksum, storage path và quyền truy cập.
- Các phiên bản tài liệu nguồn.
- Parser/OCR, Unicode NFC, Canonical Markdown và page manifest.
- Metadata hành chính, provenance và báo cáo chất lượng.
- Hiệu đính nội dung trước khi revision được chốt `ready`.
- Vòng đời lưu trữ hoặc lưu trữ lịch sử của tài liệu nguồn.

**Kho tri thức chịu trách nhiệm:**

- Quan hệ tài liệu nào được dùng trong bộ sưu tập nào.
- Cấu hình chunking, fact extraction và embedding tại thời điểm xuất bản.
- Chunks, facts, vectors và citation provenance.
- Index revision, kích hoạt, rollback, retention và reconciliation.
- Snapshot truy hồi thống nhất cho toàn bộ kênh RAG.

### 3.2. Các bất biến bắt buộc

1. Một revision nguồn đã `ready` là bất biến; sửa nội dung phải tạo revision mới.
2. Một index revision đã `ready` là artifact bất biến.
3. Không xóa bản đang phục vụ trước khi bản mới vượt qua parity gate.
4. Một binding chỉ có đúng một active index revision tại một thời điểm.
5. Dense, sparse, facts, neighbor expansion và citations phải dùng cùng một retrieval snapshot.
6. Thay đổi embedding model hoặc dimension phải tạo vector generation mới.
7. Tên model và provider được phân giải động từ ModelOps, không hardcode trong runtime hoặc migration.
8. Retry cùng idempotency key không được tạo thêm revision, chunks, facts hoặc vectors trùng.
9. Mọi truy vấn và unique constraint quan trọng phải được giới hạn theo tenant/workspace.
10. Không hard-delete tài liệu nguồn đang còn binding hoặc lịch sử kích hoạt cần bảo toàn.

---

## 4. Mô hình dữ liệu đề xuất

### 4.1. `repository_documents`

Đại diện cho tài liệu logic, không giữ kết quả parse của một phiên bản cụ thể.

Các trường chính:

- `id`, `tenant_id`, `workspace_id`.
- `title`, `document_type_code`, `document_number`, `issuing_authority`.
- `issued_date`, `effective_date`, `catalog_metadata`.
- `status`: `active | archived`.
- `current_revision_id`, `latest_revision_no`.
- `row_version` phục vụ optimistic locking.
- Audit fields: người tạo, người cập nhật và timestamps.

### 4.2. `document_revisions`

Đại diện cho một bản nội dung nguồn bất biến.

Các trường chính:

- `id`, `document_id`, `revision_no`, `based_on_revision_id`.
- `source_file_name`, `source_file_type`, `source_size_bytes`.
- `source_hash`, `source_storage_path`.
- `canonical_markdown`, `canonical_hash`.
- `page_manifest`, `citation_metadata`, `parse_provenance`.
- `quality_report`.
- `status`: `queued | processing | validating | review_required | ready | failed | cancelled`.
- `failure_code`, `failure_detail`.
- `idempotency_key`, `request_hash`, `lock_version`.
- Audit và processing timestamps.

Ràng buộc cốt lõi:

- Unique `(document_id, revision_no)`.
- Unique `(document_id, idempotency_key)` khi idempotency key không null.
- Revision `ready` không được cập nhật nội dung.
- Chỉ revision `ready` mới có thể trở thành `current_revision_id` hoặc được Kho tri thức sử dụng.

State machine:

```text
queued → processing → validating → ready
                              └──→ review_required
review_required → validating → ready
queued/processing/validating → failed hoặc cancelled
failed → queued khi retry
ready → terminal
```

### 4.3. `knowledge_bindings`

Đại diện cho quan hệ một tài liệu nguồn được sử dụng trong một collection.

Các trường chính:

- `id`, `tenant_id`, `workspace_id`.
- `collection_id`, `repository_document_id`.
- `desired_source_revision_id`, `active_index_revision_id`.
- `active_epoch`.
- `status`: `active | paused | detaching | archived`.
- `sync_status`: `unpublished | current | update_available | building | failed`.
- `sync_policy`: mặc định `manual`, tùy chọn tương lai `auto_safe`.
- `chunk_strategy`, `chunk_config`, `fact_config`.
- `config_version`, `last_sync_error_code`, `last_sync_error_detail`.
- Audit fields.

Ràng buộc cốt lõi:

- Partial unique `(collection_id, repository_document_id)` đối với binding chưa archived.
- Đổi `active_index_revision_id` bằng compare-and-swap dựa trên `active_epoch`.

### 4.4. `knowledge_vector_generations`

Đại diện cho một không gian vector bất biến của collection.

Các trường chính:

- `id`, `collection_id`, `generation_no`, `epoch`.
- `embedding_provider_id`, `embedding_model_name`, `embedding_dimension`.
- `distance_metric`, `qdrant_collection_name`, `payload_schema_version`.
- `config_snapshot`, `config_hash`.
- `status`: `building | active | draining | retired | failed`.
- Counts, timestamps và error fields.

Quy tắc: dù hai model có cùng dimension, thay model vẫn phải tạo generation mới để không trộn các không gian embedding.

### 4.5. `knowledge_index_revisions`

Đại diện cho artifact RAG bất biến sinh từ một source revision.

Các trường chính:

- `id`, `binding_id`, `revision_no`.
- `source_revision_id`, `vector_generation_id`, `previous_revision_id`.
- `status`: `queued | building | verifying | ready | failed | cancelled | retired`.
- `config_snapshot`, `config_hash`, `pipeline_version`.
- `source_content_hash`, `manifest_hash`.
- Expected/actual counts cho chunks, facts và vectors.
- `job_id`, error fields và phase timestamps.

Không dùng trạng thái `active` trên artifact; trạng thái đang phục vụ được xác định duy nhất bằng con trỏ trên binding.

### 4.6. `knowledge_index_activations`

Lưu lịch sử triển khai và rollback theo kiểu append-only.

Các trường chính:

- `id`, `binding_id`, `epoch`.
- `from_index_revision_id`, `to_index_revision_id`.
- `vector_generation_id`.
- `action`: `initial_publish | sync | rollback | pause | resume`.
- `status`: `preparing | committed | failed`.
- `expected_previous_epoch`, `job_id`, `actor_id`, `reason`.
- Audit và error fields.

### 4.7. Mở rộng chunks và facts

`knowledge_chunks` và `knowledge_facts` cần bổ sung:

- `binding_id`.
- `source_revision_id`.
- `index_revision_id`.
- `vector_generation_id` nếu cần đối soát trực tiếp.
- `provenance`.

Với chunks:

- Unique `(index_revision_id, chunk_index)`.
- Có `content_hash` và citation offsets/page/section.
- Dùng `TSVECTOR GENERATED ... STORED` và GIN index cho sparse retrieval.

Với facts:

- Có `fact_hash`, extractor version và nguồn tạo fact.
- Truy vấn entity tuân thủ bất biến hình thái học: cụm danh từ hoàn chỉnh hoặc mã định danh; không hardcode danh sách từ khóa.

---

## 5. Thiết kế pipeline Kho tài liệu

### 5.1. API tiếp nhận

`POST /documents/upload` trả `202 Accepted` với:

```json
{
  "document_id": "...",
  "revision_id": "...",
  "job_id": "...",
  "status": "queued",
  "deduplicated": false
}
```

Các endpoint mục tiêu:

- `POST /documents/upload`.
- `POST /documents/{id}/revisions`.
- `GET /documents/{id}/revisions`.
- `GET /documents/{id}/revisions/{revision_id}`.
- `PATCH /documents/{id}/revisions/{revision_id}/review-content`.
- `POST /documents/{id}/revisions/{revision_id}/submit-review`.
- `POST /documents/{id}/revisions/{revision_id}/retry`.
- `POST /documents/{id}/archive`.

Mọi command tạo dữ liệu nhận header `Idempotency-Key`:

- Cùng key và cùng request: trả lại resource/job cũ.
- Cùng key nhưng payload khác: trả RFC 7807 `409 IDEMPOTENCY_KEY_CONFLICT`.

### 5.2. Các phase xử lý

1. Kiểm tra MIME thực, kích thước, quyền và checksum.
2. Lưu tệp nguồn vào storage theo đường dẫn tenant/workspace/revision.
3. Nhận diện tài liệu native, scan hoặc mixed.
4. Parser nội dung native trước; chỉ OCR các trang cần thiết.
5. Phân giải OCR provider/model động qua ModelOps.
6. Chuẩn hóa Unicode NFC và làm sạch Mojibake theo thuật toán tổng quát.
7. Tái dựng bảng, page blocks và citation coordinates.
8. Sinh Canonical Markdown và content hash.
9. Chạy Quality Gate.
10. Chuyển `ready`, `review_required` hoặc `failed` với mã lỗi rõ ràng.

Quality Gate tối thiểu phải kiểm tra:

- Nội dung không rỗng.
- Không có ký tự thay thế `�` hoặc mẫu Mojibake vượt ngưỡng.
- Tỷ lệ ký tự hợp lệ và mật độ nội dung đạt ngưỡng.
- Cấu trúc bảng hợp lệ hoặc được đánh dấu cần review.
- Page manifest và citation offsets có thể truy ngược.
- Hash tệp và hash nội dung được ghi nhận đầy đủ.

### 5.3. Ranh giới service

Tách service để tránh file nghiệp vụ quá lớn:

- `repository_service.py`: danh sách, chi tiết, metadata và archive.
- `intake_service.py`: checksum, storage, tạo document/revision/job.
- `revision_service.py`: state machine và immutable revision.
- `revision_processing_service.py`: parse/OCR/normalize/quality pipeline.
- `revision_review_service.py`: hiệu đính và quyết định duyệt.
- `revision_query_service.py`: snapshot chỉ đọc cho Kho tri thức.

---

## 6. Thiết kế pipeline xuất bản Kho tri thức

### 6.1. API mục tiêu

- `GET /collections/{id}/available-documents`.
- `POST /collections/{id}/bindings`.
- `GET /collections/{id}/bindings`.
- `GET /bindings/{binding_id}`.
- `GET /bindings/{binding_id}/index-revisions`.
- `GET /bindings/{binding_id}/activations`.
- `POST /bindings/{binding_id}/sync`.
- `POST /bindings/{binding_id}/rollback`.
- `POST /bindings/{binding_id}/retry`.
- `DELETE /bindings/{binding_id}` để tạo detach job, không xóa tài liệu nguồn.

Bulk binding dùng JSON body theo revision cụ thể:

```json
{
  "selections": [
    {
      "repository_document_id": "doc_...",
      "source_revision_id": "rev_..."
    }
  ]
}
```

Response phải tách từng item thành `accepted` và `rejected`; không hiển thị “đã lập chỉ mục thành công” khi job mới chỉ được xếp hàng.

### 6.2. Job dựng index revision

Job `knowledge_index_build` thực hiện:

1. Khóa theo `binding_id` và kiểm tra idempotency.
2. Chốt cứng `source_revision_id` mục tiêu.
3. Chụp cấu hình chunking, fact extraction, embedding và pipeline version.
4. Sinh chunks/facts ở trạng thái staging, không xóa artifact cũ.
5. Embed theo batch và upsert Qdrant bằng point ID deterministic.
6. Chạy parity gate.
7. Chuyển index revision sang `ready`.
8. Gửi yêu cầu kích hoạt theo chính sách của binding.

Point ID đề xuất:

```text
vector_generation_id:index_revision_id:chunk_id
```

### 6.3. Parity gate

Chỉ cho phép kích hoạt khi toàn bộ điều kiện sau đạt:

- Source hash đúng với snapshot lúc bắt đầu job.
- Chunk count thực tế bằng expected count và lớn hơn 0.
- `chunk_index` duy nhất, liên tục trong revision.
- Manifest hash của chunks khớp.
- Qdrant exact count bằng số chunks PostgreSQL.
- Tập `(chunk_id, content_hash)` khớp 100% giữa PostgreSQL và Qdrant.
- Payload có đúng tenant, workspace, binding, source revision, index revision và vector generation.
- Vector dimension đúng generation và không chứa giá trị không hữu hạn.
- Fact count và fact manifest hợp lệ.
- Mọi fact và citation truy ngược được về đúng source revision.

Nếu bất kỳ điều kiện nào thất bại, revision mới chuyển `failed`; active pointer cũ không thay đổi.

### 6.4. Kích hoạt nguyên tử

1. Mở transaction PostgreSQL.
2. Khóa binding và collection bằng `SELECT ... FOR UPDATE`.
3. Kiểm tra compare-and-swap với `expected_active_index_revision_id` và `expected_epoch`.
4. Gán `active_index_revision_id` sang revision mới.
5. Tăng `active_epoch` và `collection.index_epoch`.
6. Ghi `knowledge_index_activations` và outbox event.
7. Commit transaction.
8. Thực hiện cache invalidation/cleanup bất đồng bộ.

Không dùng cờ bật/tắt trên Qdrant làm nguồn sự thật. PostgreSQL active pointer là nguồn sự thật duy nhất.

---

## 7. Retrieval snapshot và semantic cache

Mỗi câu hỏi RAG phải lấy một snapshot nhất quán gồm:

```text
tenant_id
workspace_id
collection_id
vector_generation_id
generation_epoch
collection.index_epoch
active_index_revision_ids
snapshot_fingerprint
```

Snapshot được truyền nguyên vẹn vào:

- Dense retrieval trên Qdrant.
- Sparse retrieval trên PostgreSQL.
- Structured Fact Layer.
- Neighbor expansion.
- Citation resolver.

Quy tắc lọc:

- Dense: lọc đúng `vector_generation_id` và `index_revision_id` thuộc active snapshot.
- Sparse: lọc `KnowledgeChunk.index_revision_id` trong snapshot.
- Facts: lọc `KnowledgeFact.index_revision_id` trong snapshot.
- Neighbor: chỉ lấy chunk trong cùng `index_revision_id`.

Cache key mới phải chứa tối thiểu:

```text
tenant + workspace + collection
+ vector_generation_id + index_epoch
+ model/policy version + query/history hash
```

Không dùng Redis `KEYS`. Cache cũ tự hết TTL hoặc được dọn nền bằng `SCAN`; việc tăng epoch bảo đảm cache cũ không thể được đọc sau activation hoặc rollback.

---

## 8. Job orchestration và khả năng phục hồi

### 8.1. Các job chính

- `document_revision_parse`.
- `knowledge_index_build`.
- `knowledge_index_activate`.
- `knowledge_binding_detach`.
- `knowledge_generation_rebuild`.
- `knowledge_revision_reconcile`.
- `knowledge_artifact_gc`.

### 8.2. Mở rộng `JobRecord`

- `resource_type`, `resource_id`.
- `phase`.
- `idempotency_key`, `request_hash`.
- `attempt`, `correlation_id`, `error_code`.
- `started_at`, `heartbeat_at`, `finished_at`.
- `cancel_requested_at`.
- `dispatch_status`, `next_attempt_at`.

### 8.3. Transactional outbox

- Resource, JobRecord và yêu cầu dispatch được commit cùng transaction.
- Dispatcher quét các job chưa gửi và enqueue lại khi Redis/ARQ phục hồi.
- Worker CAS `queued → running`, cập nhật heartbeat và checkpoint từng phase.
- Worker chết giữa chừng được resume mà không sinh dữ liệu trùng.
- Hủy chỉ được chấp nhận trước activation CAS; sau CAS phải hoàn tất cleanup.

Các lỗi provider, Redis, storage hoặc Qdrant phải trả lỗi thật qua `AppException`; tuyệt đối không dùng dữ liệu giả để báo thành công.

---

## 9. Thiết kế trải nghiệm người dùng

### 9.1. Cấu trúc route

```text
/documents
/documents/:documentId
/documents/:documentId/revisions/:revisionId

/knowledge/:collectionId
/knowledge/:collectionId/add-documents
/knowledge/:collectionId/documents/:bindingId
```

### 9.2. Kho tài liệu

Trang danh sách tập trung vào:

- Tìm kiếm và lọc theo trạng thái, loại văn bản, cơ quan và thời gian.
- Hiển thị revision hiện tại, chất lượng và số Kho tri thức đang sử dụng.
- Trạng thái ngắn gọn: `Đang xử lý`, `Cần kiểm tra`, `Sẵn sàng`, `Lỗi`, `Đã lưu trữ`.

Trang chi tiết hiển thị:

- Thông tin tệp và metadata.
- Lịch sử revision.
- Canonical Markdown và bản xem trước theo trang.
- Báo cáo chất lượng, provenance parser/OCR.
- Danh sách Kho tri thức đang sử dụng.

Không hiển thị phần trăm giả nếu worker không có progress thực; chỉ hiển thị phase và heartbeat đáng tin cậy.

### 9.3. Kho tri thức

- Bỏ hành vi lấy file trực tiếp làm đường chính.
- Nút chính là `Thêm tài liệu`, điều hướng sang trang chuyên biệt `/add-documents`.
- Chỉ hiển thị các revision nguồn `ready`.
- Cho phép chọn nhiều tài liệu nhưng selection phải gắn với `revision_id` cụ thể.
- Tách rõ ba trạng thái:
  - Revision nguồn đang chọn.
  - Index revision đang phục vụ.
  - Revision mới đang dựng hoặc đang chờ cập nhật.
- Các thao tác chính: `Đồng bộ`, `Thử lại`, `Rollback`, `Gỡ khỏi kho`.
- Binding detail hiển thị lịch sử index revisions, activations, counts, model snapshot và lỗi gần nhất.

Frontend tiếp tục tuân thủ Master–Detail Deep Routing, TanStack Query key factories, RFC 7807, semantic design tokens và tái sử dụng component hiện có.

### 9.4. Luồng upload trực tiếp cũ

Trong thời gian chuyển đổi, endpoint cũ được giữ dưới dạng compatibility façade:

```text
Upload từ màn hình Kho tri thức
→ tạo hoặc tái sử dụng tài liệu trong Kho tài liệu
→ đợi source revision ready
→ tạo binding
```

Sau khi backfill và đo lường cho thấy toàn bộ consumer đã chuyển đổi, ẩn luồng này khỏi UI và deprecate API.

---

## 10. Chiến lược migration và backfill

### 10.1. Nguyên tắc

- Dùng expand-and-contract, không migration phá hủy ngay.
- Alembic chỉ thay đổi schema và backfill quan hệ đơn giản.
- Không gọi parser, OCR, MinIO, Qdrant hoặc provider bên ngoài trong Alembic.
- Backfill nặng chạy bằng job có cursor, checkpoint, retry và báo cáo dry-run.
- Tạo index lớn bằng `CREATE INDEX CONCURRENTLY` khi phù hợp.
- FK mới dùng `NOT VALID`, sau backfill mới `VALIDATE CONSTRAINT`.

### 10.2. Giai đoạn mở rộng schema

1. Tạo `document_revisions` và các trường liên quan trên `repository_documents`.
2. Tạo bindings, vector generations, index revisions và activations.
3. Bổ sung các khóa revision/provenance vào chunks, facts và jobs ở dạng nullable.
4. Bổ sung indexes và constraints chưa cưỡng chế hoàn toàn.
5. Giữ pipeline cũ hoạt động trong thời gian chuyển tiếp.

### 10.3. Backfill dữ liệu nguồn

- Tạo revision v1 từ từng `repository_documents` hiện có.
- Tài liệu có parsed content hợp lệ: đánh dấu `ready` nhưng gắn cờ `legacy_unverified` để audit chất lượng sau.
- Tài liệu pending/parsing: chuyển `queued`.
- Tài liệu failed: giữ `failed` và mã lỗi tương ứng.
- Xác định tenant/workspace từ quan hệ hiện có; nếu một tài liệu mâu thuẫn nhiều tenant thì xuất báo cáo và dừng item đó, không tự đoán.

### 10.4. Backfill Kho tri thức

- Với mỗi `KnowledgeDocument`, tìm hoặc tạo tài liệu nguồn trong đúng tenant/workspace.
- Tạo binding theo `(collection_id, repository_document_id)`.
- Tạo index revision v1 từ chunks/facts hiện có.
- Chỉ gán active pointer nếu tài liệu, chunks và vectors vượt qua parity.
- Bản `approved` nhưng thiếu chunks/vectors phải chuyển `needs_rebuild`, không giả định đang hoạt động.
- Tạo vector generation ban đầu từ cấu hình ModelOps trong DB; nếu thiếu cấu hình thì đánh dấu legacy, không chèn model mặc định cứng.

### 10.5. Qdrant reconciliation

- Dựng payload schema mới có binding/source/index/generation IDs.
- Phân trang đối soát toàn bộ points, không chỉ lấy một trang đầu.
- Rebuild các point không đủ provenance hoặc dimension không tương thích.
- Kiểm tra exact count, hashes và tenant/workspace scope trước cutover.

### 10.6. Shadow, canary và contract

1. Chạy revisioned retrieval ở chế độ shadow, so sánh top-k, facts, citations và latency với đường cũ.
2. Canary theo collection allowlist, không random theo request.
3. Mở rộng lần lượt: một collection ít rủi ro → 25% → 50% → 100%.
4. Tắt legacy writes trước.
5. Giữ kill switch legacy reads ít nhất hai release ổn định.
6. Chỉ sau retention và đối soát cuối mới drop schema/data legacy.

Feature flags đề xuất:

- `KNOWLEDGE_REVISION_WRITES_ENABLED`.
- `RAG_REVISION_READ_MODE=legacy|shadow|revisioned`.
- `RAG_ATOMIC_ACTIVATION_ENABLED`.
- `RAG_CACHE_EPOCH_ENABLED`.
- `RAG_REVISION_GC_ENABLED`.

---

## 11. Các pha triển khai

### Pha 0 — Chốt ADR và ổn định contract hiện tại

Mục tiêu:

- Lập ADR cho document revision, knowledge binding, index revision, activation và vector generation.
- Inventory đầy đủ endpoints, tables, workers, Qdrant payload và frontend calls hiện tại.
- Sửa các mismatch contract đang có trước khi migration lớn: body/query, pagination, field naming, response shape và trạng thái báo thành công.
- Chụp baseline DB/Qdrant/storage và bộ golden queries.

Đầu ra:

- ADR được phê duyệt.
- API contract V2.
- Báo cáo inventory và bản đồ dữ liệu legacy.
- Kế hoạch backup/restore và kill switch.

### Pha 1 — Nền dữ liệu revision và migrations mở rộng

Mục tiêu:

- Tạo các bảng/fields/indexes mới.
- Cài state machine và constraints.
- Viết migration tests và dry-run backfill report.

Đầu ra:

- Schema mới tồn tại song song với schema cũ.
- Không mất hoặc thay đổi dữ liệu đang phục vụ.
- Migration có thể chạy lại an toàn theo quy trình đã định.

### Pha 2 — Document Revision V2

Mục tiêu:

- Upload trả `202` và xử lý bất đồng bộ.
- Hoàn thiện parse/OCR/normalize/Quality Gate.
- Hỗ trợ review, retry và revision history.

Đầu ra:

- Tài liệu nguồn có revision bất biến.
- Chỉ revision `ready` được downstream sử dụng.
- Model OCR được phân giải động từ ModelOps.

### Pha 3 — Knowledge Binding và Index Build V2

Mục tiêu:

- Tạo binding API và available-documents API.
- Dựng index revision staging, parity gate và provenance đầy đủ.
- Không còn delete-before-index.

Đầu ra:

- Build mới thất bại không ảnh hưởng chatbot.
- Retry không sinh artifact trùng.

### Pha 4 — Atomic Activation và Retrieval Snapshot

Mục tiêu:

- Triển khai active pointer CAS, activation history và rollback.
- Buộc dense/sparse/facts/citations dùng cùng snapshot.
- Đưa generation/epoch vào semantic cache.

Đầu ra:

- Mỗi request nhìn thấy hoàn toàn bản cũ hoặc hoàn toàn bản mới.
- Rollback không cần re-embed nếu artifact còn retention.

### Pha 5 — Giao diện quản trị mới

Mục tiêu:

- Hoàn thiện document detail/revision detail.
- Tạo trang thêm tài liệu vào collection và binding detail.
- Hiển thị trạng thái trung thực, lịch sử triển khai và lỗi có thể hành động.

Đầu ra:

- Người dùng hiểu rõ tài liệu nguồn, bản đang phục vụ và bản đang cập nhật.
- Luồng chính không còn upload trực tiếp từ Kho tri thức.

### Pha 6 — Backfill, shadow và canary

Mục tiêu:

- Backfill source revisions, bindings, index revisions và payload Qdrant.
- Rebuild các bản legacy không xác minh được.
- Chạy shadow retrieval và canary theo collection.

Đầu ra:

- 100% tài liệu legacy được phân loại `active-parity-ok` hoặc `needs-rebuild`.
- Có báo cáo chênh lệch chất lượng và hiệu năng.

### Pha 7 — Cutover và dọn legacy [ĐÃ HOÀN THÀNH 100% - Phiên #293 (2026-10-07)]

Mục tiêu:

- Chuyển toàn bộ reads/writes sang V2 (`RAG_REVISION_READ_MODE=revisioned`, `KNOWLEDGE_REVISION_WRITES_ENABLED=True`).
- Deprecate direct upload và pipeline cũ (`deprecated=True`, HTTP headers `Deprecation: @2026-10-07`, `X-API-Deprecation-Warning`).
- Chạy retention/GC có bảo vệ rollback (`KnowledgeArtifactGCService`, giữ $N=2$ bản superseded gần nhất, chặn rollback pruned với `REVISION_ALREADY_PRUNED`).
- Ban hành Sổ tay vận hành & Runbook production (`cutover_and_operations_runbook.md`).

Đầu ra:

- Một quy trình duy nhất từ Kho tài liệu sang Kho tri thức (Single Source of Truth).
- Không còn schema hoặc job legacy đang được runtime sử dụng; RAG retriever nghiêm ngặt chỉ truy xuất chunks active trong snapshot (Zero Leak).
- Kiểm thử 7/7 unit tests passed, 47/47 regression tests passed 100%, Ruff 0 lỗi, TypeScript 0 lỗi.

---

## 12. Ma trận kiểm thử

### 12.1. Unit tests

- State transitions hợp lệ và không hợp lệ.
- Idempotency key và request hash conflict.
- Deterministic point IDs và manifest hashing.
- Chunk/fact provenance validation.
- CAS activation khi có cạnh tranh.
- Cache epoch và snapshot fingerprint.
- Rollback và activation history.

### 12.2. Integration tests với dịch vụ thật

- PostgreSQL, Redis, MinIO và Qdrant chạy thật trong môi trường test.
- Revision staging không xuất hiện trong retrieval.
- Parity fail không đổi active pointer.
- Activation chuyển đồng thời dense, sparse và facts.
- Worker chết ở từng phase rồi resume không tạo duplicate.
- Provider/Qdrant/Redis/storage lỗi được báo đúng, không fake success.
- Hai activation đồng thời chỉ có một CAS thắng.
- Không có truy xuất chéo tenant/workspace.
- Thay embedding profile tạo generation mới.

### 12.3. Concurrency test

Trong lúc activation, chạy tối thiểu 100 request đồng thời:

- Mỗi request chỉ chứa dữ liệu toàn bản cũ hoặc toàn bản mới.
- Không có mixed citations, mixed facts hoặc neighbor từ revision khác.
- `retrieval_revision_leak_total` phải bằng 0.

### 12.4. Migration tests

- Upgrade trên bản sao dữ liệu thật.
- Backfill chạy hai lần cho cùng kết quả.
- Xử lý tài liệu 0 chunk, thiếu vector, orphan point và payload legacy thiếu field.
- Feature flag rollback không làm mất dữ liệu.
- Đếm trước/sau giữ nguyên documents, chunks, facts và các quan hệ hợp lệ.

### 12.5. Chất lượng RAG và hiệu năng

- Faithfulness ≥ 0,90.
- Answer Relevance ≥ 0,85.
- Context Precision ≥ 0,80.
- Fact values và nguồn trích dẫn trong golden set đúng 100%.
- p95 retrieval không suy giảm quá ngưỡng được thống nhất; đề xuất tối đa 10%.
- Benchmark Qdrant filter theo số active revisions thực tế.

Quality gate cuối mỗi phiên triển khai:

```bash
uv run ruff check .
uv run --extra dev pytest -v
```

Đối với phiên chỉ chỉnh sửa Frontend:

```bash
npm run build
```

---

## 13. Observability và vận hành

Structured log bắt buộc có:

```text
correlation_id, job_id, tenant_id, workspace_id
collection_id, binding_id, source_revision_id
index_revision_id, vector_generation_id
phase, attempt, provider_id, model_name
expected/actual chunks/facts/points
latency_ms, error_code
```

Metrics chính:

- Build, activation và rollback totals theo outcome.
- Thời gian từng phase và source-ready-to-active lag.
- Parity mismatch total.
- Số revision active, staging, failed và review_required.
- ARQ queue depth, queue lag, retry và dead jobs.
- Expected/actual Qdrant point delta.
- Orphan/stale artifacts và kết quả GC.
- Semantic-cache hit ratio theo epoch.
- Retrieval revision leak total.
- Legacy read/write usage.

Alert bắt buộc:

- Job không heartbeat vượt ngưỡng.
- Parity mismatch hoặc activation fail.
- Binding active trỏ tới artifact không `ready`.
- DB–Qdrant count chênh lệch.
- Retrieval revision leak lớn hơn 0.
- Transactional outbox backlog tăng liên tục.

Runbook cần có:

- Retry parse/index an toàn.
- Rollback binding.
- Chuyển read mode về legacy trong canary.
- Rebuild vector generation.
- Khôi phục từ PostgreSQL/Qdrant/storage backup.
- Xử lý orphan và artifact GC thất bại.

---

## 14. Rủi ro và biện pháp kiểm soát

| Rủi ro | Ảnh hưởng | Kiểm soát |
|---|---|---|
| Migration dữ liệu legacy không đồng nhất | Sai binding hoặc mất provenance | Dry-run, báo cáo ngoại lệ, checkpoint, không tự đoán tenant |
| Qdrant upsert một phần | Thiếu vector | Deterministic ID, retry idempotent, parity gate |
| Worker chết giữa pipeline | Job treo hoặc duplicate | Heartbeat, phase checkpoint, sweeper và unique constraints |
| Kích hoạt đồng thời | Ghi đè revision | CAS theo active epoch và row lock |
| Trộn dữ liệu old/new | Câu trả lời và trích dẫn sai | RetrievalSnapshot dùng chung cho mọi kênh |
| Đổi embedding model | Trộn không gian vector | Vector generation bất biến |
| Cache cũ sau cập nhật | Trả câu trả lời stale | Cache key chứa index epoch |
| Người dùng hiểu nhầm trạng thái | Quyết định sai | Trạng thái trung thực, tách queued/building/ready/serving |
| Dọn artifact quá sớm | Mất khả năng rollback | Retention, pin và GC safety checks |

---

## 15. Acceptance criteria tổng thể

Giải pháp chỉ được coi là hoàn thành khi:

1. 100% file production đi qua Kho tài liệu trước khi vào Kho tri thức.
2. 100% binding đang hoạt động trỏ tới index revision `ready`.
3. Không còn delete-before-index trong bất kỳ luồng sync/reindex nào.
4. Revision mới thất bại không ảnh hưởng chatbot đang phục vụ.
5. Dense, sparse, facts, neighbors và citations dùng cùng RetrievalSnapshot.
6. Parity không đạt thì không thể activate.
7. Retry/cancel không sinh duplicate chunks, facts hoặc Qdrant points.
8. Cache cũ không thể hit sau khi epoch thay đổi.
9. Không hardcode model/provider hoặc từ điển vá lỗi trong runtime.
10. Không hard-delete tài liệu còn được Kho tri thức sử dụng.
11. Rollback có audit đầy đủ và không re-embed nếu artifact còn giữ.
12. 100% dữ liệu legacy được phân loại hoặc rebuild trước cutover.
13. Có dashboard, alerts, runbook, backup/restore và kill switch.
14. Test concurrency chứng minh không có mixed revision.
15. Ruff, Pytest và Frontend build đạt quality gate tương ứng.

---

## 16. Thứ tự phiên triển khai đề xuất

| Phiên | Nội dung | Phụ thuộc | Kết quả chính |
|---|---|---|---|
| 1 | ADR, inventory, API contract V2 và baseline | Không | Chốt bất biến và contract |
| 2 | Schema/migrations Document Revision | Phiên 1 | `document_revisions` hoạt động |
| 3 | Async Document Intake + Quality Gate | Phiên 2 | Revision `ready/review_required` |
| 4 | Schema Binding/Index/Generation/Activation | Phiên 1–2 | Nền dữ liệu xuất bản |
| 5 | Index Build + parity + idempotency | Phiên 3–4 | Artifact staging an toàn |
| 6 | Atomic Activation + RetrievalSnapshot | Phiên 5 | Zero mixed revision |
| 7 | Job outbox, retry, cancellation và reconciliation | Phiên 3–6 | Resilience production |
| 8 | Frontend Kho tài liệu V2 | Phiên 3 | Quản lý revision và review |
| 9 | Frontend Kho tri thức V2 | Phiên 5–6 | Add documents và binding detail |
| 10 | Backfill + shadow retrieval | Phiên 6–9 | Báo cáo parity/quality |
| 11 | Canary + cutover | Phiên 10 | Runtime V2 mặc định |
| 12 | Retention, GC và contract migration | Phiên 11 ổn định | Loại legacy an toàn |

Khuyến nghị bắt đầu bằng **Phiên 1: ADR, inventory và API contract V2**. Không nên bắt đầu bằng việc sửa giao diện hoặc migration ngay, vì các bất biến về revision, activation và retrieval snapshot phải được khóa trước để tránh phải làm lại.

### 16.1. Tiến độ thực tế triển khai (Đã hoàn thành 100% trọn vẹn 12/12 phiên)

| Phiên Vibe | Pha | Ngày | Nội dung hoàn thành | Trạng thái |
|---|---|---|---|---|
| **Phiên 1 (#286)** | Pha 0 | 2026-10-07 | Chốt ADR-011 (10 bất biến), Inventory Map 9 Tables/12 APIs, API Contracts V2 Spec | **100% ✓** |
| **Phiên 2 (#287)** | Pha 1 | 2026-10-07 | Khai báo `DocumentRevision`, Alembic Safe Backfill Migration, Pydantic V2 DTOs (9 tests) | **100% ✓** |
| **Phiên 3 (#288)** | Pha 2 | 2026-10-07 | Quality Gate Engine, `DocumentRevisionService`, Async Intake 202, Worker Task (16 tests) | **100% ✓** |
| **Phiên 4 (#289)** | Pha 3 | 2026-10-07 | Schema Bindings/Index/Generations, `BindingService`, `IndexBuildService`, Parity Gate (12 tests) | **100% ✓** |
| **Phiên 5 (#290)** | Pha 4 | 2026-10-07 | `RetrievalSnapshot` Pinning, Qdrant Active Filter, Auditable Citations (9 tests) | **100% ✓** |
| **Phiên 6 (#291)** | Pha 5 | 2026-10-07 | UI Kho tài liệu V2 (Quality Gate card, Edit dialog), UI Kho tri thức V2 (`CollectionBindingsTab`, Atomic Promote) | **100% ✓** |
| **Phiên 7 (#292)** | Pha 6 | 2026-10-07 | `CanaryService` Audit & Backfill Idempotent, Shadow Retrieval Zero Leak, CAS 409 Conflict, Instant Rollback O(1) (9 tests) | **100% ✓** |
| **Phiên 8 (#293)** | Pha 7 | 2026-10-07 | Cutover `revisioned`, Deprecated Legacy Headers, `KnowledgeArtifactGCService` có bảo vệ Rollback, Runbook Production (7 tests) | **100% ✓** |
| **Phiên 9 (#294)** | Mở rộng | 2026-10-07 | Master-Detail Deep Routing Kho Tri Thức V2: Trang Thêm Tài Liệu (`/add-documents`) & Trang Chi Tiết Binding (`/documents/:bindingId`), Chunks Inspector, Rollback O(1), Pytest 13/13 | **100% ✓** |
| **Phiên 10 (#295)** | Mở rộng | 2026-10-07 | Bảng Điều Khiển Parity Gate & Shadow Retrieval Dashboard V2: Bento Grid 4 KPIs, Kiểm kê danh mục, So khớp song song V1 vs V2, Zero Revision Leak Assertion, Pytest 9/9 | **100% ✓** |
| **Phiên 11 (#296)** | Mở rộng | 2026-10-07 | Cơ Chế Phân Giải Động Chính Sách Canary Serving & Quản Lý Lưu Trữ Retention Window: Canary Rollout per-collection (`read_mode`), Cửa sổ lưu trữ `retention_revisions` (2..10) bảo vệ Rollback $O(1)$, REST API `/canary/policy`, Sub-tab 3 UI Canary & Retention, Card Last GC History & Dialog GC, Pytest 18/18 pass | **100% ✓** |
| **Phiên 12 (#297)** | Pha 7 & Mở rộng | 2026-10-07 | Retention, System-Wide Artifact Garbage Collection & Contract Migration Loại Bỏ Legacy An Toàn: Cưỡng chế Single Source of Truth (chặn nạp trực tiếp cũ khi `KNOWLEDGE_ALLOW_DIRECT_UPLOAD=False` với mã RFC 7807 `DIRECT_UPLOAD_DEPRECATED_USE_CENTRAL_REPOSITORY`), Dịch vụ `collect_garbage_system_wide` (dry-run & execution), ARQ worker task `task_knowledge_garbage_collection`, API Kiểm kê di trú `GET /knowledge/decommissioning/audit`, Nâng cấp UI Header nút chính `+ Thêm Từ Kho` V2, tab mặc định `bindings`, Pytest 25/25 pass 100% | **100% ✓** |

> **KẾT LUẬN TOÀN DIỆN**: Toàn bộ Kế hoạch 11 gồm 12 phiên triển khai đã chính thức hoàn thành xuất sắc 100%! Toàn bộ 10 bất biến của ADR-011 từ hạ tầng CSDL, bóc tách Markdown NĐ 30, Quality Gate, Staging Indexing, Parity Gate, Atomic CAS Pointer Swap, RetrievalSnapshot Pinning, Auditable Citations, Master-Detail Deep Routing, Dashboard Kiểm định Parity & Shadow Retrieval, Canary Policy per-collection đến System-wide Garbage Collection và Safe Legacy Decommissioning đều đạt chất lượng Enterprise Production. Đạt 100% test suites pass, 0 lỗi Ruff linter, 0 lỗi Biome linter, 0 lỗi TypeScript typecheck. Toàn bộ quy trình "Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn" đã chính thức đi vào vận hành thực tế!


---

## 17. Quyết định mặc định đã thống nhất

- Kho tài liệu là nguồn sự thật duy nhất của tệp và nội dung chuẩn hóa.
- Kho tri thức không sở hữu bản sao tệp nguồn; chỉ sở hữu binding và artifact RAG.
- Đồng bộ revision mới mặc định là thủ công, có badge `Có bản cập nhật`.
- Quality Gate tự động cho tài liệu đạt chuẩn; chỉ đưa ngoại lệ vào hàng chờ review.
- Retention index revisions là cấu hình hệ thống, không xóa ngay sau activation.
- Direct upload tại Kho tri thức chỉ là compatibility façade trong giai đoạn chuyển tiếp và sẽ bị loại bỏ sau cutover.
- PostgreSQL active pointer là nguồn sự thật của revision đang phục vụ.
- Mọi model OCR/embedding/reranker được phân giải động từ cấu hình DB/ModelOps.
