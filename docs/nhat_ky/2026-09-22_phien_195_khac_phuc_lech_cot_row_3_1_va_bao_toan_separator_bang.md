# Nhật Ký Làm Việc — Phiên #195 (2026-09-22 22:50 UTC+7)

## Tiêu Đề
**Khắc Phục Lệch Cột Row 3.1 ("Ban Hành") & Bảo Toàn 100% Dòng Phân Cách Bảng Markdown (`:---`)**

---

## 1. Mục Tiêu & Bối Cảnh
Sau khi kiểm tra kết quả bóc tách thực tế trên tệp `KE HOACH TRIEN KHAI NHIỆM VỤ 2025-2026_update 16_9_2025.pdf` (22 trang), hệ thống đã đạt được các tiến bộ vượt bậc:
- ✅ Ghép nối trọn vẹn nội dung dài đa trang ở dòng 4.10, 7.2, 8.1.
- ✅ Gộp số La Mã ngắt đôi `VII` + `I` thành `VIII` và loại bỏ hàng thừa.
- ✅ Triệt tiêu 100% số trang rác ở chân trang.
- ✅ Cấu trúc 1 dòng = 1 bản ghi với `<br>` cho ô nhiều dòng.

Tuy nhiên, qua rà soát chi tiết từng hàng và cú pháp Markdown, phát hiện 2 thiếu sót kỹ thuật trọng yếu:
1. **Lệch cột tại Hàng 3.1**: Cột "Nội dung nhiệm vụ" bị trống; nội dung `"Ban hành quy định đo lường, đánh giá CTĐT..."` bị đẩy sang Cột "Đơn vị chủ trì"; và cả cụm `"Phòng KT&BĐCL Trung tâm S&HL; Các khoa Các quy định, quy chế..."` bị dồn thành một chuỗi vào Cột "Sản phẩm kết quả".
2. **Mất dòng phân cách bảng (`|:---|:---|...|`)**: Mọi bảng xuất ra đều thiếu dòng phân cách sau tiêu đề, khiến trình xem Markdown (GitHub, VS Code Preview, React/Vite renderer) không hiển thị được định dạng bảng chuẩn mà hiện văn bản thô.

---

## 2. Phân Tích Nguyên Nhân Kỹ Thuật (Root Cause Analysis)

### 2.1. Lệch Cột Hàng 3.1
- Trong `table_reconstructor.py`, regex `_LEAD_UNIT_RE = re.compile(r"^(?:ban|cđ|đtn|...)\b")` sử dụng `ban` để bắt các "Ban" (Ban Giám hiệu, Ban Quản lý, Ban Chấp hành).
- Tuy nhiên, cụm `"Ban hành quy định..."` bắt đầu bằng từ `"Ban"`, dẫn tới việc regex nhận nhầm động từ "Ban hành" thành Đơn vị chủ trì.
- Hơn nữa, tại `_normalize_spacer_columns`, khi hàng có đủ số ô $\ge$ số cột tiêu đề và PyMuPDF đã bóc tách đúng vị trí các cột danh nghĩa, logic lại tự động gọi hàm đoán `_compact_task_row` thay vì dùng trực tiếp `semantic_indices` của trang.

### 2.2. Mất Dòng Phân Cách Markdown
- Trong `cleaner.py`, hàm `_stitch_table_continuations` duyệt qua các dòng bảng.
- Khi gặp dòng tiêu đề (dòng 0), dòng tiếp theo (dòng 1) là dòng phân cách `| :---: | :--- | ... |`.
- Do `_is_table_row` trả về `True` cho dòng phân cách và số cột bằng nhau, hàm đã xử lý dòng này như một bảng con nối tiếp và chạy lệnh `if _is_table_sep(lines[k]): k += 1`, bỏ qua dòng phân cách mà không ghi vào kết quả đầu ra.
- Nguyên nhân: logic chỉ được phép bỏ qua header/separator lặp khi giữa 2 bảng có ranh giới trang thực sự (`---` hoặc `<!-- Trang N -->`). Với 2 dòng liền kề trong cùng 1 bảng, dòng phân cách phải được giữ nguyên vẹn.

