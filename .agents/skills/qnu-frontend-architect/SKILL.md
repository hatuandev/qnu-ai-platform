---
name: qnu-frontend-architect
description: >-
  Use this skill when developing, refactoring, or extending Frontend components, pages, hooks, and UI interfaces on QNU AI Platform (Vite + React 19, OKLCH Academic Teal design tokens, 3-tier component hierarchy, Biome, TanStack Query, Master-Detail Deep Routing). Do NOT use for backend Python code or database schema changes.
---

# Hướng Dẫn Kiến Trúc & Quy Chuẩn Giao Diện Frontend QNU AI Platform

Tài liệu này là cẩm nang bắt buộc cho mọi kỹ sư Frontend và AI Agent khi phát triển, chỉnh sửa và mở rộng giao diện người dùng trên nền tảng **`qnu-ai-platform`**.

---

## 1. Tôn Chỉ Thiết Kế & Hệ Thống Nhận Diện QNU

1. **Đồng bộ 100% Hệ thống Thiết kế ĐH Quy Nhơn (`qnu-ktx`)**:
   - Sử dụng sắc xanh Teal học thuật làm màu chủ đạo: `--primary: oklch(0.46 0.13 160)`.
   - Dark Mode là công dân hạng nhất (First-class citizen), chuyển đổi mượt mà, không giật màn hình (FOUC).
   - Tuyệt đối không hardcode màu thô (`bg-white`, `text-black`, `bg-blue-500`), luôn sử dụng semantic tokens (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `text-primary`).
2. **Production-First & Trọng Lượng Nhẹ (Lightweight SPA)**:
   - Sử dụng Vite 6 + React 19 + TypeScript + Tailwind CSS v4.
   - Không đưa vào các thư viện thừa gây phình to bundle. Bundle production phải giữ mức tối ưu.
   - Tuyệt đối 0 lỗi linter (Biome) và 0 lỗi kiểu dữ liệu (TypeScript `tsc --noEmit`).
3. **Trải Nghiệm Thẩm Mỹ Cao Cấp (Rich & Premium Aesthetics)**:
   - Đường viền tinh tế (`border-border/60`), hiệu ứng làm mờ kính (`backdrop-blur-md`), bóng đổ siêu mảnh (`shadow-2xs`).
   - Tốc độ phản hồi tức thì (<16ms, 60fps). Trạng thái tải dữ liệu mượt mà qua Skeleton và Spinner.
   - Giao diện AI chuyên nghiệp: chữ streaming mượt mà, trích dẫn minh chứng rõ ràng, không giật cuộn trang.

---

## 2. Cấu Trúc Mã Nguồn Frontend (3-Tier Component Hierarchy)

Mọi thành phần giao diện phải được phân loại và đặt đúng vị trí theo kiến trúc 3 tầng:

```text
frontend/src/
├── components/
│   ├── ui/             # TẦNG 1: Primitives (Radix UI + shadcn/ui)
│   │   ├── button.tsx, input.tsx, card.tsx, badge.tsx, dialog.tsx,
│   │   ├── dropdown-menu.tsx, table.tsx, tabs.tsx, sheet.tsx,
│   │   └── kbd.tsx, spinner.tsx, skeleton.tsx, ...
│   ├── admin/          # TẦNG 2: Admin Helpers (Tái sử dụng cho trang quản trị)
│   │   ├── empty-state.tsx     (Hiển thị khi danh sách rỗng)
│   │   ├── kpi-metric.tsx      (Thẻ chỉ số FinOps, Tokens, TM-08)
│   │   ├── status-badge.tsx    (Huy hiệu trạng thái có dot chỉ báo)
│   │   ├── file-upload.tsx     (Kéo thả tệp tri thức đa định dạng)
│   │   ├── confirm-dialog.tsx  (Xác nhận xóa/phê duyệt hành động)
│   │   └── field.tsx           (Wrapper trường nhập liệu kèm label và lỗi)
│   └── ai/             # TẦNG 3: AI Suite (Chuyên biệt cho Trợ lý AI)
│       ├── chat-message.tsx    (Tin nhắn phân tách User/Assistant kèm avatar)
│       ├── chat-bubble.tsx     (Khung nội dung Markdown, copy, retry)
│       ├── message-scroller.tsx (Tự động ghim đáy mượt mà, chống giật)
│       ├── citation-sheet.tsx  (Ngăn kéo trượt hiển thị dẫn chứng RAG)
│       ├── attachment.tsx      (Thẻ đính kèm tài liệu OCR)
│       ├── questionnaire-card.tsx (Thẻ câu hỏi trắc nghiệm Bloom/TM-08)
│       └── dag-canvas.tsx      (Đồ thị DAG Engine bằng @xyflow/react)
├── layouts/            # Khung vỏ ứng dụng (AdminShell, AppSidebar, Topbar, CommandMenu)
├── pages/              # Các màn hình nghiệp vụ độc lập (1 route = 1 page component)
├── navigation/         # Cấu hình điều hướng tập trung (`config.ts`)
├── hooks/              # Custom React Hooks (`useRAGStream.ts`)
├── services/           # Typed API Client (`api-client.ts` + TanStack Query)
└── styles/             # Design tokens (`tokens.css`, `globals.css`)
```

