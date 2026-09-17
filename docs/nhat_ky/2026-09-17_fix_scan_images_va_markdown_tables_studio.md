# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Khắc Phục Triệt Để Hiển Thị Ảnh Scan Thật & Render Markdown Bảng Biểu Chuẩn QNU-AI-Core

### 1. Bối cảnh & Vấn đề Phát hiện
Người dùng phản ánh 2 vấn đề nghiêm trọng trên màn hình Studio Bóc tách & Đối soát (`/knowledge/collections/:id/verify/:docId`):
1. **"Scan chưa giống với qnu-ai-core"**: Cột trái trước đây hiển thị một khung HTML giả lập văn bản thô thay vì ảnh scan thực tế của tài liệu gốc. Các trang từ 3 đến 14 trước đó bị trắng hoàn toàn.
2. **"Việc bóc tách dữ liệu thành dạng md có đúng với bên core không vậy sao tôi thấy trên UI khác quá"**: Cột phải in text thô bằng `<div className="whitespace-pre-wrap">{editableMarkdown}</div>`, dẫn đến toàn bộ bảng biểu tuyển sinh 53 ngành, mã ngành, chỉ tiêu, điểm chuẩn không được render thành bảng HTML mà chỉ là các ký tự gạch đứng `| STT | Mã xét tuyển |`.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Sao chép và đồng bộ 14 trang ảnh scan thực tế 300 DPI**:
   - Trích xuất toàn bộ 14 tệp ảnh scan trang thực tế (`page_1.jpg` đến `page_14.jpg`) từ kho cache của `qnu-ai-core` (`services/studio-ui/public/ocr-cache/ccbf29700d/`) sang thư mục tĩnh [`frontend/public/ocr-cache/doc_ts_2026/`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/public/ocr-cache/doc_ts_2026/).
2. **Tách dữ liệu bóc tách độc lập (Single Responsibility Principle)**:
   - Tạo tệp [`frontend/src/services/verification-data.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/verification-data.ts) (1,393 dòng, 69KB) chứa toàn bộ dữ liệu bóc tách, Bounding Boxes chuẩn OpenCV và Layout Regions của 14 trang scan Đề án tuyển sinh 2026.
   - Bổ sung trường `image_url` cho từng trang trong DTO [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts) và loại bỏ mock data inline thừa.
3. **Nâng cấp Component Visualizer ([`frontend/src/components/admin/document-bounding-visualizer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/document-bounding-visualizer.tsx))**:
   - Thay thế toàn bộ khung HTML giả lập cũ bằng thẻ `<img src={currentImageSrc} alt="Trang scan N" ... />` hiển thị trực tiếp ảnh scan 300 DPI thực tế.
   - Sửa lỗi so sánh kiểu `box.type === "text" || box.type === "header"` chuẩn TypeScript.
4. **Tích hợp `ReactMarkdown` + `remarkGfm` ([`frontend/src/pages/document-verification-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-verification-studio-page.tsx))**:
   - Render Markdown bằng `ReactMarkdown` kết hợp `remarkGfm` với custom components:
     - `table`: Khung cuộn ngang, viền phân cách, border shadow.
     - `th`: Nền xám nhạt (`bg-muted/50`), chữ đậm, căn lề trên.
     - `td`: Viền bao quanh, khoảng cách thoáng đãng, hỗ trợ dòng xuống `<br />`.
     - `tr`: Hiệu ứng hover và alternating row background.
     - `blockquote`: Viền Academic Teal trích dẫn văn bản chỉ đạo.
   - Cải tiến chế độ **"Sửa tay" (Human-in-the-loop)**: Bổ sung nút **"Xem trước" (Preview)** bên cạnh ô textarea cho phép cán bộ đối soát kết quả render trước khi nạp vào Vector DB.
5. **Backend Clean Code ([`backend/app/main.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py))**:
   - Dời đoạn mã dọn dẹp biến môi trường Windows `no_proxy` xuống sau toàn bộ module imports chuẩn để loại bỏ lỗi PEP 8 E402.

### 3. Kết Quả Kiểm Thử (Verification)
1. **Backend Linter**:
   ```bash
   uv run ruff check .  # All checks passed! (0 lỗi)
   ```
2. **Frontend Linter & Typecheck**:
   ```bash
   npm run lint        # Biome check src: 0 lỗi, 0 cảnh báo
   npm run typecheck   # tsc --noEmit: 0 lỗi
   npm run build       # Vite build thành công (11.13s)
   ```
3. **Playwright E2E Suite 09**:
   ```bash
   npx playwright test tests/e2e/09_knowledge_ingestion_studio.spec.ts --project="Google Chrome"
   # Running 3 tests using 1 worker
   # ok 1 TC-INGEST-01: Verifies Knowledge Master View with 3-column card grid (2.5s)
   # ok 2 TC-INGEST-02: Verifies Dedicated Detail View with 3 sub-tabs (2.7s)
   # ok 3 TC-INGEST-03: Full-Screen Split-Pane Studio with Bounding Boxes (12.1s)
   # 3 passed (18.6s)
   ```
