# NHẬT KÝ LÀM VIỆC — PHIÊN #149
**Ngày thực hiện**: 20/09/2026  
**Tiêu đề**: Khắc Phục Lỗi Che Khuất Lề Trang PDF Trong Scan Studio Bằng Cơ Chế Fit-To-Width Đồng Bộ

---

## 1. Bối Cảnh & Vấn Đề

Sau khi nâng cấp sang `react-pdf`, người dùng tải trang và phản hồi kèm ảnh chụp màn hình:
> *"ok được rồi nhưng mà giao diện xem file bị che rồi"*

### Phân tích nguyên nhân:
- Nhìn vào ảnh chụp: Trang PDF A4 nằm ngang ở trang 3 bị cắt mất phần bên trái (mất cột "TT", chữ "Nội dung nhiệm vụ" bị cắt thành "ng nhiệm vụ") và phần bên phải (mất cột "Sản phẩm kết quả").
- **Nguyên nhân gốc rễ**:
  1. `<Page width={effectivePageWidth} />` nhận chiều rộng cứng là `1131px` (do `800 * Math.SQRT2`).
  2. Nhưng cột Canvas bên trái của layout grid (7/12 cols) chỉ rộng khoảng `650px - 700px` trên màn hình người dùng.
  3. `page-wrapper` lại bị giới hạn bởi `maxWidth: 100%` (khiến khung canvas co lại còn 700px).
  4. Đồng thời `page-canvas` có `overflow-hidden` và `flex items-center justify-center`.
  5. **Hậu quả**: Canvas của `react-pdf` vẽ ở kích thước 1131px nhưng bị nhét vào khung 700px bị cắt mất `(1131 - 700) / 2 ≈ 215px` ở mỗi bên lề trái và phải!

---

## 2. Giải Pháp Triệt Để (Synchronized Fit-To-Width)

1. **Đo đạc kích thước thực tế của khung nhìn (`ResizeObserver`)**:
   - Sử dụng `ResizeObserver` trên `containerRef` để liên tục đo đạc chiều rộng khả dụng thực tế của container (`containerWidth = clientWidth - padding`).
2. **Tính toán chiều rộng render đồng bộ (`pageRenderWidth`)**:
   - Ở zoom 100%:
     * Trang nằm ngang: `idealBaseWidth = Math.min(containerWidth, 1200)`.
     * Trang đứng: `idealBaseWidth = Math.min(containerWidth, 800)`.
   - Khi zoom: `pageRenderWidth = Math.round((idealBaseWidth * zoomLevel) / 100)`.
3. **Khóa đồng bộ 100% giữa Canvas và PDF Page**:
   - `page-wrapper`: `style={{ width: `${pageRenderWidth}px` }}` (bỏ `maxWidth: 100%` gây co ép bất đối xứng).
   - `page-canvas`: `style={{ width: `${pageRenderWidth}px`, aspectRatio: `${aspectRatio}` }}`.
   - `<Page width={pageRenderWidth} />`: Nhận chính xác `pageRenderWidth`.
   - Bỏ các lớp `overflow-hidden` cắt cụt lề.
4. **Chống lỗi Flexbox Centering Scroll Inaccessibility**:
   - Thay vì `items-center` trực tiếp trên container cuộn ngoài cùng `overflow-auto` (vốn sẽ đẩy lề trái ra ngoài vùng tọa độ âm khi nội dung lớn hơn container và không thể cuộn tới được), bọc nội dung trong `<div className="w-fit min-w-full flex flex-col items-center">`.
   - Kết quả: Khi nhỏ hơn khung, trang tự động căn giữa tuyệt đẹp; khi lớn hơn khung (hoặc zoom to), lề trái bắt đầu từ 0 và thanh cuộn ngang cho phép cuộn từ mép trái sang mép phải trọn vẹn 100%.

---

## 3. Các Tệp Đã Chỉnh Sửa

| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) | `MODIFY` | Tích hợp `ResizeObserver` đo `containerWidth`, tính `pageRenderWidth` đồng bộ cho `page-wrapper`, `page-canvas` và `<Page width={pageRenderWidth} />`. Áp dụng `w-fit min-w-full` chống scroll inaccessibility. |

---

## 4. Kết Quả Kiểm Thử

- **Frontend**:
  - `npm run lint` $\rightarrow$ **Checked 165 files. No fixes applied. (0 lỗi)**.
  - `npm run typecheck` $\rightarrow$ **0 lỗi**.
  - `npm run build` $\rightarrow$ **Vite v6.4.3 built in 9.61s thành công (0 lỗi)**.
- **Backend**:
  - `uv run ruff check .` $\rightarrow$ **All checks passed! (0 lỗi)**.
