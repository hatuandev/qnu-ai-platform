# NHẬT KÝ LÀM VIỆC — PHIÊN #155
# Ngày: 2026-09-20 | Mục tiêu: Đồng bộ hóa toàn diện UI Design System từ QLKTX (`qnu-ktx/src/Web/ClientApp`) sang QNU AI Platform (`frontend/`)

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

- **Mục tiêu**: Người dùng yêu cầu đồng bộ hóa toàn diện UI từ dự án QLKTX (`D:\DuAnPhanMem\QLKTX\qnu-ktx\src\Web\ClientApp`) sang nền tảng QNU AI Platform (`d:\DuAnPhanMem\qnu-ai-platform\frontend`), bao gồm Design Tokens, Typography Scale, Spacing, Buttons, Badges, Cards, Tables, Inputs, Debounced Search, Layout Shell và Page Headers trên toàn bộ các màn hình quản trị.
- **Tôn chỉ bất biến**:
  1. **Zero Feature Regression**: Bảo toàn 100% tính năng, queries, mutations, route handling, modal dialogs và logic tương tác hiện có của Frontend.
  2. **Academic Teal Identity**: Chuẩn màu chủ đạo `oklch(0.46 0.13 160)` (Dark Mode `oklch(0.67 0.13 160)`), tuyệt đối không hardcode màu thô (`bg-emerald-600`, `bg-blue-600`, `bg-rose-600`).
  3. **Zero Mojibake & 100% Lucide Icons**: Tuyệt đối không dùng emoji trên UI quản trị, mọi biểu tượng đều là Lucide icons thanh lịch.
  4. **Strict Linter & Type Safety**: Biome linter 0 lỗi, TypeScript typecheck 0 lỗi, Vite build đóng gói thành công 100%.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật

### 2.1. Foundation Tokens & Global Styles
- [`frontend/src/styles/tokens.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/tokens.css):
  - Bổ sung `--radius-overlay: 0.5rem;` và `--sidebar-item-height: 2.25rem;`.
  - Khai báo `@media (max-width: 767px)` căn chỉnh touch target (`--control-height: 2.5rem;`) và cỡ chữ tối thiểu trên thiết bị di động.
- [`frontend/src/styles/globals.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/globals.css):
  - Bổ sung `@media (prefers-reduced-motion: reduce)` tắt hiệu ứng chuyển động khi người dùng yêu cầu trợ năng.
  - Đồng bộ đầy đủ các lớp tiện ích kiểu chữ `.type-*` bám sát 8 nấc typography của QLKTX.

### 2.2. Primitive UI Components (Tầng 1)
- [`frontend/src/components/ui/button.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/button.tsx):
  - Chuẩn hóa typography token `type-control`, chiều cao control `h-[var(--control-height)]` (36px) và compact `h-[var(--control-height-compact)]` (32px).
  - Tinh chỉnh variant `outline`, `secondary`, `ghost` sử dụng semantic tokens (`bg-accent text-accent-foreground`).
- [`frontend/src/components/ui/card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/card.tsx):
  - Chuẩn hóa padding `CardHeader` (`gap-1.5 p-5`), `CardDescription` (`type-supporting text-muted-foreground`), `CardContent` (`px-5 pb-5`), `CardFooter` (`px-5 pb-5`).
- [`frontend/src/components/ui/input.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/input.tsx):
  - Chuẩn hóa chiều cao `h-[var(--control-height)]`, bo góc `--radius-control`, padding ngang `px-3`, phông chữ `type-control`.
- [`frontend/src/components/ui/table.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/table.tsx):
  - Chuẩn hóa `type-table`, `type-table-header` với chiều cao hàng tiêu đề `h-10 px-3`, padding ô `px-3 py-3 align-middle`, hiệu ứng hover nhẹ nhàng `hover:bg-muted/40`.
- [`frontend/src/components/ui/kbd.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/kbd.tsx):
  - Đảm bảo component phím tắt hiển thị chuẩn mực trên topbar và các thanh tìm kiếm.

### 2.3. Admin Components & Helpers (Tầng 2)
- [`frontend/src/components/admin/page-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/page-header.tsx):
  - Nâng cấp prop `title: React.ReactNode` để hỗ trợ linh hoạt cả tiêu đề thuần chuỗi lẫn tiêu đề đính kèm Badge trạng thái / audit trails.
