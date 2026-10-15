# Phiên 448 — Đối chiếu nội dung cẩm nang Word 2025 với PDF gốc

## Mục tiêu và phạm vi

Người dùng yêu cầu xem nội dung cẩm nang có gì không đúng. Chỉ đọc và đối chiếu; không chỉnh DOCX, mã runtime, DB, cấu hình, chỉ mục hay trạng thái xuất bản. Không gọi model, không chạy lại chatbot. Dùng skill documents và pdf để đọc nội dung cùng ảnh trang PDF.

Nguồn Word: `C:/Users/AnhTuan/Downloads/Cam_Nang_Tuyen_Sinh_Dai_Hoc_2025_QNU.docx`, 80.639 byte; SHA-256 `09e77734621c1a57f3c06d690f91abd0ffea13fa6836ee73f561eeeabddbe887`.

Nguồn đối chiếu: `C:/Users/AnhTuan/Downloads/TUYỂN SINH - HẰNG-20261012T083111Z-1-001/TUYỂN SINH - HẰNG/BÁO CÁO TUYỂN SINH/Cẩm Nang Tuyển Sinh Đại Học Năm 2025 (1).pdf`, 108 trang. Kết luận là độ trung thành với PDF người dùng cung cấp, không thay thế xác nhận pháp lý hoặc thông báo tuyển sinh cập nhật.

## Sai lệch và thiếu nội dung đã xác nhận

1. Phương thức 2 trong Word bỏ điều kiện **trừ các ngành sư phạm**. Điều kiện này hiện rõ ở trang 1 PDF; bỏ điều kiện có thể khiến bot tư vấn xét học bạ cho sư phạm năm 2025 sai.
2. Phương thức 3 thêm **ĐHQG Hà Nội**. Trang 1 PDF chỉ ghi ĐHQG TP.HCM, kèm loại trừ sư phạm. Chưa có căn cứ trong PDF cho phần bổ sung.
3. Phương thức 4 đổi **Trường ĐHSP Hà Nội** thành **các trường ĐH Sư phạm**, mở rộng phạm vi không được nguồn trang 1 chứng minh.
4. Word thêm `(VẬT LÝ KỸ THUẬT)` vào tiêu đề Khoa học vật liệu và ghi chú tương ứng hai định hướng. Trang 70 PDF ghi Khoa học vật liệu / 7440122; bảng trang 3 ghi Vật lý kỹ thuật (chuyên ngành Bán dẫn) / 7520401. Khác biệt tên/mã đã tồn tại trong PDF; không thể dùng ghi chú tự thêm để xác nhận đồng nhất hai ngành. Cần người có thẩm quyền xác nhận, giữ hai thông tin riêng trong lúc chờ.
5. Word không có tổng **5.800 chỉ tiêu** ở trang 1 PDF.
6. Word thiếu khối liên hệ trang 108 PDF: hotline `1800 55 88 49`, email `tuvantuyensinh@qnu.edu.vn`, website `tuyensinh.qnu.edu.vn`, fanpage Tuyển sinh Trường Đại học Quy Nhơn; địa chỉ 170 An Dương Vương, TP. Quy Nhơn, Bình Định ở trang 1 cũng không được giữ lại. Đây là thông tin lịch sử theo bản 2025, không tự khẳng định còn là địa chỉ hiện hành.

Sai khác nhỏ khi chuyển thành bản chữ: lược câu mô tả tính tỉ mỉ/nhẫn nại của công việc phiên-biên dịch Ngôn ngữ Trung Quốc (PDF trang 39); lược danh sách tỉnh của các Sở TNMT ở phần đối tác Công nghệ kỹ thuật hóa học (PDF trang 81). Danh sách đối tác ô tô trong PDF có dòng Hyundai Bình Định lặp, bản Word bỏ lần lặp; không coi việc khử lặp này là đổi nghĩa.

## Nội dung đúng và phân biệt lỗi dữ liệu với lỗi app

- Word có một bảng native 53 hàng: 1 header + 52 mục ngành. Hàng Sư phạm Lịch sử / 7140218 trong Word có đầy đủ 7 tổ hợp; không chỉ có ký tự `(`. Việc DB phiên 447 chỉ có 7 facts và hàng cuối bị cụt là vấn đề ingestion/parse qua trang, không chứng minh Word mất bảng.
- Word có 51 mục mô tả ngành tương ứng 51 cặp trang PDF 4–105. So sánh tập số theo từng mục không thấy số riêng thêm/mất trong phần mô tả; đây chỉ là kiểm tra hỗ trợ, không chứng nhận toàn bộ ngữ nghĩa đều đúng.
- Đã xem trực tiếp trang 72 PDF: Kỹ thuật phần mềm 4,5 năm / 150 tín chỉ / Kỹ sư khớp Word. Sư phạm Toán 4 năm / 138 tín chỉ / Cử nhân khớp PDF trang 4.
- Không tự kết luận mục mô tả thiếu Kỹ thuật cơ khí động lực là lỗi chuyển đổi: PDF có 52 mục trong bảng nhưng chỉ 51 mục mô tả.
- 1.034 paragraph Word đều dùng style Normal, không có Heading 1/2; hình thức có thể đậm nhưng semantic heading không được khai báo. Nên chuẩn hóa heading ngành/tiểu mục và năm/phạm vi trước khi thay nguồn, đồng thời sửa parser giữ bảng native. Không coi chỉ sửa Word là đủ sửa mọi lỗi RAG.

## Phương pháp và giới hạn kiểm tra

Các script chỉ phục vụ đọc/so sánh, nằm tại `tmp/camnang_docx_review_2025/`: `inspect_content.py`, `compare_sections.py`, `text_differences.py`; tạo JSON/text/ảnh QA nội bộ. Dùng python-docx đọc body theo thứ tự, giữ hàng/cột bảng; so sánh 51 mục với text PDF và mở ảnh các trang quan trọng. Không dùng tỷ lệ giống chuỗi làm accuracy.

Renderer đóng gói thất bại vì không có LibreOffice `soffice.exe`. Thử mở read-only bằng Word COM để xuất preview cũng thất bại `0x80070520` (không có phiên logon phù hợp). Vì vậy đã kiểm tra nội dung XML và ảnh PDF gốc, **chưa kiểm chứng bố cục render của DOCX**; không trả một DOCX mới hay tuyên bố layout đạt.

Ruff/Pytest/Vite không chạy: không sửa runtime hoặc frontend. DOCX gốc không bị thay đổi. Cập nhật nhật ký này, README, PROJECT_CONTEXT và WORK_LOG để tránh nhầm lỗi tài liệu với lỗi ingestion đã ghi ở phiên 447.

## Hướng xử lý đề xuất, chưa triển khai

Sửa 3 sai lệch phương thức theo nguồn, bỏ ghi chú gộp ngành chưa được chứng minh, bổ sung chỉ tiêu/liên hệ lịch sử, dùng Heading 1/2 và giữ bảng native đầy đủ. Sau khi người dùng duyệt bản sửa mới thay revision rồi duyệt/nạp vector/xuất bản lại; không tự upload, reindex hoặc publish trong phiên này. Lỗi phạm vi năm, audit thiếu ý và key busy vẫn thuộc app, không được che bằng chỉnh tài liệu.
