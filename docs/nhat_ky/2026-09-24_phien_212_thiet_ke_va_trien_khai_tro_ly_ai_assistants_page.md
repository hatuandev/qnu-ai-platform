# NHẬT KÝ PHIÊN LÀM VIỆC #212
# Thời gian: 2026-09-24 15:35
# Nội dung: Thiết Kế & Triển Khai Hoàn Chỉnh Phân Hệ Trợ Lý AI (/assistants) Trên Frontend2 Chuẩn Master-Detail Deep Routing

---

## 1. Mục Tiêu Phiên Làm Việc
1. **Đóng vai trò Chuyên gia UI/UX & Senior Full-Stack Architect** thiết kế toàn diện kiến trúc phân hệ Trợ Lý AI (`/assistants`) trên nền tảng Next-Gen `frontend2`.
2. **Triển khai kiến trúc Master-Detail Deep Routing** (Mục 4.5 của `AGENTS.md`):
   - Danh sách tổng quan Master View: `/assistants`
   - Trung tâm quản trị điều hành Dedicated Detail View: `/assistants/:assistantId`
3. **Hiện thực hóa quy trình 7 lớp tạo lập Trợ lý AI** (Mục 2 của `AGENTS.md` & skill `qnu-chatbot-builder`):
   - Lớp 1: Persona & Scope
   - Lớp 2: Knowledge & RAG Binding
   - Lớp 3: ModelOps & Fallback Policy
   - Lớp 4: Guardrails & Safety Defense
   - Lớp 5: Tools Gateway & Human-in-the-loop (HITL)
   - Lớp 6: Output Formatting & Citations
   - Lớp 7: Quality Eval & Observability (TM-08: Faithfulness $\ge 0.90$)
4. **Bảo đảm chuẩn kiểm thử Frontend**: Biome check 0 lỗi, TypeScript typecheck 0 lỗi, Vite build thành công sinh chunk riêng biệt.

---

## 2. Các Thành Phần Đã Triển Khai

### A. Định Tuyến File-Based TanStack Router (`frontend2/src/routes/`)
- [`frontend2/src/routes/assistants.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/assistants.tsx): Layout Route bọc `<Outlet />`.
- [`frontend2/src/routes/assistants.index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/assistants.index.tsx): Tuyến `/assistants/` hiển thị `AssistantsPage`.
- [`frontend2/src/routes/assistants.$assistantId.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/assistants.$assistantId.tsx): Tuyến chi tiết động `/assistants/:assistantId` hiển thị `AssistantDetailPage`.

### B. Màn Hình Danh Sách Master View: [`AssistantsPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistants-page.tsx)
- **Header & Action Bar**: Tiêu đề "Trợ Lý AI", các nút hành động ngắn gọn: "Đồng bộ mẫu", "Nhập bundle", "Thêm trợ lý".
- **Dải chỉ số KPI Telemetry Strip 4 ô gộp trong Card nguyên khối**:
  1. Trợ lý AI: Tổng số và số đang bật hoạt động.
  2. Đạt chuẩn TM-08: Số trợ lý có rào chắn Groundedness $\ge 0.90$.
  3. Kho tri thức: Tổng số kho tri thức chính thức liên kết.
  4. Quy trình DAG: Tổng số luồng xử lý điều phối thông minh.
- **Thanh công cụ Toolbar**: Ô tìm kiếm debounced thời gian thực, bộ lọc lĩnh vực (Select 165px chống cắt chữ), bộ lọc trạng thái (Hoạt động / Tạm dừng), nút chuyển chế độ xem Thẻ (Grid) / Bảng (Table).
- **Thẻ Trợ Lý AI [`AssistantCard`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/assistants/assistant-card.tsx)**:
  - Header: Icon chuyên ngành trong container `bg-primary/10 text-primary`, Tên trợ lý, Badge mã code font mono, Badge lĩnh vực, Switch bật/tắt hoạt động.
  - Body: Mô tả 2 dòng, dải thông số kỹ thuật (Mô hình AI, Kho tri thức, Tiêu chuẩn TM-08).
  - Footer: Các nút bấm súc tích 1-2 từ: "Thử nghiệm" (chat sandbox), "Sơ đồ DAG", "Quản trị", menu "Nhân bản", "Lịch sử", "Mã nhúng", "Xuất bundle".
