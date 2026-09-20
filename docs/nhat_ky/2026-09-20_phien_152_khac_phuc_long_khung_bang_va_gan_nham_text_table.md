# NHẬT KÝ PHIÊN LÀM VIỆC #152
# Ngày: 2026-09-20 | Nội dung: Khắc Phục Triệt Để Lỗi Lồng Khung Bảng (Nested Tables), Đè Khung Text và Gán Nhầm Text Thành Table Trong Scan Studio

---

## 1. Bối Cảnh & Vấn Đề Thực Tế
Sau khi phân tích ảnh chụp màn hình do người dùng cung cấp và đối soát trực tiếp tọa độ hình học với 2 tệp PDF:
1. **Vấn đề 1 (Ảnh 1 — Trang 9/14 tài liệu Tuyển sinh `doc_c2e3bb0eafdc`)**:
   - **Đoạn văn a, b, c bị biến thành khung cam `table`**: Tại hàm `classifyStudioRegion` trong [`scan-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/scan-studio-page.tsx) và `ingestion_service.py`, biểu thức logic `(height <= 15 || hasTableSignals)` có dấu ngoặc lỏng. Khi trang trước có bảng (`prevHasBottomTable = true`), toàn bộ các đoạn văn bản ở đầu trang 9 (`Trường hợp...`, `b. Điểm cộng...`, `c. Sử dụng chứng chỉ...`) có `height <= 15` đều bị nhận diện nhầm thành `table` tiếp nối dù không chứa mã ngành hay tổ hợp môn.
   - **Các khung tím `text` đè lên ô số 5.0, 8.0 của bảng IELTS/VSTEP**: Hai bảng này nằm song song trên cùng 1 dòng ngang, PyMuPDF gom `5.0 8.0 4.0 8.0` thành 1 text block duy nhất bắt cầu qua cả 2 bảng ($x=152 \rightarrow 475$). Thuật toán cũ kiểm tra cứng `bx0 >= tx0 - 2 and bx1 <= tx1 + 2` đối với từng bảng đơn lẻ nên text block này bị lọt qua và vẽ thêm khung tím đè lên bảng.
2. **Vấn đề 2 (Ảnh 2 — Trang 16/22 tài liệu Kế hoạch `doc_99eff1224947`)**:
   - **Khung cam `table` con lồng trong ô 6.8 ("Sản phẩm kết quả")**: PyMuPDF `find_tables()` và OpenCV nhận diện cả bảng lớn toàn trang (`Table 0`) lẫn một bảng con (`Table 1`) bên trong ô 6.8. Do thiếu cơ chế **Nested Table Suppression (NMS)**, hệ thống emit cả 2 bảng khiến ô 6.8 bị đóng thêm 1 khung cam con lồng bên trong.

---

## 2. Các Thay Đổi Kỹ Thuật Đã Triển Khai (Cơ Chế Bảo Vệ 2 Lớp - Dual-Defense)

### 2.1. Lớp 1: Backend Core
- **`backend/app/modules/knowledge/parsers/blocks.py`**:
  * Bổ sung hàm `suppress_nested_tables(table_list)`: Tự động so sánh tỷ lệ diện tích giao cắt. Nếu bảng $T_A$ có diện tích nhỏ hơn và nằm lọt $\ge 70\%$ bên trong bảng $T_B$, loại bỏ bảng con $T_A$, chỉ giữ bảng cha $T_B$.
  * Nâng cấp `extract_page_blocks`: Tính tổng diện tích giao cắt đa bảng giữa `block` và tất cả các bảng trên trang. Nếu tỷ lệ diện tích giao cắt $\ge 0.40$ hoặc tâm block nằm trong bất kỳ bảng nào, xác định là text của bảng và loại bỏ (`is_inside_tbl = True`), không emit block `text` độc lập.
  * Siết chặt `classify_text_block`: Kiểm tra `is_admin_paragraph`, cấm tuyệt đối biến đoạn văn bản quy định hành chính thành bảng tiếp nối.
- **`backend/app/modules/ocr/layout_detector.py`**:
  * Tích hợp `suppress_nested_tables` vào `_detect_hybrid_pdf_regions`.
  * Khử triệt để text blocks rơi vào bảng song song.
- **`backend/app/modules/knowledge/parsers/pdf_parser.py`**:
  * Tích hợp `suppress_nested_tables` khi parse danh sách `CanonicalTable`.
  * Nâng cấp `_is_table_text` hỗ trợ tính tổng diện tích giao cắt đa bảng.
- **`backend/app/modules/knowledge/services/ingestion_service.py`**:
  * Sửa hàm `_ensure_page_blocks` / `_assemble_verification_pages`: Bắt buộc phải có `has_tbl_signals` và `not is_admin_paragraph` mới được rescue thành `table tiếp nối`.

### 2.2. Lớp 2: Frontend Client
- **`frontend/src/pages/scan-studio-page.tsx`**:
  * Sửa hàm `classifyStudioRegion`: Yêu cầu bắt buộc `hasTableSignals` và không phải là đoạn văn bản quy định (`!isAdminParagraph`). Chấm dứt 100% việc gán nhầm đoạn văn thành bảng.
  * Bổ sung hàm `cleanStudioRegions`:
    - Khử Nested Sub-tables (overlap $\ge 70\%$).
    - Khử Table Text Suppression: loại bỏ các hộp `text` nếu rơi vào hoặc giao cắt $\ge 40\%$ với bất kỳ bảng nào trên trang.
  * Tích hợp vào `mapVerificationDataToStudioDoc`.

---

## 3. Kết Quả Kiểm Thử (Verification)

### Backend:
- `uv run ruff check .`: **All checks passed (0 lỗi)**.
- `uv run --extra dev pytest tests/test_table_reconstructor.py`: **10/10 passed (100%) in 1.19s** (Bổ sung 2 test cases mới: `test_suppress_nested_tables` và `test_extract_page_blocks_suppresses_side_by_side_tables_text`).
- `uv run --extra dev pytest tests/test_table_reconstructor.py tests/test_domain_records_and_quality_gate.py tests/test_knowledge.py`: **47/47 passed (100%)**.

### Frontend:
- `npm run lint`: **165 files checked, 0 errors**.
- `npm run typecheck`: **0 errors**.
- `npm run build`: **✓ built in 17.53s**.
