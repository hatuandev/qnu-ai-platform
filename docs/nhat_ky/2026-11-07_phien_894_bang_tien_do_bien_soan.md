# Phiên 894 — Bảng tiến độ biên soạn nền

## Yêu cầu và phạm vi

Người dùng muốn bảng theo dõi góc phải tương tự hàng đợi Google Drive. Giữ job Compiler trong backend hiện có; chỉ đổi trải nghiệm frontend. Bảo toàn mọi thay đổi chưa commit của phiên trước/người dùng. Không gọi model, sửa DB, restart app, phát hành hay push.

## Thay đổi

- `compilation-activity.tsx`: danh sách lượt được theo dõi trong phiên đăng nhập, ghép theo run ID để replay không tạo dòng trùng. Provider ở cấp ứng dụng giữ trạng thái khi đổi trang; thay actor/session hoặc đăng xuất xóa danh sách ngay. Phản hồi tạo lượt về muộn không ghi vào phiên mới.
- `compilation-activity-panel.tsx`: bảng cố định góc phải dưới, tên tài liệu mở đúng trang kết quả; trạng thái và số nhóm từ API `/progress`. Chỉ có phần trăm khi tổng nhóm đã xác định, không dự báo thời gian hay tăng phần trăm theo đồng hồ. Thu gọn giữ observer; GET cập nhật mỗi 3 giây đến terminal, không tạo lại job. Lỗi kết nối là cảnh báo theo dõi, không biến thành thất bại job; 401/403/404 bỏ mục không còn truy cập được.
- Mutation tạo Compiler đăng ký lượt vào bảng sau phản hồi thành công; trang tệp giữ nguyên thay vì chuyển bắt buộc sang chi tiết. Một POST tạo job như trước, giữ khóa idempotency và cấu hình nguồn/model. Lượt terminal có menu ẩn khỏi danh sách, không xóa dữ liệu.
- AdminShell gắn bảng cho các trang V1. Tái dùng Button/Collapsible/Progress/DropdownMenu, semantic tokens và Lucide; không thêm dependency.

## Kiểm chứng thực chạy

CWD `frontendV1` nếu không ghi khác:

1. `npx vitest run tests/compilation-activity-894.test.tsx tests/compilation-dialog-state-809.test.tsx tests/compilation-tabs-849.test.tsx`: **24 PASS**, exit 0. Gồm 13 ca mới: tạo lượt đúng endpoint, replay dedup, chuyển trang, thu gọn vẫn poll, terminal dừng poll, chưa có tổng không giả %, nhiều workspace, đổi session/actor/logout, mất quyền, mất kết nối, các trạng thái terminal, phản hồi muộn sau đổi tài khoản. Lượt đầu phát hiện cần `hidden` tường minh cho panel và test clock phải được thiết lập trước khi observer tạo interval; đã sửa, không thay kỳ vọng nghiệp vụ.
2. Biome phạm vi 10 file sửa/test: **PASS**, exit 0. `npm run build` lần đầu và lượt cuối `npx vite build` + `npx tsc --noEmit`: **PASS**, exit 0. Vite vẫn cảnh báo chunk lớn hơn 500 KB và config native như trước.
3. `npx vitest run --maxWorkers=2`: **FAIL**, exit 1, 842 PASS / 10 FAIL, 99/102 file đạt. Log `tmp/check-894-full-fe.log`. Sáu failure OCR806 trùng danh sách baseline882 (zoom; cases 3/5/7/8/12); một failure publication transport là assertion `/draft$` trong khi URL có `?group_by_source=true` đã ghi ở879. Ba ca replacement678 chờ nút `/Tải lên phiên bản/` nhưng UI hiện là `Tải lên` (defaults staged; upload mode/idempotency; switching source). Test và `revision-upload-dialog.tsx` không đổi so với HEAD. Không sửa hoặc loại bỏ các ca ngoài phạm vi để làm xanh. Ca mới phản hồi muộn bổ sung sau lượt full, kiểm lại trong nhóm 24 đạt ở mục1; chưa chạy full lần hai.
4. Chromium qua Vite cô lập cổng3094, API giả lập chặn mọi `/platform/v1alpha1/**`: **4 cấu hình PASS**, 390/1280px, sáng/tối. Mỗi kịch bản đúng một POST, hai GET progress; chuyển trang vẫn thấy bảng, thu gọn vẫn cập nhật, mở đúng kết quả và ẩn terminal qua menu. Đã xem ảnh sáng/tối; không tràn màn hình. Receipt `tmp/check-894-browser-receipt.json`; ảnh `tmp/check-894-panel-{light,dark}-{390,1280}.png`. Dừng server cô lập và xóa hai fixture FE sau kiểm tra.

## Giới hạn và cách dùng

- Từ lượt mới, bấm Biên soạn rồi tiếp tục dùng ứng dụng; bảng tự hiện, bấm tên để xem bản nháp. Thu gọn không dừng công việc. Chưa thêm nút hủy job trong bảng.
- Danh sách theo dõi nằm trong bộ nhớ của phiên hiện tại; tải lại/đóng trang làm mất bảng, không làm mất/dừng job backend. Có thể vào lịch sử Biên soạn của kho để xem kết quả. Không lưu token hoặc tên tài liệu vào browser storage.
- Mốc phần trăm phản ánh các nhóm hoàn tất, không đo phần đang sinh token. Bổ sung AI chưa đầy đủ vẫn phải đọc thông báo tại trang kết quả; hoàn tất biên soạn không đồng nghĩa duyệt/phát hành.
- **NOT RUN** model thật/backend suite trong phiên này vì không đổi hành vi backend. Mock/UI tests không chứng minh tốc độ hoặc chất lượng model.
