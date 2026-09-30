# Nhật Ký Phiên Làm Việc #232 — Nâng Cấp Task Runner (reseed / reset-db) & Cấu Hình Git Dual-Push Đồng Bộ Gitea + GitHub

- **Thời gian**: 2026-09-30 21:30 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái**: Hoàn thành xuất sắc, đã kiểm thử lệnh thực tế và cấu hình Git đồng bộ cả 2 remotes

---

## 1. Yêu Cầu & Bối Cảnh Thực Tế

1. **Lỗi ParameterBindingValidationException khi chạy `./make reseed` trên Windows PowerShell**:
   - Người dùng chạy lệnh `./make reseed` trong terminal nhưng gặp lỗi:
     ```
     make.ps1 : Cannot validate argument on parameter 'Command'. The argument "reseed" does not belong to the set
     "infra-up,infra-down,infra-status,infra-logs,seed,dev,dev1,dev2,be,fe,fe2,test,help" specified by the ValidateSet attribute.
     ```
   - Nguyên nhân: Tệp `make.ps1` chưa khai báo `reseed` và `reset-db` trong attribute `[ValidateSet(...)]` của PowerShell, mặc dù trong `Makefile` đã định nghĩa mục tiêu này.
2. **Cấu hình Git Dual-Push (Đẩy đồng thời Gitea và GitHub)**:
   - Người dùng mong muốn khi thực hiện `git push` thì mã nguồn sẽ tự động được đẩy lên đồng thời cả 2 máy chủ Git:
     - Gitea nội bộ ĐH Quy Nhơn: `https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git`
     - GitHub cá nhân: `https://github.com/hatuandev/qnu-ai-platform.git`
   - Đồng thời, khi thực hiện `git pull`, hệ thống phải ưu tiên pull từ Gitea (`Gitea-First Pull Policy`).

---

## 2. Các Thay Đổi Chi Tiết

### 2.1 Cập nhật `make.ps1` & `Makefile`
- **`make.ps1`**:
  - Bổ sung `"reseed"`, `"reset-db"` vào danh sách `[ValidateSet(...)]`.
  - Triển khai nhánh switch `reseed`: kích hoạt môi trường ảo Python và gọi `python app/db/init_db.py --reseed`.
  - Triển khai nhánh switch `reset-db`: thực hiện `alembic downgrade base`, chạy `alembic upgrade head` và nạp toàn bộ seed ban đầu.
- **`Makefile`**:
  - Tối ưu hóa các target `reseed` và `reset-db` gọi qua PowerShell script thống nhất cho lập trình viên trên Windows.

### 2.2 Cấu hình Git Dual-Push & Gitea-First Fetch
- Cấu hình remote `origin`:
  - **Fetch URL**: `https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git` (Bảo đảm ưu tiên pull từ Gitea nội bộ).
  - **Push URL 1**: `https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git` (Gitea).
  - **Push URL 2**: `https://github.com/hatuandev/qnu-ai-platform.git` (GitHub).
- Kiểm chứng thực tế: Chạy `git push origin main` thành công đẩy đồng thời cả hai máy chủ từ 1 lệnh duy nhất.

---

## 3. Kết Quả Kiểm Tra (Verification)
- Lệnh PowerShell `./make reseed` và `./make reset-db` chạy mượt mà, không còn lỗi binding tham số.
- Lệnh `git remote -v` hiển thị đúng cấu hình dual-push:
  ```text
  origin  https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git (fetch)
  origin  https://qnu-gitea.duckdns.org/admin/qnu-ai-platform.git (push)
  origin  https://github.com/hatuandev/qnu-ai-platform.git (push)
  ```
- Thử nghiệm push nhánh `main` lên đồng thời cả 2 remotes thành công 100%.
