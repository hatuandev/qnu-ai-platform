# Nhật Ký Làm Việc: Loại Bỏ Tính Năng Tia Quét & Chuẩn Hóa Khung Nhận Diện Scan Bố Cục Văn Bản Hành Chính (NĐ 30/2020/NĐ-CP)
**Thời gian**: 2026-09-17 17:25 (UTC+7)
**Mục tiêu**: Loại bỏ hoàn toàn tính năng tia quét (laser beam animation) theo yêu cầu người dùng, và chuẩn hóa triệt để thuật toán nhận diện scan bố cục văn bản hành chính Việt Nam trên tệp PDF thực tế (`KH2240 Trien khai nang cap phan mem cong thong tin dien tu QNU-signed (2) (1).pdf`).

---

## 1. Yêu Cầu Của Người Dùng & Thực Trạng
1. **Loại bỏ tính năng tia quét**: Người dùng không có nhu cầu sử dụng hiệu ứng tia quét laser, yêu cầu gỡ bỏ hoàn toàn khỏi giao diện để giao diện thoáng gọn và tập trung vào dữ liệu bóc tách.
2. **Chuẩn hóa khung nhận diện scan bố cục**:
   - Khi quét tệp PDF hành chính 4 trang (`KH2240`), xảy ra các khiếm khuyết:
     - **Trang 1**: Khung màu tím `text` bao gồm quá nhiều đoạn căn cứ gộp chung và bị cụt ngang giữa chừng, bỏ sót nửa dưới trang.
     - **Trang 2 & 3**: Bảng kế hoạch 9 hàng bị phân mảnh thành hàng chục khối nhỏ li ti thay vì 1 khối bảng `table` duy nhất.
     - **Trang 4**: Các mục 3, 4 bị gộp thành một khối xanh lá `list` khổng lồ chiếm 80% trang; mục `Nơi nhận:` bị mất; khung `signature` chỉ vẽ đúng một vòng tròn đỏ mà bỏ sót chức danh `HIỆU TRƯỞNG` và họ tên `PGS. TS. Đoàn Đức Tùng`.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện

### A. Frontend (`frontend/src/`)
1. **[`document-bounding-visualizer.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/document-bounding-visualizer.tsx)**:
   - Xóa bỏ import `ScanLine`.
   - Xóa bỏ state `isScanning` và hàm bật/tắt tia quét.
   - Xóa nút "Tia quét" trên thanh điều khiển.
   - Xóa lớp overlay laser scan `animate-scan-beam` và badge HUD `AI Scan Active`.
2. **[`scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx)**:
   - Xóa bỏ import `ScanLine`.
   - Xóa bỏ state `isScanning` và nút "Tia quét".
   - Xóa lớp overlay laser beam animation.

### B. Backend (`backend/app/modules/ocr/`)
1. **[`layout_detector.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/layout_detector.py)**:
   - **Chế độ Hybrid Vector + Vision (`_detect_hybrid_pdf_regions`)**:
     - Tận dụng `fitz_page.get_text("blocks")` để trích xuất chính xác tọa độ vector của các khối văn bản số hóa.
     - Tích hợp `fitz_page.find_tables()` để phát hiện trọn vẹn toàn bộ khung viền của bảng dữ liệu.
     - **Triệt tiêu phân mảnh ô bảng**: Toàn bộ các text block nằm lọt bên trong bảng (IoU hoặc containment $\ge 0.65$) đều được tự động loại trừ (suppress), giữ lại duy nhất 1 khung `table` liền mạch cho cả bảng.
   - **Ngưỡng mật độ con dấu tương thích (Adaptive Stamp Density)**:
     - Con dấu tròn thực tế của Trường ĐH Quy Nhơn có ruột trắng và chữ số, mật độ điểm đỏ trên diện tích bounding box là $\approx 0.067$. Ngưỡng cũ `0.08` làm rơi mất con dấu.
     - Áp dụng ngưỡng tương thích: con dấu lớn ($\ge 5000\text{ px}$) dùng ngưỡng `0.04`, dấu nhỏ dùng `0.06`.
   - **Hợp nhất Chức danh, Con dấu và Họ tên người ký (`signature`)**:
     - Do mực dấu đỏ thường đóng đè lên chức vụ hoặc họ tên người ký, thuật toán điều chỉnh dung sai:
       - Chức danh (`HIỆU TRƯỞNG`): `(s_top - 12.0) <= tb_top <= (s_top + 8.0)`.
       - Họ tên (`PGS. TS. Đoàn Đức Tùng`): `(s_bottom - 8.0) <= tb_bottom <= (s_bottom + 16.0)`.
     - Tự động đánh dấu `used_text_indices` để hấp thụ hoàn toàn vào khung `signature`, không để lại các khối `text` trùng lặp rời rạc.
     - Bổ sung cơ chế fallback cho văn bản không có mực đỏ hoặc scan đen trắng.
   - **Quy tắc phân loại ngữ nghĩa hành chính Việt Nam (Nghị định 30/2020/NĐ-CP)**:
     - `header`: Quốc hiệu, Tiêu ngữ, Cơ quan ban hành, Số ký hiệu ở đầu trang 1.
     - `title`: Tên loại văn bản (`KẾ HOẠCH`), số La Mã (`I.`, `II.`), mục số (`1.1.`, `1.2.`), tên cơ quan phụ trách (`1. Trung tâm Số và Học liệu`, `3. Phòng Tổ chức - Nhân sự`).
     - `list`: Gạch đầu dòng `- `, dấu cộng `+ `, chấm tròn `• `, tiểu mục số, và khối `Nơi nhận:`.
     - `text`: Từng đoạn văn độc lập (Căn cứ, bối cảnh triển khai).

2. **[`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) & [`ocr/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/service.py)**:
   - Chuyển tiếp `fitz_page=page` từ đối tượng tài liệu PyMuPDF vào `detect_layout_regions`.

3. **[`test_smart_layout.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_smart_layout.py)**:
   - Thêm suite kiểm thử đơn vị tự động kiểm tra 3 thành phần cốt lõi: Phân loại hành chính, mật độ con dấu tương thích, và hợp nhất layout PDF hybrid.

---

## 3. Kết Quả Kiểm Thử Toàn Diện
- **Backend**:
  - `uv run ruff check .`: 0 lỗi.
  - `uv run --extra dev pytest tests/ -q`: **125/125 passed (100%)** trong 25.21s.
- **Frontend**:
  - `npm run lint`: Biome check 78 files, **0 lỗi**.
  - `npm run typecheck`: TypeScript `tsc --noEmit`, **0 lỗi**.
  - `npm run build`: Vite build thành công đóng gói bundle trong **5.54s**.
