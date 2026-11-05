# Phiên871 — Đối chiếu bản biên soạn DOCX mới

Người dùng yêu cầu xem lượt `cmp_f92e89414db2` tại collection
`col_539580c0ee19`. Chỉ đọc API có xác thực/quyền workspace, tải artifact vào
thư mục bỏ qua Git `tmp/docx-review-871/`; không sửa code/dữ liệu ứng dụng,
không gọi model, không publish/index hay khởi động lại dịch vụ.

## Kết quả thực đọc và đối chiếu

- Run completed, source_first=true, thời gian thực0,412739s; bản nháp chưa xuất bản.
- Nguồn DOCX có cùng SHA256 với mẫu đã đối chiếu phiên869/870; extraction dùng
  qnu-native/v2 và MinerU. OCR nguồn hoàn tất18/18 trang.
- Giữ11 bảng/660 ô, bằng dữ liệu canonical và kết quả đối chiếu offline phiên870
  về giá trị, rowspan/colspan/header. Bảng trang17 giữ đúng thứ tự dấu gạch dưới,
  số0 đầu và ký hiệu.
- 450 khối nội dung chính giữ nguyên text đã bóc tách; không thiếu khối có text.
  1111/1111 citation trỏ evidence tồn tại và đúng hash nguồn/canonical.
- Trang13 có thêm6 khối text OCR ảnh với asset/bbox nguồn, đọc được nhãn/nội
  dung của3 khung. Nhìn trực tiếp ảnh nguồn xác nhận còn2 lỗi chữ/dấu cần sửa.
- Bảng nối trang9–11 vẫn requires_review do từng mảnh chưa khớp duy nhất với
  toàn bảng DOCX. Giữ cảnh báo, chưa coi là đã xác minh header liên trang.
- Khối ảnh gốc trang13 có text rỗng, trong khi text OCR vùng đã nằm ở block khác.
  Thông báo chưa có text cho khối gốc dễ gây hiểu nhầm rằng cả ảnh chưa đọc.
- Semantic faithfulness của bản nhanh là not_evaluated; chưa kiểm chất lượng
  câu trả lời RAG hoặc coi việc giữ đủ ID là chứng minh đúng mọi ngữ nghĩa.

## Bằng chứng và giới hạn

Python venv V1 gọi GET status/draft/markdown/progress và GET OCR
status/document/manifest/raw page13 đều HTTP200, exit0. Script đối chiếu
`comparison.json` ghi không có citation hỏng, text thay đổi hoặc khối text bỏ sót
so với canonical. Đọc ảnh sơ đồ và đối chiếu bảng gốc bằng python-docx, exit0.
Đây là kiểm tra artifact thật, không chạy Pytest/build vì không đổi ứng dụng.

Khuyến nghị rà lại2 lỗi chính tả OCR và3 mảnh bảng trước phát hành; tiếp tục giữ
nguồn và phiên bản. Chưa tự tạo sửa văn bản, compiler mới hoặc review AI.
