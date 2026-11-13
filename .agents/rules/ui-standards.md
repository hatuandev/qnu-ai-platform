# Quy Chuẩn Thiết Kế & Vibe Giao Diện QNU AI Platform (Mandatory UI Vibe Rules)

Tài liệu này là **quy tắc bắt buộc (Hard Rule)** cho mọi AI Model (Claude, Gemini, GPT/Codex, Cursor, Windsurf, Antigravity, v.v.) khi tạo mới, chỉnh sửa hoặc "vibe coding" giao diện trên nền tảng `qnu-ai-platform` (`frontendV2/`).

---

## 1. Kiến Trúc Trang & Thứ Bậc Thị Giác (Page Anatomy & Visual Hierarchy)

1. **Bắt buộc dùng `<PageHeader />`**:
   - Mọi trang danh sách hoặc trang chức năng phải mở đầu bằng `<PageHeader eyebrow="..." title="..." description="..." actions={...} />` từ `@/components/admin/page-header`.
   - `description` ngắn gọn 1 câu nói rõ giá trị nghiệp vụ; **cấm** viết câu giải thích cơ chế kỹ thuật thừa thãi (ví dụ: *"Đường dẫn URL sẽ giữ lựa chọn khi tải lại trang"*).
2. **Quy tắc "1 Primary CTA" trên toàn màn hình**:
   - Tại một thời điểm, mỗi màn hình chỉ có **tối đa 1 nút Primary (`variant="default"` nền xanh Teal)** cho hành động quan trọng nhất của trang (ví dụ: `Tạo kho`, `Tải tài liệu`, `Bắt đầu bóc tách`, `Lưu thay đổi` khi có bản nháp).
   - Các hành động cấp 2 trên thanh Header dùng `variant="outline"` (tối đa 2–3 nút).
   - Toàn bộ hành động phụ hoặc ít dùng (`Đổi tên`, `Di chuyển`, `Bóc tách lại`, `Tải phiên bản mới`, `Dùng để biên soạn`, `Lưu trữ`, `Xóa`) **bắt buộc gom vào duy nhất 1 menu `⋯` (`DropdownMenu` với icon `MoreHorizontal`)**.

---

## 2. Cấm Rải Nút Bấm & Quy Tắc "1 Menu `⋯` Duy Nhất" (Zero Button Sprawl)

1. **Cấm rải `<Button>` vào từng Card hoặc từng dòng Table**:
   - ❌ **Nghiêm cấm**: Đặt hàng loạt nút `<Button variant="outline">` hoặc `<Button variant="default">` (*Xem*, *Chi tiết*, *Bóc tách*, *Sửa*, *Xóa*, *Quản lý*) lặp đi lặp lại dưới đáy mỗi Card hoặc ở cột cuối của mỗi dòng Table.
   - ✅ **Chuẩn mực**:
     - Tiêu đề Card / Dòng Table là `<Link>` trực tiếp để mở trang chi tiết (`hover:text-primary`).
     - Footer của Card chỉ hiển thị metadata nhẹ nhàng (Badge trạng thái, số lượng, dung lượng) và một liên kết chữ tinh gọn (`Mở kho ▸`, `Đối chiếu ▸`, `Chi tiết ▸`).
     - Góc phải trên của Card hoặc cột cuối của Table chỉ đặt **duy nhất 1 nút icon `⋯` (`MoreHorizontal`, `variant="ghost"`, `size="sm"`, `className="size-7 p-0"`)** chứa tất cả thao tác quản lý và vòng đời (Lưu trữ / Xóa).
2. **Tuyệt đối cấm đặt 2 nút menu `⋯` hoặc `Quản lý` đứng cạnh nhau**:
   - Mọi thao tác vòng đời (`LifecycleActionDialog`: Lưu trữ, Khôi phục, Xóa) phải được tích hợp thẳng vào chung `DropdownMenu` của đối tượng đó (ngăn cách bằng `<DropdownMenuSeparator />`), không bao giờ render 2 `DropdownMenuTrigger` rời rạc trên cùng một Card/Row.

---

## 3. Cấm "Hộp Trong Hộp" & Viền Kép (Zero Box-in-Box / Double-Border)

1. **Thanh công cụ & Bộ lọc phẳng (Flat Filter Bar)**:
   - ❌ **Nghiêm cấm**: Bọc thanh tìm kiếm, breadcrumb thư mục, bộ chọn trang hoặc `<ViewModeToggle />` trong một khung `<Card>` hay `<div className="rounded-xl border bg-card p-3 shadow-2xs">`.
   - ✅ **Chuẩn mực**: Đặt trực tiếp trên nền trang với bố cục phẳng:
     ```tsx
     <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 pb-2 border-b border-border/60">
     ```
   - Ô tìm kiếm (`DebouncedSearchInput` / `Input`) bên trái giới hạn độ rộng `w-full sm:w-64` hoặc `sm:w-80` (cấm dùng `flex-1` kéo dài toàn màn hình Desktop). Cụm lọc và `<ViewModeToggle />` nằm bên phải.
