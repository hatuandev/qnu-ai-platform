# NHẬT KÝ LÀM VIỆC: CHUYỂN CẤU HÌNH MÔ HÌNH KHO TRI THỨC TỪ MODAL SANG TAB CHUYÊN BIỆT (FULL-WIDTH)

- **Thời gian**: 2026-10-06 09:48:00
- **Phiên làm việc**: Phiên 272
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xóa bỏ hoàn toàn việc nhồi nhét cấu hình mô hình (Vector Embedding, Vision OCR) trong Dialog/Modal hẹp, nâng cấp thành Tab thứ 4 chuyên trách (`Mô hình & Cấu hình`) ngay trên trang chi tiết Kho Tri Thức (`/knowledge/:id`), tận dụng toàn bộ chiều rộng màn hình thoáng đãng, chuẩn Master-Detail Deep Routing Pattern.

---

## 1. Bối Cảnh & Động Lực (Context & Motivation)

- **Vấn đề**: Khi bấm nút "Sửa" hoặc cấu hình Kho tri thức, trước đó hệ thống mở một Modal/Dialog (`CollectionConfigDialog`) rộng 576px. Với nhiều thông số cấu hình quan trọng (chọn 4 mô hình Embedding, chọn Primary/Fallback OCR, giải thích Vector Invariance), modal bị co hẹp, cuộn dài và gây cảm giác tù túng, bí bách cho người dùng.
- **Giải pháp**: 
  - Triệt tiêu hoàn toàn Modal cấu hình kho.
  - Bổ sung Tab thứ 4 chính thức: `Mô hình & Cấu hình` (`value="models"`) trên `TabsList` của trang chi tiết Kho tri thức (`/knowledge/:id`).
  - Nút "Cấu hình" trên header hoặc nút "Sửa" trên danh sách kho tri thức (`/knowledge`) kích hoạt chuyển hướng hoặc chuyển tab trực tiếp sang tab `models`.

---

## 2. Chi Tiết Triển Khai Kỹ Thuật

### A. Component Tab Chuyên Trách (`CollectionModelsTab`)
Tạo mới [`frontend2/src/components/knowledge/tabs/collection-models-tab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/tabs/collection-models-tab.tsx):
1. **Header Toolbar**:
   - Tiêu đề "Cấu Hình Kho & Ràng Buộc Mô Hình AI" (ModelOps Binding).
   - Nút hành động: `Khôi phục` (RotateCcw) và `Lưu thay đổi` (Save, loading spinner).
2. **Bố Cục Lưới Bento 2 Cột (Grid 12 Cột Thoáng Đãng)**:
   - **Cột Trái (5/12) — Định Danh & Phạm Vi Tri Thức**:
     - Tên kho (Input), Mã hệ thống (Read-only Badge), Mô tả chi tiết (Textarea 4 dòng), Thống kê số tệp tài liệu và số chunks đã lập chỉ mục.
   - **Cột Phải (7/12) — Mô Hình Vector Embedding (Toán Học Không Gian)**:
     - Banner cảnh báo **Vector Invariance Rule**: Tự động hiển thị Alert hổ phách khi `document_count > 0` giải thích không gian vector toán học Qdrant đang bị cố định.
     - Lưới 4 Cards trực quan lựa chọn mô hình: BGE-M3 1024D (On-Premise RTX 5090 - Khuyến nghị), Cloudflare BGE-M3, OpenAI Small 1536D, OpenAI Large 3072D.
3. **Hàng Toàn Chiều Rộng (Full-Width) — Mô Hình Thị Giác Vision OCR**:
   - Banner Switch: "Kích hoạt OCR Rescue khi PDF quét/ảnh".
   - 2 Cột lựa chọn:
     - **Primary Model**: `Qwen3-VL 8B Instruct (RTX 5090 On-Premise)` - Khuyến nghị, Google Gemini 3.1 Flash Lite, Gemini 2.5 Flash, GPT-4o-mini Vision, Mistral OCR.
     - **Fallback Model**: Google Gemini 3.1 Flash Lite, Gemini 2.5 Flash,...
4. **Bottom Sticky Save Bar**:
   - Thanh lưu thay đổi ở cuối trang giúp thao tác tiện lợi.

### B. Nâng Cấp Trang Chi Tiết Kho Tri Thức (`collection-detail-page.tsx`)
1. Cập nhật `CollectionDetailTab`:
   `export type CollectionDetailTab = "documents" | "facts" | "tasks" | "models";`
2. Thêm `initialTab?: CollectionDetailTab` vào props và route search params `/knowledge/:id?tab=models`.
3. Đưa `CollectionModelsTab` vào `<TabsContent value="models">`.
4. Khi bấm nút "Cấu hình" trên Header: tự động `setActiveTab("models")` thay vì mở dialog.
5. Gỡ bỏ hoàn toàn `CollectionConfigDialog` modal khỏi trang chi tiết.

### C. Đồng Bộ Trang Danh Sách Kho Tri Thức (`knowledge-page.tsx`)
- Khi người dùng click nút "Sửa" hoặc "Cấu hình" của một kho tri thức:
  Tự động điều hướng SPA sang:
  `navigate({ to: "/knowledge/$collectionId", params: { collectionId: col.id }, search: { tab: "models" } })`.
- Gỡ bỏ hoàn toàn modal `CollectionConfigDialog` khỏi trang danh sách.

---

## 3. Kết Quả Kiểm Thử (Verification)

- **Frontend2 Build**: Chạy `npm run build` (`vite build && tsc --noEmit`):
  - **Kết quả**: `✓ built in 2.98s` — **Exit Code 0, 0 lỗi TypeScript, 0 lỗi cú pháp**.
- **UX/UI**: Giao diện rộng rãi, thoáng đãng, người dùng có không gian trực quan lớn để xem và cấu hình đầy đủ tham số mô hình AI mà không bị gò bó trong modal.
