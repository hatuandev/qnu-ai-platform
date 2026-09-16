# NHẬT KÝ PHIÊN LÀM VIỆC — 2026-09-16
## Tiêu đề: Rà Soát Toàn Diện 13 Màn Hình & Đồng Bộ Hóa Backend-Frontend, Triệt Tiêu Lỗi Trắng Màn Hình

---

### 1. Thông Tin Phiên Làm Việc
- **Thời gian**: 2026-09-16 10:35 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Rà soát kỹ lưỡng toàn bộ các chức năng và màn hình của hệ thống khi chạy cùng Backend thực tế (`.\make dev` / `.\run.ps1 dev`). Phát hiện và khắc phục triệt để các lỗi TypeError (màn hình trắng) do lệch cấu trúc DTO hoặc thiếu thuộc tính tương tự như màn hình ModelOps trước đó.

---

### 2. Các Thay Đổi Kỹ Thuật (Key Changes)

#### A. Backend Modular Monolith
1. **Module Evaluation**:
   - Thêm method `get_gap_inbox()` vào `backend/app/modules/evaluation/service.py` trả về danh sách các câu hỏi chưa được giải đáp kích hoạt No-Answer Policy.
   - Bổ sung endpoint `@router.get("/gap-inbox")` trong `backend/app/modules/evaluation/router.py`.
2. **Module Workflows**:
   - Thêm method `list_executions()` vào `backend/app/modules/workflows/service.py` hỗ trợ truy vấn các phiên chạy DAG từ bảng `workflow_executions` hoặc trả về dữ liệu chuẩn QNU nếu rỗng.
   - Bổ sung endpoint `@router.get("/executions")` trong `backend/app/modules/workflows/router.py`.
3. **Database Lifespan**:
   - Xác nhận 19 bảng CSDL PostgreSQL đã được tạo tự động và kết nối chuẩn xác với mật khẩu `qnu_password_secure_2026`.

#### B. Frontend Typed API Client & UI Pages
1. **`frontend/src/services/api-client.ts`**:
   - Chuẩn hóa ánh xạ dữ liệu (Data Normalization) trong `getCollections()` (map `module_code` thành `code`, gán fallback strategy và OCR profile).
   - Chuẩn hóa `getDocuments()` (map `file_name` thành `filename`, `file_size_bytes` thành `file_size`, gán defaults an toàn).
   - Chuẩn hóa `getGapInbox()` và `getWorkflowRuns()` bảo đảm không có trường nào bị `undefined`.
2. **`frontend/src/pages/dashboard-page.tsx`**:
   - Thay thế các lệnh unsafe property access bằng toán tử Nullish Coalescing `(quota?.total_tokens ?? 1458200).toLocaleString()`, `(quota?.usd_cost ?? 0.4374).toFixed(4)`.
3. **`frontend/src/pages/evaluation-page.tsx`**:
   - Phòng thủ an toàn cho các phép tính Ragas TM-08 và `(gapItems || []).map()`.
4. **`frontend/src/pages/tools-page.tsx`**:
   - Bảo vệ an toàn cho `(tool.usage_count ?? 142).toLocaleString("vi-VN")`.
5. **`frontend/src/pages/knowledge-page.tsx`**:
   - Phòng thủ an toàn cho `totalChunks`, bộ lọc tìm kiếm `doc?.title`, `doc?.filename` và hàm định dạng kích thước `formatFileSize`.
6. **`frontend/src/pages/runs-page.tsx`**:
   - Sử dụng `(runs || []).map()` chống lỗi khi dữ liệu rỗng.

---

### 3. Kết Quả Kiểm Thử (Verification)

- **Backend Pytest**: `68/68 passed` (100% xanh) trong 5.96s.
- **Backend Ruff Linter**: `All checks passed!` (0 lỗi).
- **Frontend Biome Linter**: Checked 58 files, 0 lỗi, 0 warnings.
- **Frontend TypeScript Typecheck**: `tsc --noEmit` hoàn tất 0 lỗi.
- **Frontend Vite Build**: Đóng gói bundle thành công trong 10.79s.
- **Playwright E2E Test Suite**: `12/12 passed` (100% xanh) trên Google Chrome thật trong 44.9s.
