# Nhật Ký Công Việc: Triển Khai Màn Hình Chi Tiết Provider Riêng Biệt & Toggle Switch Bật/Tắt

- **Ngày thực hiện**: 2026-09-16 11:30 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Khi click vào Card Provider thì chuyển sang Màn hình Chi tiết riêng biệt để không gian hiển thị rộng rãi, thoáng đãng, mang lại trải nghiệm UX tốt nhất (theo chuẩn tham chiếu `qnu-ai-core`). Bổ sung và đồng bộ tính năng Bật/Tắt (Toggle Switch) Provider ở cả danh sách tổng quan và Header màn hình chi tiết.

---

## 1. Bối Cảnh & Phân Tích Kỹ Thuật

Trước đây:
- Danh sách Provider gộp chung hiển thị trong Card hoặc bật một modal nhỏ để quản lý Key Pool, gây cảm giác chật chội khi xem bảng nhiều keys, thống kê quota, hay quản lý model tags.
- Nút Bật/Tắt Provider dùng dạng Badge text chưa mang tính trực quan cao như một công tắc Toggle Switch chuẩn UX.

Giải pháp nâng cấp theo chuẩn `qnu-ai-core`:
1. **Điều Hướng & Không Gian Màn Hình Chi Tiết (Detail View)**:
   - Khi click vào Card Provider ở `/models`, kích hoạt chuyển trang sang `/models/:id`.
   - Màn hình Chi tiết hiển thị toàn trang rộng rãi với Breadcrumb điều hướng quay lại danh sách (`← Quay lại danh sách Nhà cung cấp / [Tên Provider]`).
   - Hero Header Card: Icon Provider to, tên Provider, Type badge, Endpoint URL với nút Copy 1-click, **Toggle Switch Bật Hoạt Động**, Nút Test Kết Nối (Ping latency ms), Nút Chỉnh Sửa, và Nút Xóa.
   - Khối Nhóm Khóa API (Key Pool & Failover): Chiếm 2/3 không gian màn hình, bảng danh sách các key trong nhóm (Priority `#1`, `#2`, Masked Key, Quota Progress bar, Badge trạng thái `Sẵn Sàng`, `Cooldown 429`, `Hết Quota`, `Đã Tắt`), Nút Test key, Switch bật/tắt từng key, Nút Xóa key, Nút `⚡ Mô Phỏng Xoay Vòng Key (Test 429 Failover)`, và Form thêm key mới.
   - Khối Mô Hình Khả Dụng (Models Manager): Quản lý danh sách model sạch, thêm/xóa tag model, kèm **Gợi ý 1-click thêm Model tiêu chuẩn** theo từng Provider type từ Presets.
2. **Toggle Switch Bật/Tắt Provider Trực Tiếp**:
   - Ở Card tổng quan: Có Toggle Switch góc trên bên phải, chặn sự kiện nổi bọt (`e.stopPropagation()`) để khi click Switch chỉ bật/tắt trạng thái mà không bị trigger mở Màn hình Chi tiết.
   - Ở Header Chi tiết: Có Toggle Switch lớn kèm nhãn `Bật Hoạt Động` / `Tạm Dừng`, phản hồi tức thì và đồng bộ qua API `POST /modelops/providers/{id}/toggle`.

---

## 2. Chi Tiết Thay Đổi Mã Nguồn

| Tệp | Thay Đổi |
| :--- | :--- |
| [`frontend/src/App.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/App.tsx) | Cập nhật router SPA hỗ trợ cả `/models` và `/models/:id`: `if (currentPath === "/models" || currentPath.startsWith("/models/")) { return <ModelOpsPage currentPath={currentPath} onNavigate={handleNavigate} />; }`. |
| [`frontend/src/pages/modelops-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/modelops-page.tsx) | Refactor toàn diện: Quản lý 2 chế độ hiển thị `Overview View` (danh sách Card có Switch bật/tắt, click card sang chi tiết) và `Detail View` (màn hình chi tiết toàn diện rộng rãi, thoáng đãng với Hero Header, Toggle Switch, Key Pool 2/3 không gian, Models manager, và Thông số kỹ thuật). |
| [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts) | Bổ sung `suggested_models?: string[]` vào `ProviderPreset` và thêm hàm `toggleProviderKey()`. |
| [`frontend/tests/e2e/04_modelops_key_pool.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/04_modelops_key_pool.spec.ts) | Cập nhật 3 test cases E2E kiểm tra Overview Cards có Toggle Switch, Click Card chuyển sang Detail View, thao tác Key Pool form và nút quay lại danh sách. |

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Frontend Linting & Style**:
   ```bash
   npm run lint
   # Checked 58 files — 0 errors
   ```
2. **Frontend Typecheck**:
   ```bash
   npm run typecheck
   # tsc --noEmit — 0 errors
   ```
3. **Frontend Build**:
   ```bash
   npm run build
   # vite build ✓ built in 8.95s (1,050 kB bundle)
   ```
4. **Backend Linting**:
   ```bash
   uv run ruff check .
   # All checks passed! — 0 errors
   ```
5. **Backend Pytest**:
   ```bash
   uv run --extra dev pytest -v
   # 70 passed in 15.01s (100% tests pass)
   ```
6. **Playwright E2E Tests**:
   ```bash
   npx playwright test
   # 15 passed in 35.2s (100% E2E tests pass)
   ```
