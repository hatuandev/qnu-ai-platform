# ADR-012: Tách Rời Kho Tài Liệu Thuần Lưu Trữ & Chuyển Toàn Bộ Document Intelligence Vào Kho Tri Thức Đa Embedding

- **Trạng thái**: **ACCEPTED** (Đã thông qua, Supersedes một phần ADR-011)
- **Ngày quyết định**: 2026-10-10
- **Kiến trúc sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phạm vi tác động**: Phân hệ Kho Tài Liệu (`/documents`), Phân hệ Kho Tri Thức (`/knowledge`), Document Ingestion Workers, ModelOps & Hybrid RAG Engine

---

## 1. Bối Cảnh & Vấn Đề Phát Sinh Từ ADR-011

Trong [ADR-011](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md), hệ thống đã thiết lập nguyên tắc quản lý phiên bản bất biến (`document_revisions`) và quy trình xuất bản Staging / Parity Gate / CAS an toàn. Tuy nhiên, sau quá trình kiểm thử thực tế và vận hành thử nghiệm quy mô lớn tại Trường Đại học Quy Nhơn, mô hình phân chia trách nhiệm của ADR-011 bộc lộ 4 điểm nghẽn nghiêm trọng:

1. **Kho Tài Liệu bị quá tải và nhập nhằng trách nhiệm miền (Storage Domain Overburden)**:
   - Theo ADR-011, Kho Tài Liệu phải chịu trách nhiệm bóc tách nội dung, chạy OCR, nhận diện bố cục bảng biểu, chuẩn hóa Unicode NFC và quản lý Quality Gate.
   - Khi cán bộ tải lên 100 tài liệu tuyển sinh hoặc học vụ vào Kho Tài Liệu, hàng trăm job OCR/Worker bị kích hoạt cùng lúc, khiến hàng đợi bị nghẽn trong nhiều giờ dù quản trị viên chưa hề có nhu cầu đưa toàn bộ tài liệu này vào bất kỳ Kho Tri Thức nào.
   - Kho Tài Liệu đáng lẽ chỉ là kho lưu trữ tệp tin thuần túy (Storage Repository), nhưng lại bị biến thành một "Document Intelligence Processor" cồng kềnh.
2. **Khóa chặt vào một mô hình Embedding duy nhất (Single-Vector Monolithic Ingestion)**:
   - Trong ADR-011, quy trình từ bóc tách nội dung tới embedding bị gắn chặt theo chuỗi một chiều.
   - Khi Kho Tri Thức muốn thử nghiệm hoặc chuyển đổi mô hình Embedding mới (ví dụ từ `bge-m3` sang `qwen3-embedding-4b` trên GPU RTX 5090 hoặc OpenRouter Cloud), hệ thống có nguy cơ phải kích hoạt lại toàn bộ luồng bóc tách/OCR rất tốn kém tài nguyên máy tính.
3. **Liên kết nhóm nguồn lâu dài quá phức tạp và dễ phát sinh lỗi đồng bộ ngầm**:
   - Khái niệm liên kết nhóm nguồn lâu dài (`KnowledgeGroupSource`) đòi hỏi cơ chế so khớp diff liên tục giữa các nhóm tài liệu và kho tri thức, tạo ra nhiều trường hợp biên (edge cases) phức tạp về xung đột quyền sở hữu (ownership conflict) và trạng thái mồ côi khi tài liệu bị sửa đổi.
4. **Vi phạm nguyên tắc phân định miền (Domain Boundary Violation)**:
   - Kho Tài Liệu phải hiển thị card "Kho Tri Thức đang gắn", phải biết kho nào đang sử dụng tệp nào.
   - Ràng buộc khóa ngoại Foreign Key cascade giữa Documents và Knowledge tạo ra rủi ro: việc thao tác trên Kho Tài Liệu có thể ảnh hưởng ngoài ý muốn tới dữ liệu tri thức đang phục vụ RAG.

---

## 2. Quyết Định Kiến Trúc Mới (ADR-012 Decisions)

Hệ thống QNU AI Platform chính thức thiết lập mô hình kiến trúc **"Kho Tài Liệu Thuần Lưu Trữ – Kho Tri Thức Sở Hữu Document Intelligence & Đa Embedding" (Decoupled Storage Repository & Knowledge-Owned Multi-Embedding Pipeline)** với các quyết định cốt lõi sau:

