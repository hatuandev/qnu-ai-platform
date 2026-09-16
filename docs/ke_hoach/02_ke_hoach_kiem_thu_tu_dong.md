# KẾ HOẠCH & BÁO CÁO THỰC THI KIỂM THỬ TỰ ĐỘNG HÓA (AUTOMATED TESTING MASTER PLAN)
## Nền Tảng Trí Tuệ Nhân Tạo Đại Học Quy Nhơn (QNU AI Platform)

---

## 1. Tổng Quan Kế Hoạch Kiểm Thử Tự Động (Auto Testing Strategy)

Để đảm bảo toàn bộ hệ thống đạt chuẩn **Production-First**, kiến trúc kiểm thử tự động của dự án được tổ chức theo mô hình kim tự tháp 4 tầng:

```
                  ┌──────────────────────────────┐
                  │ Tầng 4: AI Agent Sub-Suite   │  Playwright MCP Server
                  │ (Autonomous Web Interaction) │  (Tương tác qua Tool Calling)
                  ├──────────────────────────────┤
                  │ Tầng 3: Frontend E2E Suite   │  Playwright Test + Chrome
                  │ (12 Test Cases - 13 Screens) │  (Smoke, Chat Studio, Tools)
                  ├──────────────────────────────┤
                  │ Tầng 2: Backend Test Suite   │  Pytest + HTTPX AsyncClient
                  │ (68 Test Cases - 8 Modules)  │  (RAG, ModelOps, Ingestion,...)
                  ├──────────────────────────────┤
                  │ Tầng 1: Code Quality Gates   │  Biome 2 + TypeScript + Ruff
                  │ (Static Analysis & Typecheck)│  (0 Warnings, 0 Errors)
                  └──────────────────────────────┘
```

---

## 2. Chi Tiết Các Tầng Kiểm Thử & Kết Quả Thực Thi

### 2.1. Tầng 1: Code Quality Gates (Kiểm Tra Tĩnh & Build Bundle)
- **Biome Linter & Formatter**: Kiểm tra toàn bộ 58 file source code Frontend.
  - Kết quả: `Checked 58 files. No fixes needed. 0 errors`.
- **TypeScript Typecheck**: Trình biên dịch `tsc --noEmit` kiểm tra kiểu dữ liệu tĩnh.
  - Kết quả: `0 errors`.
- **Ruff Linter (Backend)**: Kiểm tra chuẩn PEP 8 và Clean Code Python.
  - Kết quả: `All checks passed! 0 errors`.
- **Vite Production Bundle**: Đóng gói production bundle.
  - Kết quả: `✓ built in 6.71s`.

### 2.2. Tầng 2: Backend Integration & Unit Tests (Pytest)
Bộ 68 ca kiểm thử chuyên sâu bao phủ trọn vẹn 8 modules nghiệp vụ theo chuẩn RFC 7807:
- `test_assistants.py`: 5 Trợ lý AI QNU (Tuyển sinh, Quy chế, Thư viện, Soạn thảo, Đề thi).
- `test_knowledge.py`: Collections, bóc tách tài liệu, đa tầng OCR.
- `test_rag.py`: Hybrid Search (Qdrant Dense + PostgreSQL FTS Lexical + RRF k=60 + Cross-Encoder).
- `test_modelops.py`: Circuit Breaker 3 trạng thái, Dynamic Fallback, Quota & Token Cost Tracker.
- `test_tools.py`: Cổng UIS Tuyển sinh, xuất Word NĐ 30, xuất Excel ma trận Bloom.
- `test_evaluation.py`: Chỉ số Ragas TM-08 (Faithfulness, Relevance, Precision), Gap Inbox.
- `test_workflows.py`: Thực thi DAG pipeline, Guardrails bảo vệ.
- `test_health.py` & `test_api_core.py`: Liveness/Readiness probes.
- **Kết quả**: **68/68 PASSED (100%)** trong 6.94s.

