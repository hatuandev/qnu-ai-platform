# NHẬT KÝ LÀM VIỆC — ĐỒNG BỘ TOÀN DIỆN UI/UX KHO TRI THỨC & BÓC TÁCH TÀI LIỆU TỪ QNU-AI-CORE SANG QNU-AI-PLATFORM

- **Ngày thực hiện**: 2026-09-17
- **Thời gian**: 08:00 - 08:30 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Khắc phục trải nghiệm người dùng chưa tối ưu của giao diện Kho tri thức cũ bằng cách áp dụng toàn bộ chuẩn thiết kế mở, master-detail phân cấp sâu và Studio bóc tách split-pane từ `qnu-ai-core`.

---

## 1. Bối Cảnh & Phân Tích Hiện Trạng

Sau khi tiếp nhận phản hồi từ người dùng cùng 7 ảnh chụp màn hình từ `qnu-ai-core`, chúng tôi nhận diện rõ các điểm bất cập của giao diện cũ trên `qnu-ai-platform`:
1. **Lỗi Monolithic Tabbed View**: Gộp danh sách, form nạp tài liệu và xem chi tiết vào các thẻ tabs hoặc dialog bật lên chật hẹp, khiến không gian hiển thị bị bó hẹp và người dùng khó bookmark/F5 đúng đối tượng.
2. **Thiếu Không Gian Bóc Tách Trực Quan**: Khi tài liệu scan hoặc văn bản pháp lý phức tạp được nạp vào hệ thống, người dùng không có công cụ đối soát xem OCR đã nhận diện chuẩn chưa, các bảng biểu TableFormer được chia cột ra sao, và dấu ký nằm ở vùng nào.
3. **Thiếu Khả Năng "Sửa Tay" (Human-in-the-loop)**: Không có cách nào cho cán bộ biên tập chỉnh sửa nhanh các lỗi gõ hay format Markdown trước khi commit dữ liệu nạp vào Vector DB.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện

### 2.1. DTOs & API Client Service Layer
- File: [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts)
- Bổ sung cấu trúc dữ liệu:
  - `IngestionTask`: Thông tin tác vụ Celery Worker, tiến trình 0-100%, trạng thái, nhật ký terminal.
  - `DocumentBoundingBox`: Tọa độ vùng bao `[x, y, w, h]`, nhãn phân loại (`text`, `table`, `stamp`), độ tin cậy OCR.
  - `DocumentRegion`: Phân cấp vùng bố cục cho tài liệu scan (`title`, `section_header`, `paragraph`, `table`, `stamp`) kèm thứ tự đọc `reading_order`.
  - `DocumentVerificationData`: Mô hình dữ liệu toàn diện cho Studio đối soát gồm nhiều trang tài liệu.
- Cập nhật 5 collections chuẩn QNU (Tuyển sinh, Mẫu văn bản, Quy chế, Thư viện, Đề thi), 6 tác vụ hàng đợi nền và bộ dữ liệu bóc tách mẫu tài liệu tuyển sinh 14 trang.

### 2.2. Visualizer Components
- **`DocumentBoundingVisualizer`** ([`frontend/src/components/admin/document-bounding-visualizer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/document-bounding-visualizer.tsx)):
  - Khung Canvas tái hiện trung thực trang tài liệu gốc với các hộp bao viền nét đứt/liền có màu sắc phân biệt (`text` tím pastel, `table` cam oklch, `stamp` đỏ tươi con dấu & chữ ký).
  - Thanh công cụ điều khiển zoom slider từ 50% đến 200%, các nút filter pills bật/tắt hiển thị từng loại vùng bao, và bộ lật trang đồng bộ `< Trang X / Y >`.
- **`RegionsInspector`** ([`frontend/src/components/admin/regions-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/regions-inspector.tsx)):
  - Cây phân đoạn bố cục chuyên dụng cho tài liệu scan, hiển thị huy hiệu thứ tự đọc `#1, #2...`, loại phân đoạn và chỉ số tin cậy OCR (`98%, 99%`), cho phép cán bộ kiểm tra từng đoạn văn bản đã trích xuất.

### 2.3. Cấu Trúc Các Màn Hình Mới
- **`DocumentIngestPage`** ([`frontend/src/pages/document-ingest-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-ingest-page.tsx)):
  - Giao diện form nạp căn giữa thanh lịch: Vùng kéo thả tệp tin, chọn bộ máy OCR (PyMuPDF Fast, Docling TableFormer, EasyOCR), cấu hình mức độ ưu tiên pháp lý (10/10) và cơ chế chunking thông minh.
- **`DocumentVerificationStudioPage`** ([`frontend/src/pages/document-verification-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-verification-studio-page.tsx)):
  - Studio toàn màn hình split-pane 50-50 với Topbar chuẩn desktop, thanh thống kê (`14 Trang • 21.870 ký tự • ~37 Chunks`), 3 tab chuyển đổi (Markdown đối soát, Raw OCR, Bố cục & Khối cho bản scan), chế độ "Sửa tay" in-place với textarea, và nút xác nhận nạp trực tiếp vào Vector DB.
- **`CollectionDetailPage`** ([`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx)):
  - Tái cấu trúc thành Dedicated Detail View với 3 Sub-tabs (Danh mục tài liệu, Hàng đợi Celery Worker, Playground), tích hợp bộ lọc đa tiêu chí và subview switcher mượt mà.
- **`KnowledgePage`** ([`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx)):
  - Tái cấu trúc Master View với thanh metric tổng hợp `5 Kho • 7 Văn bản • 76 Chunks`, pill sub-tabs (`Kho Tri thức` & `Tác vụ Nền & Bóc tách`), lưới Card 3 cột tỉ lệ vàng và ô card nét đứt `+ Khởi tạo Kho Mới`.

---

## 3. Kết Quả Kiểm Thử Toàn Diện

1. **Bộ kiểm thử Playwright E2E Suite 09** (`tests/e2e/09_knowledge_ingestion_studio.spec.ts`):
   - `TC-INGEST-01`: Passed (3.3s) — Kiểm thử Master View, Metric Bar, Card Grid và Tab Tác vụ Nền Celery.
   - `TC-INGEST-02`: Passed (2.6s) — Kiểm thử Dedicated Detail View, 3 Sub-tabs và Form Nạp Tài Liệu Chuyên Biệt.
   - `TC-INGEST-03`: Passed (3.7s) — Kiểm thử Full-Screen Split-Pane Studio, Bounding Boxes, Lật trang, Regions Scan Inspector, Sửa tay Markdown và Commit nạp Vector DB.
   - **Kết quả chung**: 3/3 tests passed (13.0s).
2. **Kiểm Tra Chuẩn Clean Code (Rule 8 AGENTS.md)**:
   - `npm run lint`: Checked 72 files in 212ms. **0 errors, 0 warnings**.
   - `npm run typecheck`: **0 errors**.
   - `npm run build`: Built thành công trong **9.83s** (`dist/assets/index-D45mBCdp.js: 1,210.32 kB`).
