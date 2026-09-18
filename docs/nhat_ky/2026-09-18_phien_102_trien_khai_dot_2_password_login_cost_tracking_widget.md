# NHẬT KÝ LÀM VIỆC — PHIÊN #102
# Ngày: 2026-09-18 | Triển Khai Đợt 2: Password-Only Access Gate, Observability & Real Cost Tracking, Standalone Web Widget Embed

---

## 1. Mục Tiêu Phiên Làm Việc
Hiện thực hóa toàn diện **Đợt 2** theo đúng định hướng của người dùng:
1. **Phần Đăng Nhập Đơn Giản (Password-Only Dev Access Gate)**:
   - Form đăng nhập chỉ có đúng 1 ô nhập Mật khẩu (`QNU@2026`).
   - Bỏ qua hoàn toàn phân quyền (RBAC), phòng ban để giữ sản phẩm đơn giản, gọn gàng.
   - Bảo vệ toàn bộ các trang quản trị bằng Route Guard và bổ sung nút Đăng xuất trên thanh Topbar.
2. **Observability & Thống Kê Chi Phí Thời Gian Thực (Real-Time Cost Tracking)**:
   - Xóa bỏ số liệu giả lập trên Dashboard.
   - Ghi bản ghi `LLMUsageLog` khi gọi LLM (cả sync và stream SSE).
   - Tính toán chi phí USD dựa trên bảng giá định danh mô hình.
   - Cung cấp API `GET /platform/v1alpha1/modelops/usage-stats` và kết nối trực tiếp vào Dashboard.
3. **Web Widget Embed Độc Lập Cho Cổng Thông Tin QNU**:
   - Cung cấp tệp script `qnu-chat-widget.js` độc lập, siêu nhẹ tại `frontend/public/embed/qnu-chat-widget.js`.
   - Nâng cấp Kênh phân phối `/channels` và thêm Dialog "Mã nhúng Web Widget" trên trang chi tiết trợ lý `/assistants/:id`.

---

## 2. Danh Sách Tệp Thay Đổi & Tạo Mới

| Tệp Tin | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| [`frontend/src/types/auth.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/auth.ts) | **NEW** | Khởi tạo TypeScript interfaces `AuthActor`, `AuthStatusResponse`, `DevLoginRequest`. |
| [`frontend/src/services/auth-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/auth-api.ts) | **NEW** | Service API gọi `/auth/login`, `/auth/logout`, `/auth/me` kèm cookie `qnu_session`. |
| [`frontend/src/contexts/auth-context.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/contexts/auth-context.tsx) | **NEW** | AuthProvider và hook `useAuth()` quản lý trạng thái đăng nhập cho toàn bộ Frontend. |
| [`frontend/src/pages/login-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/login-page.tsx) | **NEW** | Màn hình đăng nhập tối giản (chỉ có 1 ô mật khẩu, toggle xem mật khẩu, nút điền mặc định `QNU@2026`). |
| [`frontend/src/layouts/topbar.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/topbar.tsx) | **MODIFY** | Tích hợp hook `useAuth()`, thêm nút Đăng xuất kích hoạt `logout()` và điều hướng về `/login`. |
| [`frontend/src/layouts/admin-shell.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/layouts/admin-shell.tsx) | **MODIFY** | Truyền `onNavigate` vào Topbar để xử lý chuyển hướng khi đăng xuất. |
| [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx) | **MODIFY** | Bọc app trong `AuthProvider`, tích hợp Route Guard tự động chuyển hướng về `LoginPage` khi chưa đăng nhập. |
| [`backend/app/modules/modelops/pricing.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/pricing.py) | **NEW** | Bảng giá mô hình LLM (OpenAI, Gemini, Mistral, Local) và hàm `calculate_cost_usd`. |
| [`backend/app/modules/modelops/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/schemas.py) | **MODIFY** | Khởi tạo Pydantic schemas `ModelUsageBreakdownItem`, `DailyUsageItem`, `UsageStatsResponse`. |
| [`backend/app/modules/modelops/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/service.py) | **MODIFY** | Thêm phương thức `record_usage_log` và `get_usage_statistics` tổng hợp metrics thật từ CSDL. |
| [`backend/app/modules/modelops/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/router.py) | **MODIFY** | Thêm endpoint `GET /platform/v1alpha1/modelops/usage-stats`. |
| [`backend/app/modules/assistants/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py) | **MODIFY** | Tích hợp hook ghi `LLMUsageLog` vào cả `chat()` và `chat_stream()`. |
| [`backend/tests/test_modelops_usage.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_modelops_usage.py) | **NEW** | 4 unit tests kiểm thử tính giá, ghi log CSDL, tổng hợp thống kê và endpoint API. |
| [`frontend/src/types/modelops.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/modelops.ts) | **MODIFY** | Bổ sung TypeScript types cho UsageStatsResponse và Breakdown items. |
| [`frontend/src/services/modelops-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/modelops-api.ts) | **MODIFY** | Thêm hàm `getModelOpsUsageStats(days, tenantId)`. |
| [`frontend/src/pages/dashboard-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/dashboard-page.tsx) | **MODIFY** | Nối dữ liệu usage thật vào KPI cards và Card 2 "Phân Bổ Token Mô Hình". |
| [`frontend/public/embed/qnu-chat-widget.js`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/public/embed/qnu-chat-widget.js) | **NEW** | File script Vanilla JS độc lập nhúng widget chat QNU (Floating button, popover, SSE streaming). |
| [`frontend/src/pages/channels-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/channels-page.tsx) | **MODIFY** | Cập nhật mã trợ lý chuẩn và đường dẫn nhúng `/embed/qnu-chat-widget.js`. |
| [`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx) | **MODIFY** | Bổ sung nút và Dialog [Mã nhúng Web Widget] 1-click cho từng trợ lý cụ thể. |
| [`docs/quy_trinh/06_modelops_circuit_breaker.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/06_modelops_circuit_breaker.md) | **MODIFY** | Đồng bộ Mục 5 đặc tả luồng Observability & Thống kê chi phí USD thời gian thực. |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Backend Verification**:
   - `uv run ruff check .`: 0 lỗi.
   - `uv run --extra dev pytest tests/test_auth.py tests/test_modelops_usage.py tests/test_assistant_readiness.py tests/test_knowledge_gaps.py`: **17/17 passed (100%)** trong 4.37s.
2. **Frontend Verification**:
   - `npm run lint`: Biome check 128 files — 0 lỗi.
   - `npm run typecheck`: TypeScript `tsc --noEmit` — 0 lỗi.
   - `npm run build`: Vite build thành công trong 6.66s, sinh đầy đủ bundle tĩnh kèm file nhúng `dist/embed/qnu-chat-widget.js`.
3. **Kiểm Toán Zero Mojibake**:
   - `python scripts/check_mojibake.py`: Quét **277/277 tệp** — 100% sạch, không có ký tự lỗi tiếng Việt.
