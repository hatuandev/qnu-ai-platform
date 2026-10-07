# NHẬT KÝ LÀM VIỆC — PHIÊN #283

- **Thời gian thực hiện**: 2026-10-07 15:30 (UTC+7)
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên**: Triển khai toàn diện phân hệ **Kho Tài Liệu Tập Trung (Central Document Repository)** lưu trữ MinIO S3, tiền bóc tách sang Markdown sạch kèm bảng biểu, cơ chế khử trùng lặp SHA-256, và tích hợp nạp dữ liệu một chạm (Attach from Repository) vào phân hệ **Kho Tri Thức (`/knowledge`)** sang cơ sở dữ liệu Vector (Qdrant).

---

## 1. Bối Cảnh & Vấn Đề Nghiệp Vụ

Trước đây trên nền tảng QNU AI Platform:
1. **Khớp nối quá chặt chẽ (Tight Coupling)**: Khi người dùng muốn đưa tri thức vào hệ thống, tệp tài liệu gốc (.pdf, .docx, .xlsx, .txt) phải được tải lên trực tiếp vào từng Kho Tri Thức cụ thể (`/knowledge/collections/:id`).
2. **Lãng phí tài nguyên tính toán (Redundant OCR & Extraction)**: Khi một tài liệu quy chế chung của Trường (ví dụ Quyết định 2139/QĐ-ĐHQN về học phí và quy chế tuyển sinh) cần dùng cho nhiều Trợ lý AI khác nhau (Trợ lý Tuyển sinh, Trợ lý Quy chế học vụ, Trợ lý Khảo thí), người dùng phải tải lên lại nhiều lần, khiến hệ thống phải kích hoạt lại Vision OCR hoặc Docling tốn thời gian và GPU/CPU VRAM.
3. **Khó khăn khi đổi mô hình Embedding**: Khi quản trị viên muốn thử nghiệm hoặc chuyển đổi mô hình nhúng vector (từ `bge-m3` sang `qwen3-embedding` hay `text-embedding-3-small`), việc phải bóc tách lại toàn bộ tài liệu gốc rất rủi ro và mất thời gian.

**Giải pháp đột phá**:
Tách bạch phân hệ **Kho Tài Liệu Tập Trung (`/documents`)** làm tầng lưu trữ và tiền xử lý tri thức (Storage & Pre-parsing Layer). Tài liệu đưa vào đây được lưu trữ an toàn trong MinIO Object Storage, khử trùng lặp nội dung bằng hàm băm SHA-256, tự động tiền bóc tách sang định dạng chuẩn Markdown (GFM) bảo tồn bảng biểu và metadata hành chính theo Nghị định 30/2020/NĐ-CP. Phân hệ **Kho Tri Thức (`/knowledge`)** chỉ cần "Gắn từ kho" (Attach from Repository), hệ thống sẽ nạp trực tiếp bản Markdown sạch vào pipeline chunking và vector embedding (Qdrant) mà không cần bóc tách lại!

---

## 2. Kiến Trúc Kỹ Thuật & Thay Đổi Chi Tiết

### A. Cơ Sở Dữ Liệu & Migration Alembic
- **Bảng `repository_documents`**:
  - `id`: Định danh UUID chuẩn RFC 4122 (`rdoc_...`).
  - `title`, `original_filename`, `content_type`, `file_size_bytes`: Thông tin tệp gốc.
  - `file_hash`: Khóa băm SHA-256 dùng để kiểm tra và ngăn chặn tải lên trùng lặp (Deduplication).
  - `storage_path`: Đường dẫn lưu trữ trong bucket MinIO (`documents/originals/{file_hash}/{filename}`).
  - `preview_image_path`: Đường dẫn ảnh render trang đầu của tài liệu PDF (`documents/previews/{file_hash}/page_1.png`).
  - `parsed_markdown`: Chuỗi văn bản Markdown sạch đã được chuẩn hóa Unicode NFC và cấu trúc GFM.
  - `parse_status`: Trạng thái xử lý (`pending`, `parsing`, `completed`, `failed`).
  - `word_count`, `table_count`, `page_count`: Số liệu thống kê trích xuất.
  - Metadata Nghị định 30/2020/NĐ-CP: `doc_type_id`, `legal_number`, `issuing_date`, `signer_title`, `signer_name`, `issuing_authority`, `field_code`.