- **Chế độ xem Bảng dữ liệu**: Bảng dữ liệu với chiều cao hàng `h-12`, hỗ trợ cuộn ngang nội bộ không vỡ layout trên mobile.

### C. Màn Hình Điều Hành Chi Tiết: [`AssistantDetailPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistant-detail-page.tsx)
- **Hero Header [`AssistantHeader`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/assistants/assistant-header.tsx)**:
  - Nút quay lại adaptive: `← Danh mục trợ lý`.
  - Dải thẩm định sẵn sàng xuất bản (Readiness Telemetry 5 tiêu chí: Tri thức, Mô hình, Công cụ, Rào chắn, Đánh giá).
  - Các nút hành động: "Lưu", "Phát hành", "Sơ đồ DAG", "Thử nghiệm", menu thao tác khác.
- **Thanh Điều Hướng 5 Tabs Chuyên Sâu [`AssistantWorkspaceNav`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/assistants/assistant-workspace-nav.tsx)**:
  1. `Cấu hình`: Phân 2 cột cân xứng (Cột trái: Định danh & Kho tri thức; Cột phải: Mô hình, An toàn & Công cụ).
  2. `Mô hình & An toàn`: Cấu hình tham số model (Temperature, Tokens) và rào chắn Guardrails (PII, Prompt Injection, Groundedness, No-answer policy).
  3. `Công cụ & Quản trị`: Danh sách Function Calling, Human-in-the-loop và Vùng nguy hiểm (Vô hiệu hóa / Khôi phục).
  4. `Sơ đồ DAG`: Thẻ quản trị quy trình DAG, chế độ quyền sở hữu Private/Shared, nút "Nhân bản riêng" và nút "Mở DAG Canvas".
  5. `Thử nghiệm`: Khung Sandbox tương tác trực tiếp [`AssistantPlaygroundTab`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistant-playground-tab.tsx).
- **Khung Sandbox Thử Nghiệm [`AssistantPlaygroundTab`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistant-playground-tab.tsx)**:
  - Tích hợp hook `useRAGStream` với SSE streaming token thời gian thực.
  - Hiển thị các câu hỏi gợi ý mẫu 1-click từ cấu hình của Trợ lý.
  - Đối soát trích dẫn minh chứng văn bản (Citations inspector) và hiển thị độ trễ suy luận.

### D. Modal Khởi Tạo Trợ Lý Đa Năng: [`CreateAssistantDialog`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/assistants/dialogs/create-assistant-dialog.tsx)
- Cung cấp 3 chế độ:
  1. **Mẫu QNU**: 4 mẫu hạt nhân (Tuyển sinh, Học vụ, Soạn thảo NĐ 30, Khảo thí Bloom).
  2. **AI phác thảo**: Người dùng nhập mô tả sơ bộ, AI tự động soạn thảo System prompt và đề xuất cấu hình.
  3. **Tùy chỉnh thủ công**: Nhập linh hoạt từ đầu.

---

## 3. Kết Quả Kiểm Thử (Verification)
- **Biome Linter**: `npx @biomejs/biome check` trên toàn bộ 20 tệp của phân hệ Trợ lý AI ➔ **0 lỗi, 0 cảnh báo**.
- **TypeScript**: `tsc --noEmit` ➔ **0 lỗi** toàn bộ codebase.
- **Vite Build**: `npm run build` ➔ **Thành công (2.15s)**:
  - Chunk danh sách `assistants.index`: **31.74 kB**.
  - Chunk chi tiết `assistants._assistantId`: **75.31 kB**.
