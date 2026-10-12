# Phiên #368 — Dừng dev và worker để người dùng chạy lại

Ngày: 2026-10-12. Theo yêu cầu người dùng, chỉ dừng Backend8001, Frontend3000 và ARQ worker của repo; giữ Docker/DB/server AI/IDE.

Kiểm tra read-only ngoài sandbox: cổng3000 PID8924, cổng8001 PID3304; worker8624. Có nhiều shell/uvicorn dev cũ chạy ẩn. Truy vết parent chain của Vite về shell frontend23868, không chọn shell terminal IDE28684 làm mục tiêu.

Dừng đúng root shells31456/9916/13780/18052/25148/21312/23868 và worker8624, kèm descendants từ snapshot CIM; kiểm tra command line của roots và CreationDate tránh PID reuse trước Stop-Process. Một số children tự thoát khi parent dừng. Không kill toàn bộ python/node hoặc các cổng khác.

Sau2giây xác nhận không còn LISTEN3000/8001 và không còn ARQ worker QNU theo command line. Không xóa log/state/file hoặc reset dữ liệu, không chạy lại dịch vụ. PID-state worker cũ được giữ; launcher kiểm tra PID/startTicks khi lần chạy tới và tạo worker mới nếu process cũ đã dừng.

Chưa kiểm tra trạng thái từng job đang chạy khi force-stop; không tuyên bố các tác vụ đã hoàn tất. Chỉ cập nhật nhật ký/index/context/snapshot/work log; không đổi source và không tests ứng dụng.
