# QUY TRÌNH 02: NẠP TRI THỨC, PHÂN NHÁNH PDF INSPECTOR/OCR & ĐỐI SOÁT HITL TRƯỚC KHI NẠP VECTOR DB

Tài liệu này đặc tả toàn diện quy trình tiếp nhận tệp tài liệu từ người dùng/cán bộ QNU, lưu trữ đối tượng bền vững (**MinIO Object Storage / Local Dual-driver**), tự động hóa cấu hình (**Smart Auto-Recommendation**), phân nhánh kiểm tra văn bản số hóa thông qua **PDF Inspector**, kích hoạt mô hình OCR cứu hộ linh hoạt, bóc tách bảo toàn bảng biểu Markdown và `page_markdowns`, phân đoạn tri thức (Chunking), bóc tách số liệu sự thật (Fact Layer), **đối soát mắt & hiệu đính con người (Human-in-the-loop Studio)**, và chỉ đánh chỉ mục kép (**Dual Indexing: Qdrant + PostgreSQL FTS**) khi đã được phê duyệt.

---

## 1. Sơ Đồ Quy Trình Luân Chuyển Dữ Liệu Toàn Diện (Pipeline Flowchart)

```mermaid
flowchart TD
    A([Người dùng / Cán bộ QNU]) -->|Kéo thả hoặc chọn File| B[Giao diện Ingestion Wizard]
    
    subgraph AUTO_CONFIG [Tầng Nhận Diện Thông Minh & ModelOps Defaults]
        B -->|file-inspector.ts| AC1[Tự nhận diện định dạng: Word/Excel/PDF/Scan]
        AC1 -->|Khuyến nghị OCR: Docling / Fast Native / Mistral OCR| AC2[Smart Recommendation Banner]
        AC1 -->|Khớp từ khóa tên file + bối cảnh Kho| AC3[Tự gán Loại văn bản: 37 loại NĐ 30]
        M1[(PostgreSQL: model_provider_configs)] -->|Lấy Model Mặc Định Hệ Thống| AC4[Default Embedding Model: Cloudflare BGE-M3 / Local CPU]
    end

    AC2 & AC3 & AC4 -->|Submit Multipart Form| C[REST API Router: POST /knowledge/collections/{id}/upload]
    
    subgraph TANG_STORAGE [1. Tầng Lưu Trữ Tệp Bền Vững - Dual Driver]
        C -->|storage_service.save| D[(Storage Driver: MinIO Bucket 'qnu-ai-documents' / Local Storage)]
        D -->|Khóa đối tượng S3/Local: uploads/col_id/UUID_filename| C
    end

    C --> E[Tạo bản ghi KnowledgeDocument ban đầu: status = 'pending']
    
    subgraph TANG_BOC_TACH [2. Tầng Bóc Tách Văn Bản & Phân Nhánh PDF Inspector]
        E -->|Đọc file bytes| G{Định dạng tệp?}
        G -->|.docx / .xlsx / .txt| H1[Parsers Chuyên Dụng: DocxParser / Openpyxl / PlainTextParser]
        G -->|.pdf| H2[PDF Inspector: Thanh tra cấu trúc từng trang PDF]
        
        H2 -->|Trang có Digital Text >= 40 ký tự| H3[PyMuPDF Fast Native: Trích xuất Text & Bảng trực tiếp 15-30ms]
        H2 -->|Trang Scan / Ảnh thuần hoặc text rỗng| H4[Cứu hộ OCR tự động: Mistral OCR Cloud / EasyOCR Local]
        
        H1 & H3 & H4 --> K1[Bảo toàn bảng biểu: _format_table_markdown chuyển đổi thành bảng GFM]
        K1 --> K2[SmartLayoutDetector OpenCV: Phân vùng vĩ mô, bóc tách con dấu đỏ, chữ ký]
        K2 --> K3[Markdown Cleaner: Chuẩn hóa Unicode NFC, loại bỏ số trang rác, footnote thừa]
        K3 --> K4[Bảo tồn Markdown từng trang: page_markdowns lưu vào doc_metadata]
    end

    subgraph TANG_PHAN_MANH [3. Tầng Phân Mảnh Tri Thức & Structured Facts]
        K4 --> L{Loại văn bản?}
        L -->|Văn bản pháp quy / Quy chế đào tạo| M[ClauseBasedChunker: Cắt theo từng Điều / Khoản có nhãn trích dẫn]
        L -->|Cẩm nang / Tuyển sinh / Giáo trình| N[SemanticChunker: Cắt phân đoạn ngữ nghĩa trôi chảy max 500 tokens]
        
        M & N -->|Lưu danh sách Chunks vào CSDL| DB_CHUNKS[(PostgreSQL: bảng knowledge_chunks)]
        M & N --> O[Fact Extractor: Trích xuất Bảng số liệu dạng cấu trúc]
        O -->|Nạp các bộ Fact: Điểm chuẩn, Mã ngành, Học phí| DB_FACTS[(PostgreSQL: bảng knowledge_facts)]
    end

    DB_CHUNKS & DB_FACTS --> RET_PENDING[Hoàn tất pha nạp: Document lưu status = 'pending']

    subgraph TANG_HITL [4. Tầng Đối Soát & Hiệu Đính Con Người - Human-in-the-loop]
        RET_PENDING --> STUDIO[Document Verification Studio: /collections/:id/documents/:docId/verification]
        STUDIO -->|Bên trái: Ảnh render tài liệu gốc / Bên phải: Markdown chuẩn hóa| AUDIT[Cán bộ đối soát nội dung bóc tách]
        AUDIT -->|Nếu OCR phát hiện sai sót| EDIT[Chế độ Sửa tay In-place: Hiệu đính trực tiếp từng trang]
        EDIT -->|Lưu sửa tay| PREVIEW[Xem trước Preview & Cập nhật page_markdowns]
        AUDIT -->|Xác nhận nội dung chuẩn sạch| BTN_APPROVE{Cán bộ bấm: 'Xác nhận & Nạp vào Vector DB'}
    end

    BTN_APPROVE -->|POST /knowledge/documents/{id}/approve| API_APPROVE[approve_document API]

    subgraph TANG_DANH_CHI_MUC [5. Tầng Đánh Chỉ Mục Kép - Dual Indexing]
        API_APPROVE --> Q[Sinh Dense Embeddings 1024D: Gọi Active Default Embedding Model]
        Q -->|Nạp Vector Points vào Qdrant| R[(Qdrant DB: Collection tương ứng)]
        
        API_APPROVE --> S[Cập nhật Sparse Lexical Index: PostgreSQL tsvector tiếng Việt]
        S -->|FTS Indexing tự động qua trigger| DB_CHUNKS
    end

    R & S --> U[Cập nhật Document: status = 'approved', indexed_chunks, human_verified = True]
    U --> V([Tri thức chính thức hoàn tất: Sẵn sàng phục vụ RAG Hybrid RRF k=60 không bịa đặt])
```

