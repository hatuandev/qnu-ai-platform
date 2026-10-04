# NHẬT KÝ LÀM VIỆC: PHIÊN #258 — CHUẨN HÓA TOÀN DIỆN HỆ THỐNG UI RULES (AGENTS.MD): BÁN KÍNH BO GÓC, ZERO RAW BUTTONS, KHỬ TRÙNG LẶP CITATION & SIDEBAR 256PX

- **Thời gian**: 2026-10-04 18:20 (UTC+7)
- **Kỹ sư / AI Agent**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu phiên (Goals)**:
  1. Rà soát và chuẩn hóa 100% giao diện người dùng theo các quy tắc thiết kế nghiêm ngặt trong `AGENTS.md` (Quy định 1.8, 4.3, 4.8, 4.9) và skill `qnu-frontend-architect`.
  2. **Quy chuẩn Bán kính bo góc (Rule 4.3 & 3.2)**:
     - Tất cả các nút bấm, ô nhập liệu, điều khiển: Chuẩn hóa bắt buộc 6px (`rounded-md` / `--radius-control`), loại bỏ các bo góc ad-hoc `rounded-xl`, `rounded-2xl`, `rounded-3xl` không đúng vị trí.
     - Các bề mặt thẻ, hộp thoại (Cards/Dialogs): Chuẩn hóa 8px (`rounded-lg` / `--radius-surface`).
     - Micro-tags / Huy hiệu nhỏ: 4px (`rounded-micro`).
  3. **Chuẩn hóa Kích thước Chiều rộng Thanh bên Sidebar (Rule 4.3)**:
     - Đưa chiều rộng Sidebar Desktop về đúng quy chuẩn `w-64` (256px) thay vì `w-72` (288px).
     - Điều chỉnh thông số animation trong `motion.aside`: `width: isOpen ? 256 : 64`.
  4. **Triệt tiêu Thẻ HTML Thô Sơ (Zero Raw Native Form Elements — Rule 1.8 & 4.9)**:
     - Thay thế toàn bộ `<button>` thô bằng các thành phần Primitives Radix UI / shadcn (`Button variant="outline"`, `Button variant="ghost"`).
     - Áp dụng cho: Nút bấm minh chứng trích dẫn (Citations), Nút chip gợi ý câu hỏi liên quan, Nút tải Artifacts, Nút chọn Trợ lý ảo (Assistant Dropdown Trigger), và Nút xóa tìm kiếm (`X`).
  5. **Tối ưu Hiển thị Minh chứng Trích dẫn (Anti-Hallucination Citations — Rule 1.4 & 4.1)**:
     - Khử trùng lặp (Deduplication): Áp dụng `useMemo` gom nhóm theo `title` và `document_name`, ngăn chặn việc một tài liệu sinh ra 5-6 huy hiệu giống hệt nhau làm rối mắt giao diện.
     - Ẩn triệt để mã ID nội bộ backend bị rò rỉ: Lọc bỏ các chuỗi dạng `(doc_1772)`, `(doc_5058)`, chỉ hiển thị Điều/Khoản hợp thức nếu có.
     - Tinh giản màu sắc: Chuyển từ các khối màu xanh lá đậm gắt (`bg-emerald-600`) sang thiết kế học thuật tinh tế (`border-border/80 bg-background text-foreground/85` kèm huy hiệu chỉ số nhỏ `[1]`, `[2]`).
  6. **Đồng bộ Thanh Thao tác (Action Toolbar)**:
     - Thay thế các nút chữ bất đối xứng ("Sao chép", "Tạo lại") bằng dãy nút icon đồng dạng `size-7 rounded-md` kèm Radix `Tooltip` chuẩn mực (`Copy`, `RotateCcw`, `ThumbsUp`, `ThumbsDown`).

---

## 1. Chi Tiết Các Tệp Mã Nguồn Đã Chỉnh Sửa

### 1.1. `frontend2/src/components/ai/chat-message.tsx`
- **Căn cứ minh chứng (Citations)**:
  - Bổ sung hàm lọc `uniqueCitations` loại bỏ các trích dẫn trùng lặp.
  - Thêm biểu thức kiểm tra regex `isRawId` để ẩn các chuỗi ID backend `doc_[a-f0-9]+`.
  - Thay `<button>` thô bằng `<Button variant="outline" size="sm">` chuẩn `rounded-md` và độ cao `h-7`.
- **Gợi ý câu hỏi tiếp theo (Suggested Questions)**:
  - Thay `<button>` thô bằng `<Button variant="outline" size="sm">` chuẩn `rounded-md` và độ cao `h-8`.