---

## 3. Quy Chuẩn Token Thiết Kế & UI Rules Bắt Buộc

### 3.1. Bảng Token Màu & Ngữ Nghĩa Trạng Thái
| Biến Token | Light Mode | Dark Mode | Ngữ Cảnh Sử Dụng |
| :--- | :--- | :--- | :--- |
| `--primary` | `oklch(0.46 0.13 160)` | `oklch(0.67 0.13 160)` | Nút bấm chính, tab active, brand icon, focus ring |
| `--success` | `oklch(0.55 0.14 160)` | `oklch(0.62 0.14 160)` | Trạng thái Healthy, Sẵn sàng, Circuit Breaker Closed |
| `--warning` | `oklch(0.72 0.15 80)` | `oklch(0.75 0.15 80)` | Cảnh báo Quota token sắp hết, Half-Open |
| `--destructive` | `oklch(0.577 0.245 27.325)` | `oklch(0.62 0.24 27.3)` | Lỗi Circuit Breaker Open, Hủy thao tác, Xóa tài liệu |
| `--info` | `oklch(0.58 0.16 250)` | `oklch(0.65 0.16 250)` | Trích dẫn RAG, tài liệu quy phạm, gợi ý tra cứu |
| `--muted-foreground` | `oklch(0.552 0.016 264)` | `oklch(0.7 0.015 264)` | Chữ phụ, mô tả ngắn, timestamp, placeholder |

### 3.2. Bán Kính Bo Góc (Border Radius)
- **Micro (4px / `--radius-micro`)**: Dùng cho `Badge`, `Kbd`, thanh tiến trình nhỏ.
- **Control (6px / `--radius-control` / `rounded-md`)**: **Bắt buộc** cho toàn bộ nút bấm (`Button`), ô nhập (`Input`), `Select`, `Textarea`.
- **Surface (8px / `--radius-surface` / `rounded-lg`)**: Dùng cho `Card`, hộp thoại `Dialog`, ngăn kéo `Sheet`, bảng `Table` wrapper.

### 3.3. Chiều Cao Chuẩn Của Điều Khiển (Control Heights)
- **Standard Control (`h-9` / 36px)**: Nút bấm chuẩn, ô nhập liệu chuẩn.
- **Compact Control (`h-8` / 32px)**: Thanh công cụ bảng, filter bar, nút bấm phụ (`size="sm"`).
- **Table Row (`h-11` / 44px)**: Hàng trong bảng dữ liệu để bảo đảm diện tích bấm dễ dàng.
- **Topbar (`h-14` / 56px)**: Chiều cao cố định của thanh điều hướng trên cùng.
- **Sidebar (`w-64` / 256px)**: Độ rộng chuẩn của thanh bên điều hướng.

### 3.4. Thứ Bậc Kiểu Chữ (Typography Hierarchy)
- **Phông chữ**: `Inter` cho văn bản (`font-sans`), `JetBrains Mono` cho mã lệnh/phím tắt (`font-mono`).
- **Body & Controls**: 14px (`text-sm`, `leading-normal`).
- **Compact Toolbars / Badges / Table Headers**: 12px (`text-xs`, `font-medium`).
- **Microcopy & Citations**: 11px (`text-[11px]`, `text-muted-foreground`).
- **Page Titles**: 20px–24px (`text-xl` hoặc `text-2xl`, `font-semibold`, `tracking-tight`).

