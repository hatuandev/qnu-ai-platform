# Nhật ký Phiên 918 — Tối ưu giao diện Chi tiết tài liệu / Studio FE V2

**Thời gian:** 2026-11-10  
**Phạm vi:** `frontendV2/src/routes/knowledge.$sourceId.tsx`, `frontendV2/src/components/knowledge/`, `frontendV2/src/lib/knowledge-studio-helpers.ts`

---

## 1. Mục tiêu và bối cảnh

Hoàn thiện giao diện Studio / Chi tiết tài liệu trong Frontend V2 của QNU AI Platform phục vụ người dùng thông thường:
- Sửa lỗi tràn / cắt giấy và đa tầng padding/border của trình xem Word (DOCX).
- Đưa mặc định xem DOCX về **Vừa chiều ngang (Fit to width)** với `ResizeObserver`, tính toán tỷ lệ scale và bù trừ chiều cao cuộn chính xác, bổ sung thanh công cụ phóng to / thu nhỏ / đặt lại.
- Tinh chỉnh mặt giấy nội dung đã chuẩn bị: font chữ đọc chính 15px, line-height thoáng (1.7), thứ bậc tiêu đề rõ ràng, loại bỏ `select-none` để người dùng sao chép văn bản tự nhiên.
- Ẩn toàn bộ mã kỹ thuật (`ev_...`, `cmp_...`) khỏi văn bản đọc, thay bằng các chip dẫn chứng tuần tự accessible **[1]**, **[2]** có Popover chi tiết (tệp nguồn, vị trí trang/khối, trích đoạn đối chiếu).
- Thu gọn Header: tên tài liệu tự động truncate có Tooltip, hiển thị 1 nút hành động chính duy nhất tương ứng chính xác với trạng thái bản đang xem (`Chuẩn bị nội dung` -> `Dừng xử lý` -> `Duyệt` -> `Phát hành` -> `Sẵn sàng phục vụ`), gom toàn bộ thao tác phụ vào menu `⋯`.
- Hỗ trợ responsive: trên màn hình hẹp (< 1024px), chuyển sang chuyển đổi mượt mà giữa hai tab **Tệp gốc** và **Nội dung đã chuẩn bị**.

---

## 2. Các thay đổi đã thực hiện

1. **`frontendV2/src/components/knowledge/docx-viewer.tsx`**:
   - Tách thành component độc lập chuyên trách kết xuất DOCX qua `docx-preview`.
   - Kết hợp `ResizeObserver` theo dõi chiều rộng thực tế của khung chứa, tự động tính toán `fitScale = (containerWidth - 32) / naturalWidth`.
   - Bố cục biến đổi CSS: thẻ bao ngoài mang kích thước co giãn thực `naturalWidth * scale` và `naturalHeight * scale`, thẻ bên trong áp `transform: scale(scale)` từ gốc `top left`. Đảm bảo thanh cuộn đọc tới tận đáy trang cuối cùng mà không bị cụt hay phát sinh cuộn ngang thừa.
   - CSS Scoped: khử nền xám và padding dày mặc định của `docx-preview`, tạo bóng đổ mờ và viền nhẹ cho từng trang.
   - Thanh công cụ tinh gọn: Zoom Out, tỷ lệ % / nút Vừa trang, Zoom In, Đặt lại và Tải tệp gốc.

2. **`frontendV2/src/components/knowledge/citation-badge.tsx`**:
   - Hiển thị chip số thứ tự tuần tự `[1]`, `[2]`.
   - Tích hợp `Popover` của Radix UI: hiển thị Căn cứ số `[N]`, tệp nguồn, vị trí trang/khối và trích đoạn.
   - Mã kỹ thuật hệ thống chỉ hiển thị ở phần chân của popover dưới dạng chữ nhỏ muted mono.

3. **`frontendV2/src/lib/knowledge-studio-helpers.ts`**:
   - `buildCitationMap`: quét tuần tự các đoạn văn và bảng dữ liệu để gán số thứ tự duy nhất, ổn định và tự động khử trùng lặp trong cùng đoạn.
   - `parseCitationLocation`: trích xuất nhãn thân thiện (ví dụ `ocr_...:ev_p001_b002` thành `Trang 1, khối 2`).
   - `resolveStudioAction`: xác định hành động chính duy nhất (`prepare`, `cancel_prep`, `save_edits`, `approve`, `publish`, `syncing`, `served`) và quyền chỉnh sửa dựa trên trạng thái thực tế của bản biên soạn đang xem.

4. **`frontendV2/src/routes/knowledge.$sourceId.tsx`**:
   - Header tái cấu trúc: Nút quay lại, Tooltip cho tiêu đề dài, Badge trạng thái, 1 nút chính theo trạng thái, nút outline Chỉnh sửa (khi có nháp), Menu `⋯` chứa Tải tệp, Xem Markdown, Lịch sử, và bộ chọn góc nhìn (Chỉ tệp gốc, Song song, Chỉ nội dung).
   - Thanh chuyển đổi di động cho màn hình nhỏ `< lg`: `[ Tệp gốc | Nội dung đã chuẩn bị ]`.
   - Mặt giấy tài liệu liền mạch (`article.bg-card`): `text-[15px] leading-relaxed`, đề mục phân cấp rõ ràng, bảng biểu gọn gàng, vùng cảnh báo dữ kiện cần làm rõ dễ đọc.

5. **`frontendV2/src/lib/knowledge-studio-helpers.test.ts`**:
   - Bộ 3 unit test cho `parseCitationLocation`, `buildCitationMap`, và `resolveStudioAction`. Chạy đạt 100% qua Node 24 native test runner.

---

## 3. Kết quả kiểm chứng

- **Unit tests**: `node --test --experimental-strip-types frontendV2/src/lib/knowledge-studio-helpers.test.ts` -> 3/3 passed (100%).
- **Biome lint**: `npm --prefix frontendV2 run lint` -> Checked 159 files, 0 errors, 0 warnings.
- **Typecheck**: `npm --prefix frontendV2 run typecheck` (`tsc --noEmit`) -> 0 errors.
- **Build**: `npm --prefix frontendV2 run build` (`vite build && tsc --noEmit`) -> Đạt trong 1.93s, 0 errors.

