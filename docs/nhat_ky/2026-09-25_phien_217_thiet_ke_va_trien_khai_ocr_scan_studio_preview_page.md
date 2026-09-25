# Nhật Ký Phiên 217 — Thiết Kế & Triển Khai Trang OCR Scan Studio Preview (Frontend2)

**Thời gian**: 2026-09-25 09:20 (Giờ địa phương)  
**Tác vụ**: Rà soát bản cập nhật mới nhất từ Git (`git pull`) và thiết kế, triển khai giao diện UI/UX hoàn chỉnh cho Trang Thẩm Định Nhận Dạng Scan (OCR Scan Studio Preview Page) trên `frontend2`.

---

## 1. Bối Cảnh & Yêu Cầu

1. **Rà soát cập nhật mã nguồn (`git pull`)**:
   - Nhận diện các thay đổi được cập nhật từ nhánh `origin/main`:
     - Bổ sung `ReactFlowProvider` bao ngoài `ReactFlow` trong [`dag-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/ai/dag-canvas.tsx) để bảo đảm Context hợp lệ.
     - Cập nhật workflow tab và service [`workflows-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/services/workflows-api.ts).
     - Đóng gói kiểm thử thành công 100% bằng Vite build.
2. **Yêu cầu UI/UX Trang Thẩm Định Nhận Dạng Scan (Scan Studio Preview)**:
   - Khi người dùng nạp dữ liệu (tải tệp lên) hoặc xem tài liệu scan, hệ thống phải có một trang Studio trực quan để xem trước (preview) kết quả nhận dạng bóc tách scan (OCR & Layout Recognition).
   - Nghiên cứu kiến trúc từ `frontend/` cũ (`scan-studio-page.tsx`, `document-verification-studio-page.tsx`, `document-studio-workspace.tsx`) và đưa lên `frontend2` theo đúng chuẩn thiết kế hiện đại (Radix UI, semantic OKLCH tokens, Academic Teal, zero emoji, responsive đa thiết bị).

---

## 2. Các Thành Phần Đã Triển Khai

1. **Trang Studio Thẩm Định Scan Hoàn Chỉnh ([`scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/scan-studio-page.tsx))**:
   - **Chế độ Đối soát & Thẩm định tài liệu thực tế (`isDocumentVerificationMode`)**:
     - Tự động kích hoạt khi có `documentId` / `docId` (từ bảng tài liệu hoặc sau khi upload).
     - Thanh Header tích hợp: Nút quay lại kho `←`, tiêu đề văn bản, huy hiệu trạng thái index, dung lượng, số trang, nút tải xuống tệp Markdown bóc tách.
     - Nút phê duyệt 1-Click: **"Xác nhận đối soát & Phê duyệt"** (nạp Vector DB), hoặc **"Cập nhật & Lập chỉ mục"** khi người dùng có chỉnh sửa tay nội dung.
   - **Chế độ Phòng Lab OCR Độc Lập (OCR Studio Lab)**:
     - Kích hoạt khi truy cập từ thanh Sidebar (`/ocr-lab`).
     - Cho phép kéo thả / tải tệp PDF hoặc ảnh scan bất kỳ để bóc tách thử nghiệm với nhiều bộ máy (`PyMuPDF`, `Docling`, `EasyOCR`, `Gemini Vision`, `Mistral OCR`).
     - Hỗ trợ tải dữ liệu mẫu QNU 14 trang để chạy thử nghiệm tức thì.
     - Modal **"Lưu Vào Kho Tri Thức"** cho phép chuyển kết quả bóc tách vào bất kỳ bộ sưu tập tri thức nào.
   - **Bố cục Split-Pane Linh Hoạt**:
     - *Cột trái (7 cols)*: `OcrToolbar` + `OcrCanvas` (hiển thị trang PDF với Bounding Boxes phân biệt màu sắc: Tables vàng cam, Headers xám xanh, Text tím, Signatures đỏ hồng, Stamps đỏ; công cụ phóng to, thu nhỏ, chế độ xem liên tục/từng trang, lọc vùng).
     - *Cột phải (5 cols)*: `OcrInspector` (Markdown preview, Raw text, Bảng tính Excel viewer, JSON cấu trúc, cho phép hiệu đính Markdown trực tiếp).

2. **Định Tuyến TanStack Router ([`ocr-lab.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/ocr-lab.tsx))**:
   - Tạo route `/ocr-lab` hỗ trợ search params `docId`, `documentId`, `collectionId`.
   - Kết nối trực tiếp với mục **"OCR Studio Lab"** trên AppSidebar của `frontend2`.

3. **Tích Hợp Luồng Nạp Tệp Kho Tri Thức ([`document-upload-dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/knowledge/dialogs/document-upload-dialog.tsx) & [`collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/collection-detail-page.tsx))**:
   - Tùy chọn bật/tắt: *"Mở Studio Thẩm định ngay sau khi bóc tách"* giúp người dùng được chuyển hướng trực tiếp vào Studio xem trước kết quả nhận dạng ngay khi quá trình tải tệp hoàn tất.
   - Nút hành động `Scan` trên từng hàng tài liệu trong danh sách tài liệu mở ngay Studio thẩm định.

---

## 3. Kiểm Thử & Nghiệm Thu

- **Vite Production Build**: `npm run build` kết thúc thành công với mã thoát `0` (built in 1.75s).
- **Phân tách Bundle**:
  - `dist/assets/ocr-lab-GnLJaIkP.js`: 16.83 kB.
  - `dist/assets/ocr-FLTmqeKL.js`: 42.70 kB.
- Đảm bảo 0 lỗi TypeScript, 0 cảnh báo linter.
