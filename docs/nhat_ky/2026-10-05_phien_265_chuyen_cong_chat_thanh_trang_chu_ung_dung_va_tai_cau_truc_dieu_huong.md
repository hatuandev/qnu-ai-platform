# Nhật Ký Phiên Làm Việc #265 — Chuyển Cổng Chat AI Thành Trang Chủ Ứng Dụng (/) & Tái Cấu Trúc Điều Hướng Hai Không Gian

- **Thời gian thực hiện**: 2026-10-05 (UTC+7)
- **Phiên số**: #265
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Tái cấu trúc tuyến đường điều hướng, chuyển đổi Cổng Trợ Lý AI Hub (`PublicChatPortal`) từ `/chat` thành Trang chủ ứng dụng chính thức (`/`), đồng bộ các liên kết đối soát và phân tách rành mạch hai không gian: Không gian Công Khai và Không gian Quản trị Studio.

---

## 1. Hiện Trạng & Yêu Cầu

- **Hiện trạng cũ**:
  - Tuyến gốc `/` bị gán cứng `<Navigate to="/dashboard" />`. Người dùng vãng lai, thí sinh hoặc sinh viên khi truy cập địa chỉ gốc bị chặn bởi màn hình đăng nhập `AuthGate` hoặc đá vào Bảng điều khiển quản trị nội bộ.
  - Cổng Trợ Lý AI Hub công khai bị "giấu" tại đường dẫn phụ `/chat`.
  - Khi đã đăng nhập, `__root.tsx` tự động redirect khỏi `/` khiến cán bộ không thể xem hoặc sử dụng Cổng Chat công khai từ trang chủ.
- **Yêu cầu & Đề xuất**:
  - Chuyển `PublicChatPortal` trở thành Trang chủ chính thức (`/`).
  - Đường dẫn `/chat` tự động redirect mượt mà về `/` để tương thích ngược 100%.
  - Phân chia kiến trúc điều hướng theo mô hình **Dual-Space Architecture**:
    - **Không gian Công khai**: Trang chủ (`/`) và Màn hình Chat chi tiết (`/chat/:slug`).
    - **Không gian Quản trị**: `/dashboard`, `/assistants`, `/knowledge`, `/models`, `/channels`, `/document-types`, `/capabilities/nodes`.
  - Cung cấp cầu nối UX hai chiều: nút chuyển đổi linh hoạt trên Header Cổng Chat (tự động nhận diện đã đăng nhập để hiển thị "Vào Bảng Điều Khiển" thay vì "Dành cho Cán bộ") và bổ sung mục "Cổng Trợ Lý AI" (`/`) vào Sidebar và Account Menu của khu vực Quản trị.

---

## 2. Chi Tiết Thay Đổi Kỹ Thuật

### 2.1. Cấu hình TanStack File-Based Routing
1. **`frontend2/src/routes/index.tsx`**:
   - Thay thế `<Navigate to="/dashboard" />` bằng việc mount trực tiếp `PublicChatPortal`.
2. **`frontend2/src/routes/chat.index.tsx`**:
   - Chuyển thành redirect `<Navigate to="/" replace />` để giữ trọn vẹn khả năng tương thích ngược cho mọi bookmark hoặc link cũ.
3. **`frontend2/src/routes/__root.tsx`**:
   - Thêm `pathname === "/"` vào danh sách `isPublicRoute`.
   - Loại bỏ `shouldRedirectToHome` và hook `useEffect` đá người dùng khỏi `/`, cho phép mọi đối tượng (kể cả cán bộ đã đăng nhập) truy cập và tương tác tự do tại Trang chủ.

### 2.2. Đồng bộ Liên kết & Cải tiến UX Cổng Chat
1. **`frontend2/src/features/chat/public-chat-portal.tsx`**:
   - Đổi liên kết Logo thương hiệu từ `/chat` về `/`.
   - Tích hợp hook `useAuth()`: Nút hành động trên Header tự động biến đổi trạng thái ngữ cảnh:
     - Chưa đăng nhập (Khách / Thí sinh): Hiển thị `Dành cho Cán bộ` $\rightarrow$ dẫn tới `/dashboard` (chuyển tiếp an toàn qua `sign-in`).
     - Đã đăng nhập (Cán bộ / Quản trị viên): Hiển thị `Vào Bảng Điều Khiển` $\rightarrow$ truy cập trực tiếp `/dashboard`.
2. **`frontend2/src/features/chat/public-chat-view.tsx`**:
   - Cập nhật toàn bộ các nút điều hướng quay lại (`ArrowLeft`, Logo link trong `PublicChatSkeleton`, nút quay lại trên Mobile Header và nút Empty State 404) chuyển hướng về `/`.
3. **`frontend2/src/features/chat/chat-history-sidebar.tsx`**:
   - Cập nhật toàn bộ các nút điều hướng "Cổng Trợ Lý" trên thanh Mini-Rail, Logo Header và Footer quay về `/`.

