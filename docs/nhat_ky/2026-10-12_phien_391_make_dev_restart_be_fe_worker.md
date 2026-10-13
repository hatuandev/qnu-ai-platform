# Phiên 391 — make dev restart BE, FE và worker

## Mục tiêu

Theo yêu cầu người dùng, mỗi lần chạy dev sẽ dừng đúng dịch vụ của checkout rồi mở lại backend8001, frontend3000 và ARQ worker một lần. Không restart Docker/DB hoặc kill tiến trình ngoài repo. Chỉ áp dụng luồng restart trên Windows.

## Thay đổi

- `scripts/dev-processes.ps1`: nhận diện BE/FE/worker theo đường dẫn repo có ranh giới, tên chương trình và entrypoint cụ thể. Lập cây con với PID/parent và thời gian tạo; tránh PID parent tái sử dụng. Trước khi dừng xác minh lại PID + CreationDate + CommandLine. Cổng thuộc tiến trình chưa xác minh làm preflight từ chối toàn bộ restart.
- `scripts/start-dev.ps1`: mutex theo checkout chống hai lệnh dev chạy đồng thời, preflight ownership/port, kiểm tra DB readiness trước khi dừng, stop roots rồi cây con, chờ tối đa10s cho cả ports và tiến trình cũ hết. Sau đó gọi start-worker đúng một lần, mở hai terminal BE/FE có đường dẫn script tuyệt đối. SupportsShouldProcess/WhatIf kiểm tra mà không chạy readiness hoặc stop/start.
- `scripts/start-dev-service.ps1`: launcher terminal rõ quyền sở hữu; BE uvicorn8001, FE Vite strictPort3000 để không âm thầm chạy cổng3001. Giữ hai terminal visible theo trải nghiệm người dùng; worker nền/log như cũ.
- `make.ps1`, `Makefile`, `make.bat`, Bash `make` nhánh Windows: dev/dev1/dev2 gọi chung start-dev.ps1, cập nhật help. Nhánh make.ps1/make.bat báo lỗi exit khi restart thất bại. Lệnh worker riêng vẫn là start/reuse như trước.
- `scripts/test-dev-processes.ps1`: 16 assertion độc lập, không dừng tiến trình thật; kiểm ownership, repo có dấu cách, repo tên gần giống, không dừng IDE, cây con, PID recycle, foreign port fail-closed và bốn entrypoints.

## Kiểm tra

- PowerShell5 parser/AST: make.ps1 và bốn script mới đạt.
- 16 assertion regression đạt.
- git diff --check phạm vi launcher đạt (LF/CRLF advisory).
- WhatIf thật ngoài sandbox: nhận đúng ARQ PID10008 của checkout, ports3000/8001 lúc kiểm tra không có listener; không stop/start/DB readiness. Chưa kiểm chứng restart live hoặc chạy dev hai lần trực tiếp.
- Không chạy Ruff/Pytest/Vite vì không đổi code backend/frontend ứng dụng, chỉ launcher PowerShell/batch/bash. Chưa có Bash binary verification trong shell hiện tại; nhánh Windows Bash chỉ dispatch chung PowerShell.

## Bàn giao và lưu ý

Người dùng chạy `make dev` hoặc `.\make.ps1 dev` để restart cả ba; worker cũ vẫn chưa bị dừng trong phiên kiểm tra này. Các job/request đang chạy có thể bị ngắt khi người dùng restart; cảnh báo rõ trong launcher, dùng recovery đã có chứ không tự approve/publish/reset. Nên restart khi batch đã kết thúc. Không xóa file/log/state hoặc thay credentials. Không tự động kiểm định server đã ready: launcher thông báo đã mở terminal và yêu cầu xem startup output; lỗi worker/BE/FE cần xem log/terminal. Terminal legacy chưa có marker sở hữu có thể còn cửa sổ rỗng; không kill cha không xác minh để tránh ảnh hưởng IDE/user shell.
