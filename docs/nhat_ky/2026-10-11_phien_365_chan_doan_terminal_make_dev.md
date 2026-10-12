# Phiên #365 — Chẩn đoán terminal make dev

Ngày: 2026-10-11. Người dùng hỏi vì sao make dev không thấy terminal. Chỉ đọc runner/trạng thái; chưa sửa hoặc khởi động/dừng dịch vụ.

- Makefile dev chạy db ensure-ready, sau đó start-worker.ps1, rồi cmd/start với cmd/k cho Backend8001 và Frontend3000. BE/FE vẫn có lệnh mở terminal, không cấu hình Hidden ở Makefile.
- scripts/start-worker.ps1 cố ý chạy ARQ bằng Start-Process -WindowStyle Hidden và redirect stdout/stderr vào backend/storage/worker_logs; worker không có cửa sổ riêng. Nếu PID/startTicks còn đúng, script trả thông báo already running và không mở worker mới. Vì vậy make dev cũng không restart worker để nhận thay đổi code.
- State ghi PID8624, Get-Process thấy python8624; chưa xác minh command line/startTicks/heartbeat trong phiên này. Get-CimInstance bị access denied; không kết luận health/ownership từ PID đơn lẻ.
- make không có trong PATH của shell công cụ; không thể dry-run từ shell này, không suy ra terminal của người dùng cũng thiếu make. Không thực thi make dev để tránh sinh process hoặc DB ensure-ready.
- Nếu cả BE/FE không hiện, cần output make dev của người dùng để biết có lỗi ở bước ensure-ready/worker trước khi tới hai lệnh start; chưa đủ bằng chứng xác định nguyên nhân này.
- Chỉ cập nhật nhật ký/index/memory/snapshot/WORK_LOG. Không sửa runner/runtime, không tests ứng dụng vì chưa đổi code.
