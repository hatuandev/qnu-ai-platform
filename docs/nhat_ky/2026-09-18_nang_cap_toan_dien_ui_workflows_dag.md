# NHẬT KÝ LÀM VIỆC: NÂNG CẤP TOÀN DIỆN UI/UX PHÂN HỆ QUY TRÌNH WORKFLOW DAG THÀNH ENTERPRISE CONTROL CENTER

- **Thời gian**: 2026-09-18 09:45 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phiên làm việc số**: #80

---

## 1. Bối Cảnh & Vấn Đề Giao Diện Cần Khắc Phục

Sau khi triển khai hạ tầng Workflow Control Plane và Seeder CSDL ở phiên #78, việc kiểm tra thực tế giao diện người dùng trên màn hình `http://localhost:3001/workflows` và `/canvas` cho thấy các khiếm khuyết UI/UX sau:
1. **Lỗi Vỡ Giao Diện Thanh Công Cụ (Header Collision & Narrow Wrap)**:
   - Trên thanh header của DAG Canvas Studio, hệ thống cố gắng hiển thị đồng thời:
     * Tiêu đề `DAG Studio • Tên workflow`.
     * 5 nút tab chọn workflow có tên đầy đủ tiếng Việt rất dài (*"Trợ lý Ngân hàng Câu hỏi & Đề thi QNU"*, *"Trợ lý Quy chế QNU"*, *"Trợ lý Soạn thảo QNU"*, *"Trợ lý Tuyển sinh QNU"*, *"Trợ lý Thư viện QNU"*).
     * 10 nút bấm chức năng (`+ Thêm node`, `Chạy thử`, `Lưu nháp`, `Kiểm tra`, `Xuất bản`, `Lịch sử`, `Sao chép link`, `Minimap`, `Fullscreen`, `Studio Chat`).
   - Hậu quả: Không gian flexbox bị co thắt nghẹt thở, tab đầu tiên bị nén thành một cột hẹp vài chục pixel, chữ wrap thành 5 dòng (*"hàng \n Câu \n hỏi & \n Đề thi \n QNU"*) màu xanh đậm đè lên icon `Network` và thanh điều hướng, gây vỡ bố cục nghiêm trọng.
2. **Thiếu Màn Hình Danh Mục Master-Detail (`/workflows`)**:
   - Khi người dùng truy cập trực tiếp đường dẫn `http://localhost:3001/workflows`, hệ thống không có trang danh mục tổng quan mà rơi vào fallback rỗng.
   - Chưa đáp ứng tôn chỉ **Master-Detail Deep Routing Pattern** quy định tại Mục 4.5 của [`AGENTS.md`](../../AGENTS.md): *"Quy chuẩn 1 Domain = List Page (`/workflows`) + Dedicated Detail Pages (`/workflows/:id`)"*.
3. **Thanh Sidebar Chưa Có Mục Truy Cập Nhanh**:
   - Sidebar chỉ có `/nodes` ("Thư Viện DAG Nodes") và `/runs` ("Lịch Sử Thực Thi DAG"), thiếu mục điều hướng trực tiếp tới phân hệ Quy trình DAG.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. Xây Dựng Trang Danh Mục Quy Trình Master View (`/workflows`)
- **Tệp mới**: [`frontend/src/pages/workflows-page.tsx`](../../frontend/src/pages/workflows-page.tsx)
- **Thanh Chỉ Số Hiệu Năng Thời Gian Thực (KPI Metrics Strip)**:
  * `totalWorkflows`: Tổng số quy trình chuẩn QNU đang quản lý (5 quy trình).
  * `activeWorkflows`: Tỉ lệ quy trình đang ở trạng thái active phục vụ thực tế (100% v1.0.0).
  * `avgNodes`: Độ phức tạp trung bình của đồ thị DAG (nodes / workflow).
  * `TM-08`: Huy hiệu xác nhận toàn bộ đồ thị tuân thủ trích dẫn và Anti-Hallucination Guardrail.
- **Bộ Lọc & Tìm Kiếm Đa Chiều**:
  * Tìm kiếm thời gian thực theo tên quy trình, mã module hoặc mô tả nghiệp vụ.
  * Bộ nút lọc theo 5 lĩnh vực chuyên môn: Tuyển sinh (`admission`), Quy chế (`regulation`), Thư viện (`library`), Soạn thảo NĐ 30 (`drafting`), Khảo thí Bloom (`question_bank`).
- **5 Thẻ Card Quy Trình Hiện Đại (`WorkflowCard`)**:
  * Icon và màu nhận diện chuyên môn, mã module `module_code`, badge version (`v1.0.0`), badge trạng thái xuất bản.
  * Tóm tắt kiến trúc DAG: Số nodes, số kết nối connections, mã định danh.
  * Trợ lý AI liên kết: Tên trợ lý và liên kết cấu hình nhanh sang `/assistants/:id`.
  * Bộ 3 nút tác vụ:
    - **[Mở DAG Studio]**: Chuyển hướng sâu tới `/workflows/:id`.
    - **[Thử nghiệm]**: Chuyển hướng tới Studio Chat của Trợ lý tương ứng.
    - **[Lịch sử]**: Mở modal phiên bản xuất bản và phục hồi rollback.
