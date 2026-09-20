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
        
        H1 & H3 & H4 --> K1[Bảo toàn bảng biểu & Canonical Normalization: Loại bỏ trùng lặp text/table, TableReconstructor nối bảng đa trang]
        K1 --> K2[SmartLayoutDetector OpenCV: Phân vùng vĩ mô, bóc tách con dấu đỏ, chữ ký]
        K2 --> K3[Markdown Renderer: Chuẩn hóa 1 hàng/dòng Markdown, reflow ô nhiều dòng thành <br>, Unicode NFC]
        K3 --> K4[Bảo tồn Markdown từng trang & CanonicalDocument trong bộ nhớ xử lý]
        K4 --> QG{Data Quality Gate}
        QG -->|Có lỗi blocking| REVIEW[status = review_pending<br/>Không sinh chunk, fact hay Qdrant point]
        QG -->|Đạt kiểm định| L
    end

    subgraph TANG_PHAN_MANH [3. Tầng Phân Mảnh Tri Thức & Structured Facts]
        L -->|Văn bản pháp quy / Quy chế đào tạo| M[ClauseBasedChunker: Cắt theo từng Điều / Khoản có nhãn trích dẫn]
        L -->|Cẩm nang / Tuyển sinh / Giáo trình| N[SemanticChunker: Cắt phân đoạn ngữ nghĩa trôi chảy max 500 tokens]
        L -->|Tuyển sinh / Kế hoạch nhiệm vụ đã đạt kiểm định| R[Record-aware chunker: 1 ngành / 1 nhiệm vụ = 1 chunk]
        
        M & N & R -->|Lưu danh sách Chunks vào CSDL| DB_CHUNKS[(PostgreSQL: bảng knowledge_chunks)]
        M & N & R --> O[Fact Extractor: Trích xuất Bảng số liệu dạng cấu trúc]
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
- **Bảo tồn Markdown từng trang (`page_markdowns`)**: Lưu trữ nội dung Markdown sạch độc lập cho từng trang trong `doc_metadata["page_markdowns"]` để khắc phục triệt để lỗi "chunks dồn hết vào trang 1 khiến trang 2..N bị trắng tinh". `CanonicalDocument` chỉ tồn tại trong phiên xử lý để kiểm định và không được tuần tự hóa vào metadata.
- **Không phát minh tiêu đề cột**: Markdown renderer không tự đặt tên kiểu `Cột N`. Bảng có header rỗng, header giả hoặc không tái dựng được sẽ không được render như dữ liệu hợp lệ.

### Bước 5: Chiến lược phân đoạn tri thức (Chunking Strategy)
- **`ClauseBasedChunker`**: Dành riêng cho Quy chế đào tạo, Quyết định, Thông tư, Quy định học vụ. Quét biểu thức chính quy `(?:Điều|Chương|Phần)\s+\d+` để cắt độc lập từng Điều, Khoản, gắn nhãn trích dẫn chính xác.
- **`SemanticChunker`**: Dành cho cẩm nang sinh viên, đề án tuyển sinh, giáo trình. Cắt theo ranh giới đoạn văn ngữ nghĩa với kích thước `max_tokens = 500`.
- **Ghi nhận `page_number` chính xác**: Mọi chunk đều được parse thẻ `<!-- Trang X -->` để gắn đúng số trang phục vụ trích dẫn gốc.
- **Record-aware chunking cho bảng nghiệp vụ**: Khi Quality Gate đạt, Tuyển sinh tạo một chunk nguyên tử cho mỗi ngành; Kế hoạch nhiệm vụ tạo một chunk cho mỗi mã nhiệm vụ. Không cắt theo độ dài giữa một bản ghi và không index lại header/trang lặp.

