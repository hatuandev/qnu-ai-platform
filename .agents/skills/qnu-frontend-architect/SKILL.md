---
name: qnu-frontend-architect
description: >-
  Use this skill when developing, refactoring, or extending Frontend components, pages, hooks,
  and UI interfaces on the QNU AI Platform. Enforces Vite 6 + React 19 architecture, OKLCH Design Tokens
  (Academic Teal), 3-tier component hierarchy (Primitives, Admin Helpers, AI Suite), Biome linting standards,
  TanStack Query caching, and AI streaming UX patterns.
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
2. **Cơ Chế Offline Seed Fallback**:
   - Khi Backend chưa bật hoặc ngắt kết nối, `api-client.ts` tự động nạp dữ liệu mẫu chất lượng cao (Seed Data).
   - Component không được sập (`crash`) khi dữ liệu trả về rỗng; luôn hiển thị `EmptyState` hoặc `Skeleton` khi `isLoading`.
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

## 8. Quy Trình Kiểm Thử & Nghiệm Thu Giao Diện Bắt Buộc

Mọi thay đổi trên Frontend trước khi kết thúc phiên làm việc bắt buộc phải vượt qua toàn bộ 3 bước kiểm tra:

```bash
# 1. Kiểm tra linter và định dạng cú pháp (Phải 0 lỗi)
npm run lint

# 2. Kiểm tra tính toàn vẹn kiểu dữ liệu TypeScript (Phải 0 lỗi)
npm run typecheck

# 3. Đóng gói kiểm thử bản Production (Phải biên dịch thành công)
npm run build
```

Nếu có bất kỳ cảnh báo hoặc lỗi nào, Agent **bắt buộc phải sửa dứt điểm** trước khi báo cáo hoàn tất công việc.
