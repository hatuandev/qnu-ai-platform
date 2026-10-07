# Kế Hoạch Triển Khai: Kho Tài Liệu Tập Trung (Central Document Repository) & Tích Hợp Kho Tri Thức (QNU AI Platform)

- **Mục tiêu**: Xây dựng phân hệ quản lý lưu trữ tập trung tài liệu số của Trường Đại học Quy Nhơn trên **MinIO S3 Object Storage**, tự động bóc tách sơ bộ cấu trúc sang Markdown sạch & bảng biểu, và cung cấp cơ chế gắn kết (attach/bind) linh hoạt vào các **Kho Tri Thức (`/knowledge`)** để nạp vào cơ sở dữ liệu Vector (`Qdrant`) mà không phải tải lên hoặc bóc tách lại nhiều lần.
- **Tôn chỉ kiến trúc**: Tuân thủ nghiêm ngặt `AGENTS.md` (Clean Architecture 4-file Backend, 3-Tier Component Frontend, MinIO S3 Native Storage, Vector Invariance, Zero-Emoji, 100% Lucide Icons, 0 Lint Errors).

---

## 1. Kiến Trúc Hai Tầng (Two-Tier Decoupled Architecture)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    TẦNG 1: KHO TÀI LIỆU TẬP TRUNG                           │
│                   (Central Document Repository - /documents)                 │
│                                                                              │
│  • Lưu trữ Object Storage (MinIO S3): documents/originals/{hash}/{filename} │
│  • Deduplication chống trùng lặp: Tính SHA-256 trước khi lưu                 │
│  • Pre-parsing & OCR Pipeline: Bóc tách trước sang Markdown Unicode NFC      │
│  • Metadata Hành chính & Pháp quy: Số hiệu, Ngày ban hành, Cơ quan, NĐ 30    │
│  • Render xem trước trang PDF: documents/renders/{hash}/page_{n}.png         │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │ 1-Click Attach & Inherit Parsed MD │
                    │ (0s Chờ OCR - 0 Chi phí GPU/API)    │
                    ▼                                     ▼
┌───────────────────────────────────────┐ ┌────────────────────────────────────┐
│ TẦNG 2A: KHO TRI THỨC TUYỂN SINH      │ │ TẦNG 2B: KHO TRI THỨC HỌC VỤ       │
│ (/knowledge/col_admissions)           │ │ (/knowledge/col_regulations)       │
│                                       │ │                                    │
│ • Chunking: ClauseBasedChunker (Điều) │ │ • Chunking: SemanticChunker        │
│ • Vector Model: BGE-M3 (1024D)        │ │ • Vector Model: Qwen3-Embedding    │
│ • Vector DB: Qdrant Collection A      │ │ • Vector DB: Qdrant Collection B   │
│ • Fact Layer: Bảng học phí, chỉ tiêu  │ │ • Fact Layer: Quy chuẩn rèn luyện  │
└───────────────────────────────────────┘ └────────────────────────────────────┘
```

---

## 2. Thiết Kế Cơ Sở Dữ Liệu (Database Schema)

### A. Bảng mới: `repository_documents`
Lưu trữ thông tin văn bản gốc, metadata hành chính, đường dẫn MinIO và nội dung đã bóc tách.

```python
class RepositoryDocument(Base):
    __tablename__ = "repository_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # rep_doc_{uuid12}
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf, docx, xlsx, txt...
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # SHA-256
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO S3 Key

    # Metadata Hành chính & Pháp quy
    document_type_code: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("platform_document_types.code", ondelete="SET NULL"), nullable=True, index=True
    )
    document_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)  # Vd: 2139/QĐ-ĐHQN
    issuing_authority: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Vd: Trường Đại học Quy Nhơn
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Ngày ban hành
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # Ngày có hiệu lực

    # Trạng thái bóc tách & Bộ nhớ đệm (Pre-parse Cache)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)  # pending, parsing, parsed, failed
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)  # qwen3-vl:8b, pymupdf...
    parsed_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)  # Nội dung Markdown đã làm sạch
    
    # Metadata mở rộng (JSONB)
    doc_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    document_type: Mapped[DocumentType | None] = relationship("DocumentType")
    knowledge_documents: Mapped[list[KnowledgeDocument]] = relationship("KnowledgeDocument", back_populates="repository_document")
