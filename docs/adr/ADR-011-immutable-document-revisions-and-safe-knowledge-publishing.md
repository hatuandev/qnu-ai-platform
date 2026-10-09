# ADR-011: Tiếp Nhận Một Lần, Quản Lý Revision Bất Biến & Xuất Bản Tri Thức RAG An Toàn

- **Trạng thái**: **ACCEPTED** (Đã thông qua)
- **Ngày quyết định**: 2026-10-07
- **Kiến trúc sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phạm vi tác động**: Phân hệ Kho Tài Liệu Tập Trung (`/documents`), Phân hệ Kho Tri Thức (`/knowledge`), Hybrid RAG Engine, Worker Jobs & ModelOps

---

## 1. Bối Cảnh (Context)

Nền tảng **QNU AI Platform** đã hoàn thành bước đột phá đầu tiên về quản lý tài sản số tập trung tại phiên #283 và #285:
- Triển khai **Kho Tài Liệu Tập Trung** (`repository_documents`) lưu trữ tệp gốc vào MinIO S3, tính toán SHA-256 chống trùng lặp, tiền bóc tách sang Markdown sạch và tự động nhận diện metadata hành chính theo Nghị định 30/2020/NĐ-CP.
- Cho phép gắn tài liệu từ Kho Tài Liệu vào Kho Tri Thức qua `repository_document_id`.

Tuy nhiên, khi vận hành quy mô sản xuất lớn (Production-Scale Enterprise RAG), hệ thống đối mặt với 6 rủi ro kiến trúc cốt tử:

1. **Ghi đè nội dung bóc tách (Destructive Overwrite)**: `repository_documents` chỉ lưu một chuỗi `parsed_markdown` duy nhất. Khi người dùng reparse hoặc hiệu đính văn bản, phiên bản cũ bị ghi đè, làm mất vết lịch sử pháp lý và không thể đối soát lại các trích dẫn cũ.
2. **Hai luồng nạp song song (Split-Brain Ingestion)**: Kho Tri Thức vừa hỗ trợ tải tệp trực tiếp (`/collections/{id}/documents`), vừa hỗ trợ gắn từ Kho Tài Liệu, dẫn đến nguy cơ bóc tách lặp lại gây lãng phí tài nguyên GPU và không đồng nhất chất lượng Markdown.
3. **Mất an toàn khi tái lập chỉ mục (Delete-Before-Index Vulnerability)**: Luồng reindex cũ xóa vector/chunks trước khi tạo bản mới. Nếu worker gặp sự cố giữa chừng, toàn bộ tri thức của collection bị rỗng khiến trợ lý AI rơi vào trạng thái No-Answer.
4. **Lệch pha truy hồi đa kênh (Cross-Channel Retrieval Drift & Mixed Citations)**: Dense retrieval (Qdrant), Sparse retrieval (PostgreSQL FTS), và Structured Fact Layer tra cứu độc lập mà không có một con trỏ snapshot chung. Điều này dẫn đến lỗi ảo giác nghiêm trọng: câu trả lời được sinh từ chunk mới nhưng bảng số liệu hoặc trích dẫn pháp lý lại trỏ về tài liệu cũ.
5. **Ô nhiễm không gian vector khi đổi mô hình (Vector Space Contamination)**: Khi thay đổi mô hình Embedding trên Kho Tri Thức, nếu không tách bạch không gian vector, các điểm vector từ 2 mô hình khác nhau có thể cùng tồn tại, phá hủy độ chính xác của khoảng cách Cosine.
6. **Thiếu tính lũy thừa và khả năng chịu lỗi (Lack of Idempotency & Transactional Dispatch)**: Khi worker bị dừng đột ngột (restart, cúp điện, OOM), hệ thống thiếu cơ chế checkpoint từng phase và transactional outbox để resume an toàn.

---

## 2. Quyết Định Kiến Trúc (Architecture Decisions)

Hệ thống QNU AI Platform chính thức áp dụng mô hình kiến trúc **"Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn" (Single-Intake, Immutable Document Revisions & Atomic Knowledge Publishing)** với 8 quyết định nền tảng:

### Quyết định 1: Phân định ranh giới trách nhiệm duy nhất (Single Source of Truth)
- **Kho Tài Liệu (`repository_documents`)**: Là Nguồn Sự Thật Duy Nhất quản lý tệp gốc, checksum SHA-256, chuỗi các phiên bản nội dung bất biến (`document_revisions`), quá trình bóc tách OCR/Markdown, Unicode NFC, page manifest và metadata hành chính NĐ 30.
- **Kho Tri Thức (`knowledge_collections`)**: Không sở hữu tệp nguồn; chỉ sở hữu quan hệ sử dụng (`knowledge_bindings`) và các artifact RAG đã xuất bản (`knowledge_index_revisions`, chunks, facts, vectors).
- **Loại bỏ luồng Upload trực tiếp tại Kho Tri Thức**: Kho Tri Thức chỉ xuất bản từ các source revision đã đạt trạng thái `ready` của Kho Tài Liệu.

