# Nhật Ký Phiên 279: Chuẩn Hóa Thống Nhất Frontend2 Thành Frontend Duy Nhất & Đồng Bộ Hệ Thống

- **Thời gian**: 2026-10-06 16:10 (UTC+7)
- **Phiên số**: #279
- **Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Thực hiện rà soát và chuyển đổi toàn diện cấu trúc thư mục từ `frontend2` thành `frontend`, cập nhật tất cả scripts (`make`, `make.bat`, `make.ps1`, `run.ps1`, `Makefile`, `docker-compose.yml`), chuẩn hóa định danh `package.json` và kiểm thử biên dịch bundle Vite + TypeScript đảm bảo 0 lỗi.

---

## 1. Bối Cảnh & Lý Do Thay Đổi

- Sau khi phiên #278 di chuyển mã nguồn frontend cũ sang `legacy/frontend_v1_backup/`, thư mục gốc vẫn tồn tại song song thư mục `frontend/` (chứa các artifact build cũ và node_modules rác) và `frontend2/` (ứng dụng chính thức đang hoạt động tại Port 3000).
- Người dùng yêu cầu rà soát và chuẩn hóa lại để đưa `frontend2` trở lại thành thư mục `frontend` chính thức, duy nhất của toàn bộ dự án.

---

## 2. Các Bước Thực Hiện Cụ Thể

### A. Dọn dẹp thư mục rác cũ & Di chuyển mã nguồn
- Xóa bỏ thư mục `frontend` cũ chứa cache untracked (`dist/`, `node_modules/`, `playwright-report/`, `test-results/`).
- Di chuyển toàn bộ thư mục `frontend2` sang `frontend` bảo toàn 100% `node_modules` và cấu trúc dự án.
- Git nhận diện 100% renames sạch sẽ (`renamed: frontend2/... -> frontend/...`).

### B. Cập nhật cấu hình & Định danh gói
1. **`frontend/package.json`**:
   - Đổi `"name": "qnu-ai-platform-frontend2"` $\rightarrow$ `"name": "qnu-ai-platform-frontend"`.
2. **`frontend/bun.lock`**:
   - Đồng bộ tên workspace thành `"name": "qnu-ai-platform-frontend"`.
3. **`docker-compose.yml`**:
   - Cập nhật build context của service `frontend`:
     ```yaml
     frontend:
       build:
         context: ./frontend
         dockerfile: Dockerfile
     ```
4. **`scratch/audit_system_deep.py`**:
   - Cập nhật `frontend_dir = Path("frontend/src")`.

### C. Cập nhật tất cả các công cụ Task Runner & Scripts
1. **`Makefile`**:
   - `dev`: Khởi chạy song song Backend (Port 8001) và Frontend Studio (Port 3000) với `cd frontend && npm run dev`.
   - `fe`: Khởi chạy riêng Frontend Studio (Port 3000) với `cd frontend && npm run dev`.
   - Giữ các alias `dev1`, `dev2` $\rightarrow$ `dev` và `fe2` $\rightarrow$ `fe`.
2. **`run.ps1`**:
   - Các lệnh `dev`, `dev1`, `dev2`, `fe`, `fe2` chuyển sang `cd frontend; npm run dev`.
3. **`make.ps1`**:
   - Khởi chạy Frontend Studio tại Port 3000: `cd frontend; npm run dev`.
4. **`make.bat`**:
   - Tinh gọn các nhãn `:do_dev`, `:do_dev1`, `:do_dev2`, `:do_fe`, `:do_fe2` trỏ đồng nhất về `cd frontend && npm run dev` tại Port 3000.
5. **`make` (Bash script)**:
   - Gộp các nhánh `dev|dev1|dev2)` và `fe|fe2)` trỏ về `frontend` tại Port 3000.

---

## 3. Kết Quả Kiểm Thử

- **Vite Build (`vite build`)**: Đóng gói thành công trong **2.04 giây**, tạo toàn bộ production chunks sạch sẽ (`dist/`).
- **TypeScript Typecheck (`tsc --noEmit`)**: Đạt **0 lỗi** toàn bộ codebase.
- **Git Working Tree**: 100% tệp từ `frontend2` được Git nhận diện là renames sạch sang `frontend`, không phát sinh conflict.

---

## 4. Trạng Thái Hệ Thống Sau Thay Đổi

- Nền tảng Frontend duy nhất: `frontend/` (React 19 + Vite 6 + TanStack Router + Tailwind v4 + Radix UI).
- Cổng dịch vụ chuẩn hóa:
  - Frontend Studio: `http://localhost:3000`
  - Backend API: `http://localhost:8001`