### 2.1. Supersede ADR-011 (Những phần được thay thế)
- **Supersedes Quyết định 1 của ADR-011**: Kho Tài Liệu **không còn** chịu trách nhiệm bóc tách nội dung, OCR, chuẩn hóa Markdown, Quality Gate hay gắn nhãn trạng thái xử lý RAG. Toàn bộ Document Intelligence được chuyển giao 100% cho Kho Tri Thức.
- **Supersedes Quyết định 2 của ADR-011**: `document_revisions` chứa `canonical_markdown` được chuyển đổi thành `repository_file_revisions` thuần tệp trong Kho Tài Liệu. Trong khi đó, `knowledge_source_revisions` thuộc chủ quyền miền Kho Tri Thức sẽ quản lý chuỗi phiên bản Markdown bóc tách.
- **Supersedes Quyết định 3 của ADR-011**: Xóa bỏ liên kết nhóm nguồn lâu dài (`KnowledgeGroupSource`). Thay thế bằng cơ chế **Nhập Snapshot Thủ Công Theo Batch (Manual Batch Snapshot Import)** độc lập một chiều.
- **Bãi bỏ Foreign Key CASCADE**: Xóa tài liệu khỏi Kho Tài Liệu tuyệt đối **không** làm mất hoặc ảnh hưởng tới các snapshot tri thức đã được xuất bản trong Kho Tri Thức.

### 2.2. Giữ nguyên vẹn các bất biến xuất sắc của ADR-011
ADR-012 tái khẳng định và kế thừa 100% các bất biến sau của ADR-011:
1. **Dựng chỉ mục tại Staging & Parity Gate**: Mọi cập nhật vector đều qua Staging và chỉ được kích hoạt khi đạt 100% tỷ lệ so khớp giữa PostgreSQL và Qdrant.
2. **Compare-and-Swap (CAS) Atomic Pointer Swap**: Kích hoạt index mới nguyên tử qua con trỏ phiên bản, không downtime, không rò rỉ trạng thái trung gian.
3. **RetrievalSnapshot Pinning**: Đóng băng phiên bản tri thức theo từng phiên hội thoại RAG đa lượt để chống trôi dạt ngữ cảnh.
4. **Instant Rollback $O(1)$ & Quản lý Retention Window**: Cho phép quay lại phiên bản chỉ mục trước đó ngay lập tức mà không cần tính toán lại vector.
5. **Idempotency & Tenant Isolation**: Mọi tác vụ batch, item, upload đều được cô lập tuyệt đối theo `tenant_id` và `workspace_id`.

---

## 3. Các Trụ Cột Kiến Trúc Của ADR-012

### 3.1. Trụ cột 1: Kho Tài Liệu Thuần Lưu Trữ Tệp (Pure Storage Repository)
- **Trách nhiệm duy nhất**:
  - Quản lý các Kho logic (`DocumentGroup`: Tuyển sinh, Đào tạo, Công tác sinh viên,...).
  - Lưu tệp nhị phân gốc an toàn trên MinIO S3 theo đường dẫn cô lập `documents/{tenant_id}/{workspace_id}/originals/{file_hash}/{safe_file_name}`.
  - Tính toán SHA-256 chống trùng lặp trong phạm vi workspace.
  - Quản lý metadata danh mục hành chính người dùng nhập (số hiệu, cơ quan ban hành, ngày ban hành,...).
  - Quản lý phiên bản tệp gốc bất biến qua `RepositoryFileRevision`.
- **Tuyệt đối cấm**: Không tự ý OCR, không gọi parser, không sinh job ARQ bóc tách khi upload. Khi tải xong, API trả về HTTP 201/200 với trạng thái `stored` tức thì.

