# Nhật Ký Làm Việc — Phiên #117 (Giai Đoạn 7)
# Ngày: 2026-09-19 | Triển Khai Giai Đoạn 7: Responsive App Shell (Mobile Drawer & 3 Layout Variants), Dọn Dẹp Dev Junk & Khung Chuẩn Hóa Trạng Thái Dữ Liệu

---

## 1. Mục Tiêu Phiên Làm Việc
- Giải quyết trực tiếp các vấn đề ưu tiên cao **P0.1, P0.3, P0.2** được chỉ ra trong [Bản nhận xét Frontend UI/UX](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/nhan_xet_frontend_ui_ux_hien_tai_2026-09-19.md).
- **Responsive App Shell & Mobile Drawer (P0.1)**:
  - Ẩn sidebar cố định trên màn hình `< 1024px` (`lg`), chuyển đổi thành **Mobile Drawer Sheet** mở ra từ nút Menu hamburger trên Topbar.
  - Tự động đóng Mobile Drawer khi người dùng click vào bất kỳ liên kết điều hướng nào.
  - Thiết lập vùng đệm chuẩn: `pl-0` trên mobile, `lg:pl-64` / `lg:pl-16` trên desktop.
  - Hỗ trợ **3 Layout Variants** cho `<main>`:
    * `full-bleed` (`h-[calc(100vh-3.5rem)]`, `p-0`, `overflow-hidden`): Dành cho DAG Canvas Studio, Scan & OCR Studio Split-Screen, Chat Studio, Conversations Desk.
    * `wide` (`max-w-[1600px] mx-auto`): Dành cho Dashboard KPI và Bảng Runs.
    * `standard` (`max-w-7xl mx-auto`): Dành cho các trang danh mục và form thông thường.
- **Dọn Dẹp Dev Junk Khỏi Production UI (P0.3)**:
  - Đọc thông tin người dùng thật từ `useAuth()` (`actor`) để hiển thị tên, email, vai trò và avatar initials thay vì dữ liệu gán cứng.
  - Ẩn triệt để các liên kết localhost (`localhost:8001/docs`, `localhost:6333`) khỏi production; chỉ hiển thị khi `import.meta.env.DEV` kèm nhãn `[Dev]`.
  - Cập nhật footer Sidebar hiển thị tiếng Việt thân thiện ("Hệ thống sẵn sàng" / "Mất kết nối máy chủ"), không rò rỉ port nội bộ.
- **Khung Chuẩn Hóa Trạng Thái Dữ Liệu (P0.2)**:
  - Tạo mới component [`StateBanner`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/state-banner.tsx) hỗ trợ các trạng thái: `degraded` (cảnh báo dữ liệu suy giảm/cache kèm timestamp và nút làm mới), `demo` (nhãn dữ liệu mẫu minh họa), `offline` (mất kết nối máy chủ), `info`, `success`.
  - Nâng cấp component [`EmptyState`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/empty-state.tsx) hỗ trợ `variant="filter-empty"` với icon `SearchX` mặc định và nút "Xóa bộ lọc" (`onReset`).
- **Bảo đảm chất lượng 100%**: Biome 0 lỗi, TypeScript 0 lỗi, Vite build thành công, Pytest 232/232 passed, Ruff 0 lỗi, Zero Mojibake.

---

## 2. Chi Tiết Các Tệp Tin Chỉnh Sửa & Tạo Mới

| Tệp Tin | Loại | Mô Tả Thay Đổi Kỹ Thuật |
| :--- | :--- | :--- |
| [`frontend/src/layouts/admin-shell.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/admin-shell.tsx) | Cập nhật | Tích hợp `Sheet` cho Mobile Drawer, quản lý state `mobileDrawerOpen`, thiết lập `pl-0` trên mobile và `lg:pl-64` / `lg:pl-16` trên desktop. Tự động ánh xạ 3 layout variants (`full-bleed`, `wide`, `standard`) theo `currentPath`. |
| [`frontend/src/layouts/app-sidebar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/app-sidebar.tsx) | Cập nhật | Bổ sung `hidden lg:flex` cho desktop sidebar, hỗ trợ prop `isMobile` và callback `onCloseMobile` để đóng Sheet khi chọn route, chuẩn hóa footer tiếng Việt không rò rỉ port. |
| [`frontend/src/layouts/topbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/topbar.tsx) | Cập nhật | Bổ sung nút hamburger Menu (`lg:hidden`) mở Mobile Drawer, desktop toggle button (`hidden lg:inline-flex`), đọc phiên đăng nhập từ `useAuth()` (`actor`), ẩn link `localhost` ở production. |
| [`frontend/src/components/admin/state-banner.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/state-banner.tsx) | Tạo mới | Component banner hiển thị chuẩn hóa các trạng thái dữ liệu `degraded`, `demo`, `offline`, `info`, `success` với màu sắc ngữ nghĩa và nút hành động. |
| [`frontend/src/components/admin/empty-state.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/empty-state.tsx) | Cập nhật | Bổ sung `variant?: "empty" | "filter-empty"`, hỗ trợ icon `SearchX` và nút "Xóa bộ lọc" (`onReset`). |
| [`docs/memory/snapshots/2026-09-19_session_117.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/memory/snapshots/2026-09-19_session_117.md) | Tạo mới | Snapshot bộ nhớ phiên 117. |
| [`docs/WORK_LOG.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/WORK_LOG.md) | Cập nhật | Bổ sung phiên 117 vào bảng tổng hợp tiến độ. |
| [`docs/memory/PROJECT_CONTEXT.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/memory/PROJECT_CONTEXT.md) | Cập nhật | Cập nhật trạng thái hoàn thành Giai đoạn 7 và đồng bộ ngữ cảnh. |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Frontend Code Quality (Biome Lint)**:
   - `npm run lint`
   - **Kết quả: Checked 135 files in 137ms. No fixes applied. 0 errors.**
2. **Frontend Type Safety (TypeScript)**:
   - `npm run typecheck`
   - **Kết quả: tsc --noEmit: 0 errors.**
3. **Frontend Production Build (Vite)**:
   - `npm run build`
   - **Kết quả: Built in 6.02s thành công.** (2548 modules transformed).
4. **Backend Code Quality (Ruff)**:
   - `uv run ruff check .`
   - **Kết quả: All checks passed!**
5. **Backend Test Suite (Pytest)**:
   - `uv run --extra dev pytest -v`
   - **Kết quả: 232 passed in 49.29s (100% pass).**
6. **Zero Mojibake Check**:
   - `python scripts/check_mojibake.py`
   - **Kết quả: Đã quét 291 tệp. 100% UTF-8 sạch, không phát hiện ký tự rác.**

---

## 4. Trạng Thái Hoàn Thành
- Giai đoạn 7 (Responsive App Shell, Dọn Dẹp Dev Junk & Khung Chuẩn Hóa Trạng Thái Dữ Liệu) hoàn thành 100%, khắc phục triệt để các hạn chế P0.1, P0.3, P0.2 trong bản chẩn đoán giao diện.
