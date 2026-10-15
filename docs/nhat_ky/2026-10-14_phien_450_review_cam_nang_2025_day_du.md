# Phiên 450 — Review cẩm nang 2025 đầy đủ do người dùng xử lý lại

## Phạm vi

Chỉ đọc file `C:/Users/AnhTuan/Downloads/Cam_nang_tuyen_sinh_Dai_hoc_Quy_Nhon_2025_day_du.docx` và đối chiếu PDF gốc 108 trang của người dùng. Không sửa DOCX, code ứng dụng, DB, index, cấu hình, upload, duyệt hay publish; không gọi model. Dùng skill documents/pdf, bộ Python bundled và ảnh PDF gốc.

File mới 54.958 byte (khoảng 53,7 KiB), SHA-256 `e6ddb2c892c3a8efbd83ddfd3dd318b91bc3eaa0ced082f5b7c2dcabfa0cd757`.

## Kết quả nội dung

- Đã sửa 3 sai lệch phiên448: học bạ có loại trừ sư phạm; PT3 chỉ ĐHQG TP.HCM và loại trừ sư phạm; PT4 cụ thể Trường ĐHSP Hà Nội. PT1 giữ năm2025.
- Có tổng5800 chỉ tiêu, mãDQN, địa chỉ lịch sử170 An Dương Vương; có hotline1800 55 88 49/emailtuvantuyensinh@qnu.edu.vn/websitetuyensinh.qnu.edu.vn/fanpage theo bản2025.
- Không còn ghi chú tự gộp Khoa học vật liệu7440122 với Vật lý kỹ thuật7520401. Hai tên/mã giữ riêng theo PDF. Khác biệt này vốn có trong PDF, chưa được xác nhận bằng văn bản mới; không tự suy tương đương hai ngành.
- Đủ108 mốc `Trang1…108`; đây là mốc trang PDF nguồn, **không phải số trang Word đã render**.
- Đủ52 records ngành/tổ hợp trong phần trang2–3, không có tổ hợp Sư phạm Lịch sử bị cắt. So sánh với bảng bảnWord trước: chỉ đổi cách viết7340301_ACCA thành7340301 ACCA (khớp cách trình bày PDF), và KT&PL/KT và PL về cùng nội dung. Đã xem ảnh bảng gốc2–3.
- So sánh text PDF trang4–106 với các phần tương ứng trongWord sau NFC: tập số theo từng trang không có số thêm/mất; khác biệt token còn lại là khử chữ tiêu đề giãn cách và sửa từ bị giãn chữ trongPDF. Trang98 Word có tiêu đề mà text extractor PDF bỏ sót; xem ảnh gốc98 xác nhận đó là tiêu đề thật, không phải nội dung tự thêm.
- Các lỗi đánh máy như `tài tợ`, `Lap7`, `VinAl` vẫn có trong text nguồn; không tự coi là sai lệch do bản chuyển đổi. Có thể biên tập chính tả sau khi đối chiếu nguồn/nguồn xác nhận, nhưng phiên này không sửa.

## Cấu trúc và lưu ý RAG

- 1242paragraphs, 0bảngWord native, 0hình. Style: Heading1=2, Heading2=108, Heading3=272, FirstParagraph=235, BodyText=415, Compact=156, Normal=54. 36paragraphs chưaNFC (Unicode tổ hợp), không phải nội dung sai hay mojibake; pipeline cần tiếp tục chuẩn hóaNFC.
- Phân cấp hiện tại: Heading2 là `Trang4`, Heading3 là `SƯ PHẠM TOÁN HỌC`; `GIỚI THIỆU`/`CƠ HỘI VIỆC LÀM` cũng Heading3; sang `Trang5` (Heading2) rồi `HỌC BỔNG` (Heading3). Theo outline, mục con không còn nằm dưới tên ngành và headingtrang thay cha khi qua trang. Đây là rủi ro semanticcontext, chưa phải kết quả kiểm thử ingestion/live.
- Khuyến nghị Heading2=tên ngành, Heading3=mục con; nhãn TrangX để ghi chú nguồn hoặc marker trang, không làm heading phá ngữ cảnh ngành. Giữ ngành qua hai phần/trang liên tiếp.
- 52 records đang là prose, nội dung đầy đủ và có thể dùng retrieval văn bản. Nếu cần StructuredFactLayer, nên giữ thêm bảngWord native với các cột mãngành/tênngành/năm/tổhợp; không tuyên bố bản prose sẽ tự sinh đầy đủ facts khi ingestion chưa thử.
- Có đoạn văn bị tách giữa viết tắt như `Đại học Kinh tế TP.` rồi `HCM,…` ở phầnTrang99; nên nối lại đoạn nguyên nghĩa khi chuẩn hóa để hạn chế câu trích bị cụt.

## Kiểm tra và giới hạn

Script đọc/so sánh nội bộ ở `tmp/camnang_docx_review_450/`; đã tái sử dụng inspector phiên448 bằng thêm tham số input/output, giữ các kết quả cũ. Không có mã runtime thay đổi, không chạy Ruff/Pytest/Vite ứng dụng. File gốc không thay đổi.

Renderer DOCX đóng gói vẫn thất bại vì thiếu `soffice.exe`. Không dùng LibreOffice desktop hay cài thêm; tiếp tục review XML/text và ảnhPDF gốc. **Chưa xác nhận bố cục trangWord**, không tuyên bố layout đạt hay giao bảnWord mới.

Kết luận: nội dung chính đã sửa đúng và bám sátPDF gốc; còn chỉnh cấu trúc heading/bảng để thuận lợi choRAG vàfact extraction trước khi coi là bảnRAG chuẩn. Chưa nạp/test trongapp; chưa thay bản đang xuất bản.
