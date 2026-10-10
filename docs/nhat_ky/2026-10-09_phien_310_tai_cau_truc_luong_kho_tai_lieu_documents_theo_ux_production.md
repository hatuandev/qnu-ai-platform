# Nhật Ký Phiên Làm Việc #310: Tái Cấu Trúc Luồng Kho Tài Liệu `/documents` Theo Chuẩn UX Production

- **Ngày thực hiện**: 2026-10-09
- **Người thực hiện**: AI Agent (Senior Full-Stack Architect & Enterprise AI Systems Specialist)
- **Mục tiêu**: Tái cấu trúc hoàn chỉnh giao diện và luồng nghiệp vụ trang `/documents`: hiển thị danh sách các Kho Tài Liệu, chỉ giữ một nút hành động duy nhất "Tạo Kho Tài Liệu" (bỏ nút Nhóm Tài Liệu và Tải Lên Tài Liệu), cập nhật dữ liệu tự động ngay sau khi tạo, cho phép người dùng click vào kho tài liệu để truy cập trang chi tiết kho và thực hiện tải lên tài liệu trực tiếp bên trong kho.

---

## 1. Bối Cảnh & Vấn Đề Cần Giải Quyết

Trước đây, khi người dùng truy cập route `/documents`, hệ thống hiển thị trang tài liệu phẳng kèm hai nút *"Nhóm Tài Liệu"* và *"Tải Lên Tài Liệu"*, dẫn đến:
1. Luồng nghiệp vụ bị phân mảnh: Người dùng muốn quản lý tài liệu theo từng Kho Tài Liệu độc lập (Document Groups), nhưng lại nhìn thấy các tệp lẻ tẻ và phải chuyển tiếp qua nhiều trang khác nhau.
2. Tồn tại nút tải lên tài liệu ở cấp danh mục gốc ngoài ý muốn của người dùng.
3. Khi tạo nhóm mới, hệ thống tự động chuyển trang ngay lập tức thay vì giữ người dùng ở lại trang danh sách để nhìn thấy kho tài liệu mới xuất hiện.

---

## 2. Chi Tiết Các Thay Đổi Kiến Trúc & Codebase

### A. Tái cấu trúc Route `/documents` thành Trang Quản Lý Kho Tài Liệu
- **Tệp**: `frontend/src/routes/documents.index.tsx`
  - Đổi component render từ `DocumentsPage` sang `DocumentGroupsPage`.
  - Giờ đây route `/documents` chính thức là trang quản lý các Kho Tài Liệu.
- **Tệp**: `frontend/src/routes/documents.groups.index.tsx`
  - Sử dụng TanStack Router `redirect({ to: "/documents" })` trong hook `beforeLoad` để chuyển hướng mượt mà, đồng nhất 1 URL duy nhất theo chuẩn Master-Detail Deep Routing của AGENTS.md.

### B. Nâng cấp `DocumentGroupsPage` (`frontend/src/features/documents/document-groups-page.tsx`)
1. **Header & Actions**:
   - Tiêu đề trang: **"Kho Tài Liệu"**.
   - Mô tả: *"Quản lý và tổ chức các kho tài liệu số tập trung, lưu trữ trên MinIO S3, tiền xử lý Markdown sạch và gắn động vào các Kho Tri Thức."*
   - Nút hành động duy nhất: **"Tạo Kho Tài Liệu"** (icon `Plus`), loại bỏ hoàn toàn nút *"Nhóm Tài Liệu"* và nút *"Tải Lên Tài Liệu"*.
2. **Luồng Tạo Kho Tài Liệu**:
   - Khi submit form tạo thành công: Modal đóng lại, form được reset, cache `["document-groups"]` và `["repository-stats"]` được invalidate để dữ liệu làm mới ngay lập tức.
   - **Không tự động chuyển trang**, bảo đảm kho tài liệu mới tạo lập tức xuất hiện ngay trên màn hình danh sách trước mắt người dùng.
3. **Trải nghiệm Điều hướng Master-Detail**:
   - Cả thẻ kho tài liệu (Card) và hàng trong bảng (Table Row) đều hỗ trợ click trực tiếp để điều hướng vào trang chi tiết `/documents/groups/:groupId`.
   - Các nút chỉnh sửa (Pencil) và xóa (Trash2) được gắn `e.stopPropagation()` để tránh kích hoạt điều hướng ngoài ý muốn.
4. **Hỗ Trợ Hai Chế Độ Xem (ViewModeToggle)**:
   - Tích hợp chuẩn `<ViewModeToggle value={viewMode} onChange={setViewMode} />` theo quy định AGENTS.md.
   - Chế độ Grid: Thẻ kho tài liệu sang trọng kèm chips trạng thái (`ready`, `đang xử lý`, `lỗi`).
   - Chế độ Table: Bảng danh sách chi tiết, đầy đủ thông tin tên kho, mô tả, số lượng tệp, trạng thái, ngày cập nhật và cụm thao tác nhanh.
5. **EmptyState**:
   - Hiển thị thông điệp *"Chưa có kho tài liệu nào"*.
   - Nút hành động: *"Tạo Kho Tài Liệu Đầu Tiên"*.

### C. Đồng Bộ Trang Chi Tiết Kho Tài Liệu (`document-group-detail-page.tsx`)
- Nút quay lại: `<ArrowLeft className="size-3.5" /> Về Kho Tài Liệu` $\rightarrow$ điều hướng về `/documents`.
- Breadcrumb phân cấp: `Kho Tài Liệu / [Tên Kho Tài Liệu]`.
- Nút nạp tài liệu trên Action Toolbar và EmptyState: Chuẩn hóa thành **"Tải Lên Tài Liệu"** (icon `Upload`).

---

## 3. Kết Quả Kiểm Thử & Quality Gate

1. **Vite Build & TypeScript Typecheck**:
   ```bash
   npm run build
   ```
   - **Kết quả**: 3,833 modules transformed, bundle đóng gói thành công trong 5.42s, **0 lỗi TypeScript, 0 lỗi biên dịch (Exit code 0)**.
2. **Biome Linter & Formatter**:
   ```bash
   npx @biomejs/biome check --write src/features/documents/document-groups-page.tsx ...
   ```
   - **Kết quả**: **0 lỗi Biome**, toàn bộ import và style tokens OKLCH tuân thủ chuẩn 100%.
3. **Git Whitespace & Format**:
   - `git diff --check` đạt chuẩn, không có lỗi thụt lề hay khoảng trắng thừa.

---

## 4. Bài Học Rút Ra
- Luôn lắng nghe chính xác mô hình tinh thần (Mental Model) của người dùng: đối với người dùng, khái niệm "Kho Tài Liệu" cần được tổ chức phân cấp rõ ràng (Kho $\rightarrow$ Chi Tiết Kho $\rightarrow$ Tải Tài Liệu Vào Kho) thay vì trộn lẫn tài liệu phẳng ra màn hình chính.
- Việc kết hợp chặt chẽ TanStack Router deep routing với Radix UI Primitives tạo ra trải nghiệm người dùng tự nhiên, mượt mà và đúng chuẩn Enterprise AI Platform.
