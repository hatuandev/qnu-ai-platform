# Phiên 1009 — Model và số lượt xử lý văn bản

## Thay đổi

- **Cài đặt → Xử lý văn bản** cho quản trị ModelOps lưu model toàn hệ thống và
  số lượt tối đa riêng cho mỗi model. Model chưa cấu hình dùng 1 lượt. API
  kiểm quyền, capability, trạng thái và trần vận hành trước khi lưu.
- Model được chọn áp dụng cho biên soạn, luồng chuẩn bị có AI và rà soát bản
  biên soạn. Yêu cầu gọi trực tiếp có model chỉ định ưu tiên lựa chọn đó.
  Lượt đã lập kế hoạch giữ model và mức đồng thời đã ghim. Các phần đang chạy
  dùng cùng cổng bảo vệ của ModelOps với các yêu cầu chat.
- Hai trần vận hành mặc định là 5 để có thể cấu hình Qwen 2 và Luna 5.
  Cấu hình hạ tầng có thể dùng trần thấp hơn. Migration 0032 thêm hai cột
  nullable trong `model_defaults`. Bản schema 0031 trên DB trống chạy tiếp
  revision 0032 trong cùng giao dịch.

## Kiểm chứng

- Ruff, Biome và build Frontend V2 (gồm TypeScript) đạt. Build có cảnh báo
  bundle chính lớn hơn 500 kB.
- Bộ test trọng tâm trên DB cô lập đạt 22 ca. Hai ca biên soạn/rà soát được
  chạy lại sau khi mở rộng kiểm tra mức 2 của biên soạn và mức 5 của rà soát.
  Cả hai đạt, xác nhận lượt đã ghim giữ mức cũ khi chuyển model trên API.
- `make.ps1 v1-db-check` trên DB đang cấu hình báo `0031_spelling_defaults`.
  Migration 0032 chỉ được áp dụng trên database thử. Chưa chạy trình duyệt,
  Qwen/Luna thật hoặc đo thời gian suy luận. Full suite backend đã khởi chạy
  cô lập, chưa có kết quả tại thời điểm ghi.

[Quy trình biên soạn và rà soát](../quy_trinh/V1_COMPILER_TAI_LIEU_LON.md#chạy-song-song-có-giới-hạn).