- **Liên kết bảng `knowledge_documents`**:
  - Bổ sung cột khóa ngoại `repository_document_id` (nullable) trỏ sang `repository_documents.id` (ondelete SET NULL), bảo đảm tính tương thích ngược 100%.
- **Alembic Migration**: Tạo tệp migration [`backend/alembic/versions/20261007_document_repository.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20261007_document_repository.py).
- **Tự động kiểm tra Schema**: Bổ sung `"repository_documents"` vào danh sách `required_tables` trong [`backend/app/cli.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/cli.py).

---

### B. Module Backend `documents` (Chuẩn 4-File Clean Architecture)
Module được thiết kế chuẩn mực 4 tệp độc lập theo quy định `AGENTS.md`:

1. **`models.py`** ([`backend/app/modules/documents/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/models.py)):
   - Khai báo model SQLAlchemy `RepositoryDocument`.
2. **`schemas.py`** ([`backend/app/modules/documents/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/schemas.py)):
   - Các Pydantic DTOs: `RepositoryDocumentUploadResponse`, `RepositoryDocumentResponse`, `RepositoryDocumentListResponse`, `RepositoryDocumentUpdate`, `RepositoryDocumentStatsResponse`, `AttachRepositoryDocumentsRequest`, `AttachRepositoryDocumentsResponse`.
3. **`service.py`** ([`backend/app/modules/documents/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/service.py)):
   - `DocumentRepositoryService`:
     - **Upload & Deduplication**: Tính toán SHA-256 hash của luồng byte; nếu tệp đã tồn tại trong kho, trả về bản ghi hiện tại kèm cờ `is_duplicate=True` tránh lãng phí dung lượng S3.
     - **Tải lên MinIO S3**: Lưu trữ an toàn tệp gốc vào `documents/originals/{hash}/{filename}`.
     - **Tự động Pre-parse Markdown**: Điều phối qua Strategy Pattern `get_document_parser(content_type)` kết hợp tầng làm sạch `clean_markdown_text` chuẩn hóa Unicode NFC và cấu trúc bảng.
     - **Render ảnh xem trước**: Sử dụng PyMuPDF (`fitz`) trích xuất trang đầu tiên của file PDF sang ảnh PNG sắc nét (DPI 150) và tải lên MinIO `documents/previews/{hash}/page_1.png`.
     - **Thao tác nghiệp vụ**: CRUD, cập nhật metadata NĐ 30, kích hoạt phân tích lại (re-parse on demand), lấy link tải tệp gốc/Markdown, thống kê KPI kho tài liệu.
4. **`router.py`** ([`backend/app/modules/documents/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/documents/router.py)):
   - REST API chuẩn RFC 7807:
     - `POST /platform/v1alpha1/documents/upload`: Tải lên tệp kèm metadata NĐ 30 và tùy chọn `auto_parse`.
     - `GET /platform/v1alpha1/documents`: Danh sách tài liệu với phân trang, tìm kiếm từ khóa, lọc loại văn bản, định dạng tệp, trạng thái parse.
     - `GET /platform/v1alpha1/documents/stats`: Thống kê tổng tài liệu, dung lượng, số tệp đã parse, số từ, số bảng biểu.
     - `GET /platform/v1alpha1/documents/{document_id}`: Chi tiết tài liệu kèm danh sách các Kho Tri Thức đang liên kết.
     - `PATCH /platform/v1alpha1/documents/{document_id}`: Cập nhật thông tin & metadata NĐ 30.
     - `DELETE /platform/v1alpha1/documents/{document_id}`: Xóa tài liệu khỏi kho và dọn dẹp MinIO storage.
     - `POST /platform/v1alpha1/documents/{document_id}/reparse`: Kích hoạt phân tích lại tài liệu sang Markdown.
     - `GET /platform/v1alpha1/documents/{document_id}/download`: Tải về tệp gốc từ MinIO.
     - `GET /platform/v1alpha1/documents/{document_id}/markdown`: Tải về tệp Markdown đã bóc tách.
     - `GET /platform/v1alpha1/documents/{document_id}/preview-image`: Xem trước ảnh trang đầu.

