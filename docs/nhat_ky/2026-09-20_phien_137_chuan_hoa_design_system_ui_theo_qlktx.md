# Nhật Ký Phiên Làm Việc #137 — Chuẩn Hóa Toàn Diện Design System UI Theo Chuẩn QLKTX & Nâng Cấp OCR Studio

- **Thời gian**: 2026-09-20 13:25 (UTC+7)
- **Mục tiêu**: Phân tích và đồng bộ Design System của QNU AI Platform theo dự án chuẩn `D:\DuAnPhanMem\QLKTX\qnu-ktx\src\Web\ClientApp`, giải quyết triệt để các vấn đề lệch pha màu sắc Light/Dark, bố cục co cụm, toolbar che lấp văn bản và bounding boxes đè nhãn trên trang Đối Soát OCR.

---

## 1. Phân Tích & Các Vấn Đề Gốc Rễ Đã Khắc Phục

1. **Lệch pha màu sắc Light/Dark**:
   - Trước đây: Nền canvas OCR bị ép cứng màu đen kịt `#121214` cùng toolbar đen, tạo sự tương phản thô kệch với toàn bộ giao diện sáng (Light mode) của hệ thống.
   - Khắc phục: Dùng `bg-muted/40 dark:bg-[#121214]` làm nền bàn làm việc thích ứng theo theme. Ở Light mode, trang giấy A4 màu trắng tinh đặt trên bàn xám dịu với bóng đổ mềm `shadow-md border border-border/80`.
2. **Khung bao bị co cụm (Sai Layout Variant)**:
   - Trước đây: Route `/knowledge/documents/:documentId/ocr` bị phân vào layout `standard` (bọc trong `max-w-7xl` với padding `p-8`), làm không gian studio 3 cột bị bóp nghẹt giữa 2 dải lề trắng.
   - Khắc phục: Thêm `pathname.includes("/ocr")` vào `full-bleed` trong `admin-shell.tsx`, giúp trang mở rộng 100% không gian màn hình `h-[calc(100vh-3.5rem)]`.
3. **Thanh Toolbar Lơ Lửng (Floating Toolbar)**:
   - Trước đây: Đặt `sticky top-3` ở đầu canvas, đè trực tiếp lên tiêu đề trang tài liệu và dùng màu đen cứng `bg-zinc-900`.
   - Khắc phục: Đổi thành `absolute bottom-4 left-1/2 -translate-x-1/2` ở đáy canvas, áp dụng semantic tokens `bg-background/95 dark:bg-card/95 border border-border shadow-lg backdrop-blur-md` và các nút compact `size-6`, icon `size-3.5`.
4. **Bounding Boxes & Nhãn Tag Chèn Lấn**:
   - Trước đây: Viền dày 1.5px, màu nền hiển thị thường trực, nhãn tag `-top-3.5` chèn lấn lẫn nhau và che lấp văn bản.
   - Khắc phục: Viền thanh mảnh 1px, nền trong suốt 100% khi chưa tương tác, nhãn tag ẩn mặc định (`opacity-0`) và chỉ hiện lên mượt mà (`opacity-100`) khi hover hoặc khi box được chọn.
5. **Đồng bộ Typography & Admin Primitives**:
   - Bổ sung bộ biến Typography Tokens và Motion Tokens vào `tokens.css`.
   - Khai báo `@layer utilities` các lớp `.type-page-title`, `.type-control`, `.type-caption`,... trong `globals.css`.
   - Tạo mới `components/admin/page-header.tsx` chuẩn QLKTX.
   - Tinh chỉnh `Button` và `Badge` sang chuẩn QLKTX (`type-control`, control height 36px/32px, badge `/12` tint).
   - Khắc phục lỗi double newline spacing trong `ReactMarkdown` của `ocr-inspector.tsx`.

---

## 2. Danh Sách Tệp Đã Chỉnh Sửa & Tạo Mới

| STT | Tệp tin | Hành động | Mô tả kỹ thuật |
| :--- | :--- | :--- | :--- |
| 1 | [`frontend/src/styles/tokens.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/tokens.css) | Modify | Bổ sung typography tokens (`--font-size-*`) và motion tokens (`--motion-*`) chuẩn QLKTX |
| 2 | [`frontend/src/styles/globals.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/globals.css) | Modify | Khai báo `@layer utilities` các lớp kiểu chữ `.type-*` và gán `font-size: var(--font-size-body)` cho body |
| 3 | [`frontend/src/components/admin/page-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/page-header.tsx) | New | Tạo component `PageHeader` chuẩn mực từ QLKTX với eyebrow, title, description, actions |
| 4 | [`frontend/src/components/ui/button.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/button.tsx) | Modify | Áp dụng `type-control`, kích thước chuẩn `h-[var(--control-height)]` và `sm: h-[var(--control-height-sm)]` |
| 5 | [`frontend/src/components/ui/badge.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/badge.tsx) | Modify | Chuyển sang style `/12` tint thanh lịch của QLKTX |
| 6 | [`frontend/src/layouts/admin-shell.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/admin-shell.tsx) | Modify | Thêm `pathname.includes("/ocr")` vào full-bleed layout |
| 7 | [`frontend/src/components/knowledge/ocr/ocr-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-canvas.tsx) | Modify | Đổi desk bg thành `bg-muted/40 dark:bg-[#121214]`, bounding box 1px trong suốt, nhãn tag ẩn/hiện theo hover |
| 8 | [`frontend/src/components/knowledge/ocr/ocr-toolbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-toolbar.tsx) | Modify | Chuyển xuống `bottom-4`, đổi sang semantic tokens `bg-background/95 dark:bg-card/95`, compact controls |
| 9 | [`frontend/src/components/knowledge/ocr/ocr-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/ocr/ocr-inspector.tsx) | Modify | Chuẩn hóa tabs `h-8`, bỏ `whitespace-pre-wrap` trên `<p>` tránh lỗi double line break |
| 10 | [`frontend/src/pages/scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) | Modify | Cập nhật top bar, file badge, KPI meta tags theo chuẩn design system |
| 11 | [`backend/tests/conftest.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/conftest.py) | Modify | Thêm `# noqa: E402` cho import `get_settings` sau khi gán biến môi trường |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Frontend**:
   - `npm run lint`: 165 files checked, **0 lỗi**.
   - `npm run typecheck`: `tsc --noEmit`, **0 lỗi**.
   - `npm run build`: Vite build thành công: **2575 modules transformed, ✓ built in 6.94s**.
2. **Backend**:
   - `uv run ruff check .`: **All checks passed (0 lỗi)**.
   - `uv run --extra dev pytest tests/test_knowledge.py -v`: **31/31 passed (100%) in 81.30s**.
