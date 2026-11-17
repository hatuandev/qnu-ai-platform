# Phiên 997 — Đối chiếu nguyên văn phía backend trước khi gọi Qwen

## Phạm vi

Tận dụng bản nháp giữ nguyên nguồn để giảm thời gian rà soát. Các mục đủ điều kiện được xử lý cục bộ trong `review/literal.py`, `review/parts.py`, `review/service.py` và `review/execution.py`. QNU dựng lại các mục từ nguồn đã ghim rồi so thứ tự, nội dung và dẫn chứng với bản nháp. Chỉ các đoạn khớp nguyên văn với duy nhất một khối nguồn không có cờ cần kiểm tra mới được đối chiếu tự động. Các đoạn nối, có cảnh báo hoặc có thay đổi tiếp tục qua luồng rà soát hiện có. Các mảnh khối dài vẫn theo kế hoạch ngân sách đã triển khai trước đó.

Phần cục bộ có phạm vi trong manifest và worker đối chiếu lại trước khi lưu kết quả. Thao tác chỉ tạo báo cáo rà soát. Tài liệu JSON đã lưu, Markdown, hash bản nháp và quy trình phát hành không bị ghi đè. Kết quả khớp chữ với nguồn trích xuất chưa bao gồm đối chiếu ảnh OCR.

## Đo lại tệp 04

Tệp cẩm nang tuyển sinh 2025, bản biên soạn `cmp_fbe67d7cb390`, so sánh cùng bundle và cấu hình `qwen3.8-27b-q4` trong kho thử `col_dd63b9a487cf`.

| Chỉ số | Trước | Sau |
| --- | ---: | ---: |
| Lượt rà soát | `rvw_8c02e65f4a4b` | `rvw_c9cb9dfe9b6a` |
| Thời gian đo qua API và worker | 2.393,41 giây | 9,67 giây |
| Số lượt Qwen | 25 | 1 |
| Token đầu vào | 384.566 | 1.553 |
| Token đầu ra | 250.171 | 111 |
| Tổng token | 634.737 | 1.664 |
| Mục nguồn | 1.402 | 1.402 |
| Mục bản nháp | 1.418 | 1.418 |
| Cần đối chiếu | 0 | 0 |

1.402 đoạn và 15 tiêu đề phân đoạn được kiểm tra cục bộ. Qwen chỉ xác minh tên tài liệu với ngữ cảnh nguồn. Lượt đo trung gian tạo một cảnh báo vì diễn giải phần chỉ có tên thành toàn bộ bản nháp. Sau khi ghim hướng dẫn riêng cho lượt kiểm tên, lượt đo cuối hoàn tất 3/3 phần. So sánh báo cáo đối chiếu đủ ID mục, nội dung và trường dẫn chứng với lượt baseline. Tệp JSON nhận qua API trước và sau khớp từng byte. Phép đo giới hạn ở tệp 04, chưa chạy phát hành, lập chỉ mục hoặc benchmark RAG.

## Kiểm chứng

- `uv run ruff check` trên tệp thay đổi, exit 0. 57 kiểm thử đơn vị đạt, gồm bỏ đoạn, sửa năm, sửa số, đổi dẫn chứng, đảo thứ tự và lặp đoạn. Kiểm tra nhóm có cảnh báo hoặc chung dẫn chứng không được tự xác nhận.
- Chạy 32 ca tích hợp trên DB cô lập. Sau khi ghim hướng dẫn kiểm tên, chạy lại ca đọc báo cáo đã lưu qua worker và kiểm nguyên vẹn JSON, đạt. Các lệnh chạy ở `backendV1` bằng `uv run pytest` và `uv run --env-file ../.env python scripts/run_isolated_tests.py`.
- Bộ kiểm thử backend chạy với `tests --maxfail=1`, exit 1 sau 8 ca đạt và 1 ca lỗi. `test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful` lặp lại đúng ID lỗi của lượt full backend phiên 990. Fixture trả lời phát sinh `KeyError: evidence`. Phần còn lại dừng theo `--maxfail=1`. DB kiểm thử đã được dọn.
- Lượt đo thật dùng `uv run --env-file ../.env python $qnuCompareScript` tại `backendV1`, với runner lưu tạm. ModelOps dùng cấu hình Qwen đang có.
