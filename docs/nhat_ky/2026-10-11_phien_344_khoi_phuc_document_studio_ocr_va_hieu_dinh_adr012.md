# Nhật Ký Phiên #344: Khôi Phục Hoàn Toàn Document Studio OCR, Nhận Dạng Khung Bounding Box & Hiệu Đính 2 Chiều ADR-012

**Thời gian thực hiện**: 11/10/2026  
**Người thực hiện**: Antigravity (Senior Full-Stack Architect & Enterprise AI Systems Specialist)  
**Mục tiêu**: Khôi phục trọn vẹn chức năng bóc tách, OCR scan, nhận dạng khung (Bounding boxes) và hiệu đính tài liệu trong luồng Kho tri thức theo kiến trúc ADR-012; tuân thủ nghiêm ngặt 5 điểm review then chốt; xác minh thực tế 100% bằng Playwright Browser Automation và dữ liệu PDF scan 2 trang thật.

---

## 1. Bối Cảnh & Các Điểm Review Then Chốt

Sau khi tái cấu trúc tách biệt Kho tài liệu (Pure Storage) và Kho tri thức (Document Intelligence ADR-012), trải nghiệm bóc tách và đối chiếu khung OCR (`DocumentStudioWorkspace`) cần được nối khớp toàn diện vào runtime mới. Người dùng đã phê duyệt triển khai và yêu cầu đáp ứng tuyệt đối 5 tiêu chuẩn kỹ thuật:

1. **Tách Biệt Confidence Tuyệt Đối**: Không đồng nhất confidence phát hiện vùng (`layout_confidence`) với confidence nhận dạng chữ OCR (`text_confidence`). Nếu OCR không cung cấp text score, ghi nhận rõ ràng ("Không được cung cấp" / `None`), tuyệt đối không gán 0% hoặc lấy layout score thay thế.
2. **Chuẩn Hóa Hệ Tọa Độ Chuẩn Xác**: Tọa độ bounding box phải chuẩn hóa theo hệ phần trăm `[0..100]%` dựa trên kích thước tự nhiên ($W \times H$) thật của ảnh trang do OCR hoặc renderer cung cấp (`dimensions`), tuyệt đối không gán cứng khổ giấy A4 $800 \times 1131$.
3. **Snapshot Độc Lập & Chống Chạy Trùng (Reparse Isolation & Anti-Collision Lock)**: Bóc tách lại (Reparse) bắt buộc đọc từ snapshot nhị phân độc lập của Knowledge domain (`snapshot_storage_path`), hoàn toàn không phụ thuộc vào việc tệp gốc còn trong Kho tài liệu hay không; đồng thời từ chối 409 (`REPARSE_ALREADY_IN_PROGRESS`) nếu nguồn đang có tiến trình bóc tách thực thi.
4. **Kiểm Thử Thực Tế Studio Scan Nhiều Trang**: Kiểm thử với PDF scan 2 trang thật (`e2e341_scan_2pages.pdf`), kiểm tra zoom/resize, cuộn trang liên tục, và cơ chế đối chiếu 2 chiều (Click Bbox trên Canvas $\leftrightarrow$ Highlight Vùng trên Inspector).
5. **Nghiệm Thu Bằng Chứng Thật (Zero-Mock E2E)**: Không dùng mock fallback `/ocr-cache/doc_ts_2026/` hay mock OCR. Xác minh có ảnh chụp màn hình đối soát thực tế.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### A. Backend OCR Adapter & Source Page Normalizer
- **`backend/app/modules/ocr/adapters/paddleocr_adapter.py`**:
  - Trích xuất $W \times H$ ảnh tự nhiên từ `prunedResult`.
  - Phân tách tường minh `layout_confidence` (từ `layout_det_res.boxes.score`) và `text_confidence: None`.
  - Chuẩn hóa tọa độ phần trăm `[0..100]%` vào `normalized_percent`.
- **`backend/app/modules/knowledge/services/source_pages.py`**:
  - `page_manifest` lưu trữ đầy đủ `dimensions`, `blocks`, `has_tables`, bảo đảm tương thích ngược 100% với toàn bộ provenance test suite.
- **`backend/app/modules/knowledge/schemas.py`**:
  - Định nghĩa `StudioBox` (hỗ trợ `layout_confidence: float | None`, `text_confidence: float | None`, `coordinates: dict[str, Any]`), `StudioRegion`, `StudioPageView` (hỗ trợ `dimensions`, `has_tables`), `ReparseSourceRequest`.

