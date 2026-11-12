# Phiên 942 — Thời hạn hội thoại và tác vụ tài liệu

- Tại tầng chuẩn bị yêu cầu ModelOps, chính sách `wait_for_completion` của model áp dụng cho biên soạn, rà soát bản biên soạn và soát chính tả. Hội thoại, trả lời RAG, làm rõ và kiểm chứng câu trả lời dùng thời hạn của model.
- Kiểm tra bằng giao dịch chỉ đọc trên DB local. Qwen mặc định có `timeout_seconds=300` và chính sách chờ đã bật. Sáu loại yêu cầu được chuẩn bị với đúng chế độ theo tác vụ. Kiểm tra này dừng trước khi gửi yêu cầu đến Qwen.
- Kiểm tra hồi quy trên DB cô lập tái hiện việc chính sách chờ của model áp dụng cả cho chat trước khi sửa. Ca này cũng xác minh bộ gọi HTTP giả lập có thể chờ phản hồi rà soát lâu hơn thời hạn thông thường.
- Tiến độ và thao tác dừng dùng cơ chế hiện có. Hàng đợi, kết nối, thời hạn toàn tác vụ và ngân sách rà soát vẫn áp dụng. Thay đổi nằm ở mã Backend V1, áp dụng sau khi tiến trình nạp mã mới.

## Kiểm chứng

- Từ root, `backendV1/.venv/Scripts/python.exe -B backendV1/scripts/run_isolated_tests.py tests/unit/test_chat_wait_760.py tests/unit/test_seed_qwen_wait_850.py tests/integration/test_chat_wait_760.py tests/integration/test_manual_review_queue_852.py tests/integration/test_chat_stop_updates_664.py -q -p no:cacheprovider` đạt 25 ca, exit 0. DB cô lập đã được dọn.
- Từ `frontendV2`, `node --experimental-strip-types --test src/lib/document-task-progress.test.ts` đạt 7 ca. Ruff trên hai tệp Python và `git diff --check` đạt.
- Full Pytest và gọi Qwen thật chưa chạy. Kiểm tra chỉ đọc dùng mã mới và cấu hình local, chưa khởi động lại API hoặc worker đang chạy.