### 2.3. Tầng 3: Frontend E2E Test Suite (Playwright)
Cấu hình trực tiếp trình duyệt Google Chrome local (`channel: 'chrome'`), tự động khởi chạy Vite Dev Server port 3000:
- **Suite 01: `01_navigation_smoke.spec.ts` (4 Test Cases)**:
  - `TC-NAV-01`: Duyệt qua toàn bộ 13 màn hình nghiệp vụ, kiểm tra không xuất hiện unhandled crash console.
  - `TC-NAV-02`: Đổi theme Dark/Light mode mượt mà, xác thực biến lớp `dark` trên thẻ `<html>`.
  - `TC-NAV-03`: Thu gọn và mở rộng thanh bên Sidebar (64px <-> 256px), kích hoạt Radix Tooltip chuẩn xác không bị crash DOM.
  - `TC-NAV-04`: Mở thanh tìm kiếm toàn cục Command Menu (Ctrl+K) và đóng bằng phím Escape.
- **Suite 02: `02_chat_studio.spec.ts` (4 Test Cases)**:
  - `TC-CHAT-01`: Render Studio Chat với trợ lý mặc định Tuyển sinh và khung nhập liệu.
  - `TC-CHAT-02`: Chuyển đổi giữa 5 Trợ lý AI QNU, cập nhật giao diện và scope tương ứng.
  - `TC-CHAT-03`: Nhập câu hỏi, kích hoạt trạng thái nút Gửi và hiển thị bong bóng tin nhắn.
  - `TC-CHAT-04`: Nhấp chọn gợi ý nhanh (Quick Prompt), tự động gửi câu hỏi vào luồng hội thoại.
- **Suite 03: `03_knowledge_tools.spec.ts` (4 Test Cases)**:
  - `TC-KNW-01`: Hiển thị kho tri thức, các bộ sưu tập mẫu và thống kê tài liệu.
  - `TC-KNW-02`: Chuyển đổi qua lại giữa các tab trong màn hình Quản trị Tri thức.
  - `TC-TOOL-01`: Hiển thị đầy đủ 3 Tool chuẩn Enterprise của ĐH Quy Nhơn.
  - `TC-TOOL-02`: Chạy thử công cụ trực tiếp trên Tool Playground và hiển thị kết quả JSON trả về.
- **Kết quả**: **12/12 PASSED (100%)** trong 34.7s.

### 2.4. Tầng 4: AI Browser Agent Sub-Suite (Playwright MCP Server)
- Tích hợp `@executeautomation/playwright-mcp-server` vào cấu hình `.agents/mcp_config.json`.
- Cung cấp các công cụ MCP để AI Agent có thể trực tiếp lái trình duyệt:
  - `playwright_navigate`: Mở trang web và kiểm tra URL.
  - `playwright_click`: Nhấp vào bất kỳ nút bấm hoặc thành phần nào trên DOM.
  - `playwright_fill`: Điền thông tin vào các trường biểu mẫu.
  - `playwright_screenshot`: Chụp ảnh giao diện lưu thành artifact để đối soát thị giác.

---

## 3. Hướng Dẫn Vận Hành Cho Lập Trình Viên

### Chạy Toàn Bộ Test E2E (Headless)
```powershell
cd frontend
npm run test:e2e
```

### Mở Giao Diện Tương Tác Trực Quan (Interactive UI Mode)
```powershell
cd frontend
npm run test:e2e:ui
```

### Xem Báo Cáo HTML Trực Quan Kèm Video & Traces
```powershell
cd frontend
npm run test:e2e:report
```

### Chạy Toàn Bộ Test Backend
```powershell
cd backend
uv run --extra dev pytest
```

### Kiểm Tra Chuẩn Code (Lint & Typecheck)
```powershell
# Frontend
cd frontend
npm run lint
npm run typecheck

# Backend
cd backend
uv run ruff check .
```
