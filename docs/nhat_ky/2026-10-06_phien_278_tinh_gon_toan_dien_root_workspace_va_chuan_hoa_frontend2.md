# NHẬT KÝ PHIÊN LÀM VIỆC 278 (WORK LOG SESSION 278)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
**Thời gian thực hiện**: 2026-10-06 (15:45 - 15:55)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Triển khai kế hoạch tinh gọn toàn diện cấu trúc thư mục dự án (Clean Workspace Initiative): dọn dẹp thư mục gốc (Root Workspace De-cluttering), lưu trữ gọn gàng các script scratch và tài liệu mẫu, chuẩn hóa phân hệ Frontend (`frontend2` độc tôn trên port 3000, lưu trữ `legacy/frontend_v1_backup/`) và điều tra lỗi phân quyền Windows trên `document_types`.

---

### 1. Hiện Trạng Trước Khi Tinh Gọn

1. **Thư mục gốc (Root Workspace)**:
   - Tồn tại tới 39 tệp/thư mục.
   - 13 tệp script thử nghiệm `scratch_*.py` nằm rải rác ngay tại Root (`scratch_draw_boxes.py`, `scratch_proto_morphology.py`, `scratch_test_smart_morphology.py`, ...).
   - 8 tệp tài liệu mẫu, hợp đồng bóc tách, công văn HEMIS và tệp `.docx`, `.html` thử nghiệm nằm lẫn lộn ở Root.
2. **Phân hệ Frontend**:
   - Tồn tại song song 2 thư mục `frontend` (bản cũ, chứa `node_modules` nặng ~500MB) và `frontend2` (bản mới chuẩn React 19 + TanStack Router).
   - File điều phối `run.ps1` vẫn còn cấu hình chạy `frontend` cũ ở lệnh `dev`.
3. **Phân hệ Backend Modules**:
   - Thư mục `backend\app\modules\document_types` bị dính cờ phân quyền Windows (*WinError 5: Access is denied / unauthorized operation*) do các tiến trình Docker container (chạy as root/SYSTEM) trước đây gây ra.

---

### 2. Các Hành Động Đã Triển Khai Thực Tế

#### 🔹 Giai đoạn 1: Dọn dẹp Root Workspace (Zero Root Clutter)
- Tạo thư mục `scratch/archive/` và di chuyển toàn bộ 13 tệp script thử nghiệm vào đây:
  - `scratch_draw_boxes.py`
  - `scratch_inspect_gaps.py`
  - `scratch_inspect_meta.py`
  - `scratch_inspect_pixels.py`
  - `scratch_make_slices.py`
  - `scratch_proto_morphology.py`
  - `scratch_render_measure.py`
  - `scratch_test_complete_morphology.py`
  - `scratch_test_detector_class.py`
  - `scratch_test_full_morphology.py`
  - `scratch_test_morphology.py`
  - `scratch_test_refined.py`
  - `scratch_test_smart_morphology.py`
- Tạo thư mục `docs/tai_lieu/samples/` và di chuyển toàn bộ 8 tệp tài liệu mẫu vào đây:
  - `Hợp đồng nâng cấp PM cổng thông tin điện tử_0001_boc_tach.md`
  - `Cong_van_6240_BGDDT_KHCNTT_ket_noi_HEMIS_boc_tach.md`
  - `Cong_van_6240_BGDDT_KHCNTT_ocr_result.md`
  - `Kế hoạch làm việc với ĐH Duy Tân.html`
  - `ke_hoach_lam_viec_duy_tan.md`
  - `hoi_thoai_ast_admissions_test_thuc_te.md`
  - `KE HOACH TRIEN KHAI NHIỆM VỤ 2025-2026_update 16_9_2025.docx`
  - `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`
- **Kết quả**: Thư mục gốc giảm từ **39 tệp xuống còn 18 tệp** chuẩn mực (chỉ còn lại các file cấu hình và điều phối chính).

#### 🔹 Giai đoạn 2: Chuẩn hóa phân hệ Frontend (`frontend2`)
- Xóa bỏ toàn bộ `node_modules` và `dist` của `frontend/` cũ, giải phóng ~500MB dung lượng ổ đĩa.
- Tạo thư mục `legacy/` và di chuyển thư mục `frontend/` cũ thành `legacy/frontend_v1_backup/` phục vụ đối soát lịch sử.
- Cập nhật [`run.ps1`](file:///d:/DuAnPhanMem/qnu-ai-platform/run.ps1):
  - Lệnh `dev`: Tự động khởi chạy Backend (Port 8001) và Frontend QNU AI chuẩn (`frontend2`, Port 3000).
  - Lệnh `fe` và `fe2`: Khởi chạy trực tiếp `frontend2` (Port 3000).

#### 🔹 Giai đoạn 3: Điều tra lỗi phân quyền `document_types`
- Điều tra xác nhận: Nội dung mã nguồn của `document_types` (`catalog.py`, `models.py`, `router.py`, `schemas.py`, `service.py`) được lưu trữ an toàn 100% trong Git (`git show HEAD:backend/app/modules/document_types/catalog.py`).
- Nguyên nhân lỗi `Access is denied` là do quyền sở hữu (ownership) bị gán cho SYSTEM/root từ Docker trước đó.
- Giải pháp: Khuyến nghị người dùng chạy lệnh PowerShell với quyền Administrator:
  ```powershell
  takeown /f "D:\DuAnPhanMem\qnu-ai-platform\backend\app\modules\document_types" /r /d y
  icacls "D:\DuAnPhanMem\qnu-ai-platform\backend\app\modules\document_types" /grant "${env:USERNAME}:(OI)(CI)F" /t
  ```

---

### 3. Kết Quả Sau Khi Tinh Gọn

| Khu vực | Trước tinh gọn | Sau tinh gọn |
| :--- | :---: | :---: |
| Số tệp/thư mục tại Root | 39 tệp | **18 tệp (Tinh gọn ~54%)** |
| Script thử nghiệm rải rác | 13 tệp ở Root | **Gom 100% vào `scratch/archive/`** |
| Tài liệu mẫu lẫn lộn | 8 tệp ở Root | **Gom 100% vào `docs/tai_lieu/samples/`** |
| Phân hệ Frontend | 2 thư mục song song | **1 frontend chính thức (`frontend2`), bản cũ lưu `legacy/`** |
| Lệnh điều phối `run.ps1` | Chạy lẫn lộn port 3001 & 3000 | **Đồng bộ 100% vào `frontend2` (Port 3000)** |
