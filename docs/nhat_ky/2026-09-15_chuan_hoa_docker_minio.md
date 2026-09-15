# NHẬT KÝ LÀM VIỆC: CHUẨN HÓA DOCKER COMPOSE DUY NHẤT & MINIO OBJECT STORAGE
- **Thời gian**: 2026-09-15 14:50
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên**:
  - Chuẩn hóa MinIO Object Storage làm tầng lưu trữ bền vững số 1 cho toàn bộ tài liệu tải lên và tệp thành phẩm.
  - Hợp nhất toàn bộ cấu hình Production vào duy nhất một tệp `docker-compose.yml`, loại bỏ file `docker-compose.prod.yml` thừa.
  - Xây dựng hệ thống thư mục Quy trình (`docs/quy_trinh/`) và thư mục Nhật ký làm việc (`docs/nhat_ky/`).
  - Bổ sung quy định bắt buộc vào `AGENTS.md` yêu cầu Agent ghi nhật ký mỗi lần Vibe Coding.

---

## 1. Các Thay Đổi Mã Nguồn & Kiến Trúc
1. **`backend/Dockerfile`**:
   - Đóng gói chuẩn Production trên nền `python:3.12-slim`.
   - Trích xuất binary `uv` trực tiếp từ image Astral (`ghcr.io/astral-sh/uv:0.4.20`).
   - Cài đặt `fonts-liberation` bảo đảm văn bản Word/PDF xuất ra chuẩn Times New Roman theo Nghị định 30/2020/NĐ-CP.
   - Cấu hình user bảo mật không đặc quyền `qnu:qnu` (UID 10001).
   - Tích hợp healthcheck probe `/health/live`.
2. **`docker-compose.yml`**:
   - Tích hợp đầy đủ 7 container: `backend`, `worker`, `postgres`, `qdrant`, `redis`, `minio`, `gotenberg`.
   - Đổi mặc định `STORAGE_DRIVER=s3`, kết nối MinIO tại `http://minio:9000`.
   - Bổ sung `depends_on: minio: condition: service_healthy` cho cả backend và worker.
   - Sửa lỗi healthcheck Qdrant từ `bash` sang `curl -f http://localhost:6333/readyz || exit 1`.
   - Kết nối toàn bộ qua mạng nội bộ bridge cô lập `qnu_network`.
3. **Loại bỏ `docker-compose.prod.yml`**: Tránh phân mảnh cấu hình, quy tụ về 1 tệp duy nhất.
4. **`.env.example` & `.env.prod.example`**: Đặt mặc định `STORAGE_DRIVER=s3`.
5. **`docs/quy_trinh/`**: Tạo 7 tệp quy trình vận hành và sơ đồ Mermaid chi tiết.
6. **`docs/nhat_ky/`**: Tạo thư mục nhật ký và mẫu ghi chép cho các phiên vibe coding tiếp theo.
7. **`AGENTS.md`**: Thêm Mục 4 ràng buộc ghi nhật ký bắt buộc.

---

## 2. Kết Quả Xác Minh
- `docker compose config`: Hợp lệ 100%, không phát sinh cảnh báo.
- `uv run ruff check .`: `All checks passed!`
- `uv run pytest -v`: `68 passed in 19.20s` (100%).
