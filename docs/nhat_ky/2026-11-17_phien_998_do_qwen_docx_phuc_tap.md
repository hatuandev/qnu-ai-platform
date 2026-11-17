# Phiên 998 — Đo thời gian xử lý DOCX phức tạp với Qwen

## Phạm vi

Tải mới `tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx` (102.423 byte) vào kho thử `col_30905ef72b43`, kiểm checksum nguồn, chạy bóc tách, chuẩn bị `auto` và rà soát. Dùng API và worker Backend V1 với cấu hình `qwen3.8-27b-q4` hiện có. Bản biên soạn `cmp_2d2e9d39776d` và lượt rà soát `rvw_c18b34c0c2c1`.

## Số liệu quan sát

| Chặng | Kết quả | Thời gian |
| --- | --- | ---: |
| Tải tệp và bóc tách | Đã tải, hash khớp, bóc tách hoàn tất | 6,72 giây cho bóc tách |
| Chuẩn bị nội dung tự động | Hoàn tất, 210 đoạn, 10 bảng. AI bổ sung dùng 2.897 token | 7,41 giây |
| Rà soát | Dừng ở `compilation_review_recovery_exhausted`, 17/26 phần hoàn tất | 949,62 giây |
| Toàn lượt chạy | Từ khởi tạo runner đến khi lưu trạng thái cuối | 966,33 giây |

Chuẩn bị đã dùng AI bổ sung nên rà soát đi theo luồng v3 hiện có, với 22 phần ban đầu. Bốn nhánh chia tiếp tạo 26 phần cuối, trong đó 17 phần hoàn tất, 1 phần lỗi và 8 phần chưa chạy. Qwen đã trả 20 phản hồi với tổng 333.984 token đầu vào và 58.974 token đầu ra. Tất cả kết thúc `stop`.

Kiểm lại phản hồi đã lưu. Phần 4, 12 và 24 có dẫn chứng vượt phạm vi phần. Phần 28 thiếu một mục bản nháp. Phần 13 thiếu ba mục bản nháp sau khi lượt đã dùng hết bốn lần phục hồi. Backend lưu bản nháp và kết quả từng phần đã đạt. Lượt này chưa có báo cáo tổng.

## Lệnh và giới hạn

Chạy tại `backendV1` với `uv run --env-file ../.env python $nextRunner`. Runner tạm kết thúc exit 1 do lỗi rà soát nói trên. Kiểm lại trạng thái và tổng token từ phản hồi provider đã lưu. Tác vụ soát chính tả ghi nhận phạm vi theo cấu hình sẵn có. Phép đo này dùng một lượt thử với chế độ tự động, dừng ở bản nháp, chưa phát hành hoặc nạp vector.
