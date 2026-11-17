# Phiên 983 — Biên soạn tài liệu dài và cấu hình soát chính tả

- Bỏ ngưỡng kết thúc 25 phút của lượt biên dịch. Mỗi phần tuân giới hạn chờ hàng đợi và thời gian đợi model đã cấu hình. Nếu kết quả chưa xác định, giữ các phần đã xác nhận và giữ quy tắc tránh gửi lại. Mốc 25 phút dùng trong thông tin tác vụ.
- PDF từng dừng ở 4/7 đã hoàn tất 7/7 khi kiểm lại từ đúng checkpoint. Chỉ ba phần chưa gửi được gọi Qwen. Cả bảy phần có đúng một lần gửi. Bản ghép vượt kiểm tra checksum và giữ 11 bảng.
- Thêm `0031_spelling_defaults` và mục Soát chính tả trong Cài đặt hệ thống. Mặc định chỉ chữ OCR tự được soát. Chữ PDF và Word đọc trực tiếp có hai lựa chọn riêng. Lượt soát thủ công vẫn có thể chọn toàn bộ. Cấu hình chỉ áp dụng khi tác vụ tự động bắt đầu lần đầu cho phiên bản.
- Sau bóc tách, chuẩn bị nội dung và soát chính tả tiếp tục được xếp hàng riêng, theo giới hạn đồng thời ModelOps. Việc người dùng lưu gợi ý vẫn tạo phiên bản văn bản mới và gửi chuẩn bị lại từ phiên bản đã ghim.
- Worker trên bản sao kiểm thử cùng Qwen soát 167/167 đoạn ở PDF scan và 12/80 đoạn ở PDF hỗn hợp. PDF đọc trực tiếp và Word đọc trực tiếp tự bỏ qua. Dữ liệu kiểm thử dùng bản bóc tách đã có.
- Chạy thủ công trên đúng tệp Word đã tự bỏ qua cho kết quả 57/57 đoạn. Giao diện trên bản chạy cô lập hiển thị đúng mặc định ba công tắc.
- Hồi quy theo phạm vi đạt 77 ca bằng `backendV1/scripts/run_isolated_tests.py`, gồm giới hạn gọi tính sau hàng đợi, tiếp tục lượt đã qua 31 phút, phân quyền và lưu cấu hình, khôi phục lượt soát và tái chuẩn bị theo phiên bản đã lưu. Biome, Ruff và build FE V2 đạt. Bảy ca tiến độ FE đạt qua `node --experimental-strip-types --test src/lib/document-task-progress.test.ts`.
- Bộ toàn hệ thống `tests -q --maxfail=2` dừng sau 43 ca đạt tại hai lỗi nền `test_review_keeps_insufficient_evidence_truthful` và `test_openai_gateway_endpoints`. Migration chỉ áp cho cơ sở dữ liệu kiểm thử. Bản chạy chính cần áp `0031_spelling_defaults` trước khi nạp backend và worker mới.
