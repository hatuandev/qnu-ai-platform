# Phiên 855 — Phân luồng trước RAG cho trợ lý V1

- Đối chiếu `web/src/services/conversationalIntent.mjs`, `web/server/guards.mjs` và `web/server/answer-safety.mjs` của chatbot-tuyensinh với hội thoại V1.
- Tích hợp lời chào, cảm ơn, nhận diện trợ lý và từ chối các mẫu yêu cầu trực tiếp tiết lộ thông tin xác thực hoặc chỉ dẫn nội bộ. Áp dụng tự động theo snapshot trợ lý. Giữ kiểm tra quyền, idempotency và lịch sử hội thoại, loại lượt trả lời trực tiếp khỏi lịch sử làm rõ truy vấn.
- Câu nghiệp vụ, câu hỗn hợp và lời đáp mơ hồ tiếp tục đi theo RAG. Quy tắc nhận diện ngoài phạm vi theo danh mục tuyển sinh và bộ lọc riêng theo trường được giữ ngoài phạm vi thay đổi.
- Ruff, Biome và `npm run build` đạt. Pytest đơn vị 11/11, Vitest trọng tâm 16/16. Lượt thử harness từ thư mục backend thiếu cấu hình PostgreSQL root và dừng trước pytest. Chạy lại từ root bằng harness DB cô lập với `tests/integration/test_conversations_649.py -q` đạt 19/19. Full backend qua `make.ps1 test-be` đã khởi chạy và chưa có kết quả tổng khi bàn giao.
- Kiểm tra với model thật và trình duyệt live chưa chạy.
