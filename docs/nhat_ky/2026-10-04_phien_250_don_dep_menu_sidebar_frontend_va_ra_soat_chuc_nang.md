# NHẬT KÝ LÀM VIỆC: DỌN DẸP MENU SIDEBAR FRONTEND VÀ RÀ SOÁT CHỨC NĂNG NỀN TẢNG

- **Thời gian**: 2026-10-04 11:40
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**:
  - Rà soát toàn bộ các phân hệ trên Sidebar của giao diện quản trị `frontend2`.
  - Khắc phục triệt để các liên kết chưa có Route (loại bỏ nguy cơ lỗi 404 cho người dùng).
  - Tinh gọn Sidebar thành 3 nhóm chức năng hoạt động 100% chuẩn Enterprise.

---

## 1. Hiện Trạng Rà Soát Trước Khi Tối Ưu

Trước phiên này, tệp cấu hình điều hướng `frontend2/src/navigation/config.ts` chứa 5 nhóm với 12 mục menu, trong đó có một số mục menu trỏ tới các đường link chưa được khởi tạo file Route trong TanStack Router:
1. `/conversations` (Hội Thoại & Handoff): Logic xem hội thoại hiện nằm trong Playground của từng Assistant; chưa có trang Master toàn sàn.
2. `/quality` (Chất Lượng & Lỗ Hổng): Chỉ số Ragas hiện nằm trên Dashboard và Tab Quality của Assistant; chưa có trang route riêng.
3. `/runs` (Giám Sát Thực Thi): Lịch sử thực thi hiện nằm trong Tab Runs của từng Assistant.
4. `/settings/integrations` (Tích Hợp & Kênh): Cấu hình widget và API channels nằm trong Tab Channels của Assistant.
5. `/capabilities/tools` (Cổng Công Cụ): Tools OpenAPI schema được quản lý trực tiếp trong Assistant Tools.

Khi người dùng click vào các mục này, hệ thống sẽ rơi vào trạng thái 404 / Route Not Found, ảnh hưởng đến trải nghiệm người dùng.

---

## 2. Các Thay Đổi Mã Nguồn & Tinh Gọn

### 2.1. Tinh Gọn Cấu Hình Điều Hướng (`frontend2/src/navigation/config.ts`)
- Loại bỏ các mục menu chưa có Route (`conversations`, `quality`, `runs`, `integrations`, `tools`).
- Tinh gọn Sidebar thành 3 nhóm chức năng cốt lõi hoạt động trơn tru 100%:
  1. **Tổng Quan**:
     - `Bảng Điều Khiển` (`/dashboard`): KPI sức khỏe hệ thống, Token Quota, Usage Stats, Quick Links.
  2. **Xây Dựng AI**:
     - `Trợ Lý AI` (`/assistants`): Master-Detail deep routing, 8 tabs cấu hình chuyên sâu.
     - `Kho Tri Thức` (`/knowledge`): Quản lý Collections, Ingestion, OCR Scan Studio, Fact Layer.
     - `Mô Hình & Provider` (`/models`): Quản trị ModelOps 4 Tab (Vision OCR, Vector, Xếp Hạng, Chat LLM), xoay tua Key Pool & Circuit Breaker.
  3. **Nâng Cao**:
     - `Thư Viện Nodes` (`/capabilities/nodes`): Quản lý danh mục các DAG nodes quy trình AI.
     - `Loại Văn Bản` (`/document-types`): Quản lý các mẫu văn bản hành chính trường ĐH Quy Nhơn.
     - `Design System` (`/design-system`): Bộ linh kiện UI Kit OKLCH Academic Teal.
- Dọn dẹp các Lucide icons không còn sử dụng (`History`, `MessagesSquare`, `Share2`, `ShieldCheck`, `Wrench`), bảo đảm 0 lỗi import dư thừa.

---

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)

- **Biên dịch Frontend (Vite Build)**:
  ```bash
  cmd /c "npm run build"
  ```
  - **Kết quả**: Exit code `0` (`✓ built in 10.82s`).
  - **Trạng thái**: 0 lỗi TypeScript, 0 lỗi cú pháp, toàn bộ bundle đóng gói thành công.
- **Kiểm tra liên kết**: 100% các mục menu hiển thị trên Sidebar hiện tại đều trỏ tới các trang thực thể hoạt động đầy đủ.

---

## 4. Trạng Thái & Công Việc Tiếp Theo

- **Trạng thái**: HOÀN THÀNH (100% Clean Navigation).
- **Kế hoạch tiếp theo**:
  - Khi có yêu cầu nghiệp vụ về trang giám sát tập trung toàn hệ thống, sẽ xây dựng các trang Master View cho `/conversations` (bảng theo dõi tất cả phiên chat trường), `/runs` (nhật ký thực thi toàn bộ workflows) và kích hoạt lại trên Sidebar.
