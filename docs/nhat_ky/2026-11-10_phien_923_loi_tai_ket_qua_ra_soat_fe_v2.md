# Phiên 923 — Lỗi tải kết quả rà soát FE V2

- Kiểm tra chỉ đọc tài liệu trên app local. `GET .../text-review?version=0` trả 200 và 559 đoạn, trong khi `GET .../text-review/checks?version=0` trả 405. OpenAPI ở cổng 8002 chỉ có `POST /checks`, mã trong checkout có cả GET và POST.
- Trang rà soát hiển thị một trạng thái tải hoặc lỗi tập trung. Khi API trả 405, báo máy chủ đang chạy chưa hỗ trợ lấy danh sách. Nút thử lại chỉ đọc lại dữ liệu lỗi. Giữ tệp gốc cho đối chiếu.
- Trong `frontendV2`, `npm run lint` kiểm 174 tệp, `npm run build` và `node --test tests/studio-browser.mjs` 15/15 đạt, exit 0. Test trình duyệt tái hiện 405, kiểm trạng thái lỗi và tải thành công sau khi API mô phỏng sẵn sàng. `git diff --check` đạt.
- Cần khởi động lại API và worker bằng checkout hiện tại để mở tính năng trên app local. Không có thay đổi backend trong phiên này, chưa khởi động lại, chưa gửi lượt soát thật.

[Snapshot phiên 923](../memory/snapshots/2026-11-10_session_923.md)