---

### C. Đấu Nối Nạp Tri Thức Từ Kho (Knowledge Integration Layer)
- **Tầng Ingestion Service** ([`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py)):
  - Xây dựng phương thức `ingest_from_repository_documents(collection_id, repository_document_ids, session)`.
  - Kiểm tra các tài liệu đã được bóc tách Markdown (`parse_status == 'completed'`).
  - Tạo bản ghi `KnowledgeDocument` với liên kết `repository_document_id`.
  - Bỏ qua toàn bộ bước gọi OCR/Docling tốn kém, đẩy trực tiếp nội dung Markdown vào bộ chia đoạn (`ClauseBasedChunker` hoặc `SemanticChunker`) và nhúng vector vào Qdrant theo đúng cấu hình embedding model của kho.
- **Knowledge Router** ([`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py)):
  - Endpoint `POST /platform/v1alpha1/knowledge/collections/{collection_id}/attach-repository-documents`.

---

### D. Giao Diện Người Dùng Frontend (Radix UI, TanStack Router & Lucide Icons)
Tuân thủ 100% quy định giao diện trong `AGENTS.md` (3-tier components, Master-Detail deep routing, Academic Teal tokens, 0 raw HTML elements, 0 emoji):

1. **Điều Hướng & Types**:
   - Thêm mục "Kho Tài Liệu" (`/documents`, icon `FileStack`) vào menu "Xây Dựng AI" trong [`frontend/src/navigation/config.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/navigation/config.ts).
   - Khai báo types chuẩn trong [`frontend/src/types/documents.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/documents.ts) và API client trong [`frontend/src/services/documents-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/documents-api.ts).
2. **Trang Danh Sách Master View (`/documents`)**:
   - [`frontend/src/features/documents/documents-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/documents/documents-page.tsx):
     - 4 thẻ KPI chỉ số (`KpiMetric`): *Tổng tài liệu*, *Đã bóc tách Markdown*, *Tổng số từ tri thức*, *Dung lượng lưu trữ*.
     - Thanh công cụ lọc mạnh mẽ: Tìm kiếm từ khóa, Lọc Loại văn bản (Quyết định, Thông báo, Quy định...), Lọc Định dạng (PDF, DOCX, XLSX...), Lọc Trạng thái Parse.
     - Nút chuyển chế độ xem chuẩn hóa `<ViewModeToggle />` giữa Thẻ lưới (Grid) và Bảng danh sách (Table).
3. **Thành Phần Lưới & Bảng**:
   - Thẻ lưới [`document-card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/documents/components/document-card.tsx): Phân biệt icon theo định dạng file, hiển thị trạng thái Markdown badge, số từ, số bảng, metadata NĐ 30, menu thao tác dropdown (Chi tiết, Reparse, Tải file, Xóa).
   - Bảng danh sách [`documents-table.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/documents/components/documents-table.tsx): Thiết kế dòng chuẩn `h-11`, hỗ trợ chọn nhiều checkbox để thao tác hàng loạt, sắp xếp theo ngày cập nhật.
4. **Modal Tải Lên Thông Minh (`document-upload-modal.tsx`)**:
   - Dropzone hỗ trợ kéo thả tệp (`.pdf`, `.docx`, `.xlsx`, `.txt`, `.md`).
   - Tự động điền tiêu đề từ tên tệp.
   - Form nhập metadata hành chính NĐ 30 (Loại văn bản, Số ký hiệu, Ngày ban hành, Cơ quan ban hành, Người ký).
   - Switch "Tự động phân tích sang Markdown ngay sau khi tải lên" (bật mặc định).
