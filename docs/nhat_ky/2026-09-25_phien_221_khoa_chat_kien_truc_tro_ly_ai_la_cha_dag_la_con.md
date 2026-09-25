# Nhật Ký Làm Việc — Phiên 221 (2026-09-25 15:15)

## 📌 Chủ Đề: Khóa Chặt Kiến Trúc "Trợ Lý AI Là Cha — Sơ Đồ Luồng DAG Là Con", Loại Bỏ Định Danh & Nút Tách Rời Trên Frontend2

---

### 1. Bối Cảnh & Yêu Cầu Người Dùng

- **Phát hiện kiến trúc từ người dùng**:
  - Người dùng nhận thấy trên giao diện Trợ lý AI vẫn còn hiển thị mã định danh riêng của DAG workflow (`drafting-assistant`, `admissions-assistant`,...) và huy hiệu phân tách quyền sở hữu `[Riêng trợ lý]`, cùng nút "Sơ đồ DAG Studio" ở góc trên bên phải trang chi tiết.
  - Điều này đi ngược lại tư duy mô hình thực thể ban đầu: **Trợ lý AI là Cha (Root Entity)**, còn **Sơ đồ DAG là Con (Child Component)** thuộc quyền sở hữu nội tại của Trợ lý AI. Trợ lý AI không phải là một thực thể vay mượn quy trình rời rạc từ bên ngoài.
- **Yêu cầu triển khai**:
  1. Triển khai kế hoạch điều chỉnh UI/UX và logic Cha - Con:
     - Xóa bỏ hoàn toàn mã định danh DAG riêng `<code>{workflowId}</code>` và huy hiệu `[Riêng trợ lý]` / `[Dùng chung]`.
     - Đặt lại tiêu đề trang trọng, thống nhất: **"Sơ Đồ Luồng Suy Luận"**.
     - Xóa bỏ nút trùng lặp `Sơ đồ DAG Studio` ở Topbar Header.
     - Thay thế dropdown lựa chọn workflow rời rạc trong Tab Công Cụ bằng một card tổng quan trực quan khẳng định Trợ lý luôn sở hữu sơ đồ DAG nội bộ của chính nó.
     - Nâng cấp điều khiển Human-in-the-Loop (HITL) sang Radix UI `<Switch>`.
  2. Rà soát và xác thực 5 Trợ lý AI và 5 Kho tri thức đã chuẩn hóa 100% theo đúng thuyết minh đề tài đã được người dùng phê duyệt trước đó.

---

### 2. Các Thay Đổi Chi Tiết

#### A. Tab Sơ Đồ DAG (`frontend2/src/features/assistants/assistant-workflow-tab.tsx`)
- Đổi tiêu đề Card từ `Sơ đồ Workflow DAG` thành **`Sơ Đồ Luồng Suy Luận`**.
- Xóa bỏ `<code>{workflowId}</code>` và huy hiệu `isPrivate` (`[Riêng trợ lý]` / `[Dùng chung]`).
- Xóa nút hành động `Tách riêng` (vì sơ đồ DAG là thành phần nội bộ bất biến của Trợ lý AI).
- Dọn dẹp các props và imports thừa (`onForkWorkflow`, `isForking`, `GitFork`, `Lock`, `Share2`).

#### B. Header Chi Tiết Trợ Lý (`frontend2/src/components/assistants/assistant-header.tsx`)
- Xóa nút trùng lặp `Sơ đồ DAG Studio` ở thanh công cụ góc trên bên phải (tránh gây hiểu lầm mở sang phân hệ phần mềm rời rạc khác).
- Cập nhật mục trong dropdown tiện ích thành `"Xem sơ đồ luồng DAG"`.

#### C. Tab Công Cụ & Tích Hợp (`frontend2/src/components/assistants/sections/assistant-tools-section.tsx`)
- Lược bỏ hoàn toàn thẻ `<Select>` chọn đổi Workflow và nút `Tách thành quy trình riêng`.
- Bổ sung Card tổng quan trực quan giới thiệu Sơ đồ luồng DAG nội bộ kèm nút điều hướng nhanh sang Tab Sơ Đồ DAG của Trợ lý.
- Nâng cấp điều khiển Phê duyệt thủ công Human-in-the-Loop sang Radix UI `<Switch>` (`@/components/ui/switch`).
- Dọn dẹp sạch sẽ `onForkWorkflow` và `isForkingWorkflow`.

#### D. Trang Chi Tiết Trợ Lý (`frontend2/src/features/assistants/assistant-detail-page.tsx`)
- Lược bỏ mutation `forkWorkflowMutation` và import `forkAssistantWorkflow` không còn sử dụng.
- Dọn dẹp việc truyền props fork xuống các sub-components.

---

### 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Kiểm tra linter Biome**:
   - Lệnh: `npx @biomejs/biome check src/features/assistants/assistant-workflow-tab.tsx src/components/assistants/assistant-header.tsx src/components/assistants/sections/assistant-tools-section.tsx src/features/assistants/assistant-detail-page.tsx`
   - Kết quả: **Checked 4 files, 0 errors, 0 warnings**.
2. **Kiểm tra biên dịch Vite (`npm run build`)**:
   - Lệnh: `npm run build` trên `frontend2`
   - Kết quả: **`✓ built in 1.60s` (Exit code: 0)**, 0 lỗi TypeScript `tsc --noEmit`, 0 lỗi cú pháp.
3. **Kiểm tra tính toàn vẹn 5 Trợ lý AI & 5 Kho tri thức trong CSDL**:
   - `admissions`: **Trợ lý ảo Tư vấn Tuyển sinh** — **Kho Tri Thức Đề Án Tuyển Sinh**
   - `regulations`: **Trợ lý ảo Tư vấn Quy chế, Quy định** — **Kho Tri Thức Quy Chế & Quy Định Đào Tạo**
   - `drafting`: **Trợ lý ảo Hỗ trợ Soạn thảo Văn bản** — **Kho Tri Thức Thể Thức & Biểu Mẫu Văn Bản**
   - `library`: **Trợ lý ảo Tra cứu & Khai thác Tài nguyên Thư viện** — **Kho Tri Thức Tài Nguyên Thư Viện & Học Liệu Số**
   - `question_bank`: **Trợ lý ảo Hỗ trợ Tạo Câu hỏi & Ngân hàng Đề thi theo Chuẩn Đầu ra** — **Kho Tri Thức Ngân Hàng Câu Hỏi & Chuẩn Đầu Ra**