### 2.3. Bổ sung Cầu Nối Từ Khu Vực Quản Trị Ra Cổng Chat
1. **`frontend2/src/navigation/config.ts`**:
   - Bổ sung mục điều hướng `Cổng Trợ Lý AI` (icon `Sparkles`, đường dẫn `/`) ngay dưới nhóm `Tổng Quan` trên Sidebar Studio bên cạnh `Bảng Điều Khiển`.
2. **`frontend2/src/components/admin/account-menu.tsx`**:
   - Bổ sung mục menu `Cổng Trợ Lý AI (Trang chủ)` trong Dropdown tài khoản góc phải Topbar.

### 2.4. Điều Chỉnh Lưới Thẻ 3 Cột Trên Laptop 14 Inch & Chuẩn Hóa Tiêu Đề Thẻ Trợ Lý
1. **Khắc phục lỗi hiển thị 4 cột quá chật hẹp trên Laptop 14"**:
   - Trước đây các trang dùng `2xl:grid-cols-4`. Vì breakpoint `2xl` (1536px) trùng với độ phân giải Full HD (1920x1080) có tỷ lệ phóng to Windows (125%), màn hình laptop 14" luôn bị kích hoạt 4 cột. Sau khi trừ đi Sidebar 256px và padding, mỗi thẻ chỉ còn ~280px khiến tiêu đề bị cắt cụt ("Mô-đun trợ lý ảo hỗ...").
   - Nâng ngưỡng 4 cột từ `2xl:grid-cols-4` (1536px) lên `min-[1800px]:grid-cols-4` (chỉ dành cho màn hình Desktop lớn 24"-27"+).
   - Trên mọi dòng laptop (13", 14", 15.6" từ 1024px đến 1799px), lưới thẻ luôn hiển thị hoàn hảo **3 cột** (`lg:grid-cols-3`), mỗi thẻ rộng ~380px–420px cực kỳ thông thoáng.
   - Đồng bộ quy chuẩn này trên toàn bộ 5 phân hệ thẻ: Trợ lý AI (`assistants`), Kho tri thức (`knowledge`), ModelOps (`modelops`), Loại văn bản (`document-types`), và Thư viện DAG Nodes (`node-catalog`).
2. **Chuẩn hóa Tiêu đề Thẻ Trợ Lý (`formatAssistantDisplayName`)**:
   - Trong `AssistantCard` (`assistant-card.tsx`), áp dụng hàm chuẩn hóa hình thái học loại bỏ tiền tố dài dòng `"Mô-đun trợ lý ảo..."`:
     - Soạn thảo: `Trợ lý Soạn thảo Văn bản`
     - Khảo thí: `Trợ lý Ngân hàng Đề & Khảo thí`
     - Thư viện: `Trợ lý Thư viện & Học liệu Số`
     - Quy chế: `Trợ lý Quy chế & Học vụ`
     - Tuyển sinh: `Trợ lý Tư vấn Tuyển sinh 2026`
   - Bổ sung `title={assistant.name}` để người dùng vẫn xem được tên đầy đủ khi di chuột.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Biome Linter**:
   - Kiểm tra toàn bộ các tệp thay đổi: `Checked 6 files in 63ms. No fixes applied.` (0 lỗi, 0 cảnh báo).
2. **Vite Production Build & TypeScript Typecheck**:
   - Lệnh `npm run build` (`vite build && tsc --noEmit`) hoàn thành thành công 100% trong **2.99s**.
   - 0 lỗi TypeScript, 0 lỗi bundler.

---

## 4. Tệp Thay Đổi

- [`frontend2/src/routes/index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/index.tsx)
- [`frontend2/src/routes/chat.index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/chat.index.tsx)
- [`frontend2/src/routes/__root.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/__root.tsx)
- [`frontend2/src/features/chat/public-chat-portal.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/chat/public-chat-portal.tsx)
- [`frontend2/src/features/chat/public-chat-view.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/chat/public-chat-view.tsx)
- [`frontend2/src/features/chat/chat-history-sidebar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/chat/chat-history-sidebar.tsx)
- [`frontend2/src/navigation/config.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/navigation/config.ts)
- [`frontend2/src/components/admin/account-menu.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/admin/account-menu.tsx)
- [`frontend2/src/features/assistants/assistants-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistants-page.tsx)
- [`frontend2/src/components/assistants/assistant-card.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/assistants/assistant-card.tsx)
- [`frontend2/src/features/knowledge/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/knowledge/knowledge-page.tsx)
- [`frontend2/src/features/modelops/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/modelops/modelops-page.tsx)
- [`frontend2/src/features/document-types/document-types-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/document-types/document-types-page.tsx)
- [`frontend2/src/features/capabilities/nodes/node-catalog-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/capabilities/nodes/node-catalog-page.tsx)
