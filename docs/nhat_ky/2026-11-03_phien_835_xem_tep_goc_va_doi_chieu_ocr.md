# Phiên 835 — Chế độ Xem tệp gốc (`docx-preview` & `react-pdf`) và làm mới bố cục đối chiếu 2 khung V1

Triển khai chế độ **Xem tệp gốc** ngay trong khung bên trái cùng với **Đối chiếu OCR** trên màn hình chi tiết tài liệu (`SourceDetailPage` → `OcrComparisonView` và `OcrTabContainer`), đồng thời hoàn thiện giao diện đối chiếu 2 khung kiểu Mistral OCR Playground.

## 1. Thay đổi chính

- **Tải tệp gốc có phân quyền & hủy kết quả cũ**:
  - Mở rộng `downloadRevisionContent` trong `frontendV1/src/features/knowledge/requests.ts` nhận `V1RequestOptions` (`signal`) qua endpoint `GET /platform/v1alpha1/workspaces/{w}/collections/{c}/sources/{s}/revisions/{r}/content` (được kiểm tra quyền `resolve_workspace_access` với `READ_ROLES` ở backend).
  - Bổ sung hook `useRevisionContentBlob` và nâng cấp `usePageImageBlobUrl`, `useRenderedPdfBlobUrl`, `usePageRawText` trong `frontendV1/src/features/knowledge/ocr-queries.ts` để tự động `abort()` request cũ, xóa ngay dữ liệu cũ khi đổi tài liệu/revision/lượt bóc tách và thu hồi `URL.revokeObjectURL`.
- **Viewer tệp gốc theo định dạng (`frontendV1/src/features/knowledge/original-file-preview.tsx`)**:
  - **DOCX (`DocxOriginalViewer`)**: Nạp lười (`import("docx-preview")`) chỉ khi mở chế độ `Xem tệp gốc`, gọi `renderAsync()` với `renderAltChunks: false`, `useBase64URL: true`, cô lập CSS trong phạm vi `.qnu-docx-preview-scope` và lọc hậu kiểm DOM (`sanitizeDocxPreviewContainer`) để chặn mọi URL ngoài (`http://`, `https://`, `//`) cũng như thẻ thực thi (`script`, `iframe`, `object`, `embed`). Hoạt động ngay cả khi tài liệu chưa bóc tách (`unprocessed`) hoặc bóc tách lỗi (`failed`), không gọi Gotenberg hay sinh PDF. Dùng vùng cuộn độc lập (`data-testid="docx-original-scroll-container"`) kèm chú thích giới hạn ngắt trang trình duyệt (`data-testid="docx-original-limitation-note"`), không dùng số trang hoặc `bbox` OCR trên bản xem Word.
  - **PDF (`PdfOriginalViewer`)**: Nạp lười `react-pdf` cùng CSS `TextLayer.css` / `AnnotationLayer.css`. Đặt tệp worker tĩnh `/pdf.worker.min.mjs` trực tiếp trong `public/` (được Vite dev server phục vụ MIME `text/javascript` chuẩn, không bị Vite SPA HTML fallback trả về thẻ `<!doctype html>` gây lỗi `SyntaxError: Unexpected token '<'`). Nhận trực tiếp cả `blob` và `blobUrl` từ `useRevisionContentBlob`, truyền `file={blobUrl ?? blob}` để dựng tài liệu mượt mà. Hỗ trợ chọn/sao chép lớp chữ nhúng (`renderTextLayer={true}`) cho PDF văn bản gốc và hiển thị canvas trang cho PDF scan, dùng chung thanh công cụ nhảy trang, tổng số trang, thu phóng, vừa chiều ngang và trọn trang.
- **Phân biệt `Đối chiếu OCR` và `Xem tệp gốc` & Bố cục 2 khung (`ocr-comparison-view.tsx`, `source-detail-page.tsx`, `ocr-tab-container.tsx`)**:
  - Thêm bộ chuyển chế độ `Đối chiếu OCR` | `Xem tệp gốc` trên thanh công cụ khung trái. Mặc định mở `Đối chiếu OCR` khi đã có kết quả bóc tách (`completed`), tự mở `Xem tệp gốc` khi tài liệu chưa bóc tách (`!activeRun`), và cho phép bấm mở `Xem tệp gốc` khi lượt bóc tách thất bại (`failed`).
  - Khi người dùng bấm `Đối chiếu trên trang` / chọn đoạn có `bbox` từ khung văn bản lúc đang ở `Xem tệp gốc`, giao diện tự động chuyển khung trái về `Đối chiếu OCR`, nhảy tới đúng trang, vẽ khung `bbox` trên bề mặt ảnh thực và cuộn vào tầm nhìn.
  - Đồng bộ trạng thái tỷ lệ chia khung `leftPanePct` giữa vách kéo `<Separator>` (hỗ trợ bàn phím `ArrowLeft`, `ArrowRight`, `Home`, `End`, `Enter`) và các nút chế độ `50:50`, `Rộng ảnh`, `Rộng chữ`, giữ nguyên trang/đoạn đang chọn và bản nháp khi chuyển tab trên màn hình hẹp.

## 2. Kiểm chứng

- `npx @biomejs/biome check` trên 9 file sửa/thêm mới: **PASS (9/9 files, 0 lỗi)**.
- `npx vitest run` trên 10 bộ test OCR (`tests/ocr-original-preview.test.tsx`, `tests/ocr-review-ux-806.test.tsx`, `tests/knowledge-ocr-errors-708.test.tsx`, `tests/knowledge-ocr-polling-708.test.tsx`, `tests/ocr-context-review-801.test.tsx`, `tests/ocr-draft-674.test.tsx`, `tests/ocr-save-cache-809.test.tsx`, `tests/regression-677-ocr-conflict-ui.test.tsx`, `tests/scan-ocr-assessment-797.test.ts`, `tests/v1-ocr.test.ts`): **10/10 suites PASS (59/59 tests PASS)**.
- `npm run typecheck` và `npm run build` trong `frontendV1`: **PASS** (sinh chunk riêng cho `docx-preview`, `react-pdf` và `pdf.worker.min.mjs`).

