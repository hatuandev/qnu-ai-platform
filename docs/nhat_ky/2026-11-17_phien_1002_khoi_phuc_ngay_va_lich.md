# Phiên 1002 — Khôi phục ngày ban hành và lịch tuyển sinh

## Phạm vi

- Khôi phục ngày bị tách khối trên tiêu đề PDF có lớp văn bản gốc, nhận lịch thi và khoảng đăng ký ở phần nội dung, ghi ngày bắt đầu áp dụng của Word.
- Sửa bộ giả lập kiểm thử câu trả lời thiếu căn cứ để phản hồi đúng hợp đồng và chạy lại ca đã lỗi.

## Thay đổi

- `issued_line.py` chỉ ghép hai khối số nguyên bản có tọa độ rõ ràng trên cùng dòng ngày tháng ở đầu trang 1. Bản nháp giữ trích dẫn về cả ba khối. Metadata ghi năm ban hành khi bản nháp có đúng đoạn đã ghép cùng dẫn chứng. Tệp và JSON bóc tách nguồn vẫn giữ nguyên.
- `event_schedule.py` đọc danh sách ngày có tháng và năm dùng chung. Khoảng đăng ký được ghép từ tối đa ba khối liền kề khi đủ nhãn, ngày bắt đầu, ngày kết thúc và dấu kết câu. Khoảng đang dở sau từ “đến” hoặc “tới” cần đủ dữ liệu mới sinh sự kiện. Ngày thi và khoảng đăng ký giữ hai vai trò riêng.
- Metadata v10 nhận nhãn ngày bắt đầu áp dụng ở đầu trường, kể cả nhãn có ghi rõ “mô phỏng” trong dữ liệu. Bộ giả lập kiểm thử đọc cả hợp đồng dự phòng `question` và `situation`.

## Kiểm chứng

- PASS 124 unit tests theo phạm vi, Ruff. PASS 7 integration tests trên cơ sở dữ liệu cô lập, gồm `test_review_keeps_insufficient_evidence_truthful`. Cơ sở dữ liệu integration trọng tâm được tự dọn.
- Lệnh integration dùng `uv run --env-file ../.env python scripts/run_isolated_tests.py -q tests/integration/test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful tests/integration/test_automatic_metadata_896.py tests/integration/test_contextual_scope_790.py` trong `backendV1`. Bộ đầy đủ đã khởi chạy riêng, kết quả tổng chưa có lúc ghi nhận.
- PASS API trên kho thử `col_bd673c79c8c5`. Ba nguồn bóc tách và hoàn tất rà soát bằng Qwen trong một lượt gọi mỗi tài liệu, đều dừng `stop`. API đăng ký nháp lưu đúng giá trị metadata đã xem trước. PDF 2026 cho ngày 31/5/2026 dẫn ba khối gốc ở trang 1. PDF 2025 cho các ngày thi 1, 2 và 3/7/2025, một khoảng đăng ký 1–28/6/2025 và kênh đăng ký trong nguồn. DOCX phức tạp ghi ngày áp dụng 1/11/2026. Báo cáo DOCX có bảy mục cần đối chiếu ảnh hoặc ghi chú nguồn.
- Đợt này dừng ở bản nháp trong kho thử. Phát hành, lập chỉ mục và kiểm tra câu trả lời từ vector chưa chạy lại.

## Thời gian

So giữa bản trước và sau trên cùng ba tệp. Các lượt Qwen mới có thời gian chạy chồng nhau. Phép đo cục bộ luân phiên bản trước và sau trong cùng tiến trình trên cùng dữ liệu bóc tách, lấy trung vị của 21 mẫu mỗi bản. Cột thời gian cục bộ gồm dựng bản nháp và nhận metadata, không gồm I/O hoặc gọi model.

| Tài liệu | Cục bộ trước → sau | Rà soát Qwen trước → sau | Token rà soát trước → sau |
| --- | ---: | ---: | ---: |
| PDF tuyển sinh 2025 | 145,42 → 148,64 ms | 48,30 → 71,08 s | 7.774 → 9.258 |
| PDF tuyển sinh 2026 | 142,43 → 140,48 ms | 28,56 → 78,17 s | 5.119 → 6.057 |
| DOCX phức tạp | 121,55 → 110,40 ms | 62,28 → 61,95 s | 10.325 → 9.651 |

Lượt mới có thời gian bóc tách lần lượt 18,14 s, 19,22 s và 10,69 s. Thời gian biên soạn lần lượt 0,78 s, 1,44 s và 7,44 s. Hai PDF chậm hơn ở bước rà soát trong lần đo này. DOCX có thời gian rà soát gần như cũ. Cần phép đo tuần tự lặp lại nếu cần tách ảnh hưởng của số token và độ trễ dịch vụ model.
