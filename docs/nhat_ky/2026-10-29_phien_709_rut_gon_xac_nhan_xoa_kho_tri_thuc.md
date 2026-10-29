# Context709 — Rút gọn xác nhận xóa kho tri thức

Ngày 2026-10-29. Người dùng yêu cầu khi xóa chỉ hỏi có muốn xóa hay không,
không bắt nhập lý do. Cấu hình model, mặc định OCR và hạn mức giữ hiện tại theo
lựa chọn trước đó của người dùng.

## Thay đổi

- `frontendV1/src/features/lifecycle/action-dialog.tsx`: xóa collection/source/document
  hỏi **Hủy / Xóa**, bỏ ô lý do và checkbox. Tự chuẩn bị preview trên server;
  nút Xóa chỉ bật sau khi có preview hợp lệ. Hủy không gửi accept.
- API lifecycle giữ nguyên: lý do audit trung tính do giao diện sinh, hash,
  kiểm quyền, hạn sử dụng và khóa chống lặp vẫn được giữ. Mất phản hồi thử lại
  cùng thao tác; preview cũ cần chuẩn bị lại và người dùng bấm Xóa lần nữa.
- Form ghim theo phiên đăng nhập, workspace, tài nguyên và thao tác; đổi đích
  không dùng lại xác nhận cũ. Các thao tác archive/restore khác giữ luồng cũ.
- `frontendV1/tests/delete-confirmation-709.test.tsx`: 11 ca hành vi, qua client
  HTTP thật với phản hồi giả lập có kiểm payload/hash/key và các lỗi âm tính.
- Đồng bộ hướng dẫn34, nhật ký/index/memory/snapshot. Không sửa backend/config.

## Kiểm chứng

Lệnh chạy trong `frontendV1`, log ở `storage/artifacts/delete-confirmation-709/`:

| Kiểm tra | Kết quả |
|---|---|
| Probe trước sửa | 9 FAIL, tái hiện còn form lý do và thiếu Hủy/Xóa |
| `npm test -- tests/delete-confirmation-709.test.tsx tests/lifecycle-operations-ui-678.test.tsx --maxWorkers=2` | 29 PASS, gồm 11 mới và 18 lifecycle cũ |
| `npm test -- --maxWorkers=2` | 50 tệp, 450 PASS, 0 FAIL, 0 SKIP (`full.log`) |
| `npm run build` (Vite + TypeScript) | PASS; còn cảnh báo kích thước bundle/config Vite (`build.log`) |
| `npm exec -- biome check src/features/lifecycle/action-dialog.tsx tests/delete-confirmation-709.test.tsx` | PASS, exit0, 2 tệp, không sửa tự động |
| Browser thật desktop và 390×844 | Hộp thoại không ô nhập/checkbox, Hủy đóng; hai tài liệu người dùng giữ nguyên |
| Backend/full lint/live OCR | NOT RUN: không đổi backend/contract; lint toàn cục có lỗi ngoài phạm vi ở phiên708; giữ cấu hình AI hiện tại |

Các tiến trình test/build đã hoàn tất khi đọc lại log sau tiếp tục phiên;
không còn session để lấy lại mã thoát. Log ghi đủ tổng PASS và build không có lỗi
TypeScript; không coi đây là một lần chạy backend mới. Kiểm scoped Biome cuối exit0.

Ảnh desktop/mobile ở `confirmation-desktop.png` và `confirmation-mobile.png`
trong thư mục artifact trên. Không bấm Xóa tài liệu thật của người dùng;
accept và retry được kiểm qua test HTTP giả lập. Preview thật chưa thay tài nguyên.

## Giới hạn và bàn giao

Chỉ rút gọn UI cho xóa trong kho tri thức; vẫn đưa vào thùng rác và khôi phục
theo quyền hiện có. Không thay đổi model/grants/quota, không restart/migrate,
publish/reindex hoặc commit/push. Dịch vụ phát triển nhận bản sửa qua hot reload.
