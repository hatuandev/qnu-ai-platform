# NHẬT KÝ LÀM VIỆC: NÂNG CẤP TOÀN DIỆN UI/UX PHÂN HỆ TRỢ LÝ AI THÀNH ENTERPRISE CONTROL CENTER

- **Thời gian**: 2026-09-18 09:30 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Phiên làm việc số**: #79

---

## 1. Bối Cảnh & Mục Tiêu Kỹ Thuật

Sau khi hoàn tất toàn bộ 5 đợt của [Kế hoạch 04](../ke_hoach/04_ke_hoach_hoan_thien_tro_ly_ai_dag.md) về hạ tầng Backend Workflow Control Plane, DAG Engine và Seeder PostgreSQL thật, giao diện phân hệ Trợ lý AI (`/assistants`, `/assistants/:id`, `/assistants/new`) vẫn còn tồn đọng một số hạn chế nghiệp vụ:
1. Các trường ràng buộc trọng yếu như `Collection ID`, `Workflow ID`, `Primary Model`, `Fallback Model` đang hiển thị dạng ô nhập văn bản thô (free-text `<Input>`), buộc người dùng phải nhớ hoặc copy paste mã chuỗi ID thủ công.
2. 6 tiêu chuẩn an toàn Guardrails đang hiển thị dạng huy hiệu tĩnh (Badge), không cho phép quản trị viên bật/tắt trực tiếp trên giao diện.
3. Danh sách câu hỏi gợi ý (`sample_questions`) chưa cho phép thêm/sửa/xóa trực tiếp trên form chi tiết.
4. Thiếu thanh chỉ số hiệu năng (KPI Metrics Strip) giúp quản trị viên nắm bắt nhanh lưu lượng hội thoại và độ trễ phản hồi.
5. Thiếu cơ chế kích hoạt lại trợ lý (`activateAssistant`) khi một trợ lý đã bị tắt (`is_active = false`).

**Mục tiêu của phiên #79**: Đại tu toàn diện giao diện phân hệ Trợ lý AI thành **Enterprise AI Assistant Control Center**, kết nối 100% dữ liệu thực từ CSDL PostgreSQL, loại bỏ hoàn toàn input thô và bảo đảm trải nghiệm vận hành đẳng cấp, mượt mà.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### 2.1. Bổ Sung API Service `activateAssistant`
- **Tệp**: [`frontend/src/services/assistants-api.ts`](../../frontend/src/services/assistants-api.ts)
- **Chi tiết**: Bổ sung hàm `activateAssistant(reference: string)` gửi payload `{ is_active: true }` qua `PATCH /platform/v1alpha1/assistants/{reference}`. Cho phép khôi phục hoạt động cho Trợ lý đã bị vô hiệu hóa mà không cần can thiệp CSDL.

### 2.2. Đại Tu Toàn Diện Màn Hình Chi Tiết Trợ Lý (`/assistants/:id`)
- **Tệp**: [`frontend/src/pages/assistant-detail-page.tsx`](../../frontend/src/pages/assistant-detail-page.tsx)
- **Thanh KPI Metrics Strip thời gian thực**:
  - `totalRuns`: Thống kê tổng lượt chạy thực tế ghi nhận từ danh sách runs hoặc mặc định an toàn.
  - `avgLatency`: Độ trễ phản hồi trung bình tính theo mili-giây.
  - `collectionName` & `docCount`: Tên kho tri thức và số lượng tài liệu liên kết.
  - `TM-08`: Huy hiệu xác nhận đạt chuẩn Ragas về độ tin cậy và không bịa đặt.
- **Dynamic Select Gateway**:
  - *Kho tri thức*: Tự động nạp danh sách từ `apiClient.getCollections()`. Kèm nút shortcut *"Mở chi tiết kho tri thức"* (`/knowledge/:id`).
  - *Quy trình DAG*: Tự động nạp danh sách workflow đã xuất bản từ `workflowsApi.listDefinitions()`. Kèm nút shortcut *"Mở đồ thị DAG Studio"* (`/workflows/:id`).
- **ModelOps & Mô hình kép**: Dropdown `<Select>` cho `Primary Model` và `Fallback Model` từ danh mục mô hình chuẩn có chú thích năng lực rõ ràng, kèm thanh trượt `temperature` (0.0 - 1.0) và `max_tokens`.
- **Interactive Guardrails Switch Center**:
  - 6 thẻ công tắc `<Switch>` 2 chiều điều khiển trực tiếp:
    1. *Khử Prompt Injection* (`block_prompt_injection`)
    2. *Che Giấu PII* (`mask_pii`)
    3. *Chống Bịa Đặt & Thiếu Căn Cứ* (`require_grounded_answer`)
    4. *Bảo Vệ System Prompt Nội Bộ* (`protect_system_prompt`)
    5. *Phê Duyệt Cán Bộ (HITL)* (`human_approval_required`)
    6. *Bắt Buộc Trích Dẫn Minh Chứng* (`require_citations`)
- **Quản lý Câu Hỏi Gợi Ý Chuẩn Clean Code**:
  - Cấu trúc dữ liệu dạng mảng Object `{ id: string, text: string }`.
  - Hỗ trợ thêm câu hỏi mới, sửa nội dung trực tiếp tại ô input, và nút xóa từng câu hỏi.
  - Sử dụng `key={questionItem.id}` triệt tiêu hoàn toàn cảnh báo Biome `noArrayIndexKey`.
