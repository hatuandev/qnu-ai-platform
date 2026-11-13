# Hướng dẫn chạy local — QNU AI Platform V1

Lệnh `dev` chạy **`backendV1/`** ở cổng 8002, ARQ worker V1 và **`frontendV2/`** ở cổng 3002; `v1-dev` chỉ chạy API/worker. FrontendV1 đã được gỡ khỏi checkout.

Xem thêm [hướng dẫn V1 chi tiết](quy_trinh/38_huong_dan_chay_qnu_v1.md) khi thiết lập máy mới, cấu hình ModelOps, xử lý lỗi và migration.

---

## 5. Cách Khởi Động & Thao Tác Với Dự Án

Toàn bộ thao tác hàng ngày được quản lý tập trung qua runner `make.ps1` (PowerShell trên Windows) hoặc `Makefile` / `make.bat`:

### 5.1. Bảng tra cứu lệnh nhanh

| Mục Đích | Lệnh PowerShell | Lệnh Make / CMD | Ghi Chú |
| :--- | :--- | :--- | :--- |
| **Kiểm tra trạng thái & schema** | `.\make.ps1 check` | `make check` | Kiểm tra kết nối Redis, PostgreSQL schema, Qdrant, storage và Vite (chỉ đọc) |
| **Bật hạ tầng Docker** | `.\make.ps1 infra-up` | `make infra-up` | Khởi động Postgres 16, Redis 7, Qdrant, MinIO, Gotenberg |
| **Xem trạng thái hạ tầng** | `.\make.ps1 infra-status` | `make infra-status` | Kiểm tra trạng thái và healthcheck các container hạ tầng |
| **Dừng hạ tầng Docker** | `.\make.ps1 infra-down` | `make infra-down` | Dừng các container hạ tầng, bảo toàn dữ liệu volumes |
| **Chạy toàn bộ môi trường Dev** | `.\make.ps1 dev` | `make dev` | Khởi chạy API V1 (8002), worker V1 và Frontend V2 (3002) |
| **Chạy riêng Backend API** | `.\make.ps1 be` | `make be` | Chạy riêng FastAPI server tại port 8002 |
| **Chạy riêng ARQ Worker** | `.\make.ps1 worker` | `make worker` | Chạy riêng worker xử lý hàng đợi nền `qnu:v1:jobs` |
| **Chạy riêng Frontend V2** | `.\make.ps1 fe2` | `make fe2` | Chạy Vite ở cổng 3002 |
| **Kiểm tra revision DB** | `.\make.ps1 db-check` | `make db-check` | Xem revision Alembic hiện tại của `backendV1` (không migrate) |
| **Nâng cấp Schema DB** | `.\make.ps1 migrate` | `make migrate` | Áp dụng các migration Alembic mới nhất cho `backendV1` |
| **Kiểm thử Backend** | `.\make.ps1 test-be` | `make test-be` | Chạy bộ test cô lập Backend (tự tạo và dọn DB test riêng) |
| **Kiểm tra chuẩn mã (Lint)** | `.\make.ps1 lint` | `make lint` | Kiểm tra Ruff (Python) và Biome (Frontend V2) |
| **Kiểm tra kiểu TypeScript** | `.\make.ps1 typecheck` | `make typecheck` | Kiểm tra kiểu TypeScript phía Frontend V2 |
| **Build sản phẩm Frontend** | `.\make.ps1 build` | `make build` | Build bundle Frontend V2 qua Vite và TypeScript |

### 5.2. Quy trình khởi chạy chuẩn hàng ngày

1. **Khởi động hạ tầng dịch vụ (PostgreSQL, Redis, Qdrant, MinIO, Gotenberg)**:
   ```powershell
   .\make.ps1 infra-up
   ```

2. **Kiểm tra kết nối và tính sẵn sàng của hệ thống**:
   ```powershell
   .\make.ps1 check
   ```

3. **Cập nhật CSDL (nếu có migration mới)**:
   ```powershell
   .\make.ps1 migrate
   ```

4. **Khởi chạy ứng dụng**:
   ```powershell
   .\make.ps1 dev
   ```
   > **Lưu ý:**
   > - Phím tắt `Ctrl + C` sẽ dừng toàn bộ các tiến trình con được khởi tạo trong phiên `dev`.
   > - Nếu cần xem log riêng, chạy `.\make.ps1 be`, `.\make.ps1 worker` và `.\make.ps1 fe2` trong ba terminal.
   > - Địa chỉ truy cập mặc định:
   >   - **Frontend V2**: [http://127.0.0.1:3002](http://127.0.0.1:3002)
   >   - **Backend API Docs**: [http://localhost:8002/docs](http://localhost:8002/docs) (API Prefix: `/platform/v1alpha1`)

---

## 6. Lưu Ý Quan Trọng
- **Không tự ý reset dữ liệu**: Không chạy các script reset/seed legacy làm mất dữ liệu DB, bucket tài liệu hoặc model encryption key đã cấu hình. Giữ nguyên DB, bucket, provider encryption key và nguồn tài liệu hiện có.
- **Biến môi trường**: Mặc định runner đọc cấu hình từ file `.env` ở thư mục gốc repo.
- **Triển khai Server/Production**: Xem tài liệu [quy trình Dokploy](trien_khai/02_quy_trinh_trien_khai_dokploy.md).
