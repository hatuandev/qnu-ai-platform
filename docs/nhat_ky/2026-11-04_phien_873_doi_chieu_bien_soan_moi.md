# Phiên873 — Đối chiếu bản biên soạn sau sửa bảng và cảnh báo ảnh

Người dùng dừng việc xem trang OCR, chuyển yêu cầu sang kiểm tra Compiler
`cmp_9aebcdead469` trong collection `col_539580c0ee19`. Chỉ đọc API có xác thực
và kiểm quyền workspace; không chỉnh dữ liệu, gọi model, restart hay xuất bản.

## Kết quả kiểm tra thật

- Lượt biên soạn completed, source_first=true, 0,361325 giây; đây là bản nhanh
  giữ nguồn, không phải một lượt AI viết lại. Tiêu đề hiện là “demo”.
- Ghim đúng `ocr_646c1a473287`, native v3, bản OCR gốc v0; chưa chọn bản sửa chữ.
  Hash tệp gốc, canonical và manifest khớp snapshot evidence trả từ server.
- Giữ18 trang, 11 mảnh bảng, 660 ô. Bảng trong draft bằng literal tables trong
  canonical, bao gồm mapping và header của ba mảnh trang9–11.
- 450 khối nội dung chính giữ nguyên, không thấy khối có text bị bỏ sót/đổi chữ.
  1111 citation khớp evidence index/phạm vi/hash; không có reference ngoài nguồn.
- Sáu ghi chú đối chiếu nguồn thuộc text OCR ảnh trang13. Một giới hạn ảnh đã
  ghi rõ “đã có văn bản OCR”, dẫn ảnh +6 khối con; không còn báo ảnh chưa đọc.
- Đối chiếu ảnh nhúng gốc (cùng source hash) còn hai lỗi chữ OCR: “Phân hồi”
  phải là “Phản hồi”, “minh chúng” phải là “minh chứng”. Compiler giữ nguyên
  OCR nên hai lỗi này vẫn hiện trong draft; chưa tự sửa hoặc phê duyệt chúng.
- Semantic faithfulness là not_evaluated. Kết quả cấu trúc/citation đạt không
  chứng minh toàn bộ nội dung hay RAG đã hoàn hảo.

## Bằng chứng và giới hạn

GET Compiler status/progress/draft/markdown và GET evidence nguồn đều HTTP200.
Script đối chiếu cuối exit0, báo cáo tại thư mục bỏ qua Git
`tmp/compilation-review-873/comparison.json`. Nguồn/artifact đọc trước khi chuyển
task ở `tmp/docx-review-873/`; không commit corpus. Không chạy Pytest/build vì
không sửa code. Lượt đọc này không thay kết quả full gate FAIL của phiên872.

Kiểm hash manifest dùng snapshot evidence của artifact lưu trữ; không lấy hash
của JSON HTTP đã serialize lại để so với hash bytes manifest lưu trên storage.

Bước tiếp: xem/sửa hai chỗ chữ ở bản dẫn xuất rồi lưu trước khi duyệt/phát hành;
không cần chạy lại AI Compiler chỉ để kiểm cấu trúc. Người dùng quyết định bản
được duyệt; chưa thực hiện publish/index hay test câu hỏi.
