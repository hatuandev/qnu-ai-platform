# NHẬT KÝ PHIÊN LÀM VIỆC — Cổng Trích Xuất & Biểu Mẫu Hành Chính (Kế Thừa QNU-AI-Core)
**Ngày thực hiện**: 2026-09-16 | **Thời gian**: 23:00 - 23:35 (UTC+7)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Triển khai Lựa chọn A từ kế hoạch kế thừa `qnu-ai-core` — Nâng cấp toàn diện phân hệ Cổng Công Cụ (`/tools`) thành Studio Xuất Bản Tài Liệu & Quản Trị Phôi Mẫu Hành Chính Chuẩn QNU.

---

## 1. Bối Cảnh & Động Lực Kỹ Thuật
Dự án `qnu-ai-core` có các công cụ trích xuất Word NĐ 30, ma trận đề thi Bloom và truy vấn UIS rất đặc thù cho khối đại học nhưng giao diện còn đơn giản, chưa mang lại trải nghiệm tương tác trực quan ("What You See Is What You Get"). Phiên làm việc này đã nâng cấp toàn diện phân hệ Công Cụ trên `qnu-ai-platform` với 4 phân hệ chuyên biệt:
1. **Docx NĐ 30 Editor with Live Paper Sheet Preview**: Trình soạn thảo văn bản hành chính kèm khung xem trước tờ giấy A4 trực quan mô phỏng chân thực quy chuẩn Nghị định 30/2020/NĐ-CP (căn lề 20-20-30-15mm, phông Times New Roman, kẻ chân quốc hiệu/tiêu ngữ và bảng chữ ký), hỗ trợ xuất file Word `.docx` tải về trực tiếp.
2. **Bloom Taxonomies Exam Matrix & Excel Exporter**: Trình thiết kế ma trận phân phối câu hỏi thi theo 4 cấp độ tư duy Bloom (Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao), tự động tính tổng câu, tổng điểm và biểu đồ thanh tỷ lệ phân bổ nhận thức trực quan, xuất file bảng tính Excel `.xlsx`.
3. **Live UIS Admissions Explorer**: Cổng tra cứu dữ liệu điểm chuẩn 3 năm gần nhất, tổ hợp môn, chỉ tiêu và học phí các ngành đào tạo ĐH Quy Nhơn thời gian thực.
4. **Administrative Templates Library**: Thư viện 6 phôi mẫu văn bản nhà trường kèm danh sách placeholder và tính năng **"Nạp Vào Form Soạn Thảo (1-Click Fill)"** giúp chuyển đổi tức thì giữa phôi mẫu và bản thảo hoàn chỉnh.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật & Chi Tiết Triển Khai |
| :--- | :---: | :--- |
| [`frontend/src/components/admin/docx-nd30-editor.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/docx-nd30-editor.tsx) | **Tạo mới** | Component soạn thảo văn bản hành chính 2 cột: Form cấu hình thông số (Loại VB, Đơn vị, Số ký hiệu, Trích yếu, Nội dung các đoạn, Nơi nhận, Người ký) và Tờ giấy A4 trực quan (`nd30-paper-preview`) với thiết kế đổ bóng giấy thật `bg-white shadow-xl border`. Nút xuất file Word `.docx` và tải về tức thì qua Blob URL. |
| [`frontend/src/components/admin/bloom-matrix-editor.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/bloom-matrix-editor.tsx) | **Tạo mới** | Component thiết kế ma trận đề thi Bloom: Ribbon thông tin học phần, Bảng nhập liệu phân bổ 4 cấp độ nhận thức theo từng chủ đề, Biểu đồ thanh tỷ lệ nhận thức 4 màu tự động tính toán tổng số câu/điểm, và nút xuất file Excel `.xlsx` chuẩn khảo thí. |
| [`frontend/src/components/admin/uis-admissions-explorer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/uis-admissions-explorer.tsx) | **Tạo mới** | Component tra cứu tuyển sinh UIS: Bộ lọc ngành nhanh, thẻ chi tiết khoa/bậc đào tạo, lịch sử điểm chuẩn 3 năm gần nhất với indicator tăng giảm, danh sách tổ hợp xét tuyển (A00, A01, D01, D07), mức học phí tín chỉ & chính sách miễn 100% học phí theo NĐ 116. |
| [`frontend/src/components/admin/administrative-templates-view.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/administrative-templates-view.tsx) | **Tạo mới** | Component thư viện 6 phôi mẫu văn bản QNU: Bộ lọc phân loại (Tờ trình, Quyết định, Thông báo, Kế hoạch, Đề thi, Công văn), thẻ hiển thị placeholders, nút sao chép phôi mẫu và nút **"Nạp Vào Form (1-Click Fill)"** kích hoạt callback chuyển tab và tự động điền form. |
| [`frontend/src/pages/tools-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/tools-page.tsx) | **Nâng cấp** | Tích hợp 4 Tabs chuyên môn kết nối liền mạch các components trên; hỗ trợ click chọn Card trên Header để chuyển thẳng tới Tab tương ứng; xử lý callback nạp phôi mẫu từ Tab Phôi mẫu sang Tab Soạn thảo Word NĐ 30. |
| [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts) | **Cập nhật** | Bổ sung DTO `ToolExecuteRequest`, `ToolExecuteResponse`, `AdministrativeTemplate`, `UisMajorInfo`; mảng dữ liệu mẫu `ADMINISTRATIVE_TEMPLATES` (6 phôi mẫu) và `UIS_MAJORS_DATABASE` (6 ngành); phương thức `executeTool(req)` kết nối API `/platform/v1alpha1/tools/execute` kèm Smart Offline Simulation Fallback. |
| [`frontend/playwright.config.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/playwright.config.ts) | **Cập nhật** | Thiết lập `reuseExistingServer: true` giúp tái sử dụng instance Vite dev server trên cổng 3001, giảm đáng kể thời gian khởi động E2E test suite. |
| [`frontend/tests/e2e/08_tools_and_templates_export.spec.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/tests/e2e/08_tools_and_templates_export.spec.ts) | **Tạo mới** | Bộ kiểm thử E2E tự động hóa 3 kịch bản: (1) Soạn thảo văn bản NĐ 30, kiểm tra tờ giấy A4 trực quan và xuất Word `.docx`; (2) Thiết kế ma trận đề thi Bloom, kiểm tra thanh tỷ lệ và xuất Excel `.xlsx`; (3) Tra cứu dữ liệu UIS và nạp phôi mẫu 1-click vào form soạn thảo. |

---

## 3. Kết Quả Kiểm Thử Nghiệm Thu (Verification)

### 3.1. Kiểm Tra Tĩnh & Clean Code (Mục 8 AGENTS.md)
- **Biome Linter**:
  ```bash
  npm run lint
  # Checked 68 files in 105ms. No fixes applied. (0 errors)
  ```
- **TypeScript Typecheck**:
  ```bash
  npm run typecheck
  # tsc --noEmit: 0 errors
  ```
- **Vite Production Build**:
  ```bash
  npm run build
  # ✓ built in 9.18s (dist/assets/index-ZacIoXU8.js: 1,200.11 kB)
  ```
- **Backend Ruff Linter**:
  ```bash
  uv run ruff check .
  # All checks passed!
  ```

### 3.2. Kiểm Thử Tự Động Hóa E2E (Playwright trên Google Chrome)
```bash
npx playwright test tests/e2e/08_tools_and_templates_export.spec.ts --project="Google Chrome"
```
**Kết quả**: **3/3 Tests Passed (11.7s)**
- `TC-TOOL-01`: Formats administrative document under Decree 30 with live paper sheet and exports Word — **PASS (2.5s)**
- `TC-TOOL-02`: Designs Bloom exam matrix with visual distribution bar and exports Excel — **PASS (3.0s)**
- `TC-TOOL-03`: Queries live UIS admissions data and loads administrative template with 1-click fill — **PASS (4.4s)**

### 3.3. Minh Chứng Ảnh Chụp Màn Hình (Artifacts)
1. `tools_nd30_paper_preview.png`: Tờ giấy A4 trực quan chuẩn thể thức Nghị định 30/2020/NĐ-CP.
2. `tools_bloom_exam_matrix.png`: Ma trận phân bổ 4 cấp độ nhận thức Bloom và thanh tỷ lệ đề thi.
3. `tools_templates_library.png`: Thư viện phôi mẫu hành chính QNU với tính năng nạp 1-click vào form.