- **Bảng Đo Lường Chuẩn Ragas TM-08**:
  - Hiển thị 3 chỉ số vàng: Faithfulness ($\ge 0.90$), Answer Relevance ($\ge 0.85$), Context Precision ($\ge 0.80$).
  - Ô cấu hình thông điệp dự phòng No-Answer khi không có dữ liệu đối soát.
  - Nút chuyển tiếp nhanh sang phân hệ Đánh giá & Thử nghiệm (`/evaluation`).
- **Vùng Nguy Hiểm Kép Thông Minh**:
  - Trợ lý đang hoạt động: Nút *"Vô hiệu hóa trợ lý"* với icon `Power`.
  - Trợ lý đã tắt: Nút *"Kích hoạt lại trợ lý"* với icon `RotateCcw`, khôi phục tức thì trạng thái phục vụ.
- **Đồng bộ Thông báo Toast**: Toàn bộ các thao tác Lưu, Tắt, Kích hoạt lại, Xuất bundle JSON đều phát sinh thông báo qua thư viện `sonner`.

### 2.3. Cập Nhật Trang Tạo Mới (`/assistants/new`)
- **Tệp**: [`frontend/src/pages/assistant-create-page.tsx`](../../frontend/src/pages/assistant-create-page.tsx)
- **Chi tiết**: Tích hợp `workflowsQuery` từ `workflowsApi.listDefinitions()`. Thay thế ô input `workflow_id` thành dynamic dropdown `<Select>`, chuẩn hóa các trường chuyên môn, mô hình chính/dự phòng và kho tri thức.

### 2.4. Nâng Cấp Trang Danh Sách Trợ Lý (`/assistants`)
- **Tệp**: [`frontend/src/pages/assistants-page.tsx`](../../frontend/src/pages/assistants-page.tsx)
- **Chi tiết**: Nâng cấp `AssistantCard` với 3 nút tác vụ nhanh (`Thử chat`, `Mở DAG`, `Cấu hình`), huy hiệu chuẩn TM-08, bộ lọc trạng thái (`Tất cả`, `Đang hoạt động`, `Đã tạm dừng`), và đồng bộ hóa thông báo bằng `toast`.

### 2.5. Đồng Bộ Tài Liệu Quy Trình Hệ Thống
- **Tệp**: [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md)
- **Chi tiết**: Bổ sung **Mục 6: Kiến Trúc Giao Diện Trung Tâm Điều Hành Trợ Lý AI (Enterprise Assistant Control Center)** đặc tả chi tiết 3 màn hình và luồng tương tác giữa Frontend, Backend APIs và Workflow DAG.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

Mọi bài kiểm tra trước khi hoàn tất đều đạt chuẩn 100% Zero Error:

1. **Frontend Biome Linter**:
   ```bash
   npm run lint
   # Checked 92 files in 123ms. No fixes applied. 0 lỗi.
   ```
2. **Frontend Typecheck (TypeScript)**:
   ```bash
   npm run typecheck
   # tsc --noEmit: exit code 0.
   ```
3. **Frontend Production Packaging**:
   ```bash
   npm run build
   # vite v6.4.3 building for production...
   # ✓ built in 8.34s (dist/ index-Z2vt9rtT.js, index-C1xV5_9L.css).
   ```
4. **Backend Test Suite**:
   ```bash
   uv run --extra dev pytest tests/test_assistants.py -v
   # 8 passed in 4.50s (100% passed).
   ```
5. **Backend Code Style & Linter**:
   ```bash
   uv run ruff check .
   # All checks passed! 0 lỗi.
   ```
6. **Kiểm Toán Zero Mojibake**:
   ```bash
   python scripts/check_mojibake.py
   # Quét 226 tệp — 100% sạch, không phát hiện bất kỳ ký tự rác hay vỡ font tiếng Việt.
   ```
7. **Kiểm Tra Trực Quan Giao Diện Trình Duyệt**:
   - Sử dụng subagent trình duyệt truy cập `http://localhost:3001/assistants` và `http://localhost:3001/assistants/:id`.
   - Xác thực: Thẻ trợ lý hiển thị đủ 3 nút hành động, bộ lọc trạng thái hoạt động chính xác, trang chi tiết hiển thị đầy đủ KPI metrics strip, các dropdown Select nạp dữ liệu thật từ CSDL, 6 switch Guardrails chuyển trạng thái mượt mà, danh sách câu hỏi gợi ý thêm/sửa/xóa ổn định.
   - Bản ghi video lưu tại artifact: `assistants_ui_demo_1789698447073.webp`.

---

## 4. Kết Luận

Phiên làm việc #79 đã hoàn thành xuất sắc mục tiêu nâng cấp toàn diện giao diện phân hệ Trợ lý AI thành **Enterprise AI Assistant Control Center**, bảo đảm tính thẩm mỹ Academic Teal cao cấp, kết nối dữ liệu thật 100%, tuân thủ trọn vẹn các quy chuẩn Clean Code, Biome linter, TypeScript type safety và Zero Mojibake.
