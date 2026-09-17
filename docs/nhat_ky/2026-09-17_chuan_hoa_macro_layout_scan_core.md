# Nhật Ký Làm Việc: Chuẩn Hóa Phân Vùng Bố Cục Vĩ Mô (Macro Layout Sections) Theo Chuẩn QNU-AI-Core
**Thời gian**: 2026-09-17 17:40 (UTC+7)
**Mục tiêu**: Khắc phục triệt để hiện tượng nhận diện scan bị quá chi tiết (micro-segmentation) trên các trang tài liệu văn bản, kế thừa triết lý phân vùng bố cục vĩ mô của `qnu-ai-core`.

---

## 1. Vấn Đề Người Dùng Phản Ánh & Đối Soát Với `qnu-ai-core`
- **Phản ánh từ người dùng**: *"hiện tại tôi test thì thấy việc nhận diện scan lại đang quá chi tiết, bạn thử tìm hiểu lại bên core ở chỗ nhận diện scan xem thử"*.
- **Kết quả đối soát `qnu-ai-core`**:
  - Tại `qnu-ai-core/services/platform-api/.../smart_layout_detector.py` và `test_layout_classifier.py`:
    - Core **không bao giờ đóng khung từng dòng căn cứ hay từng gạch đầu dòng `- `**.
    - Core thiết lập quy tắc gộp các dải văn bản kề nhau (Adjacent Merging) có khoảng cách trắng nhỏ ($\le 3.5\%$) thành các **khối lớn duy nhất**.
    - Dữ liệu mẫu `sample-data.ts` (Quyết định 2699): Trang 1 có 8 khung lớn, Trang 2 có 2 khung, Trang 3 có 2 khung, Trang có bảng có 3 khung.
  - Trong khi đó, tại `qnu-ai-platform`: Do chưa qua tầng gom cụm sau khi nhận blocks từ PyMuPDF, Trang 1 bị chẻ thành **14 khung**, Trang 3 bị **10 khung**, Trang 4 bị **10 khung** khiến giao diện bị rối mắt.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. **Bổ sung tầng Gom cụm Vĩ mô (`_merge_into_macro_regions`) trong [`SmartLayoutDetector`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/layout_detector.py)**:
   - **Header Trang 1**: Tự động gom các dòng cơ quan ban hành bên trái thành 1 khung Header Trái; các dòng quốc hiệu, tiêu ngữ, ngày tháng bên phải thành 1 khung Header Phải.
   - **Bảo tồn Tiêu đề chính**: Tiêu đề văn bản (`KẾ HOẠCH`, `QUYẾT ĐỊNH`) giữ nguyên là 1 khung `title` độc lập.
   - **Gom các đoạn căn cứ & thuyết minh**: Toàn bộ các đoạn Căn cứ được gom thành 1 khối `text` duy nhất.
   - **Gom các nội dung chỉ đạo & danh sách kề nhau**: Các tiểu mục và gạch đầu dòng trong cùng một phần chỉ đạo được gom thành 1 khối nội dung lớn.
   - **Bảo vệ Bảng biểu, Nơi nhận và Chữ ký**: Khung `table`, `signature` và `list` (Nơi nhận) được giữ nguyên vẹn.
2. **Hỗ trợ từ khóa tiêu đề không dấu**:
   - Cập nhật regex `_is_doc_or_section_title` hỗ trợ cả dạng có dấu và không dấu (`KẾ HOẠCH` / `KE HOACH`, `QUYẾT ĐỊNH` / `QUYET DINH`,...).
3. **Cập nhật bộ kiểm thử đơn vị [`test_smart_layout.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_smart_layout.py)**:
   - Cập nhật các assertions kiểm tra tính toàn vẹn của việc gom cụm vĩ mô.

---

## 3. Kết Quả Thực Nghiệm Trên Tệp Mẫu Của Người Dùng (`KH2240`)
- **Trang 1**: 14 khung $\rightarrow$ **5 khung vĩ mô** (Header Trái, Header Phải, Tiêu đề Kế hoạch, Căn cứ & Thuyết minh, Mục I. Mục đích, Yêu cầu).
- **Trang 2**: 2 khung $\rightarrow$ **2 khung vĩ mô** (Tiêu đề, Bảng 9 hàng).
- **Trang 3**: 10 khung $\rightarrow$ **2 khung vĩ mô** (Bảng nối tiếp, Mục III. Tổ chức thực hiện).
- **Trang 4**: 10 khung $\rightarrow$ **3 khung vĩ mô** (Mục 3, 4 Nhiệm vụ & Chỉ đạo, Nơi nhận, Con dấu & Chữ ký).
- **Tổng cộng**: Giảm từ 36 khung vụn xuống còn **12 khung vĩ mô**, đạt chuẩn giao diện thoáng đãng của `qnu-ai-core`.

---

## 4. Kết Quả Kiểm Thử (Verification)
- **Backend**:
  - `uv run ruff check .`: 0 lỗi.
  - `uv run --extra dev pytest tests/ -q`: **125/125 passed (100%)** trong 25.49s.
- **Frontend**:
  - `npm run lint`: Biome check 78 files, **0 lỗi**.
  - `npm run typecheck`: TypeScript `tsc --noEmit`, **0 lỗi**.
  - `npm run build`: Vite build thành công trong **5.33s**.
