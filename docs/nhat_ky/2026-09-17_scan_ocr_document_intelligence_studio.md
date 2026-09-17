# NHẬT KÝ LÀM VIỆC — SCAN & OCR DOCUMENT INTELLIGENCE STUDIO
# Ngày: 2026-09-17 | Phiên số: #45
# Kỹ sư / AI Agent: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist

---

## 1. Mục Tiêu Phiên Làm Việc
1. Rà soát tính năng bóc tách, scan studio preview file từ repository tham khảo `D:\DuAnPhanMem\qnu-ai-core` so với `D:\DuAnPhanMem\qnu-ai-platform`.
2. Xây dựng mới hoàn toàn tính năng **Scan & OCR Document Intelligence Studio** chuyên nghiệp, production-ready, đáp ứng đầy đủ năng lực:
   - Nhận diện phân vùng văn bản (Text blocks, Titles, Tables, Con dấu/Chữ ký đỏ, Header/Footer) bằng thuật toán hình thái học (Morphological line extraction) và HSV thresholding của OpenCV (`SmartLayoutDetector`).
   - Kết xuất bảng tính đa trang (Multi-sheet Excel Spreadsheet Viewer) hỗ trợ xem trước cấu trúc bảng, tên cột A-B-C, tìm kiếm ô, toggle mật độ hiển thị (compact), sao chép CSV.
   - Trình chiếu trang scan Split-Screen chuẩn tỉ lệ A4, zoom tương tác, bounding boxes phân màu theo nhãn với khả năng lọc vùng nhận diện, hiển thị metadata (kích thước, DPI, confidence, góc xoay).
   - Đa dạng chế độ xem kết quả: Markdown rendered GFM, Bảng tính Excel, Danh sách phân vùng (Regions Table), JSON raw response.
   - Công cụ tích hợp nhà phát triển: Hộp thoại "Mã tích hợp API" (cURL, Python Requests, Node.js Axios), tính năng "Lưu vào Kho Tri thức" (nạp trực tiếp vào Collection tuyển sinh/quy chế).
3. Đảm bảo 100% tiêu chuẩn chất lượng: 0 lỗi Biome lint, 0 lỗi TypeScript, Vite build thành công, 0 lỗi Ruff, 115/115 unit test backend pass.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật

### 2.1. Backend (`app/modules/ocr/`)
- **`app/modules/ocr/layout_detector.py`**:
  - Tạo mới class `SmartLayoutDetector` sử dụng OpenCV (`cv2`) và `numpy`.
  - Phân tách cấu trúc bảng bằng `cv2.getStructuringElement(cv2.MORPH_RECT, ...)` theo trục ngang và dọc, tìm giao điểm để định vị chính xác vị trí bảng trên trang scan.
  - Nhận diện con dấu, chữ ký mực đỏ cơ quan nhà nước bằng không gian màu HSV (`cv2.inRange` với hai dải Hue 0-10 và 170-180), lọc diện tích contour để phát hiện vùng dấu.
  - Phân vùng văn bản (Heading, Paragraph, Header, Footer) bằng hình thái học dãn/co và chiếu histogram.
  - Cơ chế Non-Maximum Suppression (NMS) loại bỏ các phân vùng chồng lấn không mong muốn.
- **`app/modules/ocr/schemas.py`**:
  - Bổ sung `StudioOCRRegion`: chứa `id`, `type`, `label`, `box_2d` [ymin, xmin, ymax, xmax], tọa độ phần trăm (`top`, `left`, `width`, `height`), `confidence`, `text`.
  - Bổ sung `StudioOCRPageResponse`: chứa metadata trang (`page_number`, `width`, `height`, `image_url`, `dpi`, `rotation`), danh sách `regions`, `markdown_content`, danh sách `excel_sheets` (nếu có).
  - Bổ sung `StudioOCRParseResponse`: hỗ trợ `file_hash`, `filename`, `file_size`, `page_count`, `ocr_method`, `total_characters`, `overall_confidence`, `processing_time_ms`, danh sách các trang `pages`. Cung cấp camelCase aliases để Frontend tiêu thụ mượt mà.
- **`app/modules/ocr/service.py`**:
  - Bổ sung hàm `parse_studio_document(...)`: đọc file PDF/ảnh/Excel, kết xuất ảnh trang scan qua PyMuPDF (hoặc openpyxl cho Excel), gọi `SmartLayoutDetector` phát hiện phân vùng, trích xuất text/markdown, lưu ảnh render tạm thời vào cache.
  - Bổ sung hàm `get_studio_page_image(...)`: trả về FileResponse trực tiếp cho ảnh trang scan đã bóc tách từ `file_hash` và `filename`.
  - Bổ sung hàm `get_sample_document(...)`: tạo tài liệu mẫu tuyển sinh Đề án 2026 đầy đủ phân vùng (Title, Table, Stamp, Paragraphs) kèm bảng điểm chuẩn 5 ngành phục vụ trải nghiệm tức thì.