- **Thanh thao tác (Actions Toolbar)**:
  - Chuẩn hóa thành cụm nút icon `size-7 rounded-md` có Tooltip giải thích chi tiết, đồng bộ trải nghiệm với Google Gemini & ChatGPT.

### 1.2. `frontend2/src/features/chat/chat-history-sidebar.tsx`
- **Quy chuẩn Chiều rộng**: Chuyển từ `288px` (`w-72`) sang chuẩn `256px` (`w-64`) theo đúng Rule 4.3 (`width: isOpen ? 256 : 64`).
- **Quy chuẩn Bán kính**:
  - `rounded-xl` trên từng dòng lịch sử chat -> chuyển thành `rounded-md`.
  - `rounded-lg` trên ô nhập đổi tên nhanh -> chuyển thành `rounded-md`.
  - `rounded-lg` trên nút tìm kiếm và nút đóng thanh bên -> chuyển thành `rounded-md`.
  - `rounded-lg` trên ô nhập tìm kiếm -> chuyển thành `rounded-md`.
  - `rounded-2xl` trên icon rỗng -> chuyển thành `rounded-lg` (surface).
  - `rounded-lg` trên các nút chân trang -> chuyển thành `rounded-md`.
- **Zero Raw Button**: Thay nút xóa từ khóa tìm kiếm `<button>` thành `<Button variant="ghost" size="icon">`.

### 1.3. `frontend2/src/features/chat/public-chat-view.tsx`
- **Quy chuẩn Topbar**: Chuyển các nút điều khiển di động, nút tải markdown và nút đổi giao diện sáng/tối từ `rounded-lg` sang `rounded-md`.
- **Dropdown chọn Trợ lý**: Chuyển thẻ `<button>` thô sang `<Button variant="ghost" className="h-9 px-2 gap-2 rounded-md ...">`.
- **Cards Gợi ý Câu hỏi (Gemini Empty State)**: Chuyển bo góc `rounded-2xl` sang `rounded-lg` (`--radius-surface` = 8px) đúng quy chuẩn thiết kế thẻ giao diện.

### 1.4. `frontend2/src/features/chat/public-chat-portal.tsx`
- Khắc phục vi phạm Biome Rule `lint/suspicious/noArrayIndexKey`: Thay thế `key={idx}` bằng `key={q}` duy nhất trong danh sách câu hỏi mẫu.

---

## 2. Kết Quả Kiểm Thử & Xác Minh (Verification)

1. **Biome Linter Check**:
   ```bash
   .\node_modules\@biomejs\cli-win32-x64\biome.exe check src/features/chat/ src/components/ai/chat-message.tsx
   ```
   - **Kết quả**: `Checked 4 files in 41ms. No fixes applied.` -> **0 lỗi Biome (100% Clean)**.

2. **TypeScript Compilation (Typecheck)**:
   ```bash
   bun.exe node_modules\typescript\bin\tsc --noEmit
   ```
   - **Kết quả**: **0 lỗi biên dịch TypeScript**.

---

## 3. Bài Học & Rút Kinh Nghiệm (Lessons Learned)
- **Kỷ Luật Design Tokens Trong Vibe Coding**: Khi làm việc nhanh theo cảm hứng (Vibe Coding), rất dễ bị cuốn theo các bo góc tùy ý của Tailwind (`rounded-xl`, `rounded-2xl`, `rounded-3xl`). Việc định kỳ rà soát và "ép" toàn bộ hệ thống về đúng 2 thang đo chuẩn (`rounded-md` 6px cho điều khiển/nút bấm và `rounded-lg` 8px cho thẻ/bề mặt) giúp giao diện lập tức toát lên vẻ chuyên nghiệp, cao cấp và chuẩn mực Enterprise.
- **Tránh Rò Rỉ Tri thức Thô Từ Backend (Information Leakage)**: RAG pipeline khi trích xuất tài liệu thường gán ID mặc định nếu tài liệu không có tên điều/khoản pháp lý (`doc_1772`). Frontend cần có lớp phòng vệ hiển thị (UI Sanitization) để không làm giảm trải nghiệm của người dùng phổ thông.
- **Sức mạnh của Component Primitives**: Việc sử dụng 100% các primitives từ `@/components/ui/` (`Button`, `Badge`, `Tooltip`) bảo đảm khả năng hỗ trợ bàn phím (Keyboard accessibility), focus ring, và tương thích hoàn hảo giữa Light/Dark mode.
