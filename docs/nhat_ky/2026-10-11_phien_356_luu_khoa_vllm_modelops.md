# Phiên #356 — Lưu khóa vLLM vào ModelOps

- Người dùng yêu cầu lưu khóa cho `prov_rtx5090_vllm`.
- Truyền khóa qua nhập ẩn trong tiến trình tạm, không ghi khóa vào mã nguồn, script seed, .env hay nhật ký.
- Kiểm tra trùng khóa bằng dữ liệu giải mã trong bộ nhớ; thêm qua `ProviderService.add_provider_key` để đồng bộ Key Pool PostgreSQL và cấu hình provider.
- Xác nhận DB: khóa mã hóa, một khóa khớp đang active. Không thay endpoint/model hoặc cấu hình PaddleOCR.
- Kiểm tra thật qua Tailscale: vLLM `/models` gửi Bearer từ bộ nhớ trả HTTP 200, danh sách 2 model. Chưa kiểm thử embedding/rerank inference trong phiên này.
- Không sửa runtime source; không cần chạy lại build/Pytest cho thay đổi dữ liệu cấu hình. Không reset DB, không restart worker, không sửa qnu-sso.
- Khóa đã xuất hiện trong hội thoại: nên thay khóa sau khi hoàn tất kiểm thử.