### 3.2. Trụ cột 2: Kho Tri Thức Sở Hữu Toàn Bộ Document Intelligence
- **Trách nhiệm**:
  - Chủ động hiển thị danh sách ứng viên từ Kho Tài Liệu (Candidate Picker) kèm bộ lọc 2 chiều: **Trạng thái nguồn** (`Chưa có`, `Đã có`, `Cần cập nhật`, `Đang xử lý`, `Lỗi`) và **Trạng thái vector theo generation** (`Đã lập chỉ mục`, `Chưa lập chỉ mục`,...).
  - Chụp snapshot độc lập một chiều tại thời điểm nạp (Provenance: `origin_document_id`, `origin_file_hash`, `origin_group_id`).
  - Thực thi toàn bộ pipeline: Parse/OCR $\rightarrow$ Chuẩn hóa Unicode NFC/Markdown sạch $\rightarrow$ Quality Gate $\rightarrow$ Hiệu đính $\rightarrow$ Phê duyệt $\rightarrow$ Chunking $\rightarrow$ Structured Facts $\rightarrow$ Vector Generations $\rightarrow$ Qdrant.

### 3.3. Trụ cột 3: Nguyên Tắc "Parse Once, Embed Many"
Tách biệt chuỗi dữ liệu thành 3 tầng độc lập:
1. **Tầng Nội Dung Chuẩn Hóa (`KnowledgeSourceRevision`)**:
   - Lưu trữ Canonical Markdown, Page Manifest, Citation Metadata, và Quality Gate Report trong PostgreSQL.
   - Bóc tách một lần duy nhất theo `source_artifact_key = SHA-256(source_file_hash + parser_profile_hash + normalizer_version)`.
2. **Tầng Phân Đoạn & Tri Thức Có Cấu Trúc (`KnowledgeChunkSet`)**:
   - Lưu trữ các đoạn chunks và Structured Facts trong PostgreSQL.
   - Xác định theo `chunk_set_key = SHA-256(knowledge_source_revision_id + chunk_strategy + chunk_config_hash)`.
3. **Tầng Không Gian Vector Đa Thế Hệ (`KnowledgeVectorGeneration`)**:
   - Quản lý chỉ mục vector trên Qdrant theo từng cấu hình mô hình từ ModelOps (`vector_artifact_key`).
   - **Khi thay đổi mô hình Embedding**: Hệ thống tái sử dụng 100% `KnowledgeChunkSet` có sẵn để sinh vector mới vào Qdrant, **tuyệt đối không chạy lại OCR/Parser**.

---

## 4. Mô Hình Dữ Liệu Additive Mới

```text
DocumentGroup
  └── RepositoryDocument
        └── RepositoryFileRevision (phiên bản tệp gốc thuần túy)
                │ (Snapshot thủ công, provenance một chiều)
                ▼
KnowledgeImportBatch
  └── KnowledgeImportItem
        └── KnowledgeBinding (Nguồn tri thức trong Collection)
              └── KnowledgeSourceRevision (Markdown chuẩn, Quality Gate)
                    └── KnowledgeChunkSet (Chunks + Facts)
                          ├── Vector Generation 1 (BGE-M3 1024D)
                          └── Vector Generation 2 (Qwen3 2560D)
```

1. **`repository_file_revisions`**: Lưu chuỗi phiên bản tệp gốc nguyên bản.
2. **`knowledge_import_batches`**: Điều phối batch nạp tài liệu từ kho vào collection.
3. **`knowledge_import_items`**: Quản lý vòng đời xử lý từng tài liệu trong batch (tránh all-or-nothing, cho phép partial failure và retry từng tệp).
4. **`knowledge_source_revisions`**: Quản lý phiên bản Markdown sạch, provenance và Quality Gate trong domain Knowledge.
5. **`knowledge_chunk_sets`**: Tách tập chunks và facts độc lập để tái sử dụng cho nhiều thế hệ vector.

---

## 5. Kế Hoạch Chuyển Đổi An Toàn (Additive Cutover Strategy)

- **Nguyên tắc Additive-First**: Trong các phiên đầu tiên, toàn bộ bảng và cột mới được tạo bổ sung. Không drop bất kỳ bảng (`document_revisions`, `knowledge_group_sources`) hay cột legacy nào.
- **Backfill Dữ Liệu**: Tại Phiên 8, dữ liệu hiện hữu sẽ được di trú an toàn (backfill) sang cấu trúc mới trước khi chính thức decommission code legacy.
- **Zero Downtime**: Đảm bảo toàn bộ hệ thống Chatbot và Hybrid RAG hiện hành tiếp tục hoạt động liên tục 24/7 trong suốt quá trình nâng cấp.
