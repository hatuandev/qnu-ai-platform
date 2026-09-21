# NHẬT KÝ LÀM VIỆC — PHIÊN #170
**Thời gian**: 2026-09-21 10:40 (UTC+7)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu**: Khắc phục lỗi Publish Gate chặn Trợ lý Tuyển sinh (đưa điểm sẵn sàng lên 100%), và tích hợp hệ thống thông báo Toast popup toàn cục hiển thị phản hồi tức thì khi người dùng bấm nút [Lưu thay đổi] trên giao diện Quản trị Trợ lý AI.

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

1. **Lỗi Chặn Xuất Bản (Publish Gate 71% - Blocked)**:
   - Người dùng tải lên tệp tri thức vào Kho Tuyển sinh thành công (16 chunks, trạng thái `ready`), nhưng khi vào Trợ lý Tuyển sinh lại bị báo cờ đỏ:
     - ❌ *Kho tri thức 'col_admissions' chưa có tài liệu đối soát sẵn sàng (25/100)*: Do `readiness.py` chỉ tìm `status in ["processed", "approved"]`, trong khi tài liệu sau khi bóc tách & nạp Qdrant mang trạng thái `ready` hoặc `completed`.
     - ❌ *Công cụ chưa đăng ký trong Tool Registry: admissions.fact_lookup (30/100)*: Do cấu hình trợ lý lưu mã công cụ legacy, trong khi Tool Registry đăng ký mã chuẩn `lookup_admission_score`.
2. **Không Hiển Thị Thông Báo Khi Bấm [Lưu thay đổi]**:
   - Khi người dùng bấm nút `[Lưu thay đổi]`, request gửi API thành công và gọi `toast.success()`, nhưng giao diện hoàn toàn không có bất kỳ thông báo popup nào hiện lên do thành phần `<Toaster />` của thư viện `sonner` chưa từng được mount vào gốc `App.tsx`.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

### 2.1. Backend: Khắc Phục Triệt Để 2 Lỗi Chặn Xuất Bản
1. [`backend/app/modules/assistants/readiness.py`](../../backend/app/modules/assistants/readiness.py):
   - Mở rộng điều kiện đếm tài liệu đối soát sẵn sàng:
     ```python
     or_(
         KnowledgeDocument.status.in_(["processed", "approved", "ready", "completed"]),
         KnowledgeDocument.index_status == "indexed",
     )
     ```
   - Điểm tiêu chí Kho tri thức chuyên biệt của Trợ lý Tuyển sinh tăng từ **25/100 lên 100/100**.
2. [`backend/app/modules/tools/registry.py`](../../backend/app/modules/tools/registry.py):
   - Khai báo `ALIASES` cho các công cụ legacy:
     ```python
     ALIASES: dict[str, str] = {
         "admissions.fact_lookup": "lookup_admission_score",
         "document.docx_export": "export_administrative_document",
         "assessment.xlsx_export": "export_exam_matrix",
     }
     ```
   - Cập nhật phương thức `get(name)` tự động ánh xạ qua `ALIASES`.
   - Đồng bộ cấu hình CSDL `enabled_tools` cho các trợ lý, điểm Tool Gateway đạt **100/100**.
   - **Tổng điểm sẵn sàng đạt 100/100 (5/5 tiêu chí ĐẠT, 0 lỗi chặn)**.

### 2.2. Frontend: Tích Hợp Sonner Toaster Toàn Cục & Nâng Cấp Thông Báo Lưu
1. [`frontend/src/components/ui/sonner.tsx`](../../frontend/src/components/ui/sonner.tsx) *(MỚI)*:
   - Xây dựng component `Toaster` chuẩn shadcn/ui tích hợp mượt mà với `useTheme()`, vị trí `top-right`, hỗ trợ `richColors`, `closeButton`, và áp dụng tokens thiết kế của QNU (`rounded-surface`, `bg-card`, `border-border`).
2. [`frontend/src/App.tsx`](../../frontend/src/App.tsx):
   - Import và mount `<Toaster />` bên trong `ThemeProvider`, mở khóa tính năng thông báo popup cho hơn 50 màn hình trên toàn hệ thống.
3. [`frontend/src/pages/assistant-detail-page.tsx`](../../frontend/src/pages/assistant-detail-page.tsx):
   - Nâng cấp `updateMutation.onSuccess`: Hiển thị thông báo chi tiết:
     ```tsx
     toast.success("Đã lưu thay đổi cấu hình thành công!", {
       description: `Các thiết lập của "${assistant.name}" đã được cập nhật vào hệ thống.`,
     });
     ```
   - Tự động làm mới cache readiness (`assistant-readiness`) sau khi lưu.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Backend**:
   - `uv run ruff check .`: 0 lỗi linter.
   - `uv run --extra dev pytest tests/test_assistant_readiness.py tests/test_tools.py tests/test_assistants.py`: **27/27 passed (100%) in 5.65s**.
   - API `GET /platform/v1alpha1/assistants/admissions/readiness`: Trả về `overall_readiness_score: 100`, `is_ready_for_publish: true`, `blockers: []`.
2. **Frontend**:
   - `npm run lint`: Checked 168 files, 0 lỗi Biome.
   - `npm run typecheck`: 0 lỗi TypeScript `tsc --noEmit`.
   - `npm run build`: Đóng gói bundle Vite thành công trong 11.26s.