---

## 2. Chi Tiết Các Bước Kỹ Thuật Chuẩn Hóa

### Bước 1: Tự động hóa cấu hình (Smart Auto-Recommendation) & Lọc Model Động
- Khi cán bộ chọn hoặc kéo thả tệp vào trang **Nạp Tài Liệu** (`/knowledge/collections/:id/ingest`), thanh tra tệp tại [`frontend/src/lib/file-inspector.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/lib/file-inspector.ts) tự động thực hiện:
  - **Nhận diện bộ máy OCR phù hợp**:
    * File `.docx`, `.xlsx`: Đề xuất tự động `Docling TableFormer / openpyxl` nhằm bảo toàn 100% cấu trúc ma trận bảng biểu.
    * File `.pdf`: Đề xuất tự động `Fast-path + Mistral OCR` (ưu tiên PyMuPDF nhanh 15ms, tự động chuyển cứu hộ Mistral OCR nếu là bản scan).
    * File ảnh `.png`, `.jpg`: Đề xuất `Mistral OCR Cloud` (hoặc Local OCR nếu không có API key).
  - **Tự động nhận diện Loại văn bản (Taxonomy 37 loại NĐ 30)**: So khớp biểu thức chính quy với tên tệp (ví dụ từ khóa `tuyen sinh` $\rightarrow$ loại `de_an`) kết hợp với ngữ cảnh của Kho Tri Thức (`col_admissions` $\rightarrow$ `de_an`, `col_regulations` $\rightarrow$ `quy_che`).
  - **Mô hình Embedding Mặc Định Hệ Thống (Active System Defaults)**: Tự động tải mô hình embedding mặc định được cấu hình tại Quản Trị ModelOps (Cloudflare Workers AI `@cf/baai/bge-m3` hoặc Local CPU `BAAI/bge-m3`), người dùng không phải chọn lại thủ công.
  - **Lọc danh sách Provider**: Chỉ những Provider đang có trạng thái **Đang Bật (`is_active = True`)** mới được phép tham gia vào danh mục lựa chọn.

### Bước 2: Lưu trữ tệp gốc an toàn (Dual-Driver Storage: MinIO S3 / Local Disk)
- Lớp trừu tượng hóa lưu trữ [`app/core/storage.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/storage.py) vận hành theo mẫu **Adapter Pattern**:
  - **Production Mode (`STORAGE_DRIVER=s3`)**: Kết nối trực tiếp tới MinIO / S3 Object Storage:
    * Bucket: `qnu-ai-documents`.
    * Khóa đối tượng (S3 Key): `uploads/{collection_id}/{uuid4[:8]}_{safe_filename}`.
  - **Development / Test Mode (`STORAGE_DRIVER=local`)**: Tự động lưu trữ tại thư mục cục bộ `./storage/uploads/...` giúp lập trình viên chạy kiểm thử và phát triển mà không phụ thuộc hạ tầng cụ thể.
