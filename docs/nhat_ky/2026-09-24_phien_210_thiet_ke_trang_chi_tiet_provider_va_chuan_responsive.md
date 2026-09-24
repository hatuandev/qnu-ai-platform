# NHẬT KÝ PHIÊN LÀM VIỆC #210
# Thời gian: 2026-09-24 10:05
# Nội dung: Thiết Kế Trang Chi Tiết Provider Độc Lập (/models/:providerId), Bổ Sung Quy Chuẩn Responsive & Nhãn Nút Ngắn Gọn Vào AGENTS.md

---

## 1. Mục Tiêu Phiên Làm Việc
1. **Khắc phục triệt để lỗi 404 Not Found** khi người dùng truy cập hoặc F5 tải lại trang chi tiết Provider `http://localhost:3000/models/prov_c9d9d380`.
2. **Thiết kế & Xây dựng Giao Diện Trang Chi Tiết Provider (`ProviderDetailPage`)** theo chuẩn **Master-Detail Deep Routing** (Mục 4.5 của `AGENTS.md`) trên `frontend2`.
3. **Bổ sung 2 Quy Chuẩn Bắt Buộc vào `AGENTS.md` & `qnu-frontend-architect`**:
   - Quy chuẩn 10: **Thiết kế Đa Thiết Bị & Responsive (Cross-Device & Responsive Standard)**.
   - Quy chuẩn 11: **Đặt Tên Nút Bấm & Nhãn Điều Khiển Ngắn Gọn (Concise Action Labels & Microcopy Standard)**.
4. **Tối ưu hóa toàn diện giao diện di động (Mobile Responsive UI)** dựa trên ảnh chụp thực tế từ iPhone của người dùng:
   - Sửa lỗi tràn và gập dòng Breadcrumb "Chi Tiết Provider".
   - Thu gọn padding, tinh chỉnh nút hành động Hero card (`Hoạt động`, `Kiểm tra`, `Xuất JSON`, `Sửa`, `Xóa`).
   - Xóa bỏ số đếm badge rườm rà trên tab header và rút gọn nhãn tabs con (`Mô hình`, `Khóa API`, `Chịu lỗi & Mạng`).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### A. Định Tuyến File-Based TanStack Router (`frontend2/src/routes/`)
- [`frontend2/src/routes/models.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/models.tsx): Chuyển thành layout route chứa `<Outlet />`.
- [`frontend2/src/routes/models.index.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/models.index.tsx): Tuyến khớp chính xác `/models/` hiển thị danh sách tổng quan (`ModelOpsPage`).
- [`frontend2/src/routes/models.$providerId.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/routes/models.$providerId.tsx): Tuyến động khớp `/models/:providerId` hiển thị `ProviderDetailPage`.

### B. Thành Phần Trang Chi Tiết [`ProviderDetailPage`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/features/modelops/provider-detail-page.tsx)
- Breadcrumb và nút quay lại danh sách (`ArrowLeft`) mượt mà, hỗ trợ Deep Linking qua URL.
- Dải KPI Telemetry rút gọn nhãn: "Mô hình", "Khóa API", "Độ trễ (Ping)", "Circuit Breaker" với chấm trạng thái nhấp nháy.
- Tab điều hướng rút gọn: "Mô hình", "Khóa API", "Chịu lỗi & Mạng", loại bỏ toàn bộ số đếm badge thừa.
- Hỗ trợ cuộn ngang (`overflow-x-auto`) không giật trang trên màn hình di động.

### C. Tối Ưu Header Hero [`ProviderDetailHeader`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend2/src/components/modelops/provider-detail-header.tsx)
- Ẩn badge phụ "Chi Tiết" trên màn hình hẹp (<640px) để chống ép tràn breadcrumbs.
- Thu gọn nhãn nút quay lại: `<span className="hidden sm:inline">Danh sách Provider</span><span className="sm:hidden">Provider</span>`.
- Rút gọn nhãn các nút bấm:
  - `Bật Hoạt Động` ➔ `Hoạt động` (kèm Switch).
  - `Test Kết Nối` ➔ `Kiểm tra` (kèm icon `Play`/`RefreshCw`).
  - `Chỉnh Sửa` ➔ `Sửa` (kèm icon `Pencil`).
  - `Xuất Toàn Bộ Cấu Hình JSON` ➔ `Xuất JSON`.
  - Nút Xóa dạng icon button tinh gọn.

### D. Chuẩn Hóa Nhãn Điều Khiển Tại `models-grid.tsx` & `key-pool-section.tsx`
- Đổi "Test Tất Cả" ➔ "Test tất cả".
- Đổi "Thêm Mô Hình (Add Model)" ➔ "Thêm model".
- Đổi "Test 429 Failover" ➔ "Thử Failover".
- Đổi "Test Khóa Này" ➔ "Kiểm tra".
- Đổi "Thêm Khóa / Đóng Form" ➔ "Thêm khóa / Đóng".
- Đổi "Lưu Khóa" ➔ "Lưu".

### E. Cập Nhật Tài Liệu Quy Chuẩn Cốt Lõi
- [`AGENTS.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/AGENTS.md): Bổ sung Mục 4.10 (Quy Chuẩn Thiết Kế Đa Thiết Bị & Responsive) và Mục 4.11 (Quy Chuẩn Đặt Tên Nút Bấm & Nhãn Điều Khiển Ngắn Gọn).
- [`.agents/skills/qnu-frontend-architect/SKILL.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/.agents/skills/qnu-frontend-architect/SKILL.md): Bổ sung Mục 3.7 và Mục 3.8 tương ứng.

### F. Tinh Giản Giao Diện: Loại Bỏ Hoàn Toàn Tab "Chịu Lỗi & Mạng"
- Theo phản hồi người dùng ("cái chịu lỗi mạng này không có tác dụng gì hết thì bỏ đi nhé"), đã loại bỏ hoàn toàn:
  - Tab "Chịu lỗi & Mạng" và icon `ShieldCheck` khỏi thanh tab điều hướng.
  - Khối hiển thị `ResiliencePolicyCard` và bảng `Thông số kỹ thuật` tĩnh không có tính năng tương tác.
  - Thẻ telemetry `Circuit: CLOSED` trong header, chỉ giữ lại độ trễ ping `ms` thực tế.
  - Xóa bỏ file dead code: `frontend2/src/components/modelops/resilience-policy-card.tsx`.
- Giao diện trang chi tiết giờ chỉ tập trung trọn vẹn vào 2 khối nghiệp vụ cốt lõi:
  1. **Mô hình** (Models Grid)
  2. **Khóa API** (Key Pool)

---

## 3. Kết Quả Kiểm Thử (Verification)
- **TypeScript**: `npm run typecheck` ➔ **0 lỗi**.
- **Biome Linter**: `npx @biomejs/biome check` trên các file đã sửa ➔ **0 lỗi, 0 cảnh báo**.
- **Vite Build**: `npm run build` ➔ **Thành công (1.49s)**, loại bỏ triệt để dead code.