2. **Cấm bọc `<Card>` lớn bên ngoài một lưới `<Card>` con**:
   - Khi hiển thị danh sách dạng lưới (`grid gap-4 sm:grid-cols-2 lg:grid-cols-3`), đặt lưới trực tiếp trên nền trang; chỉ dùng `<Card>` đơn lẻ khi hiển thị trạng thái rỗng (`EmptyState`) hoặc bảng (`Table`).

---

## 4. Tỷ Lệ Dữ Liệu / Mực In Cao & Cấm Rò Rỉ Mã Kỹ Thuật (High Data-to-Ink & Zero Tech Leak)

1. **Ẩn toàn bộ ID & Mã kỹ thuật khỏi giao diện người dùng**:
   - ❌ **Nghiêm cấm**: Hiển thị các mã nội bộ như `ws_4e10f76db135`, `col_4f7ffd85ceba`, `#v_p001_b001`, hoặc nhãn loại khối thô `text` / `paragraph` trên giao diện làm việc của người dùng.
   - Chỉ hiển thị tên định danh có nghĩa nghiệp vụ; mã kỹ thuật chỉ xuất hiện trong tab `JSON` chuyên biệt hoặc hộp thoại `Raw JSON`.
2. **Không lặp lại thông tin trùng lặp trên Card**:
   - Trong thẻ tài liệu, nếu tiêu đề (`title`) đã hiển thị tên tệp, không in lặp lại dòng `file_name` giống hệt ngay bên dưới; thay bằng dòng metadata gọn gàng: `PDF · v1 · 18.8 KB`.
3. **Nhãn `<TabsTrigger>` tối giản, cấm gắn số đếm thừa**:
   - ❌ `Nội dung (36)`, `Kết quả (36 khối)`, `Danh sách mô hình (10)`
   - ✅ `Nội dung`, `Markdown`, `JSON`, `Mô hình`
4. **Dải thống kê KPI (`KpiMetric`) tinh gọn**:
   - Chỉ đặt `label`, `value` và `icon`. Bỏ hoàn toàn `helper` nếu chỉ lặp lại ý của `label`.

---

## 5. Chuẩn Giao Diện Đối Chiếu & Hiệu Đính Tài Liệu (Document Studio & Review Canvas)

1. **Khung xem bản gốc (Left Pane — Original Preview)**:
   - Mặc định ở chế độ **Vừa chiều ngang (`Fit-to-Width` — `w-full max-w-full h-auto`)** để văn bản đọc rõ ngay khi mở trang, kèm nút chuyển nhanh sang `Trọn trang` (`Fit-to-Page`) và phóng to/thu nhỏ.
   - Hiển thị tệp Word (`.docx`) gốc bằng `docx-preview`. Khi lượt bóc tách có `pagination=document`, đối chiếu theo nội dung Word. PDF giữ điều hướng theo trang.
2. **Mặt giấy hiệu đính liền mạch (Right Pane — Document Sheet Canvas)**:
   - ❌ **Nghiêm cấm**: Đóng khung từng dòng/đoạn văn ngắn thành hàng chục hộp `<Card>` rời rạc với badge `text` và nút `Sửa` cố định làm nát mạch văn bản.
   - ✅ **Chuẩn mực**: Trình bày toàn bộ các đoạn văn và bảng biểu của trang trên một **mặt giấy liền mạch (`bg-card border rounded-xl p-6 shadow-2xs`)** giữ đúng nhịp điệu văn bản hành chính/học thuật.
   - Khi di chuột (`group-hover`) vào đoạn văn mới làm nổi nhẹ nền (`hover:bg-muted/50`) và hiện nút `Sửa` ở góc phải. Đoạn đã hiệu đính được đánh dấu bằng vạch màu hổ phách bên trái (`border-l-2 border-amber-500 bg-amber-500/10`).
3. **Bộ chuyển trang gọn gàng**:
   - Dùng cụm điều hướng phẳng `Trang trước` · `Trang [ 1 ] / N` · `Trang sau`, không rải hàng chục nút số trang gây tràn thanh công cụ.

---

## 6. Tái Sử Dụng 100% Primitives & `<ViewModeToggle />`

- **100% `<ViewModeToggle />`**: Mọi trang danh sách có chuyển đổi Thẻ Lưới / Bảng bắt buộc dùng:
  ```tsx
  import { ViewModeToggle } from "@/components/ui/view-mode-toggle";
  <ViewModeToggle value={viewMode} onChange={setViewMode} />
  ```
- **100% Semantic Tokens & Lucide Icons**:
  - Chỉ dùng token màu trong `tokens.css` (`bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `text-primary`, `border-border`).
  - Chỉ dùng icon từ `lucide-react`; **tuyệt đối cấm dùng emoji** trong UI quản trị.
