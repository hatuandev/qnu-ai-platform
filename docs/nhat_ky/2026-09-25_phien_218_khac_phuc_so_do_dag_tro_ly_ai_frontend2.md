# Nhật Ký Phiên 218: Khắc Phục Triệt Để Sự Cố Sơ Đồ DAG Trợ Lý AI Trên Frontend2 & Đồng Bộ Giao Diện Chuẩn UI Rule

- **Thời gian**: 2026-09-25 09:48
- **Tác giả**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Điều tra nguyên nhân sơ đồ DAG trợ lý AI hiển thị khoảng trống ("không có gì hết"), thanh thư viện node chèn lệch sang trái dưới sidebar; đồng bộ kiến trúc từ `frontend/` sang `frontend2/` và tinh chỉnh đúng quy chuẩn UI/UX của QNU AI Platform.

---

## 1. Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Qua quá trình rà soát và đối chiếu giữa `frontend/` và `frontend2/`, phát hiện 3 nguyên nhân cốt lõi gây ra sự cố:

1. **Sự cố Viewport FitView & Vòng lặp Render trong `dag-canvas.tsx`**:
   - Trong `frontend2/src/components/ai/dag-canvas.tsx`, hook `useReactFlow()` được gọi và kích hoạt một hàm hẹn giờ `setTimeout(() => fitView({ padding: 0.25, duration: 250 }), 50)` bên trong `useEffect([initialNodes, setNodes, fitView])`.
   - Vì tại thời điểm 50ms, các DOM element của custom nodes chưa hoàn tất đo đạc kích thước thực tế (`width`, `height` bằng 0), lệnh `fitView` tính toán ra hệ số phóng to / tọa độ bị biến dạng (zoom = 0 hoặc x/y = NaN). Hậu quả là toàn bộ đồ thị bị thu nhỏ về vô cực hoặc dịch chuyển ra ngoài khung nhìn của canvas.
   - Thêm vào đó, việc phụ thuộc vào `initialNodes` trong `useEffect` gây ra vòng lặp cập nhật liên tục mỗi khi component re-render.
   - **Đối soát với `frontend/`**: Bản `frontend/` hoạt động ổn định nhờ hoàn toàn không gọi `fitView` thủ công trong hook, mà để thuộc tính nội tại `<ReactFlow fitView fitViewOptions={{ padding: 0.25 }}>` tự động căn chỉnh khung hình chuẩn xác ngay khi các node đã hoàn tất đo lường hình học.

2. **Thiếu Tệp Style CSS Toàn Cục Của `@xyflow/react` trong Tailwind v4**:
   - Tệp `frontend2/src/styles/globals.css` chưa khai báo `@import "@xyflow/react/dist/style.css";`.
   - Do Tailwind v4 sử dụng cơ chế Lightning CSS xử lý CSS độc lập, việc chỉ import style trong một file JS phụ trợ dẫn đến việc các class quan trọng như `.react-flow`, `.react-flow__renderer`, `.react-flow__pane`, `.react-flow__handle` không được tải đồng bộ ngay từ root, làm mất bố cục hiển thị.

3. **Lỗi Vị Trí Của Thư Viện Node (`NodeCatalogDrawer`)**:
   - `NodeCatalogDrawer` được định vị bằng lớp CSS `absolute top-14 left-4 z-20`.
   - Trong `assistant-workflow-tab.tsx`, component này được đặt ngoài khối `CardContent` và bên trong `<Card>` chưa có thuộc tính `relative`. Do đó, drawer bị neo theo tọa độ gốc của toàn bộ màn hình trình duyệt (`left: 16px`), rơi thẳng vào vị trí bên dưới thanh điều hướng bên trái `AppSidebar` (rộng 256px), khiến drawer bị che khuất và chỉ thò ra một dải hẹp bất thường.

4. **Thiếu Trường Dữ Liệu Tương Thích Cho Node & Property Inspector trong `dag-layout.ts`**:
   - Hàm `convertDagSpecToReactFlow` chưa bổ sung hàm `summarizeConfig`, thiếu các trường `configSummary`, `timeoutSeconds`, cũng như các trường cấu hình đặc thù `workflowNodeType`, `workflowConfig`, `workflowPolicy` cần thiết cho bảng thuộc tính `PropertyInspector`.

5. **Lỗi Sụp Đổ Chiều Cao Canvas (CSS Height Collapse `computedH: 0px`)**:
   - Khi chạy thực tế trên trình duyệt, thẻ `<div className="react-flow">` rơi vào trạng thái `computedH: 0px` đi kèm cảnh báo: `[React Flow]: The parent container needs a width and a height to render the graph. Help: https://reactflow.dev/error#004`.
   - Nguyên nhân: Trong CSS, khi các container cha sử dụng `flex-1` hoặc `min-h-[640px]` mà không có chiều cao pixel cố định (`fixed height`), quy tắc tính toán phần trăm `height: 100%` của các thẻ con bị suy biến về `0`. Do đó toàn bộ vùng hiển thị của ReactFlow bị xẹp hoàn toàn, che giấu cả dots background, minimap, controls và các node.
   - Thêm vào đó, thẻ node `condition_route` có chuỗi `configSummary` chứa JSON dài không có ràng buộc `max-w` khiến node bị kéo giãn bất thường tới `877px`.

