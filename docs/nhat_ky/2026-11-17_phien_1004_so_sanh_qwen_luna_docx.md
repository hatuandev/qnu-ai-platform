# Phiên 1004 — So sánh Qwen và Luna trên một bản nháp Word

## Phạm vi

- Bắt đầu từ kho thử mới `col_3850b799ae8e`, xác nhận danh sách nguồn trống. Tải một tệp giả lập `tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx`, mã nguồn `src_07d9e2ce2ee8`. Dữ liệu các kho trước giữ nguyên.
- Bóc tách mất 10,06 giây, xác minh 850 mã dẫn chứng giữa JSON và Markdown. Biên soạn `cmp_7d331416970f` mất 8,59 giây. Bản nháp có 10 bảng, 29 annotation metadata và một lượt AI bổ sung Qwen dùng 2.979 token. Từ upload đến khi sẵn sàng rà soát mất 19,70 giây.
- Hai lượt rà soát chạy nối tiếp qua API và tác vụ Backend V1, dùng cấu hình ModelOps đang có. Đã đối chiếu ba hash đầu vào, bản nháp và gói dẫn chứng giữa hai lượt. Cả ba đều khớp và bản nháp sau thử giữ nguyên hash.

## Kết quả

| Model | Lượt rà soát | Thời gian | Lượt gọi | Token vào / ra / tổng | Kết quả |
| --- | --- | ---: | ---: | ---: | --- |
| `qwen3.8-27b-q4` | `rvw_da7963e28fee` | 53,64 giây | 1 | 7.198 / 2.554 / 9.752 | Hoàn tất 18/18 phần. Kiểm đủ 840 mục nguồn, 862 mục nháp, 0 phát hiện cần đối chiếu |
| `cx/gpt-6-luna` | `rvw_79d689aba709` | 91,23 giây đến lúc dừng | 5 | 24.926 / 5.546 / 30.472 | `compilation_review_recovery_exhausted`. 1/22 phần cuối hoàn tất, 1 lỗi và 20 phần chờ. Chưa có báo cáo tổng |

- Luna trả HTTP 200 và `finish_reason=stop` cả năm lượt. Bốn phản hồi thiếu hai trường đánh giá bắt buộc. Phản hồi ở phần 21 có đủ mã mục nhưng trả hai nhóm đánh giá dưới dạng đối tượng theo mã, trong khi lượt này yêu cầu danh sách. Cả hai model đều thiếu số đo token suy luận riêng trong phản hồi.
- Qwen dùng cấu hình tắt reasoning đã có cho rà soát. Luna dùng `server_default` qua 9router. Kết quả phản ánh hai cấu hình đang sử dụng trên một tài liệu. Thời gian Luna là thời gian đến lúc lỗi. Phép thử chưa đo chia việc giữa hai model, độ chính xác bằng chấm tay, phát hành hay lập chỉ mục.

## Kiểm chứng

- Chạy `uv run --env-file ../.env python $runner` tại `backendV1`, runner `qnu_1004_benchmark.py` nằm trong thư mục tạm. Kết nối ModelOps và dữ liệu thật ở kho thử, gọi handler worker từ tiến trình thử. Runner exit 1 do Luna thất bại.
- Runner đọc số token từ phản hồi đã lưu. Các kiểm tra chỉ đọc `qnu_1004_progress.py`, `qnu_1004_diagnose.py` và `qnu_1004_response_schema.py` xác nhận trạng thái, hash và lý do từ chối, exit 0. Bản nháp và hai lượt vẫn có trong kho thử để đối chiếu.