- **`app/modules/ocr/router.py`**:
  - `POST /ocr/studio/parse`: tiếp nhận tệp tải lên (PDF, PNG, JPG, XLSX), thực hiện bóc tách và trả về `StudioOCRParseResponse`.
  - `GET /ocr/studio/page-image/{file_hash}/{img_filename}`: phục vụ ảnh trang scan.
  - `GET /ocr/studio/sample`: tải tài liệu mẫu.
- **`backend/tests/test_ocr.py`**:
  - Thêm 2 test cases mới: `test_studio_ocr_parse_document_and_page_image` và `test_studio_sample_document`.

### 2.2. Frontend (`frontend/src/`)
- **`src/components/admin/excel-spreadsheet-viewer.tsx`**:
  - Tạo mới component hiển thị bảng tính Excel chuyên nghiệp: thanh tìm kiếm giá trị ô, chuyển đổi đa sheet (tab bar dưới đáy), toggle chế độ Compact/Comfortable, hiển thị tên cột chuẩn Excel (A, B, C... AA, AB...), copy toàn bộ sheet sang CSV, click ô hiển thị địa chỉ ô và giá trị.
  - Tuân thủ 100% Biome accessibility: bọc ô trong semantic `<button type="button">`, phím tắt Enter/Space.
- **`src/pages/scan-studio-page.tsx`**:
  - Giao diện độc lập `/ocr` tích hợp toàn diện:
    - **Header**: Tiêu đề phân hệ, bộ điều hướng trang (Prev, Next, Page jump), zoom tương tác (Fit width, 50% - 200%), toggle hiển thị Bounding boxes, nút Đổi tệp, Tải tài liệu mẫu, Xem mã API, Lưu vào Kho Tri thức.
    - **Canvas A4 Split-Screen (Trái)**: Khung hiển thị trang scan chuẩn tỉ lệ A4, overlay các bounding boxes được phân màu sinh động (Xanh ngọc: Text, Xanh dương: Bảng, Tím: Tiêu đề, Đỏ: Con dấu, Xám: Header/Footer), nhãn nhô lên khi hover, chọn vùng hiển thị chi tiết.
    - **Panel Thông Tin & Kết Quả (Phải)**:
      - 4 Tab nội dung: **Markdown** (ReactMarkdown + remarkGfm), **Bảng tính Excel** (`ExcelSpreadsheetViewer`), **Phân vùng chi tiết** (bảng regions có lọc theo loại), **JSON thô** (cú pháp code block có nút sao chép).
      - Metadata bar: Engine OCR, Thời gian xử lý (ms), Độ tin cậy (%), Số trang, Tổng ký tự, Góc xoay, DPI.
    - **Dialog Xem Mã Tích Hợp API**: Tạo sẵn cURL, Python requests, Node.js axios tương ứng với endpoint `/ocr/studio/parse`.
    - **Dialog Lưu Vào Kho Tri Thức**: Cho phép chọn Bộ sưu tập (`collection_id`) để đẩy tài liệu vừa bóc tách vào hệ thống RAG phục vụ Trợ lý AI.
- **`src/services/api-client.ts`**:
  - Thêm các interface TypeScript: `StudioOCRRegion`, `StudioOCRPage`, `StudioOCRDocument`, `StudioExcelSheet`.
  - Thêm 2 phương thức API: `parseStudioOcr(...)` và `getStudioSampleDocument()`.
- **`src/navigation/config.ts` & `src/App.tsx`**:
  - Bổ sung mục navigation `Scan & OCR Studio` vào nhóm `knowledge_hub` với badge `Studio` (emerald).
  - Đăng ký route `/ocr` trỏ tới `ScanStudioPage`.

---

## 3. Kết Quả Kiểm Thử (Verification)

### 3.1. Frontend
- **`npm run lint`** (Biome):
  ```
  Checked 77 files in 49ms. No fixes applied.
  Exit code: 0 (0 errors, 0 warnings)
  ```
- **`npm run typecheck`** (tsc --noEmit):
  ```
  Exit code: 0 (0 errors)
  ```
- **`npm run build`** (tsc -b && vite build):
  ```
  ✓ 2490 modules transformed.
  dist/index.html                     1.50 kB │ gzip:   0.82 kB
  dist/assets/index-D-_V0uyG.css    108.50 kB │ gzip:  16.97 kB
  dist/assets/index-DHmbWd_M.js   1,296.45 kB │ gzip: 367.28 kB
  ✓ built in 5.66s
  Exit code: 0
  ```

### 3.2. Backend
- **`uv run ruff check .`**:
  ```
  All checks passed!
  Exit code: 0
  ```
- **`uv run --extra dev pytest tests/test_ocr.py -v`**:
  ```
  ====================== 11 passed, 11 warnings in 12.62s =======================
  Exit code: 0
  ```
- **`uv run --extra dev pytest -q`** (Toàn bộ test suite):
  ```
  115 passed, 22 warnings in 27.44s
  Exit code: 0
  ```
