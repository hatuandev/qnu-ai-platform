# Nhật Ký Làm Việc: Thiết Kế Lại Component Select & Chuẩn Hóa Bộ UI Primitives Theo Quy Chuẩn Thiết Kế QNU
**Thời gian**: 2026-09-17 17:05 (UTC+7)
**Mục tiêu**: Xử lý nguyên nhân triệt để khiến component Select bị "thô", thay thế toàn bộ thẻ native `<select>` bằng Radix UI Select nguyên khối, và tinh chỉnh nâng cấp các UI primitives (Badge, Input, Textarea, Scrollbars) theo đúng UI Rules của QNU AI Platform.

---

## 1. Nguyên Nhân Khiến Component Select Bị "Thô"
- **Thực trạng**: Trước đây, frontend sử dụng trực tiếp thẻ native HTML `<select>` và `<option>`. Trên hệ điều hành (đặc biệt là Windows/Chromium), thẻ `<option>` do cửa sổ điều khiển Win32 của hệ điều hành render:
  - Khung menu vuông vức, viền thô kệch, không nhận bo góc `border-radius`.
  - Nền lựa chọn màu xanh lam gắt (`#0066cc`), không ăn theo bảng màu chủ đạo Academic Teal (`oklch(0.46 0.13 160)`).
  - Không kế thừa font chữ Inter, vỡ bố cục khi chuyển Dark/Light mode.
  - Không hỗ trợ icon đánh dấu (check indicator), hiệu ứng mờ kính (backdrop blur) hay animation mượt mà.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Cài Đặt & Khởi Tạo `Select` Primitive (`@radix-ui/react-select`)**:
   - Tạo mới [src/components/ui/select.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ui/select.tsx) tích hợp đầy đủ:
     - `Select`, `SelectTrigger`, `SelectContent`, `SelectItem`, `SelectValue`, `SelectGroup`, `SelectLabel`, `SelectSeparator`.
     - Hỗ trợ biến thể kích thước `sizeVariant="sm"` (h-8, px-2.5, text-xs) chuyên cho các thanh toolbar/bộ lọc bảng, và `default` (h-9, text-sm) cho form chuẩn.
     - Tích hợp dấu tích chọn `Check` với màu thương hiệu `text-primary`.
     - Dropdown popover bo tròn chuẩn 8px (`rounded-lg`), đổ bóng mềm mại (`shadow-lg`), hiệu ứng fade-in & zoom mượt mà.
2. **Loại Bỏ 100% Thẻ Native `<select>` Trên Toàn Bộ Giao Diện**:
   - `collection-detail-page.tsx`: 3 bộ lọc danh mục tài liệu (Loại văn bản, Trạng thái, Mức ưu tiên) và bộ lọc tiến trình tác vụ.
   - `document-ingest-page.tsx`: Bộ chọn loại văn bản và cấu hình bộ máy OCR trong Wizard nạp tri thức.
   - `scan-studio-page.tsx`: Bộ chọn OCR engine (PyMuPDF, Docling, EasyOCR), bộ lọc vùng bounding box (Bảng, Dấu/Ký, Chữ) và modal chọn kho đích.
   - `modelops-page.tsx`: Bộ chọn loại Provider (OpenAI, Gemini, Mistral, Cloudflare,...).
   - `channels-page.tsx`: Bộ chọn Trợ lý AI mặc định cho kênh Widget nhúng.
   - `docx-nd30-editor.tsx`: Bộ chọn thể thức loại văn bản NĐ 30.
3. **Nâng Cấp Các UI Primitives Bị Thô Khác Theo UI Rules**:
   - **Thanh cuộn siêu mỏng (Sleek Scrollbars)** trong `globals.css`: Triệt tiêu thanh cuộn xám dày 16px mặc định của Windows; áp dụng scrollbar mỏng 6px bo tròn mềm mại, tự động ẩn hiện theo độ trong suốt của theme.
   - **`badge.tsx`**: Chuyển từ bo góc vuông cứng `rounded-sm` (2px) sang dạng viên thuốc `rounded-full` thanh thoát, sử dụng dải màu dịu nhẹ tinh tế (`bg-primary/10 text-primary`, `bg-emerald-500/10 text-emerald-600`, `bg-destructive/15 text-destructive`).
   - **`input.tsx` & `textarea.tsx`**: Tinh chỉnh viền focus từ ring dày đậm sang hiệu ứng ánh sáng nhẹ `focus-visible:ring-ring/20 focus-visible:border-ring transition-[color,box-shadow]` tạo chiều sâu cho form.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Biome Linter**: Check toàn bộ 78 files, **0 lỗi** (`npm run lint`).
- **TypeScript**: `tsc --noEmit`, **0 lỗi** (`npm run typecheck`).
- **Vite Production Build**: Hoàn tất thành công trong **5.68s** (`npm run build`).
- **Backend Tests**: 23/23 tests `test_knowledge.py` passed (100%).
