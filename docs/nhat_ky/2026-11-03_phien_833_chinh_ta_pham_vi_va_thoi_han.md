# Phiên833 — Chia nhóm và thời hạn kiểm tra chính tả

Hai lượt chọn 32 đoạn trên một trang gửi một POST và backend trả
`chat_output_truncated`. API client có thời hạn mặc định 30 giây nên giao diện
có thể ngắt trước khi nhận mã lỗi. Hai màn hình hiệu đính nay dùng cùng bộ chia
nhóm theo trang và kích thước cho mọi lựa chọn. Kết quả của phạm vi chọn có báo
cáo riêng. Lượt chọn một nhóm hoàn tất vẫn giữ liên kết đến kết quả đã lưu.

POST chính tả bỏ hẹn giờ mặc định phía trình duyệt và chờ kết quả backend theo
thời hạn ModelOps. Lỗi mất kết nối được ghi là chưa xác định, dừng phát nhóm mới
và giữ kết quả từ nhóm đang chạy. Lỗi cắt đầu ra được báo theo nhóm.

Vitest trọng tâm đạt 34 ca, gồm chọn 32 đoạn thành hai nhóm 20 và 12, loại bỏ
đoạn ngoài trang chọn và nhận lỗi backend sau 31 giây theo đồng hồ mô phỏng.
Lượt thử Playwright gặp lỗi kết nối tới cổng 3001 trước khi gửi yêu cầu model.
Toàn bộ Vitest frontend đạt 731/731 ca trong 86 tệp. Build, Biome phạm vi sửa
và `git diff --check` đạt.