- **Lưu trữ ảnh render trang phục vụ Studio**: Hệ thống đồng thời lưu ảnh kết xuất chuẩn hóa của từng trang (`cache/{document_id}/page_{page_number}.png`) trên Storage Driver để phục vụ Document Verification Studio.

### Bước 3: Cơ chế phân nhánh PDF Inspector & Bóc tách đa tầng
Đối với tệp định dạng PDF, hệ thống áp dụng cơ chế thanh tra 2 pha:
1. **Pha 1 — PDF Inspector Fast-path**:
   - Dùng PyMuPDF thanh tra nhanh cấu trúc trang. Nếu số ký tự có thể trích xuất trực tiếp $\ge 40$ ký tự: Trích xuất văn bản và cấu trúc bảng (`find_tables()`) chỉ mất **10 - 30ms**, không tiêu tốn tài nguyên OCR.
2. **Pha 2 — Cứu hộ OCR tự động (Automatic OCR Rescue)**:
   - Nếu phát hiện trang scan, trang ảnh hoặc số ký tự $< 40$, hệ thống tự động định tuyến cứu hộ qua **Mistral OCR Cloud** (`mistral-ocr-latest`) cho độ chính xác cao và tốc độ 1-2s; nếu mạng lỗi hoặc thiếu API key, hệ thống tự động rơi về **Local OCR** (`easyocr` / `docling`).

### Bước 4: Bảo toàn bảng biểu Markdown GFM, Phân vùng vĩ mô & Lưu trữ `page_markdowns`
- **Bảo toàn bảng biểu GFM**: Hàm `_format_table_markdown` chuyển đổi ma trận bảng số hóa thành bảng Markdown chuẩn GitHub Flavored Markdown (`| Tiêu đề 1 | Tiêu đề 2 |`), ngăn ngừa triệt để lỗi mất dữ liệu bảng tuyển sinh hay điểm chuẩn.
- **Phân vùng bố cục vĩ mô ([`layout_detector.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/layout_detector.py))**: Kết hợp Computer Vision OpenCV và Vector PDF để nhận diện con dấu đỏ (`HSV stamps`), khối Dấu & Ký (`signature`), phân định Quốc hiệu, Tiêu ngữ, Căn cứ pháp lý, triệt tiêu 100% hiện tượng text giả lập.
- **Làm sạch văn bản ([`cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py))**: Chuẩn hóa Unicode NFC sạch, loại bỏ dấu trang thừa, chân trang rác.
- **Bảo tồn Markdown từng trang (`page_markdowns`)**: Lưu trữ nội dung Markdown sạch độc lập cho từng trang trong `doc_metadata["page_markdowns"]` để khắc phục triệt để lỗi "chunks dồn hết vào trang 1 khiến trang 2..N bị trắng tinh".

### Bước 5: Chiến lược phân đoạn tri thức (Chunking Strategy)
- **`ClauseBasedChunker`**: Dành riêng cho Quy chế đào tạo, Quyết định, Thông tư, Quy định học vụ. Quét biểu thức chính quy `(?:Điều|Chương|Phần)\s+\d+` để cắt độc lập từng Điều, Khoản, gắn nhãn trích dẫn chính xác.
- **`SemanticChunker`**: Dành cho cẩm nang sinh viên, đề án tuyển sinh, giáo trình. Cắt theo ranh giới đoạn văn ngữ nghĩa với kích thước `max_tokens = 500`.
- **Ghi nhận `page_number` chính xác**: Mọi chunk đều được parse thẻ `<!-- Trang X -->` để gắn đúng số trang phục vụ trích dẫn gốc.

### Bước 6: Bóc tách tầng số liệu sự thật (Structured Facts Layer)
- Các bảng số liệu có tính biến động cao hoặc yêu cầu độ chính xác tuyệt đối (Mã ngành, Điểm chuẩn, Chỉ tiêu tuyển sinh, Học phí từng học kỳ) được trích xuất tự động qua `fact_extractor.py` và nạp vào bảng PostgreSQL `knowledge_facts`.
- Khi nạp tệp xong, tài liệu được lưu trong PostgreSQL với trạng thái **`status = "pending"`**. Chunks và Facts đã sẵn sàng trong DB quan hệ nhưng **CHƯA ĐƯỢC NẠP VÀO VECTOR DB**.

