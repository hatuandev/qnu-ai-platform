# Phiên 741 — Chặn runtime cũ và phục hồi compilation

- Yêu cầu tiếp tục sửa sau lượt chẩn đoán bị ngắt. Người dùng giữ ngoại lệ không tự chạy test; không restart dịch vụ hoặc gọi model trong phiên này.
- Căn cứ lượt chẩn đoán trước: log người dùng lỗi validation.unread_source_blocks undefined; draft API thiếu marker, SELECT chỉ đọc xác nhận lượt mới vẫn prompt/v2 trong khi mã trên đĩa đã v3. Checkpoint đã chuyển sang bản trung gian chưa review và giữ bản gốc trong compilationHistory.
- Sửa scripts/v1_e2e_session.py: ghi hash đường dẫn/nội dung Python backend trước khi khởi động API/worker; từ chối readiness nếu mã đổi trong lúc khởi động. run_stage chặn trước stage khi thiếu/mismatch hash; hướng dẫn restart serve, không tự restart. Chỉ xét source, không đưa bí mật vào hash/log.
- Sửa compilation-upgrade.ts/workflow.spec.ts: dùng lịch sử cùng document để tìm finding gốc nếu bản trung gian chưa có review. Nếu server đã có review cho bản trung gian thì không tự thay, để luồng hiện có xử lý trạng thái. Dùng khóa source-limits-v2 để tránh replay kết quả v1 tạo bằng mã cũ. Giữ bản cũ và gate; thông báo thiếu marker chỉ rõ restart.
- Thêm regression offline runner và frontend helper cho guard mã cũ, hash nội dung, lịch sử cùng document và không thay bản có review chưa lưu checkpoint. Chưa chạy theo yêu cầu.
- Test/build/lint/typecheck/live inference: NOT RUN. Chỉ đọc file/Git và cập nhật code/docs; không ghi DB/checkpoint/server.json phục vụ hoặc dừng tiến trình. Bằng chứng API/SELECT là lượt chẩn đoán trước, không phải runtime PASS của bản sửa này.
- Người dùng: Ctrl+C đúng cửa sổ serve, chạy lại serve/chờ sẵn sàng; cửa sổ khác run compilation, rồi publication. Không cần cleanup/init.
- Giới hạn: hash xác nhận mã ở thời điểm khởi động, không phải kiểm chứng ngữ nghĩa model; report có finding vẫn chặn. Lỗi/gate lịch sử 737 giữ nguyên.