```

### B. Mở rộng bảng `knowledge_documents` (Kho Tri Thức)
Thêm trường khóa ngoại tham chiếu sang `repository_documents`:

```python
# Trong KnowledgeDocument:
repository_document_id: Mapped[str | None] = mapped_column(
    String(64),
    ForeignKey("repository_documents.id", ondelete="SET NULL"),
    nullable=True,
    index=True,
)

# Relationship
repository_document: Mapped[RepositoryDocument | None] = relationship(
    "RepositoryDocument", back_populates="knowledge_documents"
)
```

---

## 3. Kế Hoạch Triển Khai Backend (Clean 4-File Architecture)

Tạo module mới tại `backend/app/modules/documents/`:

### A. `models.py`
- Khai báo thực thể `RepositoryDocument` như thiết kế trên.

### B. `schemas.py`
- `RepositoryDocumentResponse`: Thông tin trả về đầy đủ kèm số lượng Kho Tri Thức đang liên kết (`attached_collections_count`).
- `RepositoryDocumentListItem`: DTO rút gọn tối ưu cho bảng và danh sách thẻ.
- `RepositoryDocumentUpdate`: Cập nhật metadata hành chính (tiêu đề, số hiệu, ngày ban hành, cơ quan ban hành, loại văn bản).
- `RepositoryDocumentStatsResponse`: Thống kê KPI tổng quan (tổng văn bản, đã bóc tách, dung lượng MinIO, phân bố loại văn bản).
- `AttachRepositoryDocumentsRequest`: Payload yêu cầu gắn danh sách tài liệu từ kho vào một Kho Tri Thức:
  ```python
  class AttachRepositoryDocumentsRequest(BaseModel):
      document_ids: list[str] = Field(..., min_length=1, description="Danh sách ID tài liệu từ Kho Tài Liệu")
      chunk_strategy: str | None = Field(None, description="Chiến lược cắt đoạn: clause, semantic hoặc auto")
      auto_approve: bool = Field(True, description="Tự động duyệt và lập chỉ mục Vector tức thì")
  ```

### C. `service.py` (`document_repository_service`)
- **Tải lên & Lưu MinIO**:
  1. Nhận `file_bytes`, tính `file_hash = sha256(file_bytes)`.
  2. Kiểm tra trùng lặp qua `file_hash`: Nếu đã tồn tại, trả về bản ghi có sẵn hoặc thông báo.
  3. Lưu tệp gốc lên MinIO S3 tại `documents/originals/{file_hash}/{file_name}` qua `app.core.storage.storage_service`.
  4. Tạo bản ghi `RepositoryDocument` với trạng thái `parse_status = "parsing"`.
- **Pre-parsing & OCR Pipeline**:
  1. Chạy bóc tách nội dung dựa trên định dạng tệp (PDF/DOCX/XLSX) qua `get_document_parser`.
  2. Chuẩn hóa tiếng Việt NFC và làm sạch Markdown qua `app.modules.knowledge.cleaner.clean_markdown_text`.
  3. Render ảnh trang PDF lưu lên MinIO `documents/renders/{file_hash}/page_{n}.png` phục vụ xem trước.
  4. Cập nhật `parsed_markdown`, `parse_status = "parsed"`.
- **Phục vụ tệp & Tải xuống**:
  - `download_file(doc_id)`: Streaming đọc tệp gốc từ MinIO S3.
  - `preview_pdf(doc_id)`: Trả về PDF dạng stream hoặc presigned URL.

### D. `router.py` (`/platform/v1alpha1/documents`)
- `POST /`: Tải lên tài liệu mới vào Kho (hỗ trợ multipart form data).
- `GET /`: Danh sách tài liệu (phân trang, tìm kiếm từ khóa, lọc theo loại văn bản, lọc định dạng, lọc parse_status).
- `GET /stats`: Thống kê KPI phục vụ Dashboard & trang kho tài liệu.
- `GET /{id}`: Chi tiết một tài liệu (kèm nội dung parsed markdown và danh sách Kho Tri Thức đang dùng).
- `PATCH /{id}`: Chỉnh sửa metadata hành chính.
- `DELETE /{id}`: Xóa tài liệu (có kiểm tra cảnh báo nếu đang được các Kho Tri Thức sử dụng).
- `POST /{id}/reparse`: Bóc tách lại văn bản hoặc chạy lại OCR.
- `GET /{id}/download`: Tải tệp gốc từ MinIO.
- `GET /{id}/preview-pdf`: Stream xem trước tệp PDF.
- `GET /{id}/pages/{page}/image`: Xem trước ảnh từng trang.

### E. Mở rộng Module `knowledge` để kết nối
- Thêm method `attach_repository_documents` trong `IngestionService`:
  1. Truy vấn các `RepositoryDocument` theo IDs.
  2. Kế thừa trực tiếp `parsed_markdown` (0 giây chờ OCR).
  3. Thực hiện Chunking theo cấu hình của Kho Tri Thức (`ClauseBasedChunker` cho quy chế, `SemanticChunker` cho cẩm nang).
  4. Thực hiện Vector Embedding theo mô hình của Kho Tri Thức (`bge-m3:latest`, `text-embedding-3-small`, v.v.) và lưu vào Qdrant với payload gắn `collection_id` và `document_id`.
  5. Trích xuất sự thật vào bảng `knowledge_facts` của Kho Tri Thức.
  6. Tạo các bản ghi `KnowledgeDocument` tương ứng với `repository_document_id`.
- Thêm endpoint:
  - `POST /platform/v1alpha1/knowledge/collections/{collection_id}/attach-repository-documents`.

---

## 4. Kế Hoạch Triển Khai Frontend (Clean 3-Tier Architecture)

### A. Services & DTOs
- `frontend/src/types/documents.ts`: Định nghĩa kiểu dữ liệu `RepositoryDocument`, `DocumentStats`, `DocumentFilters`, `AttachDocumentsRequest`.
- `frontend/src/services/documents-api.ts`: API client xử lý gọi các endpoints của Kho Tài Liệu.

### B. Trang Quản Trị Kho Tài Liệu (`frontend/src/features/documents/`)
1. **Trang Danh Sách Master (`documents-page.tsx` - `/documents`)**:
   - **KPI Metric Strip**: 4 thẻ chỉ số (Tổng văn bản số, Đã bóc tách Markdown, Dung lượng MinIO đã dùng, Số loại văn bản Nghị định 30).
   - **Thanh Công Cụ Tìm Kiếm & Lọc**:
     - Input tìm kiếm theo tên tệp, số hiệu văn bản, cơ quan ban hành.
     - Select lọc Loại văn bản (`DocumentTypeSelect`).
     - Select lọc Định dạng tệp (Tất cả, PDF, Word, Excel, Plain Text).
     - Select lọc Trạng thái bóc tách (Tất cả, Đã bóc tách, Đang xử lý, Thất bại).
     - Component chuyển chế độ xem chuẩn: `<ViewModeToggle value={viewMode} onChange={setViewMode} />`.
   - **Chế Độ Xem Thẻ (Grid Mode)**:
     - Card hiển thị icon định dạng (PDF đỏ, Word xanh lam, Excel xanh lá), Badge loại văn bản, số hiệu, ngày ban hành, badge trạng thái OCR, số lượng Kho Tri Thức đang dùng.
   - **Chế Độ Xem Bảng (Table Mode)**:
     - Bảng dữ liệu Radix UI chi tiết: Tên tệp, Số hiệu, Loại VB, Kích thước, Trạng thái, Ngày nạp, Thao tác.
   - **Hộp thoại Tải Lên (`document-upload-modal.tsx`)**:
     - Vùng kéo thả tệp hiện đại.
     - Form nhập: Tiêu đề, Số hiệu văn bản, Cơ quan ban hành, Ngày ký, Loại văn bản (dropdown lấy từ `platform_document_types`), Tùy chọn OCR engine.

2. **Trang Chi Tiết Độc Lập (`document-detail-page.tsx` - `/documents/:documentId`)**:
   - Deep Routing theo chuẩn `AGENTS.md`.
   - Header: Breadcrumb `Kho Tài Liệu / [Số Hiệu] - [Tên Văn Bản]`, nút quay lại `<ArrowLeft />`.
   - Action Bar: Nút *Tải xuống từ MinIO*, *Bóc tách lại OCR*, *Chỉnh sửa thông tin*, *Xóa*.
   - Bố cục 2 cột chuyên sâu:
     - **Cột Trái (60%) - Trình xem nội dung đã bóc tách**:
       - Tab 1: Nội dung Markdown đã làm sạch (kèm bảng biểu, heading, formatting chuẩn, nút Sao chép Markdown).
       - Tab 2: Xem trước PDF gốc (PDF viewer trực tiếp).
     - **Cột Phải (40%) - Metadata & Liên kết**:
       - Thẻ Thông tin Hành chính: Loại văn bản, Số hiệu, Cơ quan, Ngày ban hành, Ngày hiệu lực, Mã SHA-256.
       - Thẻ Bóc tách & OCR: Engine đã dùng, Số trang, Số bảng trích xuất, Trạng thái chất lượng.
       - Thẻ **"Các Kho Tri Thức Đang Sử Dụng"**: Danh sách các Kho Tri Thức đang liên kết tài liệu này, kèm badge trạng thái vector index và link bấm sang Kho Tri Thức.

### C. Tích Hợp Vào Trang Chi Tiết Kho Tri Thức (`/knowledge/:id`)
- Nâng cấp Tab "Tài Liệu" (`collection-documents-tab.tsx`):
  - Bổ sung nút **"Gắn Từ Kho Tài Liệu"** (icon `<FolderArchive />` hoặc `<Link2 />`) cạnh nút "Tải từ máy tính".
  - Tạo Dialog **`attach-from-repository-dialog.tsx`**:
    - Danh sách tài liệu trong Vault với bộ lọc nhanh.
    - Checkbox chọn nhiều tệp.
    - Hiển thị rõ tài liệu nào đã được gắn vào Kho này rồi (disabled / badge "Đã có trong kho").
    - Nút hành động: **"Gắn & Vector Hóa Vào Kho"** $\rightarrow$ Hệ thống tự động kế thừa Markdown đã bóc tách, chia đoạn và sinh Vector vào Qdrant trong tích tắc.
  - Trong bảng tài liệu của Kho Tri Thức: Bổ sung chip nhỏ `[Kho Tài Liệu]` cho các tài liệu được liên kết từ Vault, click vào có thể mở chi tiết tài liệu gốc trong Kho Tài Liệu.

### D. Đồng Bộ Điều Hướng (Navigation & Routing)
- Cập nhật `frontend/src/navigation/config.ts`:
  - Thêm mục **"Kho Tài Liệu"** (`/documents`, icon `FileStack` từ `lucide-react`) vào nhóm *"Xây Dựng AI"* (ngay phía trên *"Kho Tri Thức"*).
- Tạo các files route:
  - `frontend/src/routes/documents.tsx`
  - `frontend/src/routes/documents.index.tsx`
  - `frontend/src/routes/documents.$documentId.tsx`

---

## 5. Lộ Trình Thực Thi Từng Bước (Implementation Roadmap)

| Giai Đoạn | Nhiệm Vụ Cụ Thể | Kết Quả Đạt Được |
| :---: | :--- | :--- |
| **P1: Database Migration** | Tạo migration Alembic `20261007_document_repository.py` tạo bảng `repository_documents` và liên kết `knowledge_documents.repository_document_id`. | CSDL PostgreSQL đồng bộ schema |
| **P2: Backend Module `documents`** | Xây dựng 4 file chuẩn: `models.py`, `schemas.py`, `service.py`, `router.py`, kết nối MinIO S3 (`app.core.storage`). | API `/platform/v1alpha1/documents` hoạt động đầy đủ CRUD, Upload, Download, Reparse |
| **P3: Backend Ingestion Linking** | Mở rộng `knowledge` với method & endpoint `attach-repository-documents`, kế thừa Markdown đã bóc tách và vector hóa Qdrant. | Gắn tài liệu từ Vault vào Kho Tri Thức tức thì |
| **P4: Frontend Services & Types** | Viết `documents.ts` types và `documents-api.ts`. | Giao tiếp API trơn tru với Backend |
| **P5: Frontend Master Page `/documents`** | Xây dựng giao diện Danh sách Kho Tài Liệu, KPI metrics, bộ lọc, `<ViewModeToggle />`, Modal upload tài liệu. | Giao diện quản lý tập trung hoàn chỉnh |
| **P6: Frontend Detail Page `/documents/:id`** | Xây dựng trang chi tiết văn bản: Markdown Viewer, PDF Preview, Metadata hành chính, Danh sách Kho liên kết. | Trải nghiệm Master-Detail chuyên sâu |
| **P7: Frontend Knowledge Integration** | Thêm Dialog "Gắn từ Kho Tài Liệu" trên `/knowledge/:id`, hỗ trợ chọn nhiều tệp và vector hóa. | Đấu nối hoàn chỉnh luồng nghiệp vụ 2 tầng |
| **P8: Full-Stack Verification & Nhật Ký** | Chạy Pytest backend, kiểm tra MinIO storage parity, chạy `npm run build` frontend, cập nhật tài liệu phiên #283. | Hệ thống đạt 100% chuẩn Production |
