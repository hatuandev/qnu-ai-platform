# Phiên 984 — Tối ưu biên dịch và soát chính tả

- Yêu cầu gồm bốn điểm từ review phiên 983. Phạm vi kiểm thử dùng dữ liệu thử nghiệm đã lưu và các kiểm thử cô lập.
- Lượt soát toàn văn bản chờ lượt soát tự động cùng phiên bản khi hai tác vụ đến gần nhau. Worker nhả khóa cơ sở dữ liệu khi đợi. Khi checksum, model và cấu hình khớp, lượt toàn văn bản dùng lại kết quả đã xác nhận. Tác vụ tự động bỏ qua khi đã có lượt toàn văn bản tương ứng.
- Bản nháp gộp được cập nhật tối đa một lần mỗi 30 giây khi chạy và cập nhật khi kết thúc nếu cần. Checkpoint của từng phần lưu ngay. Đường lấy bản nháp tạm và bản cuối vẫn dùng các cặp JSON/Markdown riêng kèm xác minh checksum.
- Lập ánh xạ ngữ cảnh một lần theo snapshot rồi dùng lại cho cả lập nhóm và gọi model. Trên PDF mẫu 1.128 đoạn, số lần dựng ngữ cảnh lúc lập nhóm giảm từ 1.083 xuống 46. Cùng phép đo cục bộ giảm từ 0,383 xuống 0,011 giây. So trực tiếp từng nhóm mới với cách dựng ngữ cảnh trước thay đổi đạt đủ 46/46.
- FE dùng API tóm tắt tiến độ. Phản hồi JSON mẫu của lượt PDF 7 phần giảm từ 2.834 xuống 71 byte. API chi tiết dùng một lần tải bản ghi phần và tính lại số đếm từ cùng tập dữ liệu.
- Ca tích hợp giao thoa hai lượt soát tái hiện cùng đoạn được gửi hai lần trên mã trước sửa. Sau sửa, mỗi đoạn trong bản mẫu xuất hiện đúng một lần. Bộ tích hợp cô lập đạt 57 ca. Chạy lại ba ca trọng tâm sau chỉnh sửa khóa lưu bản tạm đều đạt.
- Ruff và 34 ca đơn vị backend đạt. Biome, bảy ca tiến độ và build FE V2 đạt. Phép đo dùng bản đã bóc tách và tính riêng phần CPU hoặc phản hồi JSON. Chưa đo thời gian xử lý đầu cuối hay token trên Qwen thật cho đợt tối ưu này.
- Full gate `run_isolated_tests.py tests -q --maxfail=2` dừng sau 43 ca đạt ở cùng hai lỗi nền của phiên 983: `test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful` và `test_application_api_keys.py::test_openai_gateway_endpoints`.
