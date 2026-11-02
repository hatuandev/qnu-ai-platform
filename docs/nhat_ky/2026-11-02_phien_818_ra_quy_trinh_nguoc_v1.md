# Phiên 818 — Rà vấn đề còn lại của quy trình ngược V1

Yêu cầu: user quay lại luồng dừng phục vụ, chỉnh sửa và thay văn bản; hỏi còn gì cần xử lý. Không giao đổi model hay sửa workflow trong lượt này.

Đã đọc Git/diff/context, lifecycle/publication/source upload/replacement/index/search/conversation và FE liên quan. Giữ các docs815–817 chưa commit, không sửa mã ứng dụng.

## Phát hiện và bằng chứng

1. P2: trang compiled document dùng requested_at của index so với thời điểm publish để tính ready. Replacement chuẩn bị index trước rồi publish khi activate nên UI báo chưa index dù replacement thành công. Cần binding version/decision/hash, không sửa bằng timestamp khác.
2. P2: commit withdraw/publish chỉ invalidate publication, chưa làm mới cache conversation history/turn. Nội dung cũ có thể hiện tới refetch. Backend vẫn revalidate khi đọc lịch sử; chưa thấy bằng chứng retrieval vượt withdrawal. Cần refresh cache bị ảnh hưởng và xác định cập nhật giữa các tab nếu có yêu cầu.

Tái hiện offline bằng production expression và mutation onSuccess+QueryClient. Lệnh tại frontendV1 chạy audit mới và bốn testfiles lifecycle/replacement/809: exit1,26PASS/2FAIL. Hai FAIL đúng phát hiện trên; không sửa assert/app/retry. Giữ test trong tmp/audit818, không thêm ca đỏ vào suite mặc định.

## Việc chưa nghiệm thu

- Worker còn timeout1800s ở settings.py:62; không bị xoá bởi wait_for_completion HTTP. Chưa thử runtime >30phút ở phiên này.
- Live replacement phiên811 vẫn dừng compiler, staged→replace→chat trước/sau chưa nghiệm thu trọn với model thật. Repo có testfixtures nhưng phiên này chỉ chạy FE phạm vi; không chạy BE/API/live/build/fullsuite và không coi đó là PASS.
- Regression809 save chọn phiên bản server và giữ form compiler đạt trong lượt này.

Artifact chi tiết: tmp/audit818/REPORT.md và reverse-flow-audit-818.test.ts. Không modelcall/DBchange/reindex/restart/defaultswitch/commit/push. Kết luận: còn hai lỗi FE tái hiện và hai việc vận hành/nghiệm thu cần xử lý; không khẳng định đã sạch lỗi toàn hệ thống.