---

## 2. Các Thay Đổi & Giải Pháp Kỹ Thuật Đã Áp Dụng

### 2.1. Nạp Style Toàn Cục `@xyflow/react` (`globals.css`)
- Bổ sung `@import "@xyflow/react/dist/style.css";` vào đầu tệp [globals.css](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/styles/globals.css), bảo đảm 100% các class CSS nền tảng của React Flow luôn sẵn sàng trên toàn ứng dụng.

### 2.2. Khắc Phục Triệt Để Chiều Cao Canvas (`dag-canvas.tsx` & `assistant-workflow-tab.tsx`)
- Tại [assistant-workflow-tab.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/assistants/assistant-workflow-tab.tsx):
  - Khai báo chiều cao trực tiếp cho `<CardContent className="p-0 relative w-full overflow-hidden bg-background" style={{ height: "700px", minHeight: "640px" }}>`.
  - Thiết lập `<DAGCanvas className="w-full h-full absolute inset-0" ... />` giúp ReactFlow luôn lấp đầy đúng 700px mà không bị phụ thuộc vào tính toán flexbox auto-height.
- Tại [dag-canvas.tsx](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/ai/dag-canvas.tsx):
  - Thiết lập `minHeight: "640px"` và `height: "100%"` trực tiếp cho cả container ngoài và component `<ReactFlow>`.
  - Khống chế độ rộng `max-w-[240px] truncate` cho thẻ cấu hình `ConditionRouteNode`.

### 2.3. Bổ Sung Thông Số Dữ Liệu Node (`dag-layout.ts`)
- Bổ sung hàm tiện ích `summarizeConfig` hiển thị tóm tắt cấu hình trên từng thẻ node.
- Áp dụng toán tử an toàn `node.policy?.description` và `node.policy?.timeout_seconds` tránh crash runtime khi gặp node không có policy.
- Truyền đầy đủ các thuộc tính `workflowNodeType`, `workflowNodeVersion`, `workflowConfig`, `workflowPolicy` cho `PropertyInspector`.

### 2.4. Khắc Phục Bố Cục Drawer & Vị Trí Giao Diện (`assistant-workflow-tab.tsx`, `node-catalog-drawer.tsx`, `property-inspector.tsx`)
- Thêm `relative` vào thẻ bao ngoài `<Card>` và đưa `<NodeCatalogDrawer>` vào bên trong `<CardContent className="p-0 relative ...">`.
- Điều chỉnh tọa độ drawer trong canvas:
  - `NodeCatalogDrawer`: Đổi từ `absolute top-14 left-4 z-20` thành `absolute top-3 left-3 z-30 max-h-[calc(100%-1.5rem)]`.
  - `PropertyInspector`: Đổi từ `absolute top-14 right-4 z-20` thành `absolute top-3 right-3 z-30 max-h-[calc(100%-1.5rem)]`.
- Drawer giờ đây trượt ra êm ái ngay trên bề mặt canvas, nằm gọn bên trong khung làm việc và tuyệt đối không bao giờ chèn lấn thanh sidebar ứng dụng.

---

## 3. Kiểm Thử & Nghiệm Thu (Fast-Path Verification)

Tuân thủ nghiêm ngặt **Quy tắc 7 (Fast-Path Frontend Verification)** của `AGENTS.md`:
1. **Kiểm tra Linter & Định dạng Biome**:
   ```bash
   npx @biomejs/biome check src/components/ai/dag-layout.ts src/components/ai/dag-canvas.tsx src/components/admin/node-catalog-drawer.tsx src/components/admin/property-inspector.tsx src/features/assistants/assistant-workflow-tab.tsx
   # Kết quả: Checked 5 files. 0 errors, 0 warnings.
   ```
2. **Kiểm thử Biên dịch Bundle & Typecheck Frontend**:
   ```bash
   npm run build
   # Kết quả: vite build && tsc --noEmit hoàn tất thành công trong 1.65s, 0 lỗi TypeScript, exit code 0.
   ```
3. **Kiểm Thử Render Thực Tế Cả 5 Trợ Lý Seeded Qua Headless Playwright**:
   - `admissions`: 8 nodes, height 700px (100% OK)
   - `regulations`: 6 nodes, height 700px (100% OK)
   - `library`: 6 nodes, height 700px (100% OK)
   - `drafting`: 10 nodes, height 700px (100% OK)
   - `question_bank`: 6 nodes, height 700px (100% OK)
   - Cảnh báo ReactFlow error #004 biến mất hoàn toàn. Sơ đồ tự động căn giữa (fitView) ở tỷ lệ zoom chuẩn xác.
