# NHẬT KÝ PHIÊN LÀM VIỆC #214
# Thời gian: 2026-09-24 16:55
# Nội dung: Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Loại Văn Bản (/document-types) Trên Frontend2 Chuẩn Master-Detail Deep Routing

---

## 1. Mục Tiêu Phiên Làm Việc
1. **Thiết kế và triển khai phân hệ Quản Lý Loại Văn Bản (`/document-types`)** trên nền tảng Next-Gen `frontend2` (Vite 6 + React 19 + TanStack Router + Tailwind v4 + Radix UI + Biome) tại địa chỉ `http://localhost:3000/document-types`.
2. **Hiện thực hóa chuẩn thể thức văn bản hành chính** theo **Nghị định 30/2020/NĐ-CP** và quy chế học thuật của Trường Đại học Quy Nhơn.
3. **Áp dụng kiến trúc Master-Detail Deep Routing** (Mục 4.5 của `AGENTS.md`):
   - Danh sách tổng quan Master View: `/document-types`
   - Trung tâm quản trị chi tiết Dedicated Detail View: `/document-types/:code`
4. **Bảo đảm chuẩn responsive** theo quy định (4 cards trên Desktop, 2 cards trên Tablet, 1 card trên Mobile).
5. **Đạt chuẩn kiểm thử Frontend 100%**: Biome check 0 lỗi, TypeScript typecheck 0 lỗi, Vite build phân tách bundle thành công.

---

## 2. Các Thành Phần Đã Triển Khai

### A. Định Tuyến File-Based TanStack Router (`frontend2/src/routes/`)
- [`frontend2/src/routes/document-types.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/document-types.tsx): Layout Route bọc `<Outlet />`.
- [`frontend2/src/routes/document-types.index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/document-types.index.tsx): Tuyến danh sách `/document-types/` hiển thị `DocumentTypesPage`.
- [`frontend2/src/routes/document-types.$code.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/document-types.$code.tsx): Tuyến chi tiết chuyên sâu `/document-types/:code` hiển thị `DocumentTypeDetailPage`.

### B. Màn Hình Danh Sách Master View: [`DocumentTypesPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/document-types/document-types-page.tsx)
- **Header & Action Bar**: Tiêu đề "Loại Văn Bản", nút súc tích: **"Đồng bộ"** (nạp 37+ loại văn bản chuẩn từ core) và **"Thêm loại"** (mở modal khởi tạo).
- **Dải chỉ số KPI Telemetry Strip 4 ô gộp trong Card nguyên khối**:
  1. *Tổng loại văn bản*: Tổng số thể thức CSDL chuẩn hóa.
  2. *Chuẩn NĐ 30/2020*: Số loại văn bản hành chính nhà nước (NĐ 30/2020/NĐ-CP).
  3. *Đào tạo & Học thuật*: Số lượng loại văn bản chuyên môn đào tạo, đề án tuyển sinh, học vụ.
  4. *Đang hoạt động*: Tỷ lệ thể thức đang cho phép nạp vào Kho Tri Thức.
- **Thanh công cụ Toolbar liền mạch (Seamless Filter Bar)**:
  - Ô tìm kiếm debounced theo tên hoặc mã code font mono.
  - Bộ lọc Nhóm phân loại (Dropdown 175px chống cắt chữ: Quy phạm & Nội bộ, Hành chính Điều hành, Đào tạo & Học thuật, Biểu mẫu & Tiếp nhận).
  - Bộ lọc Trạng thái (Tất cả, Đang hoạt động, Đã tạm dừng).
  - Cụm chip lọc nhanh: "Tất cả" | "Chuẩn NĐ 30" | "Tùy chỉnh".
  - Chuyển đổi chế độ xem Thẻ (Grid) / Bảng (Table).
