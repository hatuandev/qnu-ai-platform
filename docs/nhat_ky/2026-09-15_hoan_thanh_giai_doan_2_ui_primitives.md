# NHẬT KÝ LÀM VIỆC: HOÀN THÀNH GIAI ĐOẠN 2 FRONTEND (UI PRIMITIVES & ADMIN COMPONENTS)
- **Thời gian**: 2026-09-15 19:35
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên**: Xây dựng toàn diện 21 UI Primitives cơ sở và 6 Linh kiện Quản trị tái sử dụng theo chuẩn Design System QLKTX ĐH Quy Nhơn (màu OKLCH Teal, Bo góc 6px controls / 8px surfaces, ThemeProvider 3 chế độ) và trang Showcase kiểm thử trực quan.

---

## 1. Tóm Tắt Các Thay Đổi Kỹ Thuật

| Lớp Linh Kiện | Tên Linh Kiện | Tệp Tin Mã Nguồn | Đặc Tả Kỹ Thuật & Nghiệp Vụ |
| :--- | :--- | :--- | :--- |
| **Hệ Thống Theme** | `ThemeProvider` | [`frontend/src/components/theme-provider.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/theme-provider.tsx) | Quản lý 3 chế độ: `light`, `dark`, `system` (tự động theo HĐH), lưu trữ `localStorage`. |
| **Lớp 1: UI Primitives** | `Button` | [`frontend/src/components/ui/button.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/button.tsx) | Chiều cao 36px (default), 32px (sm), 40px (lg); variants: primary teal, destructive, outline, ghost, link; bo góc 6px. |
| | `Input` | [`frontend/src/components/ui/input.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/input.tsx) | Chiều cao 36px (default), 32px (sm); viền focus ring theo chuẩn QNU. |
| | `Textarea` | [`frontend/src/components/ui/textarea.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/textarea.tsx) | Ô nhập văn bản đa dòng min-h=80px cho System Prompts. |
| | `Label` | [`frontend/src/components/ui/label.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/label.tsx) | Radix LabelPrimitive font-medium 14px. |
| | `Badge` | [`frontend/src/components/ui/badge.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/badge.tsx) | Micro radius 4px; các biến thể: default, secondary, success, warning, destructive, info. |
| | `Card` | [`frontend/src/components/ui/card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/card.tsx) | Bo góc 8px (surface), shadow-2xs; CardHeader, CardTitle, CardDescription, CardContent. |
| | `Dialog` | [`frontend/src/components/ui/dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/dialog.tsx) | Radix DialogPrimitive; modal backdrop-blur-xs, phím ESC và nút đóng X. |
| | `AlertDialog` | [`frontend/src/components/ui/alert-dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/alert-dialog.tsx) | Radix AlertDialogPrimitive; modal cảnh báo thao tác phá hủy (destructive). |
| | `Sheet` | [`frontend/src/components/ui/sheet.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/sheet.tsx) | Ngăn kéo Drawer 4 hướng (top, bottom, left, right) phục vụ `CitationSheet`. |
| | `DropdownMenu` | [`frontend/src/components/ui/dropdown-menu.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/dropdown-menu.tsx) | Radix DropdownMenuPrimitive cho thanh thao tác và tùy chọn tài liệu. |
| | `Tabs` | [`frontend/src/components/ui/tabs.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/tabs.tsx) | Chuyển đổi tab Documents / Ingestion Jobs / RAG Playground. |
| | `Table` | [`frontend/src/components/ui/table.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/table.tsx) | Chiều cao dòng chuẩn 44px (2.75rem), header 12px muted. |
| | `Tooltip` | [`frontend/src/components/ui/tooltip.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/tooltip.tsx) | Chú giải khi hover icon chức năng. |
| | `Popover` | [`frontend/src/components/ui/popover.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/popover.tsx) | Khung nổi cấu hình nhanh và bộ lọc. |
| | `Avatar` | [`frontend/src/components/ui/avatar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/avatar.tsx) | Avatar đại diện Trợ lý AI và Cán bộ quản trị. |
| | `Progress` | [`frontend/src/components/ui/progress.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/progress.tsx) | Thanh tiến độ embedding vector và OCR bóc tách. |
| | `Skeleton` | [`frontend/src/components/ui/skeleton.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/skeleton.tsx) | Khung xương tải dữ liệu bất đồng bộ mượt mà. |
| | `Switch` | [`frontend/src/components/ui/switch.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/switch.tsx) | Cần gạt cấu hình Circuit Breaker và Guardrails an toàn. |
| | `Separator` | [`frontend/src/components/ui/separator.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/separator.tsx) | Đường phân chia ranh giới ngang/dọc 1px. |
| | `Spinner` | [`frontend/src/components/ui/spinner.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/spinner.tsx) | Vòng xoay W3C Accessible Output hiển thị trạng thái sinh token. |
| | `Kbd` | [`frontend/src/components/ui/kbd.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/kbd.tsx) | Phím tắt bàn phím (`Ctrl + K`, `Enter`, `Esc`). |
| **Lớp 2: Admin Helpers** | `StatusBadge` | [`frontend/src/components/admin/status-badge.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/status-badge.tsx) | Hiển thị chấm trạng thái và nhãn cho: Closed, Open, Half-Open, Ready, Processing, Tripped... |
| | `KpiMetric` | [`frontend/src/components/admin/kpi-metric.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/kpi-metric.tsx) | Thẻ đo lường chỉ số FinOps, Token Quota và độ trung thực Ragas TM-08. |
| | `EmptyState` | [`frontend/src/components/admin/empty-state.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/empty-state.tsx) | Khung hiển thị khi danh sách rỗng kèm icon và nút CTA. |
| | `Field` | [`frontend/src/components/admin/field.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/field.tsx) | Khung bao bọc Input/Label kèm dấu sao bắt buộc `*` và lỗi kiểm định Zod. |
| | `ConfirmDialog` | [`frontend/src/components/admin/confirm-dialog.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/confirm-dialog.tsx) | Hộp thoại cảnh báo và xác nhận hủy tiến trình hoặc xóa tài liệu. |
| | `FileUpload` | [`frontend/src/components/admin/file-upload.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/file-upload.tsx) | Vùng kéo thả tệp tải lên (PDF, DOCX, XLSX, TXT) kèm nhận diện icon và dung lượng. |
| **Showcase & App** | `DesignSystemPage` | [`frontend/src/pages/design-system-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/design-system-page.tsx) | Trang Showcase trực quan hóa toàn bộ 6 nhóm linh kiện. |
| | `App` | [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx) | Tích hợp `ThemeProvider`, bộ chuyển đổi giữa Tổng quan và Design System Showcase. |

---

## 2. Kết Quả Kiểm Thử & Nghiệm Thu (Verification)

### 2.1. Frontend Checks
* **Biome Linter & Formatter**:
  ```powershell
  npm run lint
  # Checked 33 files in 21ms. No fixes applied. (0 errors, 0 warnings)
  ```
* **TypeScript Typecheck**:
  ```powershell
  npm run typecheck
  # tsc --noEmit -> 0 errors
  ```
* **Vite Production Build**:
  ```powershell
  npm run build
  # ✓ 1990 modules transformed.
  # dist/index.html                   1.48 kB │ gzip:   0.82 kB
  # dist/assets/index-D7I6TSiX.css   39.59 kB │ gzip:   7.28 kB
  # dist/assets/index-BbA9j_aE.js   431.90 kB │ gzip: 132.82 kB
  # ✓ built in 4.90s
  ```

### 2.2. Backend Checks
* **Ruff Code Style**: `uv run ruff check .` $\rightarrow$ `All checks passed!` (0 errors).
* **Pytest Suite**: `uv run --extra dev pytest` $\rightarrow$ `68 passed, 3 warnings in 4.64s` (100% pass).

---

## 3. Trạng Thái Hoàn Thành
- **Giai đoạn 2**: **HOÀN THÀNH 100% (PASSED)**.
- **Bước tiếp theo**: Sẵn sàng triển khai **Giai đoạn 3: Dựng Khung Vỏ Layout Shell (`AdminShell`)** gồm `AppSidebar`, `Topbar`, `Breadcrumbs`, và `CommandMenu` (`Ctrl + K`).
