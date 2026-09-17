# Nhật Ký Làm Việc: Rollback Font Chữ & Kích Thước Typography Sidebar Về Ban Đầu
**Thời gian**: 2026-09-17 16:48 (UTC+7)
**Mục tiêu**: Phục hồi (rollback) lại toàn bộ cấu hình font-family và typography của thanh Sidebar bên `qnu-ai-platform` về trạng thái ban đầu theo yêu cầu của người dùng nhằm giữ layout quen thuộc và ổn định.

---

## 1. Nội Dung Thực Hiện
- Khôi phục `frontend/src/styles/globals.css`:
  - Trả `--font-sans` về nguyên trạng: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;`.
- Khôi phục `frontend/src/layouts/app-sidebar.tsx`:
  - Phục hồi font size nav buttons về `text-xs py-2 gap-3 px-3`.
  - Phục hồi subtitle về `text-[10px]`.
  - Phục hồi group label về `px-3 text-[10px] font-bold uppercase tracking-wider text-muted-foreground/70`.
  - Phục hồi badge size về `text-[10px]`.
  - Phục hồi footer info về `text-[11px]` và `text-[10px]`.

---

## 2. Kết Quả Kiểm Thử (Verification)
- `npm run lint`: Biome check 77 files, **0 lỗi**.
- `npm run typecheck`: TypeScript `tsc --noEmit`, **0 lỗi**.
- Git diff: `app-sidebar.tsx` khôi phục 100% sạch sẽ về commit gốc.