- **Thẻ Thể Thức [`DocumentTypeCard`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/document-types/document-type-card.tsx)**:
  - Bố cục lưới responsive 4-2-1: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4`.
  - Icon chuyên ngành trong container `bg-primary/10 text-primary`, Tên thể thức, Mã code font mono, Switch bật/tắt hoạt động nhanh.
  - Badges chuẩn NĐ 30/2020 (sky), Hệ thống vs Tùy chỉnh.
  - Dải thông số kỹ thuật: Mức ưu tiên RAG (1-10), Thời hạn bảo quản văn thư, Số lượng tài liệu thực tế liên kết.
  - Nút **"Chi tiết"** outline Academic Teal và Dropdown menu (Chỉnh sửa, Sao chép mã, Xem Kho tri thức).
- **Chế độ xem Bảng dữ liệu (Data Table View)**:
  - Bọc trong `w-full overflow-x-auto`, chiều cao hàng chuẩn `h-11`.
  - Đầy đủ các cột nghiệp vụ, hỗ trợ thao tác nhanh không xô lệch giao diện.

### C. Màn Hình Điều Hành Chi Tiết: [`DocumentTypeDetailPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/document-types/document-type-detail-page.tsx)
- **Top Header**: Nút quay lại adaptive `← Danh mục`, Tên loại văn bản, Mã code font mono, Badge nhóm, Switch hoạt động trực tiếp, Nút **"Lưu"** (`Save`).
- **Bố cục 2 cột chuyên nghiệp**:
  - *Cột trái (2 spans)*:
    - Card "Thông Số Thể Thức & Phân Loại": Mã chuẩn (disabled nếu là hệ thống), Tên tiếng Việt chính quy, Nhóm phân loại (Select), Mô tả thể thức & hướng dẫn văn thư áp dụng (Textarea).
    - Card "Trọng Số Hybrid RAG & Thời Hạn Bảo Quản": Mức độ ưu tiên trích xuất RAG (Input number + Visual progress bar giải thích RRF ranking), Thời hạn bảo quản (Vĩnh viễn, 70 năm, 10 năm,...).
  - *Cột phải (1 span)*:
    - Card "Căn Cứ Pháp Lý & Xuất Xứ": Căn cứ NĐ 30/2020/NĐ-CP, Tính chất phân loại, Nguồn đồng bộ `qnu-ai-core`, Mã băm nguồn, Thời điểm đồng bộ và cập nhật.
    - Card "Tài Liệu Đang Áp Dụng": Đếm số văn bản đã bóc tách trong Kho Tri Thức và nút "Mở Kho Tri Thức".
    - Card "Vùng Nguy Hiểm (Danger Zone)": Tạm dừng / Kích hoạt lại thể thức văn bản.

### D. Modal Khởi Tạo Mới: [`CreateDocumentTypeDialog`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/document-types/dialogs/create-document-type-dialog.tsx)
- Form nhập liệu chuẩn 100% Radix/shadcn (`Input`, `Textarea`, `Select`, `Button`, `Field`).
- Tự động kiểm tra và chuẩn hóa mã code (chữ thường, số, dấu gạch dưới `_`).
- Chọn nhóm phân loại kèm mô tả chi tiết từng nhóm.
- Nhập mức ưu tiên RAG (1-10) và thời hạn lưu trữ văn thư.

---

## 3. Kết Quả Kiểm Thử Toàn Diện
- **TypeScript Typecheck**: `npm run typecheck` (`tsc --noEmit`) $\rightarrow$ **0 lỗi** toàn bộ codebase.
- **Biome Linter**: `npx @biomejs/biome check` trên 7 tệp mới $\rightarrow$ **0 lỗi, 0 cảnh báo**.
- **Vite Production Build**: `npm run build` $\rightarrow$ **Thành công 100% trong 1.58s**:
  - `dist/assets/document-types.index-BBHKxiL_.js`: 18.26 kB (gzip: 5.44 kB)
  - `dist/assets/document-types._code-IoZ484Bl.js`: 14.90 kB (gzip: 4.34 kB)
  - `dist/assets/document-type-card-rN27KRbp.js`: 5.44 kB (gzip: 1.90 kB)
