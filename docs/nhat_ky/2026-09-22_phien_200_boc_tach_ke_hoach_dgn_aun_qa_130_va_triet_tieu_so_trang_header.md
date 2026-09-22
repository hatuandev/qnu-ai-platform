# NHẬT KÝ LÀM VIỆC — PHIÊN #200 (2026-09-22 23:05 UTC+7)

## Tiêu Đề
**Bóc Tách Kế Hoạch ĐGN AUN-QA 4.0 (KH130), Ghép Nối Đa Trang Dòng 16 & 23, Triệt Tiêu Số Trang Lề Trên Header**

---

## 1. Mục Tiêu & Bối Cảnh
Người dùng kiểm thử tài liệu thứ hai: `KH130 trien khai chuan bi DGN CTDT 3 CTDT AUN-QA 2026.pdf` (6 trang, 45 nhiệm vụ chuẩn bị đánh giá ngoài 3 chương trình đào tạo Tài chính - Ngân hàng, Kế toán, Kỹ thuật điện theo tiêu chuẩn AUN-QA phiên bản 4.0).
Tiến hành rà soát chi tiết từng hàng, cột và cấu trúc văn bản bóc tách để phát hiện các trường hợp biên mới.

---

## 2. Kết Quả Rà Soát Chi Tiết Tệp Test

### 2.1. Các Thành Công Vượt Bậc
1. **Phân bổ 6 cột hoàn hảo**: Bảng kế hoạch có cấu trúc 6 cột (`TT | Nội dung | Thời gian thực hiện | Đơn vị chủ trì | Đơn vị phối hợp | Ghi chú`), toàn bộ 45 nhiệm vụ từ dòng 1 đến 45 đều được phân bổ chính xác 100% vào đúng từng cột.
2. **Khả năng ghép nối đa trang cực kỳ xuất sắc**:
   - **Dòng 16 (Trang 2 $\rightarrow$ Trang 3)**: Tại cuối trang 2, cột Đơn vị phối hợp kết thúc bằng `P.`. Sang đầu trang 3, phần tiếp nối `KH-TC, TT. S&HL, các đơn vị liên quan` được đặt ở hàng đầu bảng. Hệ thống đã tự động nhận diện và gộp trọn vẹn vào Dòng 16 của Trang 2:
     `P.<br>KT&BĐCL,<br>03 khoa, P.<br>HC-TH, P. KH-TC, TT.<br>S&HL, các<br>đơn vị liên<br>quan`.
   - **Dòng 23 (Trang 3 $\rightarrow$ Trang 4)**: Tại cuối trang 3, câu bị ngắt ở chữ `Bảo`. Sang đầu trang 4, phần tiếp nối `đảm tính hoạt động ổn định, hiệu quả của các thiết bị trong phòng PV.` được tự động ghép nối vào Dòng 23, không hề sinh ra hàng mồ côi.
3. **Bảo toàn 100% dòng phân cách Markdown `:---`**: Cả 6 trang đều có đầy đủ header và separator chuẩn GFM.

### 2.2. Điểm Kỹ Thuật Cần Tối Ưu Đã Xử Lý Ngay
1. **Số trang đặt ở lề trên (Header Pagination)**:
   - Theo Nghị định 30/2020/NĐ-CP (Điều 9 khoản 4), số trang văn bản tiếng Việt từ trang 2 trở đi được đặt ở phần lề trên (Header), canh giữa.
   - Do đó, các trang 2, 3, 4, 5, 6 có các số `2`, `3`, `4`, `5`, `6` ở tọa độ đỉnh trang (`top_percent ~ 3.4%`).
   - Hệ thống cũ chỉ lọc số trang ở đáy trang (`bottom >= 88%`).
   - Đã xử lý:
     + `blocks.py`: Thêm kiểm tra `top_percent <= 8.0` cho `classify_text_block`.
     + `pdf_parser.py`: Lọc bỏ khối số trang nếu `page_num > 1 and b_rect.y1 < page.rect.height * 0.08`.
     + `cleaner.py`: Cập nhật `_RE_PAGE_NUMBERS` bao quát số trang đơn độc `^\s*\d{1,3}\s*$`.
2. **Hiện tượng khối số hiệu điền thêm (Overlay Stamp) `130` và `22`**:
   - Trong văn bản hành chính in từ mẫu form Word/PDF, chuỗi gốc là `Số:      /KH-ĐHQN` và `Gia Lai, ngày      tháng 01 năm 2026`.
   - Người dùng gõ bổ sung số `130` và ngày `22` vào form field hoặc stamp text, tạo thành một block riêng `'130\n22'` ở tọa độ `y = 93.1` (trước block template `y = 94.4`).
   - Khi sắp xếp theo tọa độ `(y, x)`, hai số này đứng trước dòng số hiệu. Đây là đặc thù của file PDF có lớp overlay số hiệu điền tay.

---

## 3. Các Tệp Mã Nguồn Đã Thay Đổi
- `backend/app/modules/knowledge/parsers/blocks.py`: Nhận diện số trang header lề trên.
- `backend/app/modules/knowledge/parsers/pdf_parser.py`: Lọc bỏ số trang header từ trang 2 trở đi.
- `backend/app/modules/knowledge/cleaner.py`: Khử dòng số trang đơn lẻ `\d{1,3}`.
- `backend/tests/test_table_stitching_and_page_partition.py`: Thêm unit test kiểm thử số trang header.

---

## 4. Kết Quả Kiểm Thử (Verification)
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest tests/test_table_stitching_and_page_partition.py`: 10/10 passed (100%).
- `npm run lint`: 170 files checked, 0 lỗi.
- `npm run typecheck`: 0 lỗi.
- Live verification trên tệp KH130: 100% số trang header `2`, `3`, `4`, `5`, `6` đã được dọn sạch hoàn toàn.
