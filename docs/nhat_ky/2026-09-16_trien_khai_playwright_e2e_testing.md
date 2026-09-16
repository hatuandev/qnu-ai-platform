# NHẬT KÝ LÀM VIỆC — Triển Khai Hệ Sinh Thái Automated Testing Toàn Diện

- **Thời gian**: 2026-09-16 09:55 (UTC+7)
- **Mục tiêu**: Xây dựng và chuẩn hóa toàn bộ kế hoạch và hạ tầng Auto Testing cho QNU AI Platform (Playwright MCP Server, Playwright E2E Test Suite, Pytest Backend và CI Quality Gates).

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Trước đây, nền tảng mới chỉ có 68 unit/integration test ở tầng Backend (Pytest). Để đảm bảo chất lượng phần mềm đạt chuẩn Enterprise Production-First:
1. Cần một công cụ cho AI Agent có thể tương tác trực tiếp với trình duyệt để tự động kiểm thử (Web MCP / Playwright MCP).
2. Cần một bộ test E2E độc lập, tự động hóa 100% việc kiểm thử tương tác người dùng, điều hướng giữa 13 màn hình, thao tác trên Chat Studio, xem phản hồi RAG, và chạy thử Tools Gateway.
3. Tránh việc tải Chromium từ CDN quốc tế (dễ bị timeout hoặc chặn mạng tại Việt Nam) bằng cách cấu hình trực tiếp Google Chrome có sẵn trên Windows (`channel: 'chrome'`).

---

## 2. Các Thay Đổi Kỹ Thuật Chính (Key Changes)

1. **Cấu hình Playwright MCP Server**:
   - Cài đặt `@executeautomation/playwright-mcp-server` qua npm.
   - Cấu hình tệp [`.agents/mcp_config.json`](../../.agents/mcp_config.json) gắn biến môi trường `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"`.

2. **Khởi tạo Framework Playwright E2E**:
   - Tệp cấu hình [`frontend/playwright.config.ts`](../../frontend/playwright.config.ts): cấu hình `channel: "chrome"`, `workers: 1`, `baseURL: "http://localhost:3000"`, và tự động khởi chạy dev server Vite bằng `webServer`.
   - Bổ sung lệnh kiểm thử trong [`frontend/package.json`](../../frontend/package.json):
     - `test:e2e`: Chạy kiểm thử tự động ở chế độ headless.
     - `test:e2e:ui`: Mở giao diện tương tác trực quan Playwright UI.
     - `test:e2e:report`: Mở báo cáo HTML chi tiết kèm video và ảnh chụp lỗi nếu có.

3. **Khắc phục Lỗi Cốt Lõi SPA Routing & TooltipProvider**:
   - Trong [`frontend/src/App.tsx`](../../frontend/src/App.tsx): Đồng bộ `currentPath` với `window.location.pathname`, lắng nghe sự kiện `popstate` để hỗ trợ điều hướng trực tiếp qua URL từ Playwright.
   - Thêm `<TooltipProvider delayDuration={0}>` bọc ngoài `<AppContent />` để ngăn chặn lỗi Radix Tooltip unmount toàn bộ React DOM khi thu gọn thanh bên.

4. **Xây Dựng 3 Test Suites Chuẩn Hóa**:
   - [`frontend/tests/e2e/01_navigation_smoke.spec.ts`](../../frontend/tests/e2e/01_navigation_smoke.spec.ts): Smoke test 13 màn hình, đổi theme Dark/Light, thu gọn/mở rộng Sidebar, mở Command Menu.
   - [`frontend/tests/e2e/02_chat_studio.spec.ts`](../../frontend/tests/e2e/02_chat_studio.spec.ts): Kiểm tra Chat Studio, chuyển đổi giữa 5 Trợ lý AI QNU, nhập tin nhắn, gửi gợi ý nhanh Quick Prompt.
   - [`frontend/tests/e2e/03_knowledge_tools.spec.ts`](../../frontend/tests/e2e/03_knowledge_tools.spec.ts): Quản trị tri thức (tabs, bộ sưu tập), kiểm tra 3 Tool ngoại vi QNU và thực thi Tool Playground hiển thị JSON.

5. **Thiết Lập Bộ Điều Phối Lệnh Makefile & PowerShell Runner (`run.ps1`)**:
   - [`Makefile`](../../Makefile): Bộ lệnh tự động hóa chuẩn POSIX/GNU Make cho toàn hệ thống (`make dev`, `make be`, `make fe`, `make test`, `make lint`).
   - [`run.ps1`](../../run.ps1): Tập lệnh hỗ trợ trực tiếp môi trường Windows PowerShell (`.\run.ps1 dev`, `.\run.ps1 be`, `.\run.ps1 fe`).

---

## 3. Kết Quả Kiểm Thử Thực Tế

| Thành phần | Lệnh kiểm tra | Kết quả |
| :--- | :--- | :---: |
| **Backend Lint** | `uv run ruff check .` | 0 lỗi |
| **Backend Pytest** | `uv run --extra dev pytest` | **68/68 PASSED** (100%) |
| **Frontend Lint** | `npm run lint` | 0 lỗi (Biome 2) |
| **Frontend Typecheck** | `npm run typecheck` | 0 lỗi (TypeScript) |
| **Frontend Production Build** | `npm run build` | **Thành công** (6.71s) |
| **Frontend E2E Playwright** | `npm run test:e2e` | **12/12 PASSED** (100% trong 34.7s) |