### Bước 7: Tầng đối soát & Hiệu đính con người (Human-in-the-loop Verification Studio)
- Cán bộ mở **Document Verification Studio** (`/knowledge/collections/:id/documents/:docId/verification`):
  - **Màn hình đối soát song song**: Cột trái hiển thị ảnh scan tài liệu gốc; Cột phải hiển thị kết quả Markdown đã chuẩn hóa.
  - **Công cụ Right Toolbar tối giản**: Chuyển đổi linh hoạt giữa `[Trang hiện tại]` và `[Toàn bộ file]`; chuyển đổi giữa `[Xem render GFM]` và `[Xem mã nguồn .md]`.
  - **Chế độ Sửa tay (In-place Edit)**: Nếu phát hiện ký tự OCR bị nhầm lẫn hoặc bảng biểu bị lệch cột, cán bộ bấm `[✏️ Sửa tay]`, chỉnh sửa Markdown trực tiếp, bấm `[Xem trước]` và `[Lưu sửa]`. Dữ liệu hiệu đính được cập nhật ngay vào `page_markdowns` và đánh dấu `human_verified = True`.

### Bước 8: Phê duyệt & Đánh chỉ mục kép (Dual Indexing)
- Khi cán bộ bấm nút **`[Xác nhận & Nạp vào Vector DB]`** (gọi API `POST /knowledge/documents/{document_id}/approve` hoặc `POST /knowledge/documents/batch-approve`):
  1. **Chỉ mục Ngữ nghĩa (Dense Vector Search)**: Sinh vector 1024 chiều bằng mô hình Embedding đang hoạt động (Cloudflare BGE-M3 hoặc Local CPU), đẩy các điểm vector (`points`) vào Qdrant Vector DB kèm metadata số trang, trích đoạn.
  2. **Chỉ mục Từ khóa (Sparse Lexical Search)**: Cập nhật chỉ mục `tsvector` tiếng Việt trên cột `tsv_content` của bảng PostgreSQL `knowledge_chunks` phục vụ tra cứu từ khóa chính xác và chữ viết tắt (DQN, CNTT, UIS).
  3. **Chuyển đổi trạng thái hoàn tất**: Tài liệu được cập nhật sang **`status = "approved"`**, ghi nhận `indexed_chunks` và sẵn sàng 100% cho bộ máy Hybrid RAG kết hợp thuật toán **Reciprocal Rank Fusion (RRF $k=60$)** và Cross-Encoder Reranking không bịa đặt.

### Bước 9: Tái Đối Soát Facts Khi Sửa Tay (Fact Reconciliation) & Xóa Thác Đổ (Cascading Cleanup) Chống Ghost Vector
- **Tái đối soát Facts khi sửa tay (Facts Reconciliation)**: Khi cán bộ phê duyệt tài liệu sau khi sửa tay các trang trong Verification Studio (`approve_document`), hệ thống tự động xóa toàn bộ Facts cũ (`DELETE FROM knowledge_facts WHERE document_id = ...`) và kích hoạt trích xuất lại Facts mới từ Markdown đã hiệu đính, ngăn chặn triệt để tình trạng Facts lỗi thời mâu thuẫn với nội dung trang.
- **Xóa thác đổ (Cascading Cleanup) triệt tiêu Ghost Vectors**:
  * Khi gọi API Xóa tài liệu (`DELETE /knowledge/documents/{id}`), Lưu trữ (`POST /knowledge/documents/{id}/archive`) hoặc Xóa bộ sưu tập (`DELETE /knowledge/collections/{id}`), hệ thống xóa đồng bộ và dọn dẹp triệt để trên 4 tầng:
    1. **Tầng Lưu trữ (MinIO / Local Disk)**: Xóa tệp gốc và toàn bộ ảnh render trang trong thư mục cache.
    2. **Tầng Vector DB (Qdrant)**: Xóa toàn bộ point vectors theo `document_id` hoặc xóa collection tương ứng (triệt tiêu vĩnh viễn vector mồ côi / ghost vector).
    3. **Tầng CSDL Quan hệ (PostgreSQL)**: Xóa cascading bản ghi tài liệu, chunks và facts liên kết.
    4. **Tầng Bộ nhớ Đệm (Redis Semantic Cache)**: Tự động vô hiệu hóa toàn bộ cache ngữ nghĩa của collection liên quan (`invalidate_collection`), bảo đảm các truy vấn sau đó không nhận kết quả từ dữ liệu đã xóa.
