# Phiên 798 — Bản xem OCR MD/JSON có đánh dấu chính tả

Người dùng muốn xem đầu ra OCR và bôi đậm các chỗ lỗi chính tả. Tạo bản xem dẫn
xuất từ OCR 176 DPI của phiên797, không thay nguồn, bản sửa27 hoặc compiler.

## Đầu ra

- `tmp/ocr798/quy-che-363-ocr-highlight.md`: đủ32trang, bôi đậm chữ gốc và ghi chữ sửa.
- `tmp/ocr798/quy-che-363-ocr-highlight.json`: giữ text/bbox/bảng gốc; thêm
  `text_markdown`, `spelling_annotations`, vị trí Unicode, trang/evidence/status.
- `tmp/ocr798/ocr-original.json` và `ocr-original.md`: bản gốc để đối chiếu.
- `tmp/ocr798/verification.json`: kết quả kiểm tra dẫn xuất.

Đánh dấu170 gợi ý đã được AI áp dụng (chưa đối chiếu ảnh toàn bộ), cùng1lỗi còn lại
ở trang31 đã xem ảnh nguồn: PHỤ LỰC → PHỤ LỤC, chưa áp dụng thay đổi này vào DB.
40gợi ý bị loại nằm riêng, không đánh dấu như lỗi đã xác nhận. Trang27 và bảng
trang32 vẫn có ghi chú unresolved từ phiên797. Không tuyên bố đã tìm hết lỗi.

## Kiểm tra đã chạy

- GET canonical qua API và kiểm SHA256 khớp `bf81dd5b252b66e18dfb1e3f32ae271f340d49f411324a9a6ef4e31a1ac7dcb0`.
  JSON baseline lưu bởi runner đã đổi whitespace; đối chiếu bằng cấu trúc, lấy bytes
  API thật làm bản gốc xuất kèm và đối chiếu hash. Không bỏ kiểm tra hash.
- Xác nhận170span đều khớp đúng chữ gốc, đúng đoạn đã lưu sửa, không chồng lấn;
  171annotation gồm1lỗi đối chiếu ảnh, không có span rỗng/whitespace biên.
- Xác nhận32trang, mọi text/bbox/cell giữ nguyên,40gợi ý bị loại tách biệt;
  JSON đọc lại hợp lệ, UTF-8 không BOM/LF, diff whitespace PASS.
- Xem ảnh nguồn trang31 và đọc mẫu Markdown. Không gọi model mới, không đổi
  ModelOps, không sửa code ứng dụng, không publish/index. Không chạy lại suite ứng dụng
  cho việc tạo bản xem; kết quả test797 vẫn là lịch sử.

Ảnh tham chiếu cục bộ: `tmp/ocr797/page-31.png`. Các file bản xem nằm trong tmp,
không thêm corpus vào Git. Bản xem này không phải canonical dùng làm bằng chứng mới.
