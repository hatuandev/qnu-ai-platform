# QUY TRÌNH 02: NẠP TRI THỨC, PHÂN NHÁNH PDF INSPECTOR/OCR & LƯU TRỮ MINIO

Tài liệu này đặc tả toàn diện quy trình tiếp nhận tệp tài liệu từ người dùng/cán bộ QNU, lưu trữ đối tượng bền vững trên **MinIO Object Storage**, phân nhánh kiểm tra văn bản số hóa thông qua **PDF Inspector**, kích hoạt mô hình OCR động từ **Quản Lý Provider** (chỉ cho phép các Provider đang BẬT), phân đoạn tri thức (Chunking), bóc tách số liệu sự thật (Fact Layer) và đánh chỉ mục kép (Dual Indexing).

---

## 1. Sơ Đồ Quy Trình Luân Chuyển Dữ Liệu Toàn Diện (Pipeline Flowchart)

```mermaid
flowchart TD
    A([Người dùng / Cán bộ QNU]) -->|Upload File + Điền thông tin| B[Giao diện Ingestion Wizard]
    
    subgraph DYNAMIC_PROVIDER [Tầng Lựa Chọn Mô Hình Từ Quản Lý Provider]
        M1[(CSDL PostgreSQL: model_provider_configs)] -->|Lọc WHERE is_active = True| M2[Danh sách Provider Đang Bật]
        M2 -->|Chọn Model Bóc tách / OCR| B_OCR[Model OCR: Mistral OCR / Docling]
        M2 -->|Chọn Model Vector Embedding| B_EMB[Model Embedding: BGE-M3 Local / Cloudflare]
    end

    B -->|Submit Form Multipart| C[REST API Router: POST /knowledge/collections/{id}/upload]
    
    subgraph TANG_MINIO [1. Tầng Lưu Trữ Tệp Bền Vững MinIO]
        C -->|S3StorageDriver.save| D[(MinIO Object Storage: Bucket 'qnu-ai-documents')]
        D -->|Trả về S3 Key: uploads/col_id/UUID_filename| C
    end

    C --> E[Tạo bản ghi KnowledgeDocument: storage_path = S3 Key, status = UPLOADED]
    E -->|Lưu Metadata ban đầu| F[(PostgreSQL: bảng knowledge_documents)]
    
    subgraph TANG_BOC_TACH [2. Tầng Bóc Tách Văn Bản & Phân Nhánh PDF Inspector]
        E -->|Đọc file bytes trực tiếp từ MinIO| G{Định dạng tệp?}
        G -->|.docx / .xlsx / .txt| H1[Parsers Chuyên Dụng: DocxParser / Openpyxl / PlainTextParser]
        G -->|.pdf| H2[PDF Inspector: Thanh tra cấu trúc từng trang PDF]
        
        H2 -->|Trang có Digital Text >= 40 ký tự| H3[PyMuPDF Fast Native: Trích xuất Text & Bảng trực tiếp 15ms]
        H2 -->|Trang Scan / Ảnh thuần hoặc text rỗng| H4[Kích Hoạt Model OCR Đang Bật Đã Chọn: Mistral OCR / Docling]
        
        H1 --> K[Markdown Cleaner: Xóa số trang rác, footnote, dấu phân trang thừa]
        H3 --> K
        H4 --> K
    end

    subgraph TANG_PHAN_MANH [3. Tầng Phân Mảnh Tri Thức & Structured Facts]
        K --> L{Loại văn bản?}
        L -->|Văn bản pháp quy / Quy chế đào tạo| M[ClauseBasedChunker: Cắt theo từng Điều / Khoản]
        L -->|Cẩm nang / Thông tin tuyển sinh / Giáo trình| N[SemanticChunker: Cắt phân đoạn ngữ nghĩa trôi chảy]
        
        M --> O[Fact Extractor: Trích xuất Bảng số liệu dạng cấu trúc]
        N --> O
        O -->|Nạp các bộ Fact: Điểm chuẩn, Mã ngành, Mức học phí| P[(PostgreSQL: bảng knowledge_facts)]
    end

    subgraph TANG_DANH_CHI_MUC [4. Đánh Chỉ Mục Kép (Dual Indexing)]
        M --> Q[Sinh Dense Embeddings 1024D: Gọi Model Embedding Đang Bật Đã Chọn]
        N --> Q
        Q -->|Nạp Vector Points| R[(Qdrant DB: Collection tương ứng)]
        
        M --> S[Sinh Lexical FTS Index: PostgreSQL tsvector tiếng Việt]
        N --> S
        S -->|Nạp bản ghi Chunks| T[(PostgreSQL: bảng knowledge_chunks)]
    end

    R --> U[Cập nhật Document: status = INDEXED, ocr_provider, embedding_provider]
    T --> U
    U --> V([Tri thức sẵn sàng phục vụ tra cứu RAG không bịa đặt])
```

---

## 2. Chi Tiết Các Bước Kỹ Thuật Chuẩn Hóa

