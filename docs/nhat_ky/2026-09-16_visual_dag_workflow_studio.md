# NHẬT KÝ PHIÊN LÀM VIỆC — Visual DAG Workflow Studio (Kế Thừa QNU-AI-Core)
**Ngày thực hiện**: 2026-09-16 | **Thời gian**: 22:00 - 22:50 (UTC+7)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Triển khai Lựa chọn B từ kế hoạch kế thừa `qnu-ai-core` — Xây dựng Visual DAG Workflow Studio toàn năng trên Frontend `qnu-ai-platform`.

---

## 1. Bối Cảnh & Động Lực Kỹ Thuật
Khi nghiên cứu codebase `qnu-ai-core` (đặc biệt là `services/studio-ui`), nền tảng cũ có cấu trúc node card và luồng điều phối rất phong phú nhưng còn phân mảnh và thiếu trải nghiệm chạy thử nghiệm trực tiếp ngay trên mặt phẳng đồ thị (In-Canvas Execution). Nhằm đưa QNU AI Platform lên chuẩn mực cao cấp nhất theo `AGENTS.md`, nhóm kiến trúc sư đã hiện thực hóa trọn vẹn **Visual DAG Workflow Studio** với 5 trụ cột cốt lõi:
1. **In-Canvas Test Runner**: Khung drawer chạy thử luồng với visual animation đèn tín hiệu chuyển động lần lượt qua từng node (`idle` ➔ `running` ➔ `completed`), tính latency chi tiết $ms$ và tích hợp cơ chế phê duyệt cán bộ (**Human Approval Checkpoint**).
2. **8 Custom Node Types Tinh Tế**: Sử dụng `@xyflow/react` v12 với các loại node chuyên biệt: `chatInput`, `conditionRoute`, `ragKnowledge`, `llmGenerate`, `toolCall`, `guardrail`, `humanApproval`, `chatOutput` với handles nối dây, icon QNU Teal và hiệu ứng pulse phát sáng khi đang thực thi.
3. **Node Catalog Drawer**: Thư viện 8 danh mục Node atomic chuẩn QNU Platform, hỗ trợ tìm kiếm và lọc phân loại.
4. **Property Inspector Chuyên Sâu**: Bảng cấu hình thuộc tính node hỗ trợ 2 chế độ xem linh hoạt (Visual Form thân thiện & JSON Schema chuyên gia).
5. **05 Bộ Luồng Mẫu Chuẩn QNU**: Cung cấp sẵn 5 đồ thị DAG phân nhánh hoàn chỉnh cho Tuyển sinh, Quy chế, Soạn thảo văn bản NĐ 30, Ngân hàng đề thi Bloom, và Thư viện số.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật & Chi Tiết Triển Khai |
| :--- | :---: | :--- |
| [`frontend/src/components/admin/in-canvas-test-runner.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/in-canvas-test-runner.tsx) | **Tạo mới** | Drawer điều khiển chạy thử luồng, hỗ trợ nhập câu hỏi hoặc chọn quick prompts tuyển sinh/quy chế. Gọi API `/platform/v1alpha1/workflows/execute` (có smart simulation fallback khi backend offline). Dispatch callback `onUpdateExecutionState` chạy hiệu ứng ánh sáng lần lượt qua các node. Có nút **Phê Duyệt Ngay (Quick Approve)** khi gặp checkpoint con người. Tabs kết quả phân tách giữa Phản hồi Markdown và bảng Step Traces. |
| [`frontend/src/components/admin/node-catalog-drawer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/node-catalog-drawer.tsx) | **Tạo mới** | Thư viện khối thực thi atomic với 8 node tiêu chuẩn. Hỗ trợ tìm kiếm theo từ khóa và lọc qua 8 category pills (`input`, `route`, `rag`, `llm`, `tool`, `guard`, `human`, `output`). Mỗi card có nút "Thêm Node" kèm `data-testid` định danh. |
| [`frontend/src/components/admin/property-inspector.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/property-inspector.tsx) | **Tạo mới** | Panel trượt bên phải hiển thị khi người dùng click vào bất kỳ Node nào trên Canvas. Hỗ trợ chuyển đổi giữa Visual Form (chỉnh sửa Tên hiển thị, Mô tả tóm tắt, Cấu hình nghiệp vụ, Timeout giây) và JSON Schema Viewer với tính năng sao chép 1-click. Có nút Xóa Node khỏi đồ thị. |
| [`frontend/src/components/ai/dag-canvas.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/ai/dag-canvas.tsx) | **Nâng cấp** | Bổ sung prop `executionStates: Record<string, NodeExecutionState>`. Định nghĩa 8 custom node components bọc trong React Flow với handles `Position.Top` / `Position.Bottom`, StatusBadge, hiển thị latency $ms$, và class phát sáng `ring-2 ring-primary ring-offset-1 animate-pulse`. |
| [`frontend/src/pages/dag-canvas-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dag-canvas-page.tsx) | **Nâng cấp** | Tích hợp Top Toolbar chuyển đổi giữa 5 luồng QNU (`admissions`, `regulations`, `drafting`, `question_bank`, `library`). Quản lý state tập trung liên kết Canvas ➔ Catalog Drawer ➔ In-Canvas Test Runner ➔ Property Inspector. Hỗ trợ Thêm/Xóa/Sửa Node và Sao chép toàn bộ đặc tả DAG sang JSON. |
| [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts) | **Cập nhật** | Định nghĩa interfaces `WorkflowExecuteRequest`, `WorkflowExecuteResponse`. Bổ sung API client `executeWorkflow(req)` với smart simulation phản hồi Markdown chuẩn QNU và mảng step traces chân thực. Đồng bộ hóa typing `api_key_masked`. |
| [`frontend/vite.config.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/vite.config.ts) | **Cập nhật** | Chuyển cổng phát triển từ `3000` sang `3001` để loại bỏ hoàn toàn xung đột với máy chủ Next.js của `qnu-ai-core` đang chạy trên cổng 3000. |
| [`frontend/package.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/package.json) | **Cập nhật** | Cập nhật các lệnh `"dev": "vite --port 3001"` và `"preview": "vite preview --port 3001"`. |
| [`frontend/playwright.config.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/playwright.config.ts) | **Cập nhật** | Đồng bộ `baseURL: "http://localhost:3001"` và `webServer.url: "http://localhost:3001"`, đặt `reuseExistingServer: false`. |
| [`frontend/tests/e2e/07_dag_workflow_studio.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/07_dag_workflow_studio.spec.ts) | **Tạo mới** | Bộ kiểm thử E2E tự động hóa 3 kịch bản: (1) Chuyển đổi 5 luồng QNU và xác minh topology nodes; (2) Thêm node từ catalog và tùy biến cấu hình qua inspector; (3) Chạy mô phỏng in-canvas test runner với animation trực quan và kiểm tra markdown output. |

---

## 3. Kết Quả Kiểm Thử Nghiệm Thu (Verification)

### 3.1. Kiểm Tra Tĩnh (Static Checks & Clean Code)
- **Biome Linter**:
  ```bash
  npm run lint
  # Checked 64 files in 89ms. No fixes applied. (0 errors)
  ```
- **TypeScript Typecheck**:
  ```bash
  npm run typecheck
  # tsc --noEmit: 0 errors
  ```
- **Vite Production Build**:
  ```bash
  npm run build
  # ✓ built in 7.62s (dist/assets/index-DJvZX5wG.js: 1,142.92 kB)
  ```
- **Backend Ruff Linter**:
  ```bash
  uv run ruff check .
  # All checks passed!
  ```

### 3.2. Kiểm Thử Tự Động Hóa E2E (Playwright trên Google Chrome)
```bash
npx playwright test tests/e2e/07_dag_workflow_studio.spec.ts --project="Google Chrome"
```
**Kết quả**: **3/3 Tests Passed (13.4s)**
- `TC-DAG-01`: Switches between 5 official QNU workflows and verifies custom node topologies — **PASS (3.2s)**
- `TC-DAG-02`: Adds a new Node from Catalog and customizes properties via Property Inspector — **PASS (3.1s)**
- `TC-DAG-03`: Runs in-canvas test execution with live visual node animation — **PASS (3.6s)**

### 3.3. Minh Chứng Ảnh Chụp Màn Hình (Artifacts)
1. `dag_canvas_overview.png`: Toàn cảnh Canvas đồ thị trực quan với 5 luồng nghiệp vụ chuẩn QNU.
2. `dag_property_inspector.png`: Bảng cấu hình thuộc tính tham số Node khi được thêm mới từ Thư viện Catalog.
3. `dag_in_canvas_test_runner.png`: Khung Drawer chạy thử nghiệm luồng In-Canvas hiển thị kết quả Markdown và Step Traces.

---

## 4. Đánh Giá & Bài Học Kinh Nghiệm (Learnings & Gotchas)
1. **Xung đột cổng giữa các repository**: Dự án `qnu-ai-core` chạy Next.js trên cổng 3000, khiến Playwright tự động reuse tiến trình cũ dẫn đến định vị nhầm DOM. Việc chủ động cô lập `qnu-ai-platform` sang cổng 3001 giải quyết dứt điểm rủi ro và giúp hai dự án có thể chạy song song độc lập.
2. **Deterministic Targeting trong E2E**: Luôn bổ sung `data-testid` trên các phần tử danh sách lặp (ví dụ `data-testid={`catalog-item-${item.type}`}`) để Playwright tương tác chính xác tuyệt đối mà không phụ thuộc vào thứ tự render của DOM.
