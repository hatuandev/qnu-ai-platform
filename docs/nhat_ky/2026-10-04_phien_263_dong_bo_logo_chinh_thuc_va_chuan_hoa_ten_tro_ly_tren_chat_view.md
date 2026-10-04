# NHẬT KÝ LÀM VIỆC — PHIÊN #263: ĐỒNG BỘ LOGO CHÍNH THỨC ĐH QUY NHƠN VÀ CHUẨN HÓA TÊN TRỢ LÝ TRÊN GIAO DIỆN CHAT (/chat/:slug)

- **Thời gian**: 2026-10-04 23:42
- **Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Tập tin thay đổi**:
  - `frontend2/src/features/chat/chat-history-sidebar.tsx`
  - `frontend2/src/features/chat/public-chat-view.tsx`
  - `docs/nhat_ky/2026-10-04_phien_263_dong_bo_logo_chinh_thuc_va_chuan_hoa_ten_tro_ly_tren_chat_view.md`
  - `docs/nhat_ky/README.md`
  - `docs/memory/PROJECT_CONTEXT.md`
  - `docs/WORK_LOG.md`

---

## 🎯 1. Mục Tiêu Phiên Làm Việc
1. **Đồng Bộ Logo Chính Thức ĐH Quy Nhơn Trên Header Chat (`chat-history-sidebar.tsx`)**:
   - Thay thế khối hộp màu xanh gradient mang chữ "QNU" thô sơ ở góc trên bên trái thanh bên Lịch sử (`localhost:3000/chat/:slug`) bằng container chứa Logo chính thức của Trường Đại học Quy Nhơn (`/logo.png`).
   - Container được thiết kế chuẩn mực: `size-7 shrink-0 rounded-md bg-white p-0.5 shadow-xs border border-border/60 group-hover:border-primary/50 transition-colors` với ảnh logo `size-6 object-contain`, hiển thị sắc nét trên cả Light và Dark mode.
2. **Chuẩn Hóa Tên Hiển Thị Trợ Lý Trên Thanh Tiêu Đề Chat Canvas (`public-chat-view.tsx`)**:
   - Tích hợp hàm `formatAssistantDisplayName` vào thanh chọn Trợ lý ảo (Dropdown Selector Trigger) và danh sách lựa chọn trong DropdownMenu.
   - Thay vì hiển thị tên thô từ CSDL (`"Mô-đun trợ lý ảo tư vấn tuyển sinh"`), giao diện giờ đây hiển thị tên thương hiệu sang trọng và chuẩn mực: **`"Trợ lý Tư vấn Tuyển sinh 2026"`**.
   - Đồng bộ tên chuẩn vào cả Placeholder ô nhập liệu textarea.
3. **Kiểm Thử Biome & Tuân Thủ AGENTS.md**:
   - Biome linter pass 100% (51ms), 0 lỗi, 0 cảnh báo.
   - Tuân thủ 100% UI Rules: chuẩn hóa bán kính bo góc, 0 emoji, bảo đảm nhận diện thương hiệu Academic Teal.

---

## 🔬 2. Chi Tiết Thực Hiện
- **`chat-history-sidebar.tsx`**:
  ```tsx
  <Link to="/chat" className="flex items-center gap-2 group cursor-pointer select-none text-inherit no-underline" title="Quay lại Cổng Trợ Lý QNU AI">
    <div className="flex size-7 shrink-0 items-center justify-center rounded-md bg-white p-0.5 shadow-xs border border-border/60 group-hover:border-primary/50 transition-colors">
      <img src="/logo.png" alt="Logo Trường Đại học Quy Nhơn" className="size-6 object-contain" />
    </div>
    <div className="flex items-center gap-1.5">
      <span className="font-bold text-sm tracking-tight text-foreground group-hover:text-primary transition-colors">QNU AI</span>
      <Sparkles className="size-3 text-primary/70" />
    </div>
  </Link>
  ```
- **`public-chat-view.tsx`**:
  - Áp dụng `formatAssistantDisplayName(assistant.name, assistant.code)` cho selector trigger button.
  - Áp dụng `formatAssistantDisplayName(ast.name, ast.code)` cho danh sách switch trợ lý.
  - Áp dụng cho placeholder của `Textarea`.

---

## ✅ 3. Kết Quả Kiểm Thử
- **Biome Linter**: Kiểm tra cả 2 tệp `chat-history-sidebar.tsx` và `public-chat-view.tsx` đạt **0 lỗi, 0 cảnh báo** (51ms).
- **Thẩm mỹ**: Đồng bộ nhận diện thương hiệu ĐH Quy Nhơn 100% giữa Cổng Trợ lý (`/chat`) và Màn hình hội thoại trực tiếp (`/chat/:slug`).
