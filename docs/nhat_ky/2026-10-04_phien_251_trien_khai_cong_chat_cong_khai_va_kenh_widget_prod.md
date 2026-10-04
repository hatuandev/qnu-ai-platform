# Nhật Ký Phiên Làm Việc — 2026-10-04 (Phiên 251)
## Triển Khai Kế Hoạch Bản Production: Cổng Chat Công Khai & Kênh Phân Phối Web Widget

- **Thời gian**: 2026-10-04 13:42 - 13:54 (ICT)
- **Vai trò**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xây dựng lộ trình tổng thể đưa QNU AI Platform lên bản Production; hoàn thành ngay Sprint 1 (Cổng Chat Công Khai độc lập cho sinh viên/thí sinh) và Sprint 2 (Trang quản lý Kênh phân phối Web Chat Widget CDN kèm Live Preview 1:1).

---

### 1. Bối Cảnh & Vấn Đề

1. **Nhu cầu phát hành Production**:
   - Chatbot trước đây chỉ nằm trong màn hình Studio quản trị (`/assistants/:id?tab=playground`), chưa có cổng chat độc lập để người dùng cuối (thí sinh tuyển sinh, sinh viên, cán bộ) truy cập trực tiếp mà không cần đăng nhập.
   - Kênh Web Chat Widget nhúng website trường (`qnu.edu.vn`) chưa có trang quản lý cấu hình tập trung và Live Preview trực quan cho cán bộ quản trị.
2. **Kế hoạch chuyển đổi Enterprise Identity & RBAC**:
   - Hệ thống cần chấm dứt cơ chế Dev Access Gate (dùng chung 1 mật khẩu), chuẩn bị kiến trúc CSDL PostgreSQL chuẩn cho `users`, `roles`, `permissions` đa phòng ban.

---

### 2. Các Công Việc & Thay Đổi Đã Thực Hiện

#### A. Lập Kế Hoạch Chi Tiết Đạt Chuẩn Production
- Đã xây dựng bản kế hoạch tổng thể lưu tại artifact: [`ke_hoach_phat_hanh_chatbot_va_quan_ly_user_rbac_prod.md`](../../ke_hoach_phat_hanh_chatbot_va_quan_ly_user_rbac_prod.md) bao gồm:
  - Sơ đồ kiến trúc 4 tầng (Client Layer, Gateway Layer, Service Layer, Storage Layer).
  - Phân tích chi tiết 3 kênh phân phối: Cổng Chat Độc Lập, Web Widget CDN, Open API Gateway.
  - Thiết kế lược đồ CSDL quan hệ PostgreSQL 4 tệp cho User & RBAC 5 vai trò.
  - Lộ trình 4 Sprint với tiêu chuẩn kiểm thử và an ninh token quota.

#### B. Sprint 1: Cổng Chat Sinh Viên / Thí Sinh Công Khai (`/chat` & `/chat/$assistantSlug`)
- **Định tuyến công khai**: Cập nhật `frontend2/src/routes/__root.tsx` bổ sung `/chat` và `/chat/*` vào danh sách `isPublicRoute` để sinh viên/thí sinh truy cập trực tiếp không bị chặn bởi `AuthGate` hay gò bó trong `AdminShell`.
- **Giao diện Cổng Trợ Lý (`PublicChatPortal`)**:
  - Tệp: `frontend2/src/features/chat/public-chat-portal.tsx`.
  - Header mang đậm nhận diện ĐH Quy Nhơn (Academic Teal), nút chuyển Dark/Light mode, nút chuyển tiếp sang trang Quản trị dành cho cán bộ.
  - Thanh tìm kiếm và bộ lọc chip theo danh mục chuyên trách.
  - Lưới hiển thị danh thiếp các Trợ lý AI chính thức kèm câu hỏi gợi ý có thể click để bắt đầu trò chuyện ngay.
- **Giao diện Chat Toàn Màn Hình (`PublicChatView`)**:
  - Tệp: `frontend2/src/features/chat/public-chat-view.tsx`.
  - Tối ưu 100% Mobile First và Desktop.
  - Kết nối SSE Streaming qua `useRAGStream`, hiển thị Thinking indicator, hỗ trợ Markdown, bảng biểu, công thức toán.
  - Tích hợp đối soát nguồn văn bản trích dẫn qua `CitationSheet`.
  - Hỗ trợ xuất biên bản hội thoại Markdown (`.md`) và làm mới cuộc trò chuyện.
- **Tạo các Routes TanStack Router**:
  - `frontend2/src/routes/chat.tsx`
  - `frontend2/src/routes/chat.index.tsx`
  - `frontend2/src/routes/chat.$assistantSlug.tsx`

#### C. Sprint 2: Kênh Phân Phối & Quản Lý Web Chat Widget (`/channels`)
- **Trang Quản Trị Kênh Phân Phối (`ChannelsPage`)**:
  - Tệp: `frontend2/src/features/channels/channels-page.tsx`.
  - **Tùy biến cấu hình**: Chọn Trợ lý AI mặc định, đổi tiêu đề, câu chào ban đầu, vị trí xuất hiện (`Góc Dưới Phải` / `Góc Dưới Trái`).
  - **Trình tạo mã nhúng CDN**: Khối script HTML chuẩn kèm nút sao chép 1-click.
  - **Bảo vệ tên miền (Domain Whitelist CORS)**: Cảnh báo và giám sát danh sách domain được phép nhúng (`*.qnu.edu.vn`, `tuyensinh.qnu.edu.vn`, `daotao.qnu.edu.vn`).
  - **Live Preview 1:1**: Khung mô phỏng trình duyệt web `tuyensinh.qnu.edu.vn` với bong bóng widget nổi có thể tương tác bấm mở/đóng và chat thử nghiệm phản hồi thời gian thực trước khi lấy mã nhúng.
- **Cập nhật Điều Hướng Sidebar**:
  - Bổ sung `channels` vào `frontend2/src/navigation/config.ts` dưới nhóm `Xây Dựng AI` với icon `Share2`.
  - Cập nhật union `AppPath` trong `frontend2/src/navigation/types.ts` bổ sung `"/channels"` và `"/chat"`.
- **Sửa đường dẫn Embed**:
  - Cập nhật `frontend2/src/components/assistants/dialogs/assistant-embed-dialog.tsx` trỏ đúng tệp `/embed/qnu-chat-widget.js`.

---

### 3. Kết Quả Kiểm Thử (Fast-Path Frontend Verification)

- Lệnh kiểm tra: `npm run build` (Vite build + TypeScript check).
- **Kết quả**:
  - **Vite build thành công** trong 4.14s:
    - `dist/assets/chat.index-i6sSUR7P.js` (9.29 kB)
    - `dist/assets/chat._assistantSlug-Dfi5kVPC.js` (13.76 kB)
    - `dist/assets/channels.index-Cy5p2vzl.js` (16.34 kB)
  - **TypeScript check (`tsc --noEmit`)**: **0 lỗi biên dịch (Exit code 0)**.

---

### 4. Bài Học & Đúc Kết

- Sử dụng cơ chế `isPublicRoute` trong TanStack Router của `__root.tsx` cho phép phục vụ song song cả giao diện quản trị phức tạp (có sidebar, auth gate) lẫn cổng thông tin công khai (fullscreen, zero auth) trên cùng một dự án SPA gọn nhẹ mà không cần tách thành 2 frontend riêng biệt.
- Cơ chế Live Preview tương tác 1:1 trên trang `/channels` giúp cán bộ các phòng ban tự tin cấu hình widget trước khi giao cho bộ phận kỹ thuật web trường chèn mã vào CMS.