5. **Trang Chi Tiết Độc Lập Dedicated Detail View (`/documents/:documentId`)**:
   - [`frontend/src/features/documents/document-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/documents/document-detail-page.tsx):
     - Header với nút Quay lại, tên văn bản, các nút thao tác: *Phân tích lại (Reparse)*, *Tải tệp gốc*, *Tải tệp Markdown*, *Xóa*.
     - Bố cục 2 cột chuyên sâu tận dụng tối đa màn hình:
       - Cột trái: Tab "Nội dung Markdown" (xem trước văn bản GFM sạch, có cú pháp highlight và thống kê số từ/số bảng) và Tab "Ảnh trang đầu" (xem trước trang scan PDF từ MinIO).
       - Cột phải: Thẻ "Thông tin tệp & Trạng thái bóc tách", Thẻ "Metadata Văn bản (NĐ 30)" cho phép chỉnh sửa và lưu trực tiếp, Thẻ "Kho Tri Thức Đang Sử Dụng" (hiển thị danh sách các collection đang nạp tài liệu này).
6. **Hộp Thoại "Gắn Từ Kho" Trong Kho Tri Thức (`attach-from-repository-dialog.tsx`)**:
   - [`frontend/src/components/knowledge/dialogs/attach-from-repository-dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/dialogs/attach-from-repository-dialog.tsx): Cho phép người dùng duyệt kho tài liệu tập trung, lọc các tài liệu đã có Markdown sạch, chọn nhiều tài liệu và 1-click nạp vào bộ sưu tập hiện tại.
   - Tích hợp nút "Gắn Từ Kho" (icon `FileStack`) ngay cạnh nút "Nạp tài liệu" trên Header kho tri thức ([`collection-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/collection-header.tsx) và [`collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/features/knowledge/collection-detail-page.tsx)).

---

## 3. Kết Quả Kiểm Thử & Xác Nhận Chất Lượng

### A. Kiểm Thử Backend (Pytest & Ruff)
- **Ruff Code Linter**:
  ```bash
  uv run ruff check app/modules/documents/ tests/test_document_repository.py
  ```
  $\rightarrow$ **All checks passed (0 cảnh báo, 0 lỗi)!**
- **Unit Test Suite Chuyên Biệt (`tests/test_document_repository.py`)**:
  - `test_upload_document_success`: Kiểm thử tải file, tính hash SHA-256, lưu MinIO và kích hoạt pre-parse.
  - `test_upload_duplicate_detection`: Kiểm thử phát hiện file trùng hash, trả về bản ghi cũ kèm `is_duplicate=True`.
  - `test_list_documents_and_stats`: Kiểm thử truy vấn danh sách phân trang và tính toán số liệu KPI.
  - `test_get_and_update_document`: Kiểm thử truy vấn chi tiết và cập nhật metadata NĐ 30.
  - `test_reparse_document`: Kiểm thử kích hoạt phân tích lại tài liệu.
  - **Kết quả**: **5/5 tests PASSED 100%** trong 3.99s.

### B. Kiểm Thử Frontend (Vite Build & Typecheck)
- **Vite Bundle Build (`npm run build`)**:
  - Lệnh: `cmd /c "npm run build"`
  - Thời gian biên dịch: **3.23 giây**.
  - **Kết quả**: **0 lỗi TypeScript, 0 lỗi cú pháp Vite, exit code 0!**
  - Các route mới (`/documents`, `/documents/`, `/documents/$documentId`) được đăng ký chuẩn mực trong TanStack Router.

---

## 4. Đánh Giá Giá Trị Đạt Được & Sẵn Sàng Vận Hành

1. **Hiệu năng & Tối ưu GPU**: Giảm thiểu 100% việc lặp lại OCR đối với cùng một tài liệu khi sử dụng cho nhiều Kho Tri Thức khác nhau; giải phóng tải tính toán cho GPU server RTX 5090.
2. **Linh hoạt Vector Embedding**: Cho phép thay đổi mô hình Embedding bất cứ lúc nào trên Kho Tri Thức mà không sợ mất mát dữ liệu hoặc phải bóc tách lại từ file gốc.
3. **Chuẩn hóa Văn bản hành chính**: Tự động lưu trữ và quản lý metadata Nghị định 30/2020/NĐ-CP tập trung, hỗ trợ tra cứu và đối soát tài liệu gốc dễ dàng.
4. **UI/UX Đạt Chuẩn Enterprise**: Thiết kế nhất quán theo nhận diện ĐH Quy Nhơn (Academic Teal), 100% Lucide icons, điều hướng Master-Detail mượt mà và trực quan.