### B. Backend Document Studio & Reparse APIs
- **`backend/app/modules/knowledge/services/source_ingestion_service.py`**:
  - `get_source_studio_data(...)`: Truy xuất dữ liệu Studio độc lập từ `KnowledgeSourceRevision.page_manifest`, fallback an toàn `snapshot_metadata.title`, cung cấp `image_url` stream ảnh trang.
  - `get_source_page_image(...)`: Render ảnh JPEG 150 DPI chất lượng cao trực tiếp từ snapshot nhị phân bằng PyMuPDF (`pymupdf`), bảo đảm cô lập hoàn toàn khỏi Kho tài liệu trung tâm.
  - `reparse_source(...)`: Đọc file bytes từ snapshot nhị phân bằng `await storage_service.get(...)`, gọi PaddleOCR-VL thật, kiểm tra chống chạy trùng 409, lưu revision mới an toàn và cập nhật con trỏ `active_source_revision_id`.
- **`backend/app/modules/knowledge/router.py`**:
  - Đăng ký 3 endpoints chuẩn RFC 7807:
    * `GET /collections/{col_id}/sources/{source_id}/studio`
    * `GET /collections/{col_id}/sources/{source_id}/pages/{page_number}/image`
    * `POST /collections/{col_id}/sources/{source_id}/reparse`

### C. Frontend Document Studio Workspace
- **`frontend/src/components/knowledge/ocr/document-studio-workspace.tsx`**:
  - Hỗ trợ gọi song song `knowledgeApi.getSourceStudioView(...)` cho các binding ADR-012 (`bnd_...`).
  - Hỗ trợ lưu nội dung hiệu đính và phê duyệt bản bóc tách trực tiếp vào `knowledgeApi.updateSourceRevisionContent` và `knowledgeApi.reviewSourceRevision`.
- **`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`**:
  - Loại bỏ hoàn toàn mock fallback `/ocr-cache/doc_ts_2026/`.
  - Stream ảnh trang thật qua API `/pages/{page_number}/image`.
  - Vẽ Bbox chuẩn xác theo tọa độ percent động của ảnh thật.
- **`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`**:
  - Thêm tab "Vùng bóc tách" (`regions`) hiển thị thứ tự đọc, nhãn vùng, điểm số phân tách: "Khung nhận diện: X%" và "Nhận dạng chữ (OCR): Không được cung cấp".
  - Hỗ trợ highlight 2 chiều khi click vùng trên danh sách hoặc click khung trên Canvas.
- **`frontend/src/features/knowledge/source-detail-page.tsx`**:
  - Tách biệt rõ ràng trạng thái bóc tách nội dung (`ready`/`review_required`) và trạng thái chỉ mục vector (`active`/`pending`).
  - Bổ sung nút "Bóc tách & Studio OCR" mở Workspace toàn màn hình và modal "Bóc tách lại".

---

## 3. Kết Quả Kiểm Thử Thực Tế (E2E Verification)

1. **Inference & ARQ Worker Run**:
   - Worker chạy PaddleOCR-VL thật trên file PDF scan 2 trang 12MB (`e2e341_scan_2pages.pdf`), trích xuất thành công 6 khối bố cục (3 khối trang 1, 3 khối trang 2 gồm tiêu đề `paragraph_title` và text) trong ~6.5 giây.
2. **Page Image Streaming API**:
   - `GET .../pages/1/image`: 200 OK, `image/jpeg`, 78,283 bytes (1240x1755 px).
   - `GET .../pages/2/image`: 200 OK, `image/jpeg`, 102,346 bytes (1240x1755 px).
3. **Playwright UI Automation Verification**:
   - Đăng nhập quyền Admin qua Dev Access Gate.
   - Điều hướng tới `http://127.0.0.1:3000/knowledge/col_b04b7104008f/sources/bnd_685681798e01`.
   - Mở Document Studio Workspace thành công:
     * Cả 2 trang scan render JPEG sắc nét, đầy đủ 6 Bbox tương ứng.
     * Thao tác Zoom In (100% $\to$ 150%) và Fit Width hoạt động mượt mà.
     * Click Vùng #1 trong Inspector $\to$ Bbox trên Canvas đổi màu highlight.
     * Chuyển tab "Vùng bóc tách" $\to$ Hiển thị tách biệt rõ ràng "Khung nhận diện: 73%" và "Nhận dạng chữ (OCR): Không được cung cấp".
     * Cuộn tới trang 2 $\to$ `IntersectionObserver` tự động cập nhật `currentPage = 2`, danh sách vùng chuyển sang Trang 2 (`paragraph_title: 82%`, text: `93%`, text: `83%`).
   - Kích hoạt "Bóc tách lại" (Reparse) $\to$ Tạo thành công revision `v8 (ready)` từ snapshot độc lập.
   - Bằng chứng ảnh chụp màn hình được lưu trữ tại: `storage/e2e_fixtures/341/studio_e2e_verified.png`.
4. **Final Gate Verification**:
   - `uv run ruff check .`: PASS (0 lint errors).
   - `uv run --extra dev pytest tests/test_source_page_provenance.py tests/test_paddleocr_adapter.py`: 10/10 tests PASSED.
   - `npm run build`: Exit code 0 (0 lỗi TypeScript, 0 lỗi Vite bundle).