### Quyết định 2: Quản lý phiên bản nguồn bất biến (`document_revisions`)
- Mỗi lần tải tệp mới hoặc hiệu đính nội dung sẽ sinh ra một `DocumentRevision` mới độc lập (`rev_1`, `rev_2`,...).
- Một revision khi đã chuyển sang trạng thái `ready` sẽ bị **khóa cứng (immutable)**; tuyệt đối không cập nhật nội dung tại chỗ (`UPDATE canonical_markdown`). Nếu cần sửa đổi, bắt buộc phải tạo revision mới kế thừa (`based_on_revision_id`).
- State machine chuẩn: `queued → processing → validating → (ready | review_required)`.

### Quyết định 3: Mô hình liên kết tri thức (`knowledge_bindings`)
- Một tài liệu nguồn được sử dụng trong một Kho Tri Thức thông qua một bản ghi `knowledge_bindings`.
- Binding quản lý:
  - `desired_source_revision_id`: Revision nguồn mà quản trị viên muốn áp dụng.
  - `active_index_revision_id`: Artifact RAG hiện đang thực sự phục vụ cho các truy vấn của Chatbot.
  - `sync_policy`: Mặc định là `manual` (hiển thị nhãn `Có bản cập nhật` để cán bộ chủ động duyệt xuất bản); tùy chọn `auto_safe` trong tương lai.

### Quyết định 4: Không gian Vector độc lập (`knowledge_vector_generations`)
- Mỗi khi Kho Tri Thức thay đổi cấu hình mô hình Embedding (hoặc dimension, distance metric), hệ thống bắt buộc phải khởi tạo một `knowledge_vector_generations` mới (`generation_no` tăng tiến).
- Tuyệt đối không xóa hay ghi đè lên collection Qdrant hiện tại cho đến khi generation mới hoàn tất và được kích hoạt.

### Quyết định 5: Dựng chỉ mục tại Staging & Kiểm soát cổng chất lượng (Parity Gate)
- Khi nạp hoặc đồng bộ tài liệu, hệ thống dựng một `knowledge_index_revisions` hoàn toàn mới ở chế độ **Staging** (chưa phục vụ).
- Trước khi được phép kích hoạt, revision mới phải vượt qua **Parity Gate** nghiêm ngặt:
  1. `chunk_count` thực tế khớp 100% với expected count và $> 0$.
  2. Số lượng vector trong Qdrant khớp 100% với số chunks trong PostgreSQL.
  3. Tập `(chunk_id, content_hash)` khớp chính xác tuyệt đối giữa hai cơ sở dữ liệu.
  4. Vector dimension đúng chuẩn thế hệ embedding hiện hành.
  5. Mọi facts và trích dẫn đều có provenance truy ngược được về đúng source revision.
- Nếu Parity Gate thất bại, revision mới chuyển sang trạng thái `failed`; hệ thống giữ nguyên vẹn phiên bản đang phục vụ cũ.

### Quyết định 6: Kích hoạt nguyên tử (Atomic Pointer Swap CAS)
- Việc xuất bản revision mới được thực hiện bằng một thao tác **Compare-And-Swap (CAS)** nguyên tử duy nhất trên PostgreSQL:
  ```sql
  UPDATE knowledge_bindings
  SET active_index_revision_id = :new_index_revision_id,
      active_epoch = active_epoch + 1,
      updated_at = NOW()
  WHERE id = :binding_id AND active_epoch = :expected_epoch;
  ```
- Nguồn sự thật của trạng thái đang phục vụ nằm ở **PostgreSQL Active Pointer**, không nằm ở cờ bật/tắt trong Qdrant.
- Mọi lần thay đổi con trỏ đều được ghi nhận vào bảng nhật ký bất biến `knowledge_index_activations`, cho phép **Rollback tức thì (0ms latency)** về phiên bản cũ mà không cần re-embed nếu artifact còn trong thời hạn lưu giữ (retention).

### Quyết định 7: Truy hồi đồng bộ qua `RetrievalSnapshot`
- Mọi câu hỏi RAG gửi tới hệ thống bắt buộc phải giải nén một `RetrievalSnapshot` cố định:
  `RetrievalSnapshot = { tenant_id, collection_id, vector_generation_id, index_epoch, active_index_revision_ids }`
- Snapshot này được truyền đồng nhất vào:
  - Qdrant Dense Retrieval: Filter `vector_generation_id` & `index_revision_id IN (...)`.
  - PostgreSQL Sparse Retrieval: Filter `KnowledgeChunk.index_revision_id IN (...)`.
  - Structured Fact Layer: Filter `KnowledgeFact.index_revision_id IN (...)`.
  - Neighbor Chunk Expansion & Citations: Chỉ mở rộng trong cùng `index_revision_id`.
