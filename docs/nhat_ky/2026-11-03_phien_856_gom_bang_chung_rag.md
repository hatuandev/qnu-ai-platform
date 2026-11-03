# Phiên 856 — Gom bằng chứng theo khoản

- Cùng một khoản của Quy chế 363 được chia ở ranh giới phần biên soạn trong Gen #2. Mở rộng theo parent cũ không lấy được hai điểm kế tiếp. Đối chiếu bản ghi thật và phát lại thuật toán trên chính các chunk đã lập chỉ mục.
- Gom dãy điểm theo số khoản, thứ tự chữ cái, vị trí block liền nhau trên cùng trang, input, OCR run, revision và hash. Xác thực kết quả bổ sung với manifest và scope. Hỗ trợ chỉ mục hiện hữu. Phạm vi gom hiện giới hạn cùng trang nguồn.
- Tính lại kích thước gói bằng chứng hoàn chỉnh và bỏ đoạn lân cận tùy chọn từ cuối nếu cần. Giữ bảng và các điểm cùng khoản. Trả lỗi rõ nếu gói bắt buộc vượt giới hạn. Gom truy vấn xác minh đoạn kề thành một lần.
- Bắt buộc cùng một phạm vi metadata cho đoạn gốc với đoạn kề, và cho bảng cùng các đoạn phụ thuộc. Prompt v15 yêu cầu trả đủ các điểm đã có căn cứ, nêu rõ phạm vi khi bằng chứng thiếu.
- Ruff và `git diff --check` đạt. Pytest đơn vị trọng tâm 57/57. Harness DB cô lập chạy `test_answers_api_648.py` và ca context trong `test_rag_scope_context_672.py` đạt 31/31. Phát lại chỉ đọc từ Gen #2 chọn đúng cả khoản. Full backend qua `make.ps1 test-be` chưa có kết quả tổng lúc bàn giao. Không gọi model thật, tạo chỉ mục hoặc sửa dữ liệu live trong phiên này.
