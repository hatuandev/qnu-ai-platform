# Phiên 989 — Lịch đăng ký P5 và điểm Kế toán P7

## P5 — Lịch qua các khối OCR

- [event_schedule.py](../../backendV1/qnu/domains/knowledge/event_schedule.py) chỉ nhận khoảng ngày đầy đủ khi nối tối đa ba khối liền nhau trên cùng trang thành đúng một câu lịch có nhãn. Khối cần duyệt, bảng, hình, tiêu đề và khối mở câu mới dừng việc nối. [source_first.py](../../backendV1/qnu/domains/knowledge/compilation/source_first.py) giữ chữ và thứ tự bằng xuống dòng, giữ citation riêng của từng khối. Metadata được xác minh lại từ trích đoạn của đúng vị trí. Quy tắc metadata lên v7.
- [query_scope.py](../../backendV1/qnu/domains/knowledge/index/query_scope.py) áp năm, loại và kênh lên cùng một sự kiện đã xác minh. Khi câu hỏi chưa nêu kênh và có nhiều kênh đăng ký phù hợp, yêu cầu làm rõ. Hợp đồng `MetadataFilter` có ba trường sự kiện tùy chọn và OpenAPI đã cập nhật.
- C3 dùng đúng hai PDF đang kiểm thử. Bản source-first `cmp_8aad038ae917` đăng ký thành `cver_effe140fd95f` và phát hành trong kho cô lập sau khi ghi nhận bỏ qua rà soát. Chỉ mục `idx_c7553c7673ef` hoàn tất, dùng provider cấu hình sẵn. Câu QNU trả 01/06–30/06/2025, dẫn trang 9 và đủ ba khối `b011–b013`. Câu Bộ trả 16/07–28/07/2025, dẫn `b020–b021`. Câu hỏi chung trả mã 409 `answer_scope_clarification_required` kèm hai lựa chọn nguồn.

## P7 — Bảng trên trang trích xuất hỗn hợp

- Đối chiếu hai tầng tiêu đề và hàng Kế toán ở trang 12 PDF cập nhật. Ô `ev_p012_b001_c02_08` ghi **20,3**, thuộc cột **2025 / Điểm trúng tuyển**. Nhãn cũ ghi thiếu ô không phù hợp với PDF gốc và OCR hiện tại. Trên kho thử có giới hạn đúng hai PDF, giá trị DOCX giả lập 20,2 nằm ngoài phạm vi câu hỏi.
- Bảng có nguồn đọc trực tiếp (`block.origin=native`) và lưới hợp lệ. Trang tổng thể được đánh dấu `hybrid`, khiến [table_dependencies.py](../../backendV1/qnu/domains/knowledge/index/table_dependencies.py) trước đây bỏ qua hai hàng tiêu đề. Mã mới nhận tiêu đề nội bộ từ chính khối bảng trực tiếp trên trang hybrid. Khối OCR và quy tắc nối liên trang giữ điều kiện riêng. Chạy lại với Qwen thật trả HTTP 200, đúng 20,3 và đúng ô trên chỉ mục C3 đã tạo ở P5.

## Kiểm chứng

- Ruff theo phạm vi và `python -m pytest -q` trên tám tệp unit về lịch, scope, năm bảng và kiểm chứng dẫn chứng — **106 passed**. Harness DB cô lập chạy `test_automatic_metadata_896.py` và `test_contextual_scope_790.py` — **6 passed**, DB dọn thành công.
- Chạy đường API từ mã hiện tại với TestClient, worker gọi trực tiếp và provider thật trên đúng kho C3. P2 hồi quy trên cùng chỉ mục vẫn trả 2025 → 10,0 và 2026 → 9,0 với hai ô nguồn. Bằng chứng live lưu trong `%TEMP%/qnu_c3_989_p5_e2e.json`.
- Full backend, trình duyệt FE V2, tài liệu legacy và lượt gọi Qwen chuyên đề xuất metadata chưa được nghiệm thu ở phiên này. Không chạy bộ 100 câu. Chỉ tạo phiên bản và generation trên kho thử C3.
