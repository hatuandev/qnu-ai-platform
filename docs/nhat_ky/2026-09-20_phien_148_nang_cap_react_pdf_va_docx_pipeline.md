# NHẬT KÝ LÀM VIỆC — PHIÊN #148
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Nâng Cấp Trình Xem Tài Liệu Tương Tác Visual Document AI Bằng react-pdf (Mozilla PDF.js) & Tự Động Hóa Pipeline Word DOCX

---

## 1. Bối Cảnh & Mục Tiêu

Sau khi giải quyết vấn đề nhận diện hướng giấy A4 nằm ngang ở phiên #147, người dùng đặt câu hỏi và chốt định hướng:
> *"có công cụ này free có thể trình xem PDF mà vẫn có thể tương tác được ?"*  
> *"nếu chuyển qua vẫn có thể nhận diện scan và xử lý tương tác được với Visual Document AI phải không ?"*  
> *"khi up file pdf thì ko nói nếu up file docx thì bạn sẽ xử lý sao ?"*

Mục tiêu của phiên #148:
1. **Nâng cấp trình xem tài liệu trên Scan Studio**: Thay thế thẻ `<img>` bằng **`react-pdf` v9 (Mozilla PDF.js)**.
2. **Bảo toàn 100% Visual Document AI**: Giữ nguyên lớp phủ Bounding Boxes ngữ nghĩa tương tác (hộp cam `table`, tím `text`, xanh `title`, hồng `signature`), Two-Way Sync với Inspector và quy trình phê duyệt Human-in-the-loop.
3. **Bổ sung tính năng Selectable Text**: Cho phép người dùng dùng chuột bôi đen chữ trực tiếp trên tài liệu gốc để copy/đối soát.
4. **Tự động hóa xử lý Word DOCX**: Backend tự động chuyển đổi file DOCX sang PDF qua Gotenberg/LibreOffice, lưu cache và stream qua endpoint `GET /documents/{document_id}/preview-pdf`.

---

## 2. Chi Tiết Triển Khai Kỹ Thuật

### 2.1. Backend (`app/modules/knowledge/`)
1. **Endpoint mới `GET /documents/{document_id}/preview-pdf` (`router.py`)**:
   - Stream file PDF preview cho Scan Studio.
   - Hỗ trợ đa hình:
     * File PDF: Đọc và stream trực tiếp từ MinIO S3.
     * File Word (`.docx`, `.doc`, `.odt`, `.rtf`): Chuyển đổi tự động sang PDF qua Gotenberg, lưu cache vào `previews/{doc.id}/converted.pdf`.
     * File ảnh (`.png`, `.jpg`, `.bmp`): Chuyển đổi sang PDF vector 1 trang qua PyMuPDF `img_doc.convert_to_pdf()`.
2. **Cập nhật `get_studio_view` (`ingestion_service.py`)**:
   - Trả về trường `pdf_url: f"/platform/v1alpha1/knowledge/documents/{doc.id}/preview-pdf"`.
3. **Cập nhật Facade `service.py`**:
   - Re-export hàm `get_preview_pdf` tuân thủ Clean Architecture.

### 2.2. Frontend (`frontend/src/`)
1. **Cài đặt `react-pdf: ^9.2.1`**:
   - Gói thư viện React 19 wrapper chuẩn công nghiệp của Mozilla `PDF.js`.
2. **Nâng cấp `OcrCanvas` (`ocr-canvas.tsx`)**:
   - Cấu hình PDF.js worker cho môi trường Vite / Web qua unpkg CDN chuẩn.
   - Tích hợp `<Document file={pdfUrl}>` và `<Page pageNumber={page.pageNumber} width={effectivePageWidth} renderTextLayer={true} renderAnnotationLayer={false} />`.
   - Bắt sự kiện `onLoadSuccess` của `Page` để nhận diện kích thước gốc (`originalWidth`, `originalHeight`), tự động xoay ngang/dọc không bao giờ bị méo ảnh.
   - Lớp Bounding Boxes ngữ nghĩa phủ bên trên với `pointer-events-none` cho container và `pointer-events-auto` cho từng box: vừa click chọn box được, vừa bôi đen chữ trên PDF được.
   - Fallback an toàn sang thẻ `<img>` nếu không có `pdfUrl` hoặc khi PDF gặp sự cố nạp.
3. **Cập nhật `scan-studio-page.tsx` & Types**:
   - Nhận `pdf_url` từ API và truyền `pdfUrl` vào `OcrCanvas`.

---

## 3. Các Tệp Đã Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`frontend/package.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/package.json) | `MODIFY` | Thêm dependency `react-pdf: ^9.2.1`. |
| [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) | `MODIFY` | Tích hợp `react-pdf` (`<Document>`, `<Page>`), Text Layer và lớp phủ Bounding Boxes AI. |
| [`frontend/src/components/knowledge/ocr/types.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/types.ts) | `MODIFY` | Thêm `pdfUrl?: string` vào `OcrCanvasProps`. |
| [`frontend/src/types/studio-ocr.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/studio-ocr.ts) | `MODIFY` | Thêm `pdfUrl?: string` vào `StudioOCRDocument`. |
| [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts) | `MODIFY` | Thêm `pdf_url?: string` vào `DocumentVerificationData`. |
| [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) | `MODIFY` | Gán `pdfUrl` trong `mapVerificationDataToStudioDoc` và truyền vào `OcrCanvas`. |
| [`backend/app/modules/knowledge/services/ingestion_service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/services/ingestion_service.py) | `MODIFY` | Triển khai `get_preview_pdf` (hỗ trợ PDF gốc, Word DOCX auto-convert, Image) và thêm `pdf_url` vào `get_studio_view`. |
| [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) | `MODIFY` | Re-export `get_preview_pdf` từ `_ingestion`. |
| [`backend/app/modules/knowledge/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py) | `MODIFY` | Khai báo endpoint `GET /documents/{document_id}/preview-pdf`. |

---

## 4. Kết Quả Kiểm Thử

- **Backend**: `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed!)**.
- **Frontend**:
  - `npm run lint` $\rightarrow$ **Checked 165 files in 229ms. No fixes applied. (0 lỗi)**.
  - `npm run typecheck` $\rightarrow$ **0 lỗi**.
  - `npm run build` $\rightarrow$ **Vite bundle thành công**.