### Bước 1: Lọc động mô hình từ Quản Lý Provider (Active Providers Only)
- Khi mở giao diện Nạp Tri Thức (**Ingestion Wizard**), frontend truy vấn danh sách provider từ CSDL thông qua API `/platform/v1alpha1/modelops/providers`.
- **Nguyên tắc nghiêm ngặt**: Chỉ các nhà cung cấp có trạng thái **Đang Bật (`is_active = True`)** mới được hiển thị trong menu chọn:
  - **Mô hình OCR**: Lọc từ các provider cung cấp tính năng OCR (ví dụ: `Mistral AI - mistral-ocr-latest`, `Docling Local - docling-tableformer-local`).
  - **Mô hình Embedding**: Lọc từ các provider cung cấp mô hình nhúng vector (ví dụ: `Local SentenceTransformers - BAAI/bge-m3`, `Cloudflare Workers AI - @cf/baai/bge-m3`).
- Nếu một provider bị tắt (switch sang màu xám `is_active = False`) tại trang Quản lý Provider, provider đó lập tức biến mất khỏi danh mục lựa chọn của Ingestion Wizard.

### Bước 2: Lưu trữ tệp gốc trên MinIO S3 Object Storage
- Mọi tệp tải lên được lưu trực tiếp vào MinIO S3 thông qua lớp `S3StorageDriver` ([`app/core/storage.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/storage.py)).
- **Quy chuẩn lưu trữ**:
  - Bucket: `qnu-ai-documents`.
  - Khóa đối tượng (S3 Key): `uploads/{collection_id}/{uuid4[:8]}_{safe_filename}`.
- **Mục đích**: Bảo toàn 100% tệp gốc phục vụ văn thư điện tử, kiểm toán dữ liệu và tái lập chỉ mục (Re-indexing) khi cần thay đổi mô hình Embedding mà không bắt người dùng upload lại. Tuyệt đối không lưu tệp cục bộ trên ổ cứng máy chủ.

### Bước 3: Cơ chế phân nhánh PDF Inspector vs OCR
Đối với các tệp định dạng PDF, hệ thống áp dụng cơ chế thanh tra 2 pha:
1. **Pha 1 — PDF Inspector**:
   - Sử dụng engine phân tích cấu trúc trang của PyMuPDF/Rust để thanh tra từng trang.
   - Nếu trang có chữ số hóa (digital text layer $\ge 40$ ký tự): Trích xuất văn bản và bảng biểu trực tiếp (`find_tables()`) chỉ mất **10 - 30ms**, **không tiêu tốn tài nguyên OCR**.
2. **Pha 2 — Kích hoạt OCR có chọn lọc**:
   - Nếu phát hiện trang scan, trang dạng ảnh bitmap hoặc số ký tự text $< 40$, trang đó được đánh dấu `needs_page_ocr = True`.
   - Hệ thống render trang thành ảnh và gọi **mô hình OCR đã chọn từ danh sách Provider Đang Bật** để nhận diện ký tự quang học.

### Bước 4: Làm sạch và chuẩn hóa văn bản (Cleaning)
Hàm `clean_markdown_text` tại [`app/modules/knowledge/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py):
- Loại bỏ số trang rác, footnote, dấu trang phân cách vô nghĩa.
- Chuẩn hóa khoảng trắng, dấu ngắt dòng và giữ nguyên vẹn cấu trúc Markdown tiêu đề `#`, `##` và bảng biểu `| Col 1 | Col 2 |`.

### Bước 5: Chiến lược phân mảnh tri thức (Chunking Strategy)
- **`ClauseBasedChunker`**: Dành riêng cho Quy chế đào tạo, Quyết định, Thông tư, Quy định học vụ. Thuật toán quét biểu thức chính quy `(?:Điều|Chương|Phần)\s+\d+` để cắt độc lập từng Điều, Khoản, gắn nhãn trích dẫn chính xác.
- **`SemanticChunker`**: Dành cho bài viết giới thiệu, cẩm nang sinh viên, đề án tuyển sinh. Cắt theo ranh giới đoạn văn `\n\n` với kích thước `max_tokens = 500`, bảo đảm ngữ cảnh trôi chảy.

### Bước 6: Bóc tách tầng số liệu sự thật (Structured Facts Layer)
- Các bảng số liệu có tính biến động hoặc yêu cầu độ chính xác 100% (Mã ngành, Điểm chuẩn các năm, Chỉ tiêu, Mức học phí từng học kỳ) được trích xuất tự động và lưu vào bảng PostgreSQL `knowledge_facts`.
- Khi Trợ lý AI giải đáp, dữ liệu bảng sự thật được truy vấn ưu tiên số 1 để triệt tiêu hoàn toàn hiện tượng AI bịa đặt số liệu (Hallucination).

### Bước 7: Đánh chỉ mục kép (Dual Indexing)
- **Chỉ mục Ngữ nghĩa (Dense Vector Search)**: Sinh vector 1024 chiều bằng **mô hình Embedding đã chọn từ Provider Đang Bật**, nạp vào Qdrant Vector DB với thang đo Cosine.
- **Chỉ mục Từ khóa (Sparse Lexical Search)**: Đánh chỉ mục `tsvector` tiếng Việt trên PostgreSQL `knowledge_chunks` phục vụ tra cứu chính xác từ viết tắt (DQN, CNTT, UIS, KTX).
- Sau khi hoàn tất chỉ mục cả hai bên, tài liệu được chuyển trạng thái `status = INDEXED`, sẵn sàng phục vụ trả lời RAG kèm trích dẫn văn bản minh chứng.
