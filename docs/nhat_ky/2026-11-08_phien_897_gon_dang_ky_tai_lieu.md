# Phiên897 — Gọn hộp đăng ký tài liệu

## Yêu cầu và phạm vi

Bỏ phần “Thông tin tài liệu” chỉ để xem trong hộp đăng ký. Đã nêu rõ cách hiểu
trong trao đổi: ẩn “Thêm phiên bản mới” khi **chưa có** tài liệu đích; có đích thì
hiện để chọn. Không thay cơ chế tự nhận diện và lưu thông tin có căn cứ từ896.

## Thay đổi

- `frontendV1/src/features/knowledge/register-document-dialog.tsx`: bỏ phần thông
  tin đọc; giữ GET chuẩn bị/hash và thông báo tải/lỗi ngắn. Kho trống hiện trực
  tiếp biểu mẫu tạo tài liệu. Chỉ hiện hai lựa chọn khi truy vấn danh sách thành
  công và có đích; lỗi danh sách hiện riêng và cho tải lại. Kiểm đích còn trong
  danh sách trước gửi; khóa đổi hình thức khi đang lưu.
- Bỏ component `automatic-document-information.tsx` vừa thêm ở896 vì không còn
  nơi sử dụng; không xóa code nhận diện, API hoặc provenance.
- `frontendV1/tests/automatic-metadata-896.test.tsx`: cập nhật kiểm tra giao diện
  và bổ sung lưu phiên bản, lỗi danh sách, đích biến mất. Giữ kiểm tra hash,
  không bịa giá trị, lỗi chuẩn bị và cache theo session/run.
- Đồng bộ hướng dẫn quy trình22/33 và memory. Giữ các thay đổi chưa commit896.

## Kiểm chứng thực chạy

Trong `frontendV1/`:

- `npm exec -- biome check src/features/knowledge/register-document-dialog.tsx tests/automatic-metadata-896.test.tsx`: PASS, exit0.
- `npx vitest run tests/automatic-metadata-896.test.tsx`: PASS7/7, exit0.
  Lượt đầu5/7 do hai test mới ghi nhầm endpoint `/documents` thay vì contract
  `/compiled-documents`; sửa kỳ vọng đúng contract rồi chạy lại đủ7 ca đạt.
- `npm run build`: PASS, exit0; gồm Vite và TypeScript. Còn cảnh báo kích thước
  bundle lớn, không làm build thất bại. Log tại `tmp/check897-build.log`.
- Chromium trên fixture cô lập cổng3097: PASS8 tổ hợp,390/1280px, sáng/tối,
  kho trống/có đích. Kiểm lựa chọn, submit sẵn sàng, không có mục thông tin,
  không tràn ngang và không lỗi page. Có thử chọn tài liệu đích qua Select thật.
  Receipt `tmp/check897-browser-receipt.json`, ảnh `tmp/check897-dialog-*.png`.
  Đã xem ảnh màn hình nhỏ; không gửi POST. Đã dừng riêng Vite fixture và xóa
  hai tệp fixture HTML/TSX sau kiểm tra.

Không chạy full suite hoặc test backend/model thật cho thay đổi FE này. Lỗi nền
và phần fullBE chưa hoàn tất ở896 vẫn giữ nguyên, không tuyên bố toàn hệ thống
PASS. Không restart app, sửa DB, reindex, publish hay push. Người dùng tải lại
trang hoặc mở lại hộp đăng ký để xem thay đổi.
