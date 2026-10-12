# Phiên #367 — Hiện lại terminal make dev

Ngày: 2026-10-12. Người dùng đồng ý khôi phục cửa sổ BE/FE.

## Thay đổi

Chỉ hai dòng runtime trong make.ps1:102/106: WindowStyle Hidden → Normal cho Start-Process PowerShell của Backend8001 và Frontend3000. Nhánh chung dev/dev1/dev2 đều nhận thay đổi; giữ arguments/NoExit, readiness và worker nền/PID guard nguyên vẹn. Skill clean-code giữ thay đổi phẫu thuật, không sửa các runner khác, OCR/auth/DB/qnu-sso hoặc tiến trình đang chạy.

Đồng bộ hướng dẫn local, Quy trình01, nhật ký/index/context/snapshot/WORK_LOG. Không thay đổi semantics OCR/worker reload hoặc reset DB.

## Kiểm chứng

PowerShell Parser.ParseFile không lỗi; AST có đúng hai Start-Process WindowStyle Normal, make.ps1 không còn Hidden, start-worker.ps1 vẫn Hidden. Whitespace diff và UTF-8 kiểm tra trong phạm vi. Không chạy Pytest/Vite/Ruff vì chỉ sửa launcher PowerShell và tài liệu; không thực thi make dev để tránh mở trùng dịch vụ/đụng ensure-ready. Chưa kiểm chứng cửa sổ thực tế từ Antigravity.

## Bàn giao

Áp dụng cho lần chạy dev tiếp theo; không tự hiện lại cửa sổ cũ đã chạy ẩn. Chưa restart/kill dịch vụ. Nếu process cũ đang chiếm port, cần dừng đúng process cũ trước khi mở phiên mới; worker đang chạy vẫn được dùng lại chứ không tự nhận code mới.
