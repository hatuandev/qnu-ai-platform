# Phiên 392 — Fix restart dev khi tiến trình con đang thoát

## Mục tiêu và bằng chứng

User chạy dev và gặp `PID 2136 changed identity; refusing to stop it`. CIM khi kiểm tra cho thấy PID10008/2136 đều đã thoát. Launcher dừng root trước rồi kiểm danh tính descendants; quá trình tự đóng làm command line/danh tính không còn khớp và guard strict đã hủy restart giữa chừng. Không có snapshot CIM lúc lỗi nên chưa khẳng định PID đã tái sử dụng hay chỉ đang đóng.

## Thay đổi

- `scripts/dev-processes.ps1`: thêm IgnoreChangedIdentity riêng cho descendants. PID đổi epoch hoặc command line không bị kill; ghi warning rồi bỏ qua. Root vẫn fail-closed. Nếu Stop-Process gặp race exit thì truy vấn lại và chỉ bỏ qua khi tiến trình không còn hoặc PID thuộc epoch khác; lỗi quyền trên cùng tiến trình vẫn ném lại.
- `scripts/start-dev.ps1`: dùng cờ skip cho descendants, vẫn giữ preflight foreign ports, root checks và wait ownership/ports trước khi mở dịch vụ.
- `scripts/test-dev-processes.ps1`: thêm hai ca PID recycle/command line rỗng trong shutdown; tái hiện test fail trước sửa, đạt sau sửa. Tổng18assertions, không kill process thật trong tests.

## Kiểm chứng

- PS5 AST của3file đạt, git diff --check đạt,18assertions đạt.
- Chạy make.ps1 dev thật ngoài sandbox lúc các dịch vụ cũ đã thoát: exit0, worker20404 + BE/FE terminal mở.
- Chạy dev lần2 khi cả ba đang hoạt động: exit0, worker11896, BE wrapper16748/reloader20940, FE wrapper9680/Vite6924. Các PID20404/7916/9364/17188/1444 đã thoát.
- Port3000 listener6924, port8001 listener5224 (child của uvicorn), worker11896 startup10functions/RedisOK/health ghi j_ongoing0,queued0. Không còn lỗi PID changed identity chặn restart.
- DB ensure-ready xác nhận47tables, Alembic20261012_fact_temporal_context,11providers/5collections; không reset/migrate mới/publish/retry OCR nguồn user. Worker cron reconciliation chạy bình thường dispatched0.
- Không chạy Pytest/Ruff/Vite vì chỉ sửa launcher PowerShell, không sửa ứng dụng Python/React.

## Bàn giao

Cả3dịch vụ hiện đang chạy với lầnrestart22:19 mới; không cần user restart thêm chỉ để nhận code. User có thể thử lại mục OCR lỗi; phiên này chưa tự retry. Vẫn cảnh báo restart có thể ngắt requests/jobs đang chạy và không kill PID tái sử dụng/ứng dụng ngoàirepo. Docker/DB và dữ liệu giữ nguyên.