### Bước 6: Bóc tách tầng số liệu sự thật (Structured Facts Layer)
- Các bảng số liệu có tính biến động cao hoặc yêu cầu độ chính xác tuyệt đối (Mã ngành, Điểm chuẩn, Chỉ tiêu tuyển sinh, Học phí từng học kỳ) được trích xuất tự động qua `fact_extractor.py` và nạp vào bảng PostgreSQL `knowledge_facts`.
- **Data Quality Gate bắt buộc trước Facts/Chunks**: kiểm tra lỗi mã hóa, cột vô danh, hàng sai số cột, trùng bản ghi nghiệp vụ và mâu thuẫn chéo bảng. Lỗi `blocking` chuyển tài liệu sang **`review_pending`**, lưu `quality_report`, không lưu chunk/fact và không được phép lập chỉ mục Qdrant.
- Khi nạp tệp đạt kiểm định, tài liệu được lưu trong PostgreSQL với trạng thái **`status = "pending"`**. Chunks và Facts đã sẵn sàng trong DB quan hệ nhưng **CHƯA ĐƯỢC NẠP VÀO VECTOR DB**.

### Bước 7: Tầng đối soát & Hiệu đính con người (Human-in-the-loop Verification Studio)
- Cán bộ mở **Document Verification Studio** (`/knowledge/collections/:id/documents/:docId/verification`):
  - **Màn hình đối soát song song**: Cột trái hiển thị ảnh scan tài liệu gốc; Cột phải hiển thị kết quả Markdown đã chuẩn hóa.
  - **Công cụ Right Toolbar tối giản**: Chuyển đổi linh hoạt giữa `[Trang hiện tại]` và `[Toàn bộ file]`; chuyển đổi giữa `[Xem render GFM]` và `[Xem mã nguồn .md]`.
  - **Chế độ Sửa tay (In-place Edit)**: Nếu phát hiện ký tự OCR bị nhầm lẫn hoặc bảng biểu bị lệch cột, cán bộ bấm `[✏️ Sửa tay]`, chỉnh sửa Markdown trực tiếp, bấm `[Xem trước]` và `[Lưu sửa]`. Dữ liệu hiệu đính được cập nhật ngay vào `page_markdowns` và đánh dấu `human_verified = True`.

### Bước 8: Phê duyệt & Đánh chỉ mục kép (Dual Indexing)
- Khi cán bộ bấm nút **`[Xác nhận & Nạp vào Vector DB]`** (gọi API `POST /knowledge/documents/{document_id}/approve` hoặc `POST /knowledge/documents/batch-approve`):
  0. Nếu `quality_report.passed = false`, API từ chối phê duyệt rỗng với HTTP 409 `document_review_required`. Cán bộ phải gửi trang Markdown đã hiệu đính; hành động này là xác nhận có trách nhiệm và đặt `human_verified = true`.
  1. **Chỉ mục Ngữ nghĩa (Dense Vector Search)**: Sinh vector 1024 chiều bằng mô hình Embedding đang hoạt động (Cloudflare BGE-M3 hoặc Local CPU), đẩy các điểm vector (`points`) vào Qdrant Vector DB kèm metadata số trang, trích đoạn.
  2. **Chỉ mục Từ khóa (Sparse Lexical Search)**: Cập nhật chỉ mục `tsvector` tiếng Việt trên cột `tsv_content` của bảng PostgreSQL `knowledge_chunks` phục vụ tra cứu từ khóa chính xác và chữ viết tắt (DQN, CNTT, UIS).
  3. **Chuyển đổi trạng thái hoàn tất**: Tài liệu được cập nhật sang **`status = "approved"`**, ghi nhận `indexed_chunks` và sẵn sàng 100% cho bộ máy Hybrid RAG kết hợp thuật toán **Reciprocal Rank Fusion (RRF $k=60$)** và Cross-Encoder Reranking không bịa đặt.

