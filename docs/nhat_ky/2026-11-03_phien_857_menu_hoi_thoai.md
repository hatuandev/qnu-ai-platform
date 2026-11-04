# Phiên 857 — Thao tác hội thoại

Sidebar gắn thao tác lưu trữ vào ID của hộp đổi tên, có thể gọi nhầm đường dẫn khi chưa chọn đổi tên. Menu từng dòng và menu đầu khung chat hiện dùng chung `LifecycleActions`, truyền ID của chính hội thoại. Đưa vào thùng rác giữ cơ chế xem trước, xác nhận, quyền và audit hiện có. Khi xóa hội thoại đang xem, giao diện quay về danh sách.

## Kịch bản kiểm thử trên app V1 local

Dùng dữ liệu thử. Mở app bằng `.\make.ps1 dev` nếu chưa chạy, vào **Hội thoại** ở cổng 3001.

| Bước | Thao tác | Kết quả mong đợi |
| --- | --- | --- |
| 1 | Tạo hai hội thoại cho cùng trợ lý, đặt tên **Test A** và **Test B** | Hai dòng riêng, chọn dòng nào mở đúng hội thoại đó |
| 2 | Gửi “Xin chào” trong Test A. Mở menu ⋯ của Test B ngay trên sidebar và đổi tên thành **Test B đổi tên** | Test A vẫn đang mở. Chỉ Test B đổi tên |
| 3 | Dùng menu ⋯ của Test B để **Lưu trữ**. Nhập lý do, xem trước tác động và xác nhận | Test B rời tab **Đang mở**, xuất hiện ở **Lưu trữ**. Khi mở lại để xem, khung chat ở chế độ chỉ đọc |
| 4 | Dùng menu của Test B để **Khôi phục** qua cùng quy trình | Test B xuất hiện trong **Đang mở** và có thể gửi tin |
| 5 | Đang xem Test A, chọn **Đưa vào thùng rác** cho Test B rồi bấm **Hủy** | Hộp thoại chỉ yêu cầu xác nhận. Test B còn trong danh sách. Test A vẫn đang mở |
| 6 | Lặp lại thao tác với Test B và xác nhận | Test B biến mất khỏi danh sách thường. Test A và tin nhắn của nó vẫn hiển thị |
| 7 | Dùng menu ⋯ ở đầu Test A để **Đưa vào thùng rác** rồi xác nhận | Giao diện về danh sách. Tải lại trang, Test A vẫn ẩn. Link chi tiết cũ báo hội thoại không còn khả dụng |
| 8 | Kiểm tra lại ở màn hình hẹp và bằng bàn phím | Tab đến nút ⋯, Enter mở menu, Esc đóng menu. Nút và hộp xác nhận hiển thị trọn khung |

Nhãn **Đưa vào thùng rác** dùng đúng ngữ nghĩa của API hiện hành. Backend giữ dữ liệu gốc của hội thoại.

## Kiểm chứng

Vitest trọng tâm đạt 37/37 trên 5 file, gồm xác nhận đưa hội thoại đang mở và lưu trữ vào thùng rác qua API giả lập. Build frontend đạt. Kiểm tra trực quan và thao tác trên app local chưa chạy.