### 3.5. Quy Chuẩn Lucide Icons & Cấm Tuyệt Đối Emoji Trong Giao Diện Quản Trị
- **100% `lucide-react`**: Toàn bộ icon trong toàn bộ dự án bắt buộc phải nhập từ thư viện `lucide-react`. Tuyệt đối cấm tự tạo icon SVG ad-hoc hoặc sử dụng thư viện icon khác (FontAwesome, Material Icons, v.v.).
- **Tuyệt đối CẤM Emoji trong UI**: Cấm sử dụng các emoji ký tự (`⚡`, `📖`, `🔤`, `💾`, `⚙️`, `✓`, `❌`, `🔥`, v.v.) trên các thành phần giao diện quản trị (topbar, buttons, badges, KPI chips, table cells). Mọi chỉ số và hành động phải dùng icon Lucide thanh lịch tương ứng (`Zap`, `BookOpen`, `Type`, `HardDrive`, `Cpu`, `Check`, `X`, `Flame`).
- **Quy chuẩn kích thước & độ dày nét (Stroke & Size)**:
  - Navigation / Sidebar items: `size-4` (16px), `strokeWidth={1.5}` hoặc `1.75`.
  - Compact toolbar / Table actions: `size-3.5` (14px).
  - Feature headers / Hero tiles: `size-5` (20px) đặt trong container nền bo tròn `size-8 rounded-lg bg-primary/10 text-primary`.
- **Màu sắc ngữ nghĩa**: Luôn áp dụng semantic classes (`text-muted-foreground`, `text-primary`, `text-success`, `text-destructive`).
### 3.6. Tận Dụng Tối Đa Component UI Sẵn Có & Điều Kiện Tạo Component Mới (Component Reuse First)
- **Tận dụng 100% Component Primitives trong `@/components/ui/`**:
  Khi phát triển bất kỳ tính năng, trang, modal, popover, sheet, drawer hay form nghiệp vụ nào, kỹ sư và AI Agent **bắt buộc phải tái sử dụng các component primitives có sẵn** trong thư mục `src/components/ui/` (`Button`, `Checkbox`, `Switch`, `Input`, `Dialog`, `Select`, `Badge`, `Card`, `Tabs`, `Table`, `Sheet`, `Popover`, `Tooltip`, `DropdownMenu`, `Textarea`, `Progress`, `Skeleton`, `Kbd`, `Spinner`, `RadioGroup`, `Accordion`, `Separator`, v.v.) kết hợp cùng các helpers quản trị tầng 2 tại `src/components/admin/` (`Field`, `EmptyState`, `KpiMetric`, `StatusBadge`, `ConfirmDialog`, `FileUpload`).
- **Nghiêm Cấm Dùng Thẻ HTML Nguyên Bản (No Raw Native Form Controls)**:
  Tuyệt đối cấm sử dụng các thẻ HTML thô sơ như `<input type="checkbox">`, `<input type="radio">`, `<button>`, `<select>`, `<input type="text">` hay tự viết inline CSS/classes thủ công khi component chuẩn tương ứng đã có sẵn trong `@/components/ui/`. Thẻ HTML thô sơ không chỉ phá vỡ tính nhất quán thẩm mỹ mà còn gây lỗi hiển thị màu sắc mặc định của hệ điều hành (ví dụ: checkbox màu xanh dương của Windows thay vì màu xanh Academic Green chuẩn của ĐH Quy Nhơn).
- **Điều Kiện & Quy Chuẩn Tạo Component UI Mới**:
  - **Chỉ tạo mới khi và chỉ khi thư viện `@/components/ui/` hoàn toàn chưa có component tương đương**.
  - Component mới phải được đặt tại `src/components/ui/<component-name>.tsx`.
  - Phải kế thừa từ headless primitives của **Radix UI** (hoặc cấu trúc chuẩn shadcn/ui).
  - Phải hỗ trợ `React.forwardRef` với kiểu TypeScript tường minh (`React.ComponentRef`, `React.ComponentPropsWithoutRef`).
  - Phải ứng dụng đầy đủ design tokens OKLCH (`border-primary`, `bg-primary`, `text-primary-foreground`, `focus-visible:ring-ring`, `shadow-xs`), tương thích hoàn toàn cả Light Mode và Dark Mode.
  - Phải export rõ ràng để toàn bộ dự án có thể tái sử dụng lâu dài, tránh tình trạng viết code cục bộ phân tán.

