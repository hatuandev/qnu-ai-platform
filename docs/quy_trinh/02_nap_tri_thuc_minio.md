# QUY TRÌNH 02: NẠP TRI THỨC & LƯU TRỮ MINIO (KNOWLEDGE INGESTION & MINIO STORAGE FLOW)

Tài liệu này đặc tả quy trình tiếp nhận tệp văn bản từ người dùng/cán bộ, lưu trữ đối tượng bền vững trên **MinIO Object Storage**, bóc tách nội dung thô, làm sạch, phân mảnh tri thức (Chunking) và đánh chỉ mục kép (Dual Indexing).

---

## 1. Sơ Đồ Quy Trình Luân Chuyển Dữ Liệu (Ingestion Pipeline Flowchart)

```mermaid
flowchart TD
    A([Người dùng / Cán bộ QNU]) -->|Upload File PDF/DOCX/TXT| B[REST API Router: POST /knowledge/upload]
    B -->|Tiếp nhận file stream| C[Storage Service: S3StorageDriver]
    
    subgraph TANG_MINIO [1. Tầng Lưu Trữ Đối Tượng Bền Vững MinIO]
        C -->|boto3 put_object| D[(MinIO Object Storage: Bucket 'qnu-ai-documents')]
        D -->|Trả về S3 Key: uploads/UUID_filename| C
    end

    C --> E[Tạo bản ghi DocumentModel: storage_path = S3 Key, status = UPLOADED]
    E -->|Lưu Metadata| F[(PostgreSQL: bảng knowledge_documents)]
    
    subgraph TANG_BOC_TACH [2. Tầng Bóc Tách Văn Bản (In-Memory Extraction)]
        E -->|Đọc file bytes trực tiếp từ MinIO| G{Định dạng tệp?}
        G -->|.pdf| H[PyMuPdfParser: Trích xuất Text & Tọa độ Trang]
        G -->|.docx| I[DocxParser: Bóc tách Heading, Paragraph & Bảng]
        G -->|.txt / .md| J[PlainTextParser: Đọc thuần text UTF-8]
        
        H --> K[Markdown Cleaner: Xóa số trang rác, footnote, dấu trang thừa]
        I --> K
        J --> K
    end

    subgraph TANG_PHAN_MANH [3. Tầng Phân Mảnh & Bóc Tách Bảng Số Liệu]
        K --> L{Loại văn bản?}
        L -->|Văn bản pháp quy / Quy chế đào tạo| M[ClauseBasedChunker: Cắt theo từng Điều / Khoản]
        L -->|Cẩm nang / Thông tin tuyển sinh| N[SemanticChunker: Cắt theo phân đoạn ngữ nghĩa trôi chảy]
        
        M --> O[Fact Extractor: Trích xuất Bảng số liệu dạng cấu trúc]
        N --> O
        O -->|Nạp các bộ Fact: Điểm chuẩn, Mã ngành, Học phí| P[(PostgreSQL: bảng knowledge_facts)]
    end

    subgraph TANG_DANH_CHI_MUC [4. Đánh Chỉ Mục Kép (Dual Indexing)]
        M --> Q[Sinh Dense Embeddings 1024 chiều: Mô hình BGE-M3]
        N --> Q
        Q -->|Nạp Vector Points| R[(Qdrant DB: Collection qnu_knowledge_chunks)]
        
        M --> S[Sinh Lexical FTS Index: PostgreSQL tsvector tiếng Việt]
        N --> S
        S -->|Nạp bản ghi Chunks| T[(PostgreSQL: bảng knowledge_chunks)]
    end

    R --> U[Cập nhật trạng thái Document: status = INDEXED]
    T --> U
    U --> V([Tri thức sẵn sàng phục vụ tra cứu RAG không bị Bịa đặt])
```

---

## 2. Chi Tiết Các Bước Kỹ Thuật

### Bước 1: Lưu trữ tệp gốc trên MinIO (MinIO Object Storage)
- File upload được stream trực tiếp lên MinIO thông qua class `S3StorageDriver` ([`app/core/storage.py`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/core/storage.py)).
- Tệp được đặt tên theo quy chuẩn: `uploads/{uuid4}_{safe_filename}`.
- Bucket mặc định: `qnu-ai-documents`.
- **Mục đích**: Bảo toàn 100% tệp gốc phục vụ lưu trữ văn thư điện tử, kiểm toán dữ liệu và tái lập chỉ mục (Reindex) khi cần nâng cấp mô hình Embedding mà không yêu cầu người dùng upload lại.

### Bước 2: Bóc tách văn bản trong bộ nhớ (In-Memory Parsing)
- Sử dụng Design Pattern: **Strategy Pattern** kế thừa từ `BaseDocumentParser`:
  - `PyMuPdfParser`: Sử dụng thư viện `pymupdf` hiệu năng C cao, trích xuất text, số trang và metadata.
  - `DocxParser`: Sử dụng thư viện `python-docx` bóc tách từng phân đoạn `Heading`, `Paragraph` và bảng biểu.
  - `PlainTextParser`: Đọc văn bản thuần UTF-8.

### Bước 3: Làm sạch văn bản (Cleaning)
Hàm `clean_markdown_text` tại [`app/modules/knowledge/cleaner.py`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py):
- Loại bỏ số trang rác định dạng: `— 15 —`, `Trang 1/20`.
- Chuẩn hóa khoảng trắng thừa, xóa các dòng phân cách vô nghĩa.
- Bảo toàn cấu trúc Markdown `#`, `##` và bảng biểu `| Col 1 | Col 2 |`.

### Bước 4: Chiến lược phân mảnh (Chunking Strategy)
- **`ClauseBasedChunker`**: Dành riêng cho Quy chế đào tạo, Quyết định, Thông tư. Thuật toán quét biểu thức chính quy `(?:Điều|Chương|Phần)\s+\d+` để cắt độc lập từng Điều, Khoản. Gắn metadata tiêu đề Điều vào trường `section`.
- **`SemanticChunker`**: Dành cho bài viết giới thiệu, cẩm nang sinh viên. Tách theo ranh giới đoạn văn `\n\n` với kích thước giới hạn `max_tokens=500`, bảo đảm mạch ý trôi chảy.

### Bước 5: Bóc tách bản ghi sự thật (Structured Fact Extraction)
- Các số liệu dạng bảng (Mã ngành, Tên ngành, Tổ hợp môn, Điểm chuẩn, Mức học phí) được bóc tách và lưu trực tiếp vào bảng CSDL `knowledge_facts`.
- Dữ liệu này được ưu tiên số 1 khi truy vấn RAG để triệt tiêu tình trạng LLM tự suy diễn số liệu sai lệch.

### Bước 6: Đánh chỉ mục kép (Dual Indexing)
- **Chỉ mục Ngữ nghĩa (Dense Vector)**: Sinh vector 1024 chiều từ mô hình `BAAI/bge-m3`, nạp vào Qdrant với chỉ số khoảng cách Cosine.
- **Chỉ mục Từ khóa (Sparse Lexical)**: Đánh chỉ mục `tsvector` tiếng Việt trên PostgreSQL phục vụ tra cứu chính xác từ viết tắt (DQN, CNTT, KTX).