---

## 3. Các Thay Đổi Chi Tiết (Key Code Changes)

1. **[`backend/app/modules/knowledge/cleaner.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/cleaner.py)**:
   - Cập nhật `_stitch_table_continuations`: bổ sung kiểm tra `has_boundary = any(s.strip() == "---" or bool(re.match(r"^<!--\s*Trang\s+\d+\s*-->$", s.strip(), re.IGNORECASE)) for s in interstitial)`.
   - Chỉ khi `has_boundary` là `True` mới kích hoạt cơ chế bỏ qua header và separator lặp của trang tiếp nối. Khi không có ranh giới trang, dòng phân cách được bảo toàn 100%.

2. **[`backend/app/modules/knowledge/normalization/table_reconstructor.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/normalization/table_reconstructor.py)**:
   - Thêm negative lookahead cho `_LEAD_UNIT_RE`:
     ```python
     _LEAD_UNIT_RE = re.compile(
         r"^(?:ban(?!\s+hành)|cđ|đtn|hsv|khoa|phòng(?!\s+ngừa|\s+chống)|trung tâm|trường(?!\s+hợp)|viện(?!\s+dẫn)|văn phòng)\b",
         re.IGNORECASE,
     )
     ```
   - Trong `_normalize_spacer_columns`: Khi hàng có `len(row.cells) >= len(headers)`, trích xuất `selected_cells` theo `semantic_indices`. Nếu `first_val` là mã nhiệm vụ (`3.1`) và `lead_val` là đơn vị chủ trì (`Phòng KT&BĐCL`), sử dụng trực tiếp `selected_cells` để bảo toàn ánh xạ cột gốc từ PyMuPDF.

3. **[`backend/tests/test_table_stitching_and_page_partition.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_table_stitching_and_page_partition.py)**:
   - Bổ sung `test_clean_markdown_preserves_table_separators` xác nhận dòng phân cách không bị xóa.
   - Bổ sung `test_row_3_1_ban_hanh_not_matched_as_lead_unit` kiểm thử khả năng chống nhận nhầm "Ban hành" và phân bổ chuẩn 7 cột.

---

## 4. Kết Quả Kiểm Thử (Verification)

- **Backend Linter**: `uv run ruff check .` $\rightarrow$ 0 lỗi (All checks passed).
- **Backend Unit Tests**: `uv run --extra dev pytest tests/test_table_stitching_and_page_partition.py` $\rightarrow$ 10/10 passed (100%).
- **Frontend Linter & Typecheck**: `npm run lint` $\rightarrow$ 170 files 0 lỗi; `npm run typecheck` $\rightarrow$ 0 lỗi.
- **Frontend Build**: `npm run build` $\rightarrow$ thành công trong 8.64s.
- **Live Verification trên tệp Kế hoạch 2025-2026**:
  - Dòng 3.1:
    + Col 0: `3.1`
    + Col 1: `Ban hành quy định đo lường, đánh giá CTĐT theo chuẩn đầu ra; quy chế quản lý, khai thác phần mềm thi trắc nghiệm; phối hợp xây dựng phần mềm đo lường đánh giá.`
    + Col 2: `Phòng KT&BĐCL`
    + Col 3: `Trung tâm S&HL; Các khoa`
    + Col 4: ``
    + Col 5: ``
    + Col 6: `Các quy định, quy chế đã ban hành; phần mềm hoàn thiện, đưa vào sử dụng`
  - Dòng phân cách Markdown: 20/20 dòng phân cách trên 20 trang phụ lục được giữ nguyên.
  - Các dòng dài 4.10, 7.2, 8.1 và Section VIII tiếp tục giữ độ chính xác tuyệt đối.
