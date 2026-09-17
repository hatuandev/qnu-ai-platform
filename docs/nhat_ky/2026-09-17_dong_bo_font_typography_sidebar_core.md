# Nhật Ký Làm Việc: Đồng Bộ Font Chữ & Typography Sidebar Theo Chuẩn QNU AI Core
**Thời gian**: 2026-09-17 16:40 (UTC+7)
**Mục tiêu**: Điều tra font chữ của `qnu-ai-core` vs `qnu-ai-platform`, đồng bộ font-family (`Inter`, `ui-sans-serif`,...) và các kích thước typography của Sidebar bên Platform cho sắc nét, chuẩn thiết kế tương tự Core.

---

## 1. Kết Quả Điều Tra & So Sánh
- **Core Font Family**:
  - `font-sans`: `"Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
  - Đã nhập Google Fonts Inter (weights 300..700).
- **Core Typography Sidebar**:
  - `Header Subtitle`: `text-xs text-muted-foreground`
  - `Group Label`: `text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/80`
  - `Nav Button`: `h-9 text-sm font-medium gap-2.5 px-2.5 rounded-md`
  - `Nav Badge`: `text-[11px] font-medium`
  - `Footer Status`: `text-xs font-semibold` + `text-[11px] font-mono`

---

## 2. Các Tệp Tin Đã Chỉnh Sửa
1. `frontend/src/styles/globals.css`:
   - Cập nhật `--font-sans` sang chuẩn Inter & system stack của Core.
2. `frontend/src/layouts/app-sidebar.tsx`:
   - Đồng bộ font sizes, tracking, paddings, active pill indicator theo đúng layout và typography của Core.

---

## 3. Kết Quả Kiểm Thử (Verification)
- `npm run lint`: Biome check 77 files, **0 lỗi**.
- `npm run typecheck`: TypeScript `tsc --noEmit`, **0 lỗi**.
- `npm run build`: Vite production build hoàn tất trong **5.74s** thành công.
