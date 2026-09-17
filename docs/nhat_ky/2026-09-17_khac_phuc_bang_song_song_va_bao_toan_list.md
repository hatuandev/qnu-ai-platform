# NHẬT KÝ LÀM VIỆC — Phiên #56: Khắc Phục Bóc Tách Bảng Song Song & Bảo Toàn Danh Sách (List) Độc Lập

- **Thời gian**: 2026-09-17 17:55 (UTC+7)
- **Kỹ sư**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý triệt để phản ánh của người dùng về việc nhận diện Scan trên tài liệu 14 trang (trang 9) chỉ hiện 2 bảng và mất sạch các khối text/list, đồng thời không thấy hiển thị nhãn danh sách (`list`).

---

## 1. Bối Cảnh & Phản Ánh Của Người Dùng
- Khi người dùng kiểm thử bóc tách tài liệu Thông báo tuyển sinh 14 trang (`media_1789641791050.pdf`), tại trang 9 có 2 bảng quy đổi điểm (IELTS và VSTEP).
- Trên màn hình chỉ xuất hiện 2 khung màu cam `table`, toàn bộ văn bản đầu trang, các điểm `b.`, `c.`, mục `6. Tổ chức tuyển sinh`, `Đợt 1:`, các mục `a)`, `b)`, `c)` biến mất hoàn toàn.
- Người dùng phản hồi: *"vẫn chưa ổn, nhận dạng table ko nhận mấy cái khác, tôi cũng không thấy list đâu ?"*.

---

## 2. Phân Tích Nguyên Nhân Gốc Rễ
1. **Lọt chữ trong bảng đôi (Side-by-side table leakage)**: PyMuPDF gộp text ngang của 2 bảng song song thành các block trải rộng qua cả 2 bảng. Điều kiện `x0 >= tx0 - 5 and x1 <= tx1 + 5` cũ bị trượt vì block không nằm hoàn toàn trong bảng 1 hay bảng 2.
2. **Bắc cầu chuỗi nối gộp vi mô (Chained merging bridge)**: Các dòng lọt từ bảng có khoảng cách dọc nhỏ ($\le 3.5\%$), vô tình kết nối đoạn văn trên bảng và đoạn văn dưới bảng thành 1 khối text duy nhất phủ kín cả trang.
3. **Triệt tiêu quá tay trong `_suppress_overlapping_boxes`**: Khối text khổng lồ trên bao trùm 2 bảng nên bị coi là trùng lặp và bị xóa sổ, chỉ để lại 2 bảng.
4. **Mất nhãn `list` do gộp chéo**: Khi gộp `list` với `text`, luật cũ tự động biến thành `text`.

---

## 3. Các Thay Đổi Kỹ Thuật Chi Tiết

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :---: | :--- |
| [`backend/app/modules/ocr/layout_detector.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/layout_detector.py) | MODIFY | 1. Sửa `is_inside_table`: dùng tỷ lệ giao cắt diện tích dọc ($>50\%$) và ngang ($>10\text{px}$) hoặc tọa độ tâm block để bắt trọn chữ trong mọi bảng (kể cả bảng đôi).<br>2. Thêm cờ `table_between`: ngăn cách tuyệt đối không cho phép gộp các khối qua bảng biểu.<br>3. Chuyển sang luật Strictly Same-Type: `list` chỉ gộp với `list`, `text` chỉ gộp với `text`, giữ nguyên bản quyền nhãn `list`.<br>4. Mở rộng `_is_list_marker` và `_is_doc_or_section_title`: hỗ trợ ký tự tiếng Việt (`đ`, `Đ`), dấu ngoặc đơn, gạch đầu dòng, số thứ tự.<br>5. Sửa `_suppress_overlapping_boxes`: chỉ xóa khối text/list nếu chính nó lọt lòng trên 60% bên trong bảng. |
| [`backend/tests/test_smart_layout.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_smart_layout.py) | MODIFY | Bổ sung ca kiểm thử `test_list_preservation_and_table_separation` xác nhận bảo toàn `list` (mục `b., c.` và `a), b), c)`) và bảng biểu phân tách rõ ràng. |

---

## 4. Kết Quả Kiểm Thử (Verification)

1. **Kiểm tra trực tiếp trên Trang 9 của tài liệu người dùng**:
   - Khối 1: `[text]` (Trường hợp nhiều thí sinh có cùng điểm xét...)
   - Khối 2: `[list]` (b. Điểm cộng... c. Sử dụng chứng chỉ...)
   - Khối 3: `[table]` (Bảng quy đổi điểm IELTS)
   - Khối 4: `[table]` (Bảng quy đổi điểm VSTEP)
   - Khối 5: `[text]` (.Thí sinh nộp chứng chỉ...)
   - Khối 6: `[list]` (c. Ngưỡng đầu vào...)
   - Khối 7: `[title]` (6. Tổ chức tuyển sinh - Đợt 1:)
   - Khối 8: `[list]` (a) Thí sinh nộp hồ sơ... b) Thi năng khiếu... c) Xét tuyển đợt 1:)
   - Khối 9: `[text]` (Công bố ngưỡng bảo đảm chất lượng...)
   $\rightarrow$ **Toàn bộ các khối `table`, `list`, `title`, `text` xuất hiện đầy đủ, sắc nét, đúng ngữ nghĩa!**

2. **Backend**:
   - `uv run ruff check .` $\rightarrow$ **0 lỗi** (All checks passed!).
   - `uv run --extra dev pytest tests/ -q` $\rightarrow$ **126/126 passed (100%)** trong 26.62s.

3. **Frontend**:
   - `npm run lint` (Biome) $\rightarrow$ **0 lỗi** trên 78 files.
   - `npm run typecheck` (`tsc --noEmit`) $\rightarrow$ **0 lỗi**.
   - `npm run build` $\rightarrow$ Đóng gói thành công trong 5.32s.