### Bước 9: Tái Đối Soát Facts Khi Sửa Tay (Fact Reconciliation) & Xóa Thác Đổ (Cascading Cleanup) Chống Ghost Vector
- **Tái đối soát Facts khi sửa tay (Facts Reconciliation)**: Khi cán bộ phê duyệt tài liệu sau khi sửa tay các trang trong Verification Studio (`approve_document`), hệ thống tự động xóa toàn bộ Facts cũ (`DELETE FROM knowledge_facts WHERE document_id = ...`) và chỉ trích xuất lại Facts từ các bảng GFM có header/row hợp lệ trong Markdown đã xác nhận. Không suy đoán dữ liệu từ bảng lỗi; số lượng được lưu ở `human_verified_fact_count`.
- **Xóa thác đổ (Cascading Cleanup) triệt tiêu Ghost Vectors**:
  * Khi gọi API Xóa tài liệu (`DELETE /knowledge/documents/{id}`), Lưu trữ (`POST /knowledge/documents/{id}/archive`) hoặc Xóa bộ sưu tập (`DELETE /knowledge/collections/{id}`), hệ thống xóa đồng bộ và dọn dẹp triệt để trên 4 tầng:
    1. **Tầng Lưu trữ (MinIO / Local Disk)**: Xóa tệp gốc và toàn bộ ảnh render trang trong thư mục cache.
    2. **Tầng Vector DB (Qdrant)**: Xóa toàn bộ point vectors theo `document_id` hoặc xóa collection tương ứng (triệt tiêu vĩnh viễn vector mồ côi / ghost vector).
    3. **Tầng CSDL Quan hệ (PostgreSQL)**: Xóa cascading bản ghi tài liệu, chunks và facts liên kết.
    4. **Tầng Bộ nhớ Đệm (Redis Semantic Cache)**: Tự động vô hiệu hóa toàn bộ cache ngữ nghĩa của collection liên quan (`invalidate_collection`), bảo đảm các truy vấn sau đó không nhận kết quả từ dữ liệu đã xóa.

