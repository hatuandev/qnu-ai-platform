# Phiên 892 — Kiểm chứng biên soạn kết hợp với Qwen

Chạy một lượt Biên soạn nhanh + AI bổ sung trên nguồn v0 người dùng chỉ định trong V1 local. Kiểm tra ModelOps chọn Qwen trên máy chủ QNU. Gửi một yêu cầu qua giao diện, giữ tùy chọn rà soát tắt để đo riêng Compiler.

- Từ root, `node tmp/check-892-hybrid-live.mjs` đạt, exit 0. API trả HTTP 201. Lượt hoàn tất sau 38,84 giây tính từ lúc nhận yêu cầu, trong đó worker chạy 38,18 giây. Bản nền xuất hiện trong lần kiểm tra ở giây 6,9. Hoàn tất 4/4 nhóm, độ đồng thời 2, tổng 80.926 token và không có lỗi nhóm.
- Bản nháp dùng đúng nguồn và phiên bản, khớp 433/433 khối chữ và có 433 dẫn chứng. Nguồn bóc tách này không có bảng có cấu trúc để kiểm. Kiểm schema và liên kết dẫn chứng đạt.
- Từ root, `node tmp/check-892-hybrid-result.mjs` đạt, exit 0. Lần đọc đầu dừng ở HTTP 404 do không có lượt rà soát tự động. Sau khi xử lý đúng trạng thái này, kiểm tra đọc lại thành công và không tạo lượt mới. UI hiển thị bản nháp và mục đề xuất.
- Cả bốn đoạn gợi ý AI trùng nguyên văn khối được dẫn và đến từ một trong bốn nhóm. Ba đề xuất metadata đều có trích dẫn nguyên văn, cùng giá trị đợt tuyển sinh ở ba đoạn. Đây là kiểm chứng luồng và bảo toàn nguồn trên một tài liệu, chưa đủ để chốt lợi ích AI trên các loại tài liệu khác. Bản thử giữ ở trạng thái nháp.
