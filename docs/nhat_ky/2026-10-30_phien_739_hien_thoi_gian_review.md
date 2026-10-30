# Phiên 739 — Hiển thị thời gian review

- Người dùng đang chạy E2E và muốn biết thời gian xử lý thực tế, hiểu nhầm thông báo 300s là phải chờ đủ. Tiếp tục ngoại lệ không tự chạy test đã yêu cầu ở phiên 738.
- Sửa duy nhất thông báo/thời gian trong `frontendV1/e2e/stages/workflow.spec.ts`: nêu rõ giới hạn chờ tối đa, ghi thời gian review khi trạng thái completed bằng chênh lệch created_at/finished_at của server. Không dùng thời gian tải lại để giả làm thời gian model chạy; bỏ dòng thời gian nếu timestamp không hợp lệ.
- README E2E giải thích giới hạn và thời gian hoàn tất; thời gian review gồm toàn bộ lượt review trên server, không phải phép đo riêng tốc độ sinh token.
- Không đổi timeout, giới hạn token, thứ tự chặng, logic lỗi hoặc gọi thêm model. Không ngắt/restart phiên đang chạy. Thông báo mới có hiệu lực ở lần chạy test tiếp theo.
- Test/build/lint/live: NOT RUN theo yêu cầu. Chỉ đọc mã/diff và cập nhật file; không xác nhận runtime PASS. Kết quả/gate lịch sử giữ nguyên.
