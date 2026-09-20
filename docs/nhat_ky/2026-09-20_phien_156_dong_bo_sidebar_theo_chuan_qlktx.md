# Nhật Ký Làm Việc — Phiên #156
# Ngày: 2026-09-20 | Đồng Bộ Hóa Toàn Diện Sidebar & Chuẩn Hóa Typography Scale Font-Size Theo Chuẩn QLKTX (`ktx.qnu.edu.vn/dashboard`)

## 1. Mục Tiêu Phiên Làm Việc
1. **Khắc phục triệt để hiện tượng Sidebar chưa đồng bộ**:
   - Đồng bộ Brand Header 64px (`min-h-16 h-16`), logo vuông bo góc `size-10 rounded-xl bg-primary text-primary-foreground`, tên trường và hệ thống.
   - Đồng bộ aside background `bg-background border-r border-border` và main wrapper `lg:pl-[var(--sidebar-width)]` với cờ `data-state="expanded"|"collapsed"`.
   - Đồng bộ scrollable nav container với `min-h-0 overscroll-contain py-4 [scrollbar-gutter:stable] [-webkit-overflow-scrolling:touch] px-3 space-y-4`.
   - Đồng bộ visual active nav item `bg-primary/10 text-primary font-semibold` và group headers in hoa `text-xs font-semibold uppercase tracking-wider text-muted-foreground/80`.
   - Bổ sung User Profile footer ở đáy Sidebar: Avatar tròn với chữ cái đầu của người dùng, tên người dùng (`displayName`), email (`displayEmail`) và đèn báo trạng thái hệ thống (`backendOnline`).
   - Bổ sung nút resize handle / thu gọn thanh bên ở cạnh phải sidebar chuẩn DOM QLKTX.
2. **Nâng Cấp Toàn Diện Typography Scale & Font-Size Toàn Hệ Thống Chuẩn QLKTX**:
   - Triệt tiêu hoàn toàn tình trạng chữ bị thu nhỏ quá mức (`text-xs` 12px, `text-[10px]`, `text-[11px]`) ở các thành phần chính.
   - Tăng cỡ chữ Sidebar Navigation items lên chuẩn **`text-sm font-medium`** (14px) và icon `size-4.5`.
   - Tăng Topbar Breadcrumbs và Search Input lên **`text-sm`** (14px).
   - Tăng PageHeader: Eyebrow lên `text-xs` (12px), Title lên `text-2xl sm:text-3xl font-bold` (30px), Description lên `text-sm sm:text-base`.
   - Tăng KpiMetric: Label lên `text-sm font-medium`, Value lên `text-2xl sm:text-3xl font-bold font-mono`, Helper lên `text-xs`.
   - Tăng Button, Input, TableHead, TableCell, CardDescription lên chuẩn **`text-sm`** (14px).

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật (Key Changes)

| Tệp Tin | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| [`frontend/src/styles/tokens.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/tokens.css) | MODIFY | Tăng các token font-size chuẩn QLKTX: `--font-size-page-title: 2rem` (32px), `--font-size-section-title: 1.25rem` (20px), `--font-size-body: 0.9375rem` (15px), `--font-size-table-header: 0.875rem` (14px), `--font-size-metadata: 0.75rem` (12px). |
| [`frontend/src/styles/globals.css`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/styles/globals.css) | MODIFY | Tối ưu utilities typography scale: `.type-page-title` (line-height 1.2, font-weight 700), `.type-section-title`, `.type-control`, `.type-table`, `.type-table-header`, `.type-caption`, `.type-supporting`. |
| [`frontend/src/layouts/app-sidebar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/app-sidebar.tsx) | MODIFY | 1. Tái cấu trúc DOM `<aside>` với `bg-background`, `w-[var(--sidebar-width)]`, `data-state`.<br>2. Nâng cấp Brand Header 64px với title `text-[15px] font-bold`, subtitle `text-xs`.<br>3. Tăng Nav items lên `text-sm font-medium` (14px), icon `size-4.5`.<br>4. Tăng Section headers lên `text-xs font-semibold uppercase tracking-wider`.<br>5. User Profile footer với avatar `size-8.5`, name `text-sm font-semibold`, email `text-xs`.<br>6. Nút resize handle cạnh phải. |
| [`frontend/src/layouts/topbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/topbar.tsx) | MODIFY | Tăng Breadcrumbs lên `text-sm`, Search button lên `text-sm` (h-9), User trigger lên `text-sm font-semibold` & `text-xs text-muted-foreground`. |
| [`frontend/src/components/admin/page-header.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/page-header.tsx) | MODIFY | Eyebrow `text-xs font-semibold uppercase tracking-wider mb-1.5`, Title `text-2xl sm:text-3xl font-bold tracking-tight`, Description `text-sm sm:text-base`. |
| [`frontend/src/components/admin/kpi-metric.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/kpi-metric.tsx) | MODIFY | Label `text-sm font-medium`, Value `text-2xl sm:text-3xl font-bold font-mono`, Helper `text-xs text-muted-foreground`. |
| [`frontend/src/components/ui/button.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/button.tsx) | MODIFY | Chuẩn hóa size `default` và size `sm` lên `text-sm font-medium` (14px). |
| [`frontend/src/components/ui/input.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/input.tsx) | MODIFY | Chuẩn hóa size `sm` và `default` lên `text-sm` (14px). |
| [`frontend/src/components/ui/card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/card.tsx) | MODIFY | CardTitle `text-base sm:text-lg font-semibold`, CardDescription `text-sm text-muted-foreground`. |
| [`frontend/src/components/ui/table.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/table.tsx) | MODIFY | TableHead `text-sm font-semibold`, TableCell `text-sm text-foreground`. |
| [`frontend/src/layouts/admin-shell.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/admin-shell.tsx) | MODIFY | Truyền `onToggleSidebar`, gán `data-state` và `lg:pl-[var(--sidebar-width)]`. |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Biome Linter**:
   ```bash
   npm run lint
   # Checked 166 files in 188ms. No fixes applied. (0 errors, 0 warnings)
   ```
2. **TypeScript Typecheck**:
   ```bash
   npm run typecheck
   # tsc --noEmit: 0 errors
   ```
3. **Vite Production Build**:
   ```bash
   npm run build
   # ✓ built in 11.08s (2659 modules transformed, dist/ ready)
   ```
4. **Bảo Toàn Nghiệp Vụ (Zero Feature Regression)**:
   - Toàn bộ danh mục 5 Trợ lý AI, Kho Tri Thức RAG, Models & Providers, Vận hành, System và Workflows DAGs giữ nguyên vẹn 100%.