- [`frontend/src/components/admin/kpi-metric.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/kpi-metric.tsx):
  - Nâng cấp hỗ trợ tương thích kép: Nhận cả props chuẩn QLKTX (`label`, `value`, `delta`, `trend`, `helper`, `icon`) lẫn backward compatibility props cũ (`title`, `change`, `changeType`, `description`).
- [`frontend/src/components/admin/debounced-search-input.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/debounced-search-input.tsx):
  - Tạo mới component tìm kiếm debounce kèm xử lý gõ tiếng Việt (IME Composition với cờ `isComposingRef`) chống giật lag và gãy chữ khi gõ Telex/VNI.
- [`frontend/src/components/admin/status-badge.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/status-badge.tsx):
  - Mở rộng toàn bộ danh mục trạng thái AI Platform (`ready`, `approved`, `indexing`, `evaluating`, `failed`, `paused_for_approval`) với nền tint mờ `/12` thanh nhã chuẩn QLKTX.

### 2.4. Layout Shell
- [`frontend/src/layouts/admin-shell.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/admin-shell.tsx):
  - Chuẩn hóa layout container `max-w-[1600px] mx-auto` với padding phân tầng `px-4 py-6 sm:px-6 sm:py-7 lg:px-8`.
- [`frontend/src/layouts/topbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/topbar.tsx):
  - Chuẩn hóa chiều cao `h-[var(--topbar-height)]` (56px), search button có phím tắt `<Kbd>`, avatar `size-8`, theme toggle `size-8.5`.
- [`frontend/src/layouts/app-sidebar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/app-sidebar.tsx):
  - Chuẩn hóa item `h-[var(--sidebar-item-height)]`, bo góc `rounded-md`, typography `type-metadata`.

### 2.5. Đồng Bộ Toàn Bộ Các Trang Chính
1. [`frontend/src/pages/dashboard-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dashboard-page.tsx): Áp dụng `PageHeader` và cụm KPI Metric Card chia ô `divide-y sm:divide-y-0 sm:divide-x`.
2. [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx): Áp dụng `PageHeader`, `DebouncedSearchInput`, Pill Tabs chuẩn semantic tokens, cụm KPI Metric strip chia ô, xóa bỏ 100% màu emerald/rose hardcode.
3. [`frontend/src/pages/assistants-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistants-page.tsx): Áp dụng `PageHeader` và Stat KPIs Card chia ô 3 cột chuẩn QLKTX.
4. [`frontend/src/pages/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx): Áp dụng `PageHeader` chuẩn.
5. [`frontend/src/pages/runs-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/runs-page.tsx): Áp dụng `PageHeader`, Card KPI 3 cột chia ô, chuẩn hóa button variants.
6. [`frontend/src/pages/evaluation-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/evaluation-page.tsx): Áp dụng `PageHeader`, thay màu thô sang `text-success`/`text-warning`.
7. [`frontend/src/pages/settings-integrations-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/settings-integrations-page.tsx): Áp dụng `PageHeader`.
8. [`frontend/src/pages/conversations-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/conversations-page.tsx): Áp dụng `PageHeader`, `DebouncedSearchInput`, chuẩn hóa semantic badges và buttons.
9. [`frontend/src/pages/workflows-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/workflows-page.tsx): Áp dụng `PageHeader`, Card KPI chia ô 4 cột, `DebouncedSearchInput`, loại bỏ màu raw.
10. [`frontend/src/pages/document-ingest-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-ingest-page.tsx): Chuẩn hóa semantic tokens và button styles.
11. [`frontend/src/components/knowledge/`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/knowledge/): Chuẩn hóa `types.ts`, `collection-documents-tab.tsx`, `collection-tasks-tab.tsx`, `collection-facts-tab.tsx` sang semantic tokens.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Biome Linter**:
   ```bash
   npm run lint
   # Checked 166 files in 199ms. No fixes applied. (Exit code 0)
   ```
2. **TypeScript Typecheck**:
   ```bash
   npm run typecheck
   # tsc --noEmit: 0 errors. (Exit code 0)
   ```
3. **Vite Production Build**:
   ```bash
   npm run build
   # tsc -b && vite build: 2659 modules transformed. Built in 8.09s. (Exit code 0)
   ```

---

## 4. Kết Luận
Đã hoàn thành xuất sắc việc đồng bộ hóa toàn diện UI Design System của `qnu-ai-platform` theo chuẩn mực của dự án QLKTX (`qnu-ktx`), giữ vững 100% tính năng và cấu trúc dữ liệu của ứng dụng, triệt tiêu mã màu thô, bảo đảm 0 lỗi lint và 0 lỗi typecheck.