- **Tích Hợp Modal Lịch Sử Phiên Bản & Rollback**:
  - Gắn kết `WorkflowVersionHistoryDialog` cho phép xem lịch sử và khôi phục rollback phiên bản ngay tại trang danh mục mà không cần vào Canvas.

### 2.2. Đại Tu Toàn Diện Thanh Header DAG Canvas Studio
- **Tệp**: [`frontend/src/pages/dag-canvas-page.tsx`](../../frontend/src/pages/dag-canvas-page.tsx)
- **Triệt tiêu 100% lỗi vỡ layout**:
  * Xóa bỏ hoàn toàn dãy 5 tab nút bấm dài ngoằng.
  * Thay thế bằng **Workflow Switcher Dropdown** `<Select>` tinh gọn, hiển thị icon chuyên môn và tên quy trình cùng dirty badge indicator khi có thay đổi chưa lưu.
  * Bổ sung nút quay lại (`<ArrowLeft>`) điều hướng mượt mà về trang danh mục `/workflows`.
- **Tái cấu trúc Toolbar thành 3 khối phân định rõ ràng**:
  * *Khối Biên soạn (Authoring)*: `[+ Thêm node]`, `[▶ Chạy thử]` (nút chính nổi bật), `[💾 Lưu nháp]` (tự động đổi màu hổ phách cảnh báo khi dirty).
  * *Khối Control Plane*: `[🛡 Kiểm tra]` (static compiler), `[🚀 Xuất bản]` (immutable versioning), `[🕒 Lịch sử]` (modal rollback).
  * *Khối Tiện ích*: `[Sao chép link]`, `[Sao chép JSON]`, `[Tải lại]`, `[Studio Chat]`.
- **Dải Thông Số Bổ Trợ**:
  * Hiển thị breadcrumb và thông số bản nháp rN, số nodes, số connections.

### 2.3. Đồng Bộ Menu Sidebar Navigation & Routing
- **Tệp**: [`frontend/src/navigation/config.ts`](../../frontend/src/navigation/config.ts)
  * Thêm mục *"Quy Trình Workflow DAG"* (`/workflows`, icon `Workflow`, badge `5 DAGs`) vào phần *Kho Tri Thức & Quy Trình*.
- **Tệp**: [`frontend/src/App.tsx`](../../frontend/src/App.tsx)
  * Khai báo route `/workflows` render `WorkflowsPage`.
  * Điều hướng sâu `/workflows/:id` tiếp tục render `DAGCanvasPage`.

### 2.4. Đồng Bộ Tài Liệu Quy Trình Hệ Thống
- **Tệp**: [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md)
  * Bổ sung **Mục 7: Kiến Trúc Giao Diện Phân Hệ Quy Trình Workflow DAG (`/workflows` & `/workflows/:id`)** đặc tả chi tiết kiến trúc 2 tầng Master-Detail và thanh Header DAG Studio mới.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

Mọi bài kiểm tra trước khi hoàn tất đều đạt chuẩn 100% Zero Error:

1. **Frontend Biome Linter**:
   ```bash
   npm run lint
   # Checked 93 files in 130ms. No fixes applied. 0 lỗi.
   ```
2. **Frontend Typecheck (TypeScript)**:
   ```bash
   npm run typecheck
   # tsc --noEmit: exit code 0. 0 lỗi typecheck.
   ```
3. **Frontend Production Packaging**:
   ```bash
   npm run build
   # vite v6.4.3 building for production...
   # ✓ built in 8.17s (dist/ index-BwQ4KSom.js, index-cr_6_1s-.css).
   ```
4. **Backend Test Suite**:
   ```bash
   uv run --extra dev pytest tests/test_workflows.py -v
   # 18 passed in 5.01s (100% passed).
   ```
5. **Backend Code Style & Linter**:
   ```bash
   uv run ruff check .
   # All checks passed! 0 lỗi.
   ```
6. **Kiểm Toán Zero Mojibake**:
   ```bash
   python scripts/check_mojibake.py
   # Quét 227 tệp — 100% sạch, không phát hiện bất kỳ ký tự rác hay vỡ font tiếng Việt.
   ```
7. **Kiểm Tra Trực Quan Giao Diện Trình Duyệt**:
   - Sử dụng subagent trình duyệt truy cập `http://localhost:3001/workflows` và `http://localhost:3001/workflows/admissions-assistant`.
   - Xác thực: Trang danh mục hiển thị đầy đủ 4 KPI metrics, bộ lọc tìm kiếm hoạt động mượt mà, 5 thẻ workflow hiển thị đầy đủ kiến trúc DAG và liên kết trợ lý.
   - **Xác thực dứt điểm bug**: Thanh header DAG Canvas Studio hoàn toàn sạch sẽ, không còn tình trạng 5 tab dài chen chúc hay cột text xanh lá cây che icon. Dropdown chọn workflow hoạt động ổn định.
   - Bản ghi video lưu tại artifact: `workflows_ui_demo_1789699203962.webp`.

---

## 4. Kết Luận

Phiên làm việc #80 đã giải quyết triệt để lỗi visual collision nghiêm trọng trên thanh công cụ DAG Studio, đồng thời hoàn thiện 100% kiến trúc Master-Detail cho toàn bộ phân hệ Quy trình Workflow DAG theo đúng chuẩn Enterprise QNU.