- Semantic Cache Key được bổ sung `index_epoch`, bảo đảm cache tự động vô hiệu hóa ngay khi có bất kỳ tài liệu nào kích hoạt revision mới.

### Quyết định 8: Transactional Outbox & Dynamic ModelOps
- Các lệnh tạo Job được commit trong cùng một database transaction với bản ghi nghiệp vụ (`Transactional Outbox Pattern`), đảm bảo không có job mồ côi khi hạ tầng Redis/ARQ gặp sự cố.
- 100% tên mô hình (OCR, Embedding, Reranker) và API key được phân giải động qua CSDL ModelOps, tuân thủ Tôn chỉ 6 & 9 của `AGENTS.md`.

---

## 3. Mười Bất Biến Bắt Buộc Của Hệ Thống (The 10 Invariants)

1. **Source Immutability**: Revision nguồn đã `ready` là bất biến 100%; mọi sửa đổi đều sinh revision mới.
2. **Artifact Immutability**: `KnowledgeIndexRevision` đã xuất bản là artifact bất biến.
3. **Zero-Downtime Reindexing**: Tuyệt đối không xóa bản đang phục vụ trước khi bản mới vượt qua Parity Gate.
4. **Single Active Pointer**: Tại một thời điểm, một binding chỉ có đúng 1 active index revision.
5. **Snapshot Consistency**: Dense, Sparse, Facts, Neighbors và Citations bắt buộc dùng chung một `RetrievalSnapshot`.
6. **Vector Space Invariance**: Đổi mô hình embedding hoặc dimensions bắt buộc phải sinh `vector_generation` mới.
7. **Zero Hardcoded Models**: Tên mô hình và nhà cung cấp được phân giải động từ ModelOps DB runtime.
8. **Idempotent Retry**: Thực thi lại cùng `Idempotency-Key` tuyệt đối không sinh trùng lặp revision, chunks, facts, hoặc vectors.
9. **Tenant Isolation**: Mọi truy vấn, ràng buộc unique và vector payload bắt buộc phân lập theo `tenant_id` và `workspace_id`.
10. **Referential Integrity**: Tuyệt đối không hard-delete tài liệu nguồn đang còn binding hoạt động hoặc có lịch sử kích hoạt cần bảo toàn.

---

## 4. Mô Hình Dữ Liệu Thực Thể (Entity-Relationship Overview)

```text
RepositoryDocument (Tài liệu logic)
    ├── DocumentRevision (v1, v2 - Nguồn nội dung bất biến)
            └── KnowledgeBinding (Liên kết với Collection)
                    ├── KnowledgeIndexRevision (Artifact RAG: Chunks + Facts + Vectors)
                    └── KnowledgeIndexActivation (Lịch sử kích hoạt & Rollback)

KnowledgeCollection (Kho tri thức)
    ├── KnowledgeVectorGeneration (Không gian vector bất biến: bge-m3, qwen3...)
    └── KnowledgeBinding (Danh sách tài liệu liên kết)
```

---

## 5. Hậu Quả & Đánh Đổi (Consequences & Trade-offs)

### Mặt tích cực:
- **Độ tin cậy tuyệt đối (99.99% Availability)**: Reindex hoặc đồng bộ lỗi hoàn toàn vô hại với chatbot đang phục vụ.
- **Triệt tiêu ảo giác trích dẫn**: 100% minh chứng trích dẫn và bảng số liệu đều đồng pha với câu trả lời.
- **Rollback 0 giây**: Quay về phiên bản tri thức cũ ngay lập tức bằng việc trỏ lại con trỏ CAS mà không tốn chi phí gọi GPU/Embedding.
- **Minh bạch kiểm toán (Auditability)**: Mọi thao tác xuất bản, sửa đổi, ai duyệt, vào lúc nào đều có vết lịch sử rõ ràng.

### Đánh đổi kỹ thuật:
- **Dung lượng lưu trữ**: Do lưu giữ cả bản cũ để hỗ trợ rollback, dung lượng bảng `knowledge_chunks` và số point Qdrant sẽ tăng. Cần áp dụng chính sách Retention (giữ tối đa 2 revisions/binding: 1 active, 1 previous) và job dọn rác bất đồng bộ `knowledge_artifact_gc`.
- **Độ phức tạp điều phối**: Pipeline xử lý cần qua Staging $\rightarrow$ Parity Gate $\rightarrow$ CAS Swap thay vì ghi thẳng vào DB như trước.

---

## 6. Lộ Trình Áp Dụng (Implementation Roadmap)

ADR-011 này là văn kiện nền tảng để triển khai tuần tự **12 Phiên Làm Việc** được định nghĩa trong [Kế Hoạch Triển Khai](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/11_ke_hoach_trien_khai_quy_trinh_tiep_nhan_mot_lan_xuat_ban_tri_thuc_an_toan.md), bắt đầu từ việc chuẩn hóa Contract V2 và mở rộng Schema `document_revisions`.