### 3.7. Quy Chuẩn Thiết Kế Đa Thiết Bị & Responsive (Cross-Device & Responsive Standard)
- **Hệ Thống Breakpoints Chuẩn**:
  - Mobile: `< 640px` (điện thoại thông minh dọc)
  - Phablet / Small Tablet: `640px - 767px` (`sm`)
  - Tablet / Small Laptop: `768px - 1023px` (`md`)
  - Desktop Tiêu Chuẩn: `1024px - 1279px` (`lg` - Sidebar chuyển từ Sheet/Drawer sang thanh cố định)
  - Màn Hình Rộng: `≥ 1280px` (`xl`, `2xl`)
- **Cấm Tuyệt Đối Cuộn Ngang Toàn Trang (Zero Horizontal Page Scroll)**:
  - Tuyệt đối cấm gán chiều rộng cố định tính bằng pixel lớn (`w-[1000px]`, `min-w-[800px]`) trên các container chính.
  - Luôn dùng `w-full`, `max-w-...`, Flexbox wrap (`flex-wrap`) và CSS Grid linh hoạt (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`).
- **Khung Vỏ Ứng Dụng & Thanh Bên Đáp Ứng (Responsive Shell & Drawer)**:
  - Khi màn hình `< 1024px`, thanh AppSidebar phải tự động thu gọn và hiển thị dưới dạng ngăn kéo trượt (`Sheet / Drawer`) kích hoạt từ nút bấm trên Topbar.
  - Topbar tự động co gọn thanh tìm kiếm (`CommandMenu` chuyển thành icon kính lúp trên mobile).
- **Bảng Dữ Liệu & Khối Báo Cáo Trên Màn Hình Nhỏ**:
  - Mọi bảng `Table` bắt buộc phải được bọc trong container `w-full overflow-x-auto` để cuộn ngang nội bộ bảng mà không làm xô lệch toàn trang.
  - Trên màn hình hẹp (<640px), ưu tiên xếp chồng dạng thẻ (`Card-based view`) hoặc cuộn ngang phân tách rõ ràng.
- **Điều Khiển Tabs & Thanh Điều Hướng (Responsive Tabs & Breadcrumbs)**:
  - Cụm Tabs trên mobile phải hỗ trợ cuộn ngang (`overflow-x-auto no-scrollbar`) hoặc chia cột đều (`grid grid-cols-N`), tuyệt đối không để chữ bị cắt xén (clipping) hoặc rớt dòng gây vỡ giao diện.
  - Breadcrumbs trên mobile phải tinh gọn: ẩn các badge phụ thừa thãi (như badge *"Chi Tiết Provider"*), thu gọn nút quay lại thành nhãn 1 từ (ví dụ `← Provider`).
- **Hộp Thoại & Ngăn Kéo (Adaptive Modals & Dialogs)**:
  - `Dialog` trên Desktop hiển thị popup trung tâm, nhưng trên Mobile phải có `w-[95vw]` hoặc tự động chuyển thành ngăn kéo trượt từ đáy màn hình (`Drawer / Bottom Sheet`) để dễ thao tác bằng một tay.

### 3.8. Quy Chuẩn Đặt Tên Nút Bấm & Nhãn Điều Khiển Ngắn Gọn (Concise Action Labels & Microcopy Standard)
- **Tôn chỉ "Ít Từ - Rõ Nghĩa" (Concise & Context-Aware)**:
  - Tuyệt đối **không đặt tên nút bấm dài dòng, rườm rà** (như *"Test Kết Nối"*, *"Kiểm Tra Kết Nối Hạ Tầng"*, *"Thêm Mô Hình Mới Vào Nhà Cung Cấp"*, *"Danh Sách Mô Hình"*).
  - Mọi nhãn nút bấm phải súc tích, ưu tiên 1 đến 2 từ kết hợp icon Lucide thanh lịch.
- **Bảng Quy Chuẩn Đối Chiếu**:
  - ❌ *"Test Kết Nối"* / *"Kiểm Tra Kết Nối"* ➔ ✅ **"Kiểm tra"** (kèm icon `Play` hoặc `Activity`).
  - ❌ *"Chỉnh Sửa"* / *"Chỉnh Sửa Thông Tin"* ➔ ✅ **"Sửa"** (kèm icon `Pencil`).
  - ❌ *"Xuất Toàn Bộ Cấu Hình JSON"* ➔ ✅ **"Xuất JSON"** (kèm icon `Download`).
  - ❌ *"Thêm Mô Hình"* / *"Thêm Mô Hình (Add Model)"* ➔ ✅ **"Thêm model"** (kèm icon `Plus`).
  - ❌ *"Thêm Khóa API Mới"* ➔ ✅ **"Thêm khóa"** (kèm icon `Plus`).
  - ❌ *"Bật Hoạt Động"* / *"Bật Hoạt Động Provider"* ➔ ✅ **"Hoạt động"** (kèm Switch).
  - ❌ *"Test 429 Failover"* ➔ ✅ **"Thử Failover"** (kèm icon `Zap`).
  - ❌ *"Test Khóa Này"* ➔ ✅ **"Kiểm tra"** (kèm icon `Play`).
  - ❌ *"Dọn Model Lỗi"* / *"Dọn Dẹp Các Model Đang Chết"* ➔ ✅ **"Dọn model lỗi"** (kèm icon `Trash2`).
- **Nhãn Tabs Cực Kỳ Tối Giản & Cấm Số Đếm Thừa**:
  - ❌ *"Danh Sách Mô Hình (10)"* ➔ ✅ **"Mô hình"**.
  - ❌ *"Kho Khóa API (Key Pool)"* ➔ ✅ **"Khóa API"**.
  - ❌ *"Chính Sách Chịu Lỗi & Cấu Hình"* ➔ ✅ **"Chịu lỗi & Mạng"**.
  - Tuyệt đối cấm gắn các badge số đếm rườm rà lên nhãn tab khi không có yêu cầu đặc thù.

### 3.9. Quy Chuẩn Thanh Tìm Kiếm & Bộ Lọc Phân Tách Hai Phía (Left-Right Split Filter Bar Pattern)
- **Cấm Tuyệt Đối Viền Khung Kép (Zero Double-Border / Box-in-Box)**: Tuyệt đối không bọc thanh tìm kiếm và bộ lọc (`Filter Bar`) trong các container `bg-card p-3 rounded-lg border border-border shadow-2xs`. Các thành phần con (`Input`, `SelectTrigger`, nút `Button`) đã mang đường viền mảnh và màu nền riêng.
- **Bố Cục Phân Tách Hai Phía (Left: Search — Right: Filters)**:
  - Container thanh điều khiển luôn dùng `flex justify-between items-center`:
    ```tsx
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
    ```
  - **Bên trái (`justify-start`)**: Duy nhất ô tìm kiếm (`Input`), có icon kính lúp và nút xóa nhanh `×`.
  - **Bên phải (`justify-end`)**: Nhóm toàn bộ các điều khiển lọc (`Select` phân loại, `Select` trạng thái, nút `Đặt lại` khi active).
- **Khống Chế Độ Rộng Ô Tìm Kiếm (Zero Full-Width Desktop Search Stretch)**:
  - ❌ **Tuyệt đối CẤM dùng `flex-1` đơn độc trên ô tìm kiếm**: Làm ô tìm kiếm trên Desktop bị kéo giãn tới 800px-1000px, tạo khoảng trống mênh mông bất hợp lý và đẩy bộ lọc dạt xa về mép phải.
  - ✅ **Độ rộng chuẩn Desktop**: Khống chế trong khoảng `sm:w-72 lg:w-80` hoặc `sm:max-w-xs` (288px - 320px).
  - ✅ **Độ rộng thích ứng Mobile (`< 640px`)**: Tự động co giãn `w-full` ở trên, cụm bộ lọc chuyển xuống dưới chia 50/50 (`grid grid-cols-2 gap-2 w-full`).
- **Placeholder Súc Tích Chuẩn Microcopy**:
  - ❌ Cấm viết câu dài: `Tìm theo tên hiển thị, mã type (query.rewrite...), mô tả...`.
  - ✅ Chỉ dùng 2-4 từ: `Tìm kiếm node...`, `Tìm theo tên, mã...`, `Tìm kiếm trợ lý...`.

### 3.10. Quy Chuẩn Thẻ Thống Kê & Đếm Tinh Gọn (Zero-Fluff Counter & Minimal KPI Strip)
- **Tôn Chỉ Trọng Tâm & Dữ Liệu Cao (High Data-to-Ink Ratio)**:
  - Thẻ thống kê (`KpiMetric` / Counter Card) sinh ra để người dùng nắm bắt chỉ số tức thì trong 1 giây.
  - Cấu trúc tối giản 3 phần: **Tiêu đề chỉ số** (`label`) + **Icon Lucide thanh lịch** (`icon`) + **Con số định lượng lớn** (`value`) (kèm huy hiệu xu hướng/chênh lệch `delta` nếu có).
- **Tuyệt Đối CẤM Phụ Đề Dư Thừa & Lặp Lại (Zero Redundant Helper Text)**:
  - ❌ **Cấm tuyệt đối lặp lại con số**: Đã có số to `14` ở trên thì bên dưới cấm lặp lại phụ đề kiểu `14 manifests chuẩn Core`.
  - ❌ **Cấm phụ đề sáo rỗng hoặc liệt kê vụn vặt**: Nghiêm cấm các chuỗi như `Đầu vào, AI, RAG, HITL...`, `Tương thích QNU AI Core`, `Cổng Input & Output schemas`.
  - ✅ **Quy tắc**: Nếu tiêu đề và con số đã tự thân rõ nghĩa, **bắt buộc bỏ hoàn toàn thuộc tính `helper`** (để `helper={undefined}`). Khối KPI phải giữ chiều cao gọn gàng, thoáng đãng. Chỉ dùng `helper` khi thực sự cần chú thích mốc thời gian đặc thù (ví dụ: `24 giờ qua` hoặc `Theo chuẩn UTC+7`).

### 3.11. Quy Chuẩn Nút Chuyển Đổi Chế Độ Xem (View Mode Switcher Standard)
- **Bắt Buộc Dùng `<ViewModeToggle />` Dùng Chung**:
  - Mọi trang danh sách hỗ trợ chuyển đổi giao diện Thẻ Lưới và Danh Sách/Bảng (`/document-types`, `/knowledge`, `/capabilities/nodes`, `/assistants`, v.v.) **BẮT BUỘC PHẢI SỬ DỤNG component dùng chung** `<ViewModeToggle value={viewMode} onChange={setViewMode} />` từ `@/components/ui/view-mode-toggle`.
  - **Cấm Tuyệt Đối Vibe Coding Tự Chế Style Lệch Pha**: Không tự viết thẻ `<div><Button>...</Button></div>` thủ công, không dùng nút text "Thẻ / Bảng", không dùng `variant="default"` màu đen/quá đậm hoặc sai kích thước icon/button.
- **Thiết Kế Chuẩn Mực (Gold Standard theo `/document-types`)**:
  - **Khung chứa**: `flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30 shrink-0`.
  - **Nút con**: `variant={isActive ? "secondary" : "ghost"}` `size="sm"` `className="h-7 w-7 p-0"`. Trạng thái đang chọn có nền `secondary` nhẹ nhàng, trạng thái không chọn là `ghost`.
  - **Icon**: `<LayoutGrid className="size-3.5" />` (Grid) và `<List className="size-3.5" />` (Table/List) từ `lucide-react`.
  - **Tooltip/Title**: "Xem dạng thẻ lưới" và "Xem dạng danh sách bảng".
  - **Linh hoạt kiểu dữ liệu**: Hỗ trợ đồng thời cả `value: "grid" | "table"` và `value: "grid" | "list"`.

---

## 4. Quy Tắc Biome Linter & Chất Lượng Mã Nguồn

Khi viết mã TSX/TS, **bắt buộc tuân thủ các quy tắc sau** để tránh lỗi Biome:

1. **Không dùng hằng số số học dạng xấp xỉ (`0.000`)**:
   - ❌ `const zero = 0.000;` (Gây lỗi `lint/suspicious/noApproximativeNumericConstant`)
   - ✅ `const zero = 0;` hoặc `const zero = 0.0;` hoặc `cost.toFixed(4)`
2. **Không dùng chỉ số mảng làm key trong danh sách lặp (`key={idx}`)**:
   - ❌ `{items.map((item, idx) => <div key={idx}>...</div>)}`
   - ✅ `{items.map((item) => <div key={item.id}>...</div>)}`
   - Nếu không có ID: kết hợp thuộc tính duy nhất `key={`${item.code}-${item.timestamp}`}`
3. **Thẻ `<label>` bắt buộc có `htmlFor` hoặc dùng `<span>`**:
   - ❌ `<label className="...">Tên trường</label>` (Gây lỗi `a11y/noLabelWithoutControl`)
   - ✅ `<label htmlFor="field-id" className="...">Tên trường</label>`
   - ✅ Hoặc `<span className="text-sm font-medium">Tên trường</span>` khi chỉ làm tiêu đề hiển thị
4. **Không gán thuộc tính `role` tùy tiện trái chuẩn WAI-ARIA**:
   - ❌ `<div role="user">` hoặc `<div role="assistant">` (Gây lỗi `a11y/useAriaActivedescendantWithTabindex`)
   - ✅ Dùng `data-role="user"` hoặc `data-message-type="assistant"`
5. **Sắp xếp Import tự động theo Alphabet**:
   - Biome tự động gom nhóm và sắp xếp imports khi format. Hãy chạy `npm run format` hoặc `npm run lint` để tự động chuẩn hóa.

---

## 5. Tư Duy UI Mở & Kiến Trúc Master-Detail Deep Routing

### 5.1. Tôn Chỉ "Mở Rộng Không Gian" Thay Vì "Gò Bó Một Trang"
1. **Chống Anti-pattern "Monolithic Tabbed Page"**:
   - ❌ **Sai lầm phổ biến**: Gộp tất cả chức năng (Danh sách, Chi tiết, Wizard nạp tệp, Cấu hình sâu, Nhật ký) vào chung 1 file page duy nhất và chia bằng các thẻ `<Tabs>`. Khi người dùng bấm vào một Card/Row, hệ thống chỉ đổi tab hoặc mở một modal popup chật chội.
   - ✅ **Tư duy UI mở chuẩn mực**: Mỗi đối tượng dữ liệu trọng tâm (Bộ sưu tập Tri thức, Trợ lý AI, Provider, Workflow DAG, Đợt đánh giá TM-08) phải có **Trang Chi Tiết Độc Lập (Dedicated Detail Page)** với URL route riêng, không gian rộng rãi để trình bày đa cột và thao tác chuyên sâu.

2. **Mô Hình Phân Cấp 2 Tầng (Master - Detail Separation)**:
   - **Tầng 1: Master / List View (Trang Tổng Quan)**:
     - Tập trung vào: Search bar, Filter badges, Thẻ chỉ số tổng quan (KPIs), và Danh sách Cards hoặc Table trực quan, thoáng đãng.
     - Click vào bất kỳ Card/Hàng nào: **Bắt buộc chuyển hướng (Navigate) sang Trang Chi Tiết**.
   - **Tầng 2: Dedicated Detail View (Trang Chi Tiết Chuyên Sâu)**:
     - URL có path parameter rõ ràng: `/:domain/:id` (ví dụ: `/knowledge/collections/:id`, `/models/:id`, `/assistants/:id`, `/workflows/:id`).
     - Có thanh **Breadcrumb** phân cấp (`Kho Tri Thức / Tuyển Sinh 2026`) kèm nút quay lại (`ArrowLeft` - Về danh sách).
     - **Header & Action Toolbar**: Tên đối tượng to rõ, biểu tượng, badge trạng thái, và bộ nút hành động đặc thù (Chỉnh sửa, Xóa, Test kết nối, Bật/Tắt, Đồng bộ).
     - **Bố cục đa cột (Multi-column Deep Space)**: Tận dụng toàn bộ màn hình (ví dụ 2/3 cho nội dung chính, 1/3 cho thông số/metadata/models).

3. **Quy Tắc Tách Tệp Mã Nguồn Độc Lập**:
   - Tuyệt đối không viết code trang chi tiết thành khối component phụ hàng nghìn dòng trong cùng file trang danh sách.
   - Phải tách thành các file trang riêng biệt trong `src/pages/`:
     - `knowledge-page.tsx` (Danh sách Collections) ➔ `collection-detail-page.tsx` (Chi tiết 1 Collection).
     - `assistants-page.tsx` (Danh sách Trợ lý) ➔ `assistant-detail-page.tsx` (Chi tiết cấu hình 1 Trợ lý).
     - `modelops-page.tsx` (Danh sách Providers) ➔ `provider-detail-page.tsx` (Chi tiết cấu hình 1 Provider).
     - `workflows-page.tsx` (Danh sách Workflows) ➔ `dag-canvas-page.tsx` (Không gian vẽ đồ thị DAG).

4. **Bảo Đảm Deep Linking & URL State**:
   - Khi người dùng F5 hoặc gửi link cho đồng nghiệp (`http://.../knowledge/collections/coll_123`), hệ thống phải đọc ID từ URL và tự động render trực tiếp trang chi tiết tương ứng, không bị reset về trang chủ.

---

## 6. Quản Lý State & Tích Hợp API (TanStack Query v5)

1. **Query Key Chuẩn Hóa**:
   - Sử dụng mảng phân cấp rõ ràng:
     - `['assistants']` (danh sách)
     - `['assistants', assistantId]` (chi tiết)
     - `['knowledge', 'collections']`
     - `['knowledge', 'collections', collectionId]` (chi tiết collection)
     - `['knowledge', 'documents', collectionId]`
     - `['modelops', 'providers']`
     - `['modelops', 'providers', providerId]`
2. **Cơ Chế Phân Định Demo vs LiveMode (Tuân Thủ Anti-Mock Rule)**:
   - **Demo / Sample Mode**: Chỉ kích hoạt khi người dùng chủ động yêu cầu xem trước giao diện mẫu (thông qua công tắc bật/tắt Demo hoặc tham số URL `?mode=demo`).
   - **LiveMode (Chế độ sản xuất mặc định)**: Tuân thủ nghiêm ngặt **Anti-Mock Rule** của `AGENTS.md`. Khi Backend mất kết nối hoặc API trả lỗi, Frontend **tuyệt đối không âm thầm nạp số liệu giả/mock bịa đặt** cho dữ liệu nghiệp vụ (điểm chuẩn, học phí, chỉ tiêu, nội dung quy chế); thay vào đó phải hiển thị Error State / Empty State trung thực hoặc kích hoạt No-Answer Policy để hướng dẫn người dùng liên hệ phòng ban phụ trách.
   - Component không được sập (`crash`) khi dữ liệu trả về rỗng hoặc lỗi; luôn hiển thị `EmptyState`, `Alert` hoặc `Skeleton` khi `isLoading`.
3. **Optimistic Updates & Invalidation**:
   - Khi thực hiện `mutation` (tạo/sửa/xóa), luôn gọi `queryClient.invalidateQueries({ queryKey: [...] })` để đồng bộ lại dữ liệu mới nhất.
   - Hiển thị thông báo kết quả qua `sonner` (`toast.success()`, `toast.error()`).

---

## 7. Quy Chuẩn AI UX & Streaming Nâng Cao

1. **Server-Sent Events (SSE) Streaming qua `useRAGStream`**:
   - Phải xử lý đầy đủ các event types: `token`, `fact`, `citation`, `tool_call`, `error`, `done`.
   - Trạng thái đang sinh token phải có hiệu ứng *Thinking Indicator* nhẹ nhàng.
2. **MessageScroller & Auto-Scroll Protection**:
   - Tự động cuộn xuống đáy khi AI đang sinh chữ.
   - Nếu người dùng lăn chuột lên trên để đọc lại tài liệu cũ, **phải tự động tạm dừng cuộn** (tránh giật mắt). Khi người dùng cuộn trở lại sát đáy, tự động tiếp tục ghim đáy.
3. **Anti-Hallucination & Trích Dẫn Minh Chứng**:
   - Mỗi câu trả lời có sử dụng RAG phải gắn kèm nhãn trích dẫn (`CitationBadges`).
   - Bấm vào nhãn phải kích hoạt `CitationSheet` trượt từ bên phải hiển thị chi tiết: Tên văn bản, Điều/Khoản, Trang và Trích đoạn gốc để đối soát.
4. **Hiển Thị Đa Định Dạng (Markdown & Latex/Tables)**:
   - Sử dụng `react-markdown` kết hợp plugin `remark-gfm`.
   - Bảng biểu Markdown phải tự động có viền, bo góc và cuộn ngang nếu quá rộng trên màn hình nhỏ.

---

## 8. Quy Trình Kiểm Thử & Nghiệm Thu Giao Diện Tinh Gọn (Fast-Path Build Verification)

Khi chỉ thực hiện chỉnh sửa, tối ưu giao diện Frontend (UI/UX, CSS, Component, Page, Dialog), **tuyệt đối không chạy các bộ test Backend (`pytest`), không chạy quét toàn bộ linter hay các tác vụ cồng kềnh làm chậm quá trình phát triển**.

Agent chỉ cần chạy kiểm tra đóng gói bản Production:

```bash
# Đóng gói kiểm thử bản Production (Bảo đảm không có lỗi cú pháp, types hoặc vỡ bundle)
npm run build
```

Nếu lệnh `npm run build` kết thúc thành công (Exit code 0), Agent nghiệm thu ngay và phản hồi cho người dùng, tối ưu hóa tốc độ lặp (iteration speed).

