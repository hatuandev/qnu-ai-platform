# Phiên 994 — Chạy thử Qwen trên một tệp tuyển sinh nhỏ

## Phạm vi

Chọn `QNU_TuyenSinh_2026_VanBanThuyetMinh.docx` (43.874 byte). Dùng lại kết quả bóc tách đã ghim trong kho thử `col_7a022d5331bf`. Dựng bản biên soạn giữ nguyên nguồn `cmp_026babe0a570` trong khoảng 0,53 giây và chạy riêng bước rà soát `rvw_b657bed5badb` qua API và worker Backend V1 từ mã hiện tại. ModelOps dùng model đã cấu hình `qwen3.8-27b-q4` với thinking tắt cho rà soát.

## Kết quả

| Chỉ số | Quan sát |
| --- | --- |
| Trạng thái | `completed`, cả 2 phần hoàn tất |
| Phần xử lý cục bộ | 1 tiêu đề phân đoạn được xác minh từ nguồn đã ghim |
| Lượt gọi Qwen | 1, `finish_reason=stop`, không cần gọi lại |
| Token provider ghi nhận | 22.415 vào, 11.655 ra, tổng 34.070 |
| Thời gian rà soát | 226,81 giây theo thời điểm bắt đầu và hoàn tất, 227,08 giây đo qua API và worker |
| Độ phủ báo cáo | 57/57 mục nguồn, 59/59 mục bản nháp |
| Kết luận báo cáo | `no_issues_detected`, 0 mục cần đối chiếu |

Lệnh chạy trong `backendV1` là `uv run --env-file ../.env python $qnuReviewScript`, với `$qnuReviewScript` trỏ tới runner trong thư mục tạm của phiên. Tiến trình kết thúc với exit 0. Kiểm lại trạng thái qua API và đối chiếu model cùng token từ phản hồi đã lưu. Phiên này chỉ đo một lượt trên bản nháp giữ nguyên nguồn. Chưa có phép so sánh trước/sau trên cùng bản nháp và chưa chấm độc lập chất lượng ngữ nghĩa. Các tệp còn lại, xuất bản, lập chỉ mục và RAG nằm ngoài phạm vi chạy thử.