### Bước 10: Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV (Structured Facts Ingestion)
- **Mục đích**: Đối với các tài liệu thuần số liệu dạng ma trận (điểm chuẩn tuyển sinh 3 năm, bảng chỉ tiêu từng ngành, biểu mức học phí, danh mục học phần tiên quyết), việc bóc tách OCR từ file scan có nguy cơ lệch cột. Hệ thống hỗ trợ nạp trực tiếp qua tệp bảng tính `.xlsx`, `.xls` hoặc `.csv`.
- **Cơ chế hoạt động ([`excel_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/excel_parser.py))**:
  1. Dùng `openpyxl` hoặc `csv` để đọc mọi sheet và dòng trong tệp nạp lên.
  2. Tự động nhận diện cột Thực thể (`Mã ngành`, `Tên ngành`, `Đối tượng`) và các cột Thuộc tính (`Điểm chuẩn`, `Chỉ tiêu`, `Học phí`, `Tổ hợp môn`).
  3. Bóc tách từng dòng thành các cặp `(entity_name, entity_type, attribute_name, attribute_value)` với độ tin cậy tuyệt đối (`confidence = 1.0`).
  4. Lưu trữ bền vững vào bảng PostgreSQL `knowledge_facts`, tự động liên kết với `collection_id`.
  5. Khi Trợ lý AI nhận câu hỏi có chứa số liệu (như "Điểm chuẩn ngành Công nghệ thông tin năm 2024?"), hệ thống RAG ưu tiên tra cứu trực tiếp từ tầng Facts số hóa trước khi truy xuất văn bản thô, bảo đảm **Zero Hallucination** 100%.
### Bước 11: Vòng Đời Lập Chỉ Mục Kép, Tách Bạch Hàng Đợi & Đối Soát Bền Vững 4 Tầng (Giai Đoạn D - P1-09 đến P1-13)
- **Chuẩn hóa Document Lifecycle State Machine (Máy Trạng Thái Vòng Đời Tài Liệu)**:
  - Vòng đời tài liệu tuân thủ nghiêm ngặt cỗ máy trạng thái 7 bước:
    `uploaded` $\rightarrow$ `extracting` $\rightarrow$ `review_pending` $\rightarrow$ `approved` $\rightarrow$ `indexing` $\rightarrow$ `ready`, và `ready` $\rightarrow$ `archived`.
  - **Tách bạch dứt khoát giữa `approved` và `ready`**:
    * `approved`: Trạng thái nghiệp vụ — Cán bộ kiểm duyệt con người đã xác nhận nội dung bóc tách/OCR là sạch sẽ và chính xác.
    * `ready`: Trạng thái kỹ thuật toàn vẹn — Tất cả chunks đã được tính toán embeddings và nạp thành công vào Qdrant Vector DB (`index_status = "indexed"`). Chỉ khi đạt `status = "ready"` (hoặc `ready`/`approved`), tài liệu mới được phép xuất hiện trong kết quả truy vấn RAG.
    * Nếu xảy ra lỗi vector indexing (mất mạng, Qdrant offline), tài liệu giữ nguyên `status = "approved"`, ghi nhận `index_status = "index_failed"` kèm `index_error` chi tiết để cán bộ reindex mà không làm mất công sức kiểm duyệt của con người.
- **Quy Chuẩn Bắt Buộc 11 Metadata Fields Cho Qdrant Point Payload (Schema Version v1)**:
  - Mọi điểm vector nạp vào Qdrant bắt buộc phải có đủ 11 trường metadata, cơ chế **Fail-Fast** (`AppException(code="INVALID_POINT_PAYLOAD", status_code=400)`) sẽ từ chối ngay lập tức nếu thiếu bất kỳ trường nào:
    1. `tenant_id`: Mã định danh đơn vị thuê (ví dụ: `tenant_qnu`).
    2. `workspace_id`: Mã không gian làm việc (ví dụ: `workspace_qnu` hoặc `ws_default`).
    3. `collection_id`: Mã bộ sưu tập tri thức.
    4. `document_id`: Mã tài liệu nguồn.
    5. `document_revision`: Số phiên bản hiệu chỉnh của tài liệu (`int`).
    6. `chunk_id`: Mã phân đoạn tri thức.
    7. `document_status`: Trạng thái vòng đời (`ready` hoặc `approved`).
    8. `is_retrievable`: Cờ cho phép truy xuất RAG (`bool`, bắt buộc `True` đối với point hợp lệ).
    9. `content_hash`: Mã băm SHA-256 nội dung của chunk.
    10. `embedding_model`: Tên mô hình embedding đã sinh vector (ví dụ: `text-embedding-3-small`, `@cf/baai/bge-m3`).
    11. `payload_schema_version`: Phiên bản cấu trúc payload (bắt buộc `"v1"`).
- **Tách bạch Job Type trong hàng đợi nền (Job Queue Separation)**:
  - Tách bạch dứt khoát giữa `job_type="ingestion_extract"` (bóc tách văn bản, OCR, sinh chunks khi upload) và `job_type="vector_indexing"` (tính toán embeddings, nạp vectors vào Qdrant khi phê duyệt hoặc reindex), khắc phục triệt để nhầm lẫn hàng đợi và nghẽn tiến trình.
- **Cơ chế Khôi phục Lập chỉ mục đơn lẻ (`reindex_document`)**:
  - Cung cấp API `POST /knowledge/documents/{id}/reindex` và nút bấm trực quan `[⚡ Thử lại Index]` trên giao diện bảng danh sách tài liệu, cho phép cán bộ tái nạp vector ngay lập tức khi phát hiện tài liệu `approved` nhưng ở trạng thái `index_failed`.
- **Thanh tra Đối Soát Bền Vững 4 Tầng (`reconcile_collection` & CLI Quản Trị)**:
  - Cung cấp API `GET /knowledge/collections/{id}/reconcile`, nút `[Đối soát Kho]` trên UI, và lệnh CLI chuyên dụng:
    ```bash
    # Đối soát toàn bộ kho tri thức hoặc 1 collection cụ thể
    python -m app.cli knowledge reconcile [--collection-id col_admissions] [--fix]

    # Lập chỉ mục lại cho 1 collection hoặc 1 tài liệu cụ thể
    python -m app.cli knowledge reindex [--collection-id col_admissions] [--document-id doc_123]
    ```
  - Kiểm tra đối soát 4 tầng thực sự:
    1. **Tầng CSDL Quan hệ (PostgreSQL)**: Đếm tổng số documents, chunks và kiểm tra tính toàn vẹn trạng thái.
    2. **Tầng Vector DB (Qdrant)**: Đếm tổng số points, kiểm tra schema version v1, phát hiện `orphan_qdrant_point` (point tham chiếu chunk không còn trong DB), `scope_mismatch` (tenant/workspace lệch pha), `unretrievable_point_active` (point thuộc doc chưa sẵn sàng nhưng vẫn mở `is_retrievable=True`).
    3. **Tầng Lưu trữ Đối tượng (MinIO/Local Storage)**: Kiểm tra sự tồn tại của tệp tin vật lý gốc `storage_path` thông qua `storage_service.exists()`.
    4. **Tầng Bộ nhớ Đệm (Redis Semantic Cache)**: Hỗ trợ xóa cache phân vùng theo collection (`invalidate_collection`) bao quát cả tiền tố v1 lẫn legacy.
