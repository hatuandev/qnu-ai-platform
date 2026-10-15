# Quy định UI quản trị được chuyển từ AGENTS.md

Giữ quy ước hiện có; chỉ đọc khi chỉnh bố cục, component hoặc tương tác quản trị. Các quy tắc kiểm thử dùng tài liệu chung được liên kết bên dưới.

## 4. Các Quy Tắc Frontend & UI/UX Cốt Lõi (Tuân Thủ Skill `qnu-frontend-architect`)

1. **Hệ Thống Token Thiết Kế & Không Gian Màu OKLCH**:
   - Màu chủ đạo: QNU Academic Teal `--primary: oklch(0.46 0.13 160)` (Dark Mode: `oklch(0.67 0.13 160)`).
   - Tuyệt đối **không hardcode màu thô** (`bg-white`, `text-black`, `bg-blue-600`), luôn dùng semantic tokens (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border`, `text-primary`).
2. **Kiến Trúc 3 Tầng Components**:
   - *Tầng 1 (Primitives)*: `src/components/ui/` (Radix UI + shadcn/ui: Button, Input, Card, Dialog, Table, Sheet, Kbd, Spinner,...).
   - *Tầng 2 (Admin Helpers)*: `src/components/admin/` (EmptyState, KpiMetric, StatusBadge, FileUpload, ConfirmDialog, Field).
   - *Tầng 3 (AI Suite)*: `src/components/ai/` (ChatMessage, ChatBubble, MessageScroller, CitationSheet, Attachment, QuestionnaireCard, DAGCanvas).
3. **Quy Chuẩn Bán Kính Bo Góc & Chiều Cao Điều Khiển**:
   - Bán kính nút bấm/input: Bắt buộc 6px (`rounded-md` / `--radius-control`).
   - Bán kính Cards/Dialogs: 8px (`rounded-lg` / `--radius-surface`).
   - Chiều cao điều khiển chuẩn: `h-9` (36px); Compact toolbar: `h-8` (32px); Table row: `h-11` (44px); Topbar: `h-14` (56px); Sidebar: `w-64` (256px).
4. **Quy Tắc Biome Linter Bắt Buộc**:
   - Không dùng `0.000` (dùng `0` hoặc `0.0`).
   - Không dùng `key={idx}` trong danh sách lặp (luôn dùng unique ID).
   - Thẻ `<label>` bắt buộc có `htmlFor` hoặc dùng `<span>` / Radix Label.
   - Không gán tùy tiện `role="user"` hay `role="assistant"` trên thẻ HTML.
   - Imports sắp xếp theo alphabet.
5. **Tư Duy UI Mở & Kiến Trúc Điều Hướng Sâu (Master-Detail Deep Routing Pattern)**:
   - **Tuyệt đối không nhồi nhét "Monolithic Tabbed Page"**: Không gộp toàn bộ tính năng danh sách, chi tiết, chỉnh sửa chuyên sâu và quy trình wizard vào một file trang duy nhất bằng các thẻ Tab gò bó hay Dialog chật hẹp.
   - **Quy chuẩn 1 Domain = List Page + Dedicated Detail Pages**:
     - *Trang Danh Sách (Master/List View)*: Tập trung vào tổng quan thực thể (Kho tri thức, Trợ lý AI, Provider, Workflows), bộ lọc tìm kiếm, chỉ số KPI và danh sách Card/Bảng tối giản, thoáng đãng.
     - *Trang Chi Tiết Độc Lập (Dedicated Detail View)*: Khi người dùng click vào bất kỳ Card/Hàng bảng nào, **BẮT BUỘC PHẢI chuyển hướng sang trang chi tiết riêng biệt** với URL phân cấp rõ ràng (ví dụ: `/knowledge/collections/:id`, `/assistants/:id`, `/models/:id`, `/workflows/:id`).
     - *Tách File Độc Lập*: Trang chi tiết phải là một component/file riêng (ví dụ `collection-detail-page.tsx`, `assistant-detail-page.tsx`), không viết chung thành khối nghìn dòng trong trang danh sách.
   - **Tiêu chuẩn bắt buộc trên Trang Chi Tiết**:
     - *Thanh điều hướng quay lại & Breadcrumb*: Có nút quay lại (`ArrowLeft`) và breadcrumb phân cấp rõ ràng (`Kho Tri Thức / [Tên Bộ Sưu Tập]`).
     - *Header & Action Toolbar*: Tên đối tượng, huy hiệu trạng thái và các nút thao tác đặc thù (Chỉnh sửa, Xóa, Đồng bộ, Test,...).
     - *Không gian hiển thị sâu*: Tận dụng toàn bộ màn hình để bố trí 2-3 cột dữ liệu sâu (tài liệu con, chunks, vector embedding, facts số hóa, lịch sử hoạt động) mà không bị gò bó.
     - *Deep Linking*: Người dùng có thể F5, bookmark hoặc chia sẻ URL trực tiếp tới đúng đối tượng.
6. **Trải Nghiệm AI Streaming & Anti-Hallucination**:
   - Kết nối SSE qua `useRAGStream` hiển thị token mượt mà, kèm hiệu ứng *Thinking Indicator*.
   - Khối cuộn `MessageScroller` có cơ chế tự động ghim đáy và tạm dừng thông minh khi người dùng cuộn lên đọc lại tài liệu cũ.
   - Mọi câu trả lời có dữ liệu RAG phải hiển thị nhãn trích dẫn dẫn tới `CitationSheet` đối soát văn bản gốc.
7. **Kiểm chứng giao diện theo phạm vi**:
   - Dùng [bảng kiểm chứng chung](../../../rules/verification.md); build không chứng minh layout, quyền hay hành vi API đã đúng.
   - Không chạy backend suite cho thay đổi giao diện thuần túy.

8. **Quy Chuẩn Lucide Icons & Cấm Tuyệt Đối Emoji Trong Giao Diện Quản Trị (Lucide Icon & Zero-Emoji Standard)**:
   - **100% `lucide-react`**: Toàn bộ icon trong toàn bộ dự án bắt buộc phải nhập từ thư viện `lucide-react`. Tuyệt đối cấm tự tạo icon SVG ad-hoc hoặc sử dụng thư viện icon khác (FontAwesome, Material Icons, v.v.).
   - **Tuyệt đối CẤM Emoji trong UI**: Cấm sử dụng các emoji ký tự (`⚡`, `📖`, `🔤`, `💾`, `⚙️`, `✓`, `❌`, `🔥`, v.v.) trên các thành phần giao diện quản trị (topbar, buttons, badges, KPI chips, table cells). Mọi chỉ số và hành động phải dùng icon Lucide thanh lịch tương ứng (`Zap`, `BookOpen`, `Type`, `HardDrive`, `Cpu`, `Check`, `X`, `Flame`).
   - **Quy chuẩn kích thước & độ dày nét (Stroke & Size)**:
     - Navigation / Sidebar items: `size-4` (16px), `strokeWidth={1.5}` hoặc `1.75`.
     - Compact toolbar / Table actions: `size-3.5` (14px).
     - Feature headers / Hero tiles: `size-5` (20px) đặt trong container nền bo tròn `size-8 rounded-lg bg-primary/10 text-primary`.
   - **Màu sắc ngữ nghĩa**: Luôn áp dụng semantic classes (`text-muted-foreground`, `text-primary`, `text-success`, `text-destructive`), không để icon mang màu thô không kiểm soát.
9. **Quy Chuẩn Tận Dụng Component UI Sẵn Có & Điều Kiện Tạo Mới (Component Reuse First Policy)**:
   - **Tận dụng 100% Component có sẵn**: Trước khi viết bất kỳ form nhập liệu, danh sách, modal hay bảng nào, Agent bắt buộc phải tra cứu thư mục `src/components/ui/`. Nếu component tương ứng đã tồn tại (ví dụ: `Checkbox`, `Switch`, `Button`, `Dialog`, `Select`, `Input`, `Badge`, `Tabs`, `Table`, `Sheet`, `Popover`, `Tooltip`, `DropdownMenu`), **bắt buộc phải import và sử dụng trực tiếp**, kết hợp với các helpers quản trị tại `src/components/admin/` (`Field`, `EmptyState`, `KpiMetric`, `StatusBadge`, `ConfirmDialog`, `FileUpload`).
   - **Tuyệt đối CẤM tự ý viết lại hoặc dùng HTML thô**: Không dùng thẻ HTML nguyên bản (như `<input type="checkbox">`, `<button className="...">`, `<select>`) hoặc tự code lại logic trùng lặp.
   - **Quy trình khi thực sự cần Component mới**:
     - *Bước 1 (Kiểm tra)*: Xác nhận chắc chắn trong `src/components/ui/` chưa có component đáp ứng nghiệp vụ.
     - *Bước 2 (Kiến trúc chuẩn)*: Xây dựng component mới đặt tại `src/components/ui/<name>.tsx` dựa trên Radix UI Primitive hoặc cấu trúc chuẩn shadcn/ui.
     - *Bước 3 (Đồng bộ Token & Accessibility)*: Tuân thủ token màu OKLCH (`border-primary`, `bg-primary`, `text-primary-foreground`, `focus-visible:ring-ring`), hỗ trợ Dark/Light mode, `forwardRef`, điều hướng bàn phím, và WAI-ARIA.
     - *Bước 4 (Export toàn cục)*: Export component rõ ràng trong file để mọi trang, modal khác có thể tái sử dụng ngay.
10. **Quy Chuẩn Thiết Kế Đa Thiết Bị & Responsive (Cross-Device & Responsive Standard)**:
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
11. **Quy Chuẩn Đặt Tên Nút Bấm & Nhãn Điều Khiển Ngắn Gọn (Concise Action Labels & Microcopy Standard)**:
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
12. **Quy Chuẩn Thanh Tìm Kiếm & Bộ Lọc Liền Mạch (Seamless & Borderless Filter Bar Pattern)**:
    - **Cấm Tuyệt Đối Đóng Khung Viền Kép (Zero Double-Border / Box-in-Box)**:
      - Tuyệt đối **không bọc cụm tìm kiếm và bộ lọc (`Filter Bar`) trong các thẻ Card/Box có viền bao quanh và màu nền riêng** (như `bg-card p-3 rounded-lg border border-border shadow-2xs`).
      - *Lý do*: Bản thân các thành phần điều khiển con (`Input`, `SelectTrigger`, nút chuyển View mode `Button`) đã mang đường viền mảnh chuẩn (`border-input` / `border-border`) và nền riêng (`bg-background`). Việc bọc thêm một khung viền bên ngoài tạo ra hiệu ứng "hộp trong hộp" (box-in-box) thừa thãi, gây cảm giác chật chội, nặng nề và làm mất đi vẻ thanh thoát hiện đại.
    - **Chuẩn Bố Cục Liền Mạch (Seamless Layout Standard)**:
      - Container của thanh bộ lọc chỉ làm nhiệm vụ căn chỉnh Flex/Grid:
        ```tsx
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        ```
      - Thanh điều khiển đặt trực tiếp trên nền trang (`bg-background`), tạo khoảng thở thoáng đãng, tự nhiên phân tách giữa khu vực KPI Summary Cards và danh sách Cards/Bảng dữ liệu bên dưới.
      - Duy trì khả năng co giãn linh hoạt trên Mobile: Sử dụng `grid grid-cols-2 gap-2 sm:flex` với `w-full sm:w-[155px]` cho các dropdown lọc để chống tràn màn hình.
13. **Quy Chuẩn Thẻ Thống Kê & Đếm Tinh Gọn (Zero-Fluff Counter & Minimal KPI Strip)**:
    - **Tôn Chỉ Trọng Tâm & Dữ Liệu Cao (High Data-to-Ink Ratio)**:
      - Thẻ thống kê (`KpiMetric` / Counter Card) sinh ra để người dùng nắm bắt chỉ số tức thì trong 1 giây.
      - Bắt buộc tuân thủ cấu trúc tối giản 3 phần: **Tiêu đề chỉ số** (`label`) + **Icon Lucide thanh lịch** (`icon`) + **Con số định lượng lớn** (`value`) (kèm huy hiệu trạng thái/chênh lệch `delta` nếu có).
    - **Tuyệt Đối CẤM Phụ Đề Dư Thừa & Lặp Lại (Zero Redundant Helper Text)**:
      - ❌ **Cấm tuyệt đối lặp lại con số**: Đã có con số lớn `14` ở trên thì bên dưới cấm lặp lại phụ đề kiểu `14 manifests chuẩn Core`.
      - ❌ **Cấm phụ đề sáo rỗng hoặc liệt kê vụn vặt**: Nghiêm cấm các chuỗi như `Đầu vào, AI, RAG, HITL...`, `Tương thích QNU AI Core`, `Cổng Input & Output schemas`.
      - ✅ **Quy tắc vàng**: Nếu tiêu đề và con số đã tự thân rõ nghĩa, **bắt buộc bỏ hoàn toàn thuộc tính `helper`** (để `helper={undefined}`). Khối KPI phải giữ chiều cao gọn gàng, thoáng đãng, không chiếm dụng không gian dọc của trang. Chỉ dùng `helper` khi thực sự cần chú thích mốc thời gian hoặc công thức đặc thù (ví dụ: `24 giờ qua` hoặc `Theo chuẩn UTC+7`).
14. **Quy Chuẩn Bố Cục Thanh Tìm Kiếm & Bộ Lọc Phân Tách Hai Phía (Left-Right Split Filter Bar Pattern)**:
    - **Bố Cục Phân Tách Hai Phía (Left: Search — Right: Filters)**:
      - Khi thiết kế thanh tìm kiếm và bộ lọc trên danh sách thực thể, bắt buộc phân tách 2 đầu rõ ràng bằng `justify-between`:
        ```tsx
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        ```
      - **Bên trái (`justify-start`)**: Chỉ đặt duy nhất ô nhập liệu tìm kiếm (`Input`), có icon kính lúp bên trái và nút xóa nhanh `×` bên phải khi có ký tự.
      - **Bên phải (`justify-end`)**: Nhóm toàn bộ các điều khiển lọc (`Select` phân loại, `Select` trạng thái, nút `Đặt lại` bộ lọc khi active).
    - **Khống Chế Độ Rộng Ô Tìm Kiếm (Zero Full-Width Desktop Search Stretch)**:
      - ❌ **Tuyệt đối CẤM dùng `flex-1` đơn độc trên ô tìm kiếm**: Khi không giới hạn độ rộng, ô tìm kiếm trên màn hình Desktop sẽ bị kéo giãn tới 800px–1000px, tạo ra khoảng trống mênh mông bất hợp lý và đẩy các nút lọc dạt xa về mép phải màn hình.
      - ✅ **Độ rộng chuẩn Desktop**: Bắt buộc khống chế trong khoảng `sm:w-72 lg:w-80` hoặc `sm:max-w-xs` (288px – 320px).
      - ✅ **Độ rộng thích ứng Mobile (`< 640px`)**: Tự động co giãn `w-full` ở trên, cụm bộ lọc chuyển xuống dưới chia 50/50 (`grid grid-cols-2 gap-2 w-full`).
    - **Placeholder Súc Tích Chuẩn Microcopy (Concise Placeholder Standard)**:
      - ❌ **Cấm viết cả câu dài**: `Tìm theo tên hiển thị, mã type (query.rewrite...), mô tả...`.
      - ✅ **Chỉ dùng 2 đến 4 từ**: `Tìm kiếm node...`, `Tìm theo tên, mã...`, `Tìm kiếm trợ lý...`.
15. **Quy Chuẩn Nút Chuyển Đổi Chế Độ Xem (View Mode Switcher / Grid-Table Toggle Standard)**:
    - **Bắt Buộc Dùng `<ViewModeToggle />` Dùng Chung**:
      - Mọi màn hình danh sách có hỗ trợ chuyển đổi giữa dạng thẻ lưới và dạng bảng/danh sách (`/document-types`, `/knowledge`, `/capabilities/nodes`, `/assistants`, v.v.) **BẮT BUỘC PHẢI SỬ DỤNG component dùng chung** `<ViewModeToggle value={viewMode} onChange={setViewMode} />` từ `@/components/ui/view-mode-toggle`.
      - **Cấm Tuyệt Đối Vibe Coding Tự Chế Style Lệch Pha**: Nghiêm cấm việc mỗi lần vibe coding lại tự viết `<div><Button>...</Button></div>` với style khác nhau (như trang thì dùng nút chữ "Thẻ / Bảng", trang thì dùng `variant="default"` màu đen/nổi quá mức, trang thì dùng `rounded-sm` hay `size-7`).
    - **Thiết Kế Chuẩn Mực (Gold Standard theo `/document-types`)**:
      - **Container**: `flex items-center gap-1 border border-border rounded-md p-0.5 bg-muted/30 shrink-0`.
      - **Nút con (Buttons)**: `variant={isActive ? "secondary" : "ghost"}` `size="sm"` `className="h-7 w-7 p-0"`. Trạng thái đang chọn có nền `secondary` nhẹ nhàng, tinh tế; trạng thái không chọn là `ghost`.
      - **Icon**: `<LayoutGrid className="size-3.5" />` (cho Grid) và `<List className="size-3.5" />` (cho Table/List) từ `lucide-react`.
      - **Accessibility & Tooltip**: Có thuộc tính `title` tiếng Việt rõ nghĩa: "Xem dạng thẻ lưới" và "Xem dạng danh sách bảng".
      - **Tính Tương Thích Type Cao**: `ViewModeToggle` tự động hỗ trợ cả hai kiểu type phổ biến trong dự án: `"grid" | "table"` hoặc `"grid" | "list"`.

---
