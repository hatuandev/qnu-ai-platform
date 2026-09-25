# Phiên 216 (2026-09-24 17:30) — Chuẩn Hóa Component Nút Chuyển Đổi View Mode (Grid/Table Toggle) & Đưa Vào UI Rules Bắt Buộc

## 1. Bối Cảnh & Mục Tiêu
- **Bối cảnh**:
  - Người dùng phản hồi về sự thiếu nhất quán giữa các trang danh mục: trên trang `/document-types` nút chuyển View Mode có thiết kế đẹp mắt với cặp icon gọn gàng (`LayoutGrid` và `List`), nhưng trên `/knowledge` lại là 2 nút text thô sơ ("Thẻ" / "Bảng"), trên `/capabilities/nodes` lại sử dụng `variant="default"` màu đen/quá nổi, và trên `/assistants` lại tự viết markup inline lặp lại.
  - Mỗi lần "vibe coding", việc không có một component UI dùng chung và thiếu quy định rõ ràng trong UI Rules dẫn đến các trang mới sinh ra bị lệch pha phong cách giao diện.
- **Yêu cầu của người dùng**:
  - Chuẩn hóa nút chuyển đổi chế độ xem (Grid/Table) của trang `http://localhost:3000/document-types` thành một chuẩn chung.
  - Đưa quy chuẩn này vào UI Rules của hệ thống (`AGENTS.md` và workspace rules) để mọi lần "vibe coding" sau này đều bắt buộc phải tuân theo và giữ tính đồng nhất 100%.
  - Chỉ kiểm thử bằng `npm run build` theo chỉ dẫn "npm run build là dc rồi đừng chạy test nữa nhé".

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Khởi Tạo Component UI Chuẩn Hóa
- **Tệp tạo mới**: [`src/components/ui/view-mode-toggle.tsx`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/frontend2/src/components/ui/view-mode-toggle.tsx)
- **Thiết kế chuẩn mực (Gold Standard theo `/document-types`)**:
  - **Khung bao**: `flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30 shrink-0`
  - **Nút bấm con**: `variant={isActive ? "secondary" : "ghost"}` `size="sm"` `className="h-7 w-7 p-0"`
  - **Icon Lucide**: `<LayoutGrid className="size-3.5" />` (Grid) và `<List className="size-3.5" />` (Table/List)
  - **Tooltip/Title**: `title="Xem dạng thẻ lưới"` và `title="Xem dạng danh sách bảng"`
  - **Tương thích kiểu dữ liệu**: Hỗ trợ an toàn cả `ViewMode = "grid" | "table"` và `ViewMode = "grid" | "list"`.

### 2.2. Đồng Bộ Hóa Toàn Diện Các Trang Danh Mục Frontend2
1. **[`document-types-page.tsx`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/frontend2/src/features/document-types/document-types-page.tsx)**:
   - Thay thế đoạn mã inline bằng `<ViewModeToggle value={viewMode} onChange={setViewMode} />`.
   - Dọn sạch imports không dùng `LayoutGrid`, `List`.
2. **[`knowledge-page.tsx`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/frontend2/src/features/knowledge/knowledge-page.tsx)**:
   - Xóa bỏ hoàn toàn 2 nút văn bản thô sơ ("Thẻ" / "Bảng").
   - Tích hợp `<ViewModeToggle value={viewMode} onChange={setViewMode} />`.
3. **[`node-catalog-page.tsx`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/frontend2/src/features/capabilities/nodes/node-catalog-page.tsx)**:
   - Loại bỏ nút `variant="default"` màu đen/quá đậm và `rounded-sm`.
   - Tích hợp `<ViewModeToggle value={viewMode} onChange={setViewMode} />`.
   - Dọn sạch imports không dùng `LayoutGrid`, `List`.
4. **[`assistants-page.tsx`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/frontend2/src/features/assistants/assistants-page.tsx)**:
   - Thay thế cụm nút inline 20 dòng bằng `<ViewModeToggle value={viewMode} onChange={setViewMode} className="self-end sm:self-auto" />`.
   - Dọn sạch imports không dùng `LayoutGrid`, `List`.

### 2.3. Bổ Sung Quy Chuẩn Bắt Buộc Vào Hệ Thống UI Rules
1. **[`AGENTS.md`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/AGENTS.md)**:
   - **Mục 1, Điều 8**: Bổ sung quy định bắt buộc chuẩn hóa `ViewModeToggle` trong tôn chỉ *Component Reuse First*.
   - **Mục 4, Điều 15**: Bổ sung *Quy Chuẩn Nút Chuyển Đổi Chế Độ Xem (View Mode Switcher / Grid-Table Toggle Standard)* quy định chi tiết cấu trúc container, biến thể variant secondary/ghost, kích thước `h-7 w-7 p-0`, icon `size-3.5` và cấm tuyệt đối tự chế style khi Vibe Coding.
2. **[`.agents/skills/qnu-frontend-architect/SKILL.md`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md)**:
   - Cập nhật mục 3.11 *Quy Chuẩn Nút Chuyển Đổi Chế Độ Xem*.
3. **[`.agents/rules/ui-standards.md`](file:///d:/DuAnPhanMem/QLKTX/qnu-ai-platform/.agents/rules/ui-standards.md)**:
   - Khởi tạo tài liệu UI rule độc lập phục vụ auto-discovery của Antigravity AI Customization Engine.

---

## 3. Kết Quả Kiểm Thử
- **Biome Linter**: 5 files checked, 0 lỗi (`src/components/ui/view-mode-toggle.tsx`, `document-types-page.tsx`, `knowledge-page.tsx`, `node-catalog-page.tsx`, `assistants-page.tsx`).
- **Vite Build**: `npm run build` trên `frontend2` thành công 100% trong 3.70s (Exit code 0).
