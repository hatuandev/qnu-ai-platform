# THƯ MỤC NHẬT KÝ LÀM VIỆC (ENGINEERING WORK LOGS DIRECTORY)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn

> **Quy định bắt buộc**: Mỗi khi bắt đầu và kết thúc một phiên làm việc ("Vibe Coding") — bao gồm phát triển tính năng, tái cấu trúc (refactor), sửa lỗi, cấu hình hạ tầng hay kiểm thử — **Kỹ sư / AI Agent BẮT BUỘC phải tạo hoặc cập nhật nhật ký làm việc vào thư mục này**.

---

## 🗂️ Danh Mục Nhật Ký Làm Việc Theo Phiên

| Ngày | Tệp Nhật Ký Chi Tiết | Trọng Tâm Phiên Làm Việc | Kết Quả Đạt Được |
| :---: | :--- | :--- | :--- |
| **2026-09-15** | [`2026-09-15_hoan_thanh_8_giai_doan_backend.md`](./2026-09-15_hoan_thanh_8_giai_doan_backend.md) | Xây dựng toàn diện 8 Giai đoạn Backend theo chuẩn Enterprise Modular Monolith | 8/8 Giai đoạn hoàn thành, 68/68 Pytest Passed |
| **2026-09-15** | [`2026-09-15_kiem_thu_doc_lap_37_chuc_nang.md`](./2026-09-15_kiem_thu_doc_lap_37_chuc_nang.md) | Chạy kiểm thử chức năng độc lập 8 phân hệ qua `scripts/verify_all_modules.py` | 37/37 Chức năng Đạt chuẩn (100% Passed) |
| **2026-09-15** | [`2026-09-15_chuan_hoa_docker_minio.md`](./2026-09-15_chuan_hoa_docker_minio.md) | Chuẩn hóa Docker Compose duy nhất, Dockerfile Backend & MinIO Object Storage | Docker compose valid 100%, MinIO-First |

---

## 📝 Mẫu Tiêu Chuẩn Ghi Nhật Ký Cho Phiên Làm Việc Mới (Template)

Mỗi khi tạo tệp nhật ký mới (đặt tên theo định dạng `YYYY-MM-DD_ten_tinh_nang.md`), hãy sử dụng mẫu cấu trúc sau:

```markdown
# NHẬT KÝ LÀM VIỆC: [TIÊU ĐỀ PHIÊN LÀM VIỆC]
- **Thời gian**: [YYYY-MM-DD HH:MM]
- **Kỹ sư / Agent**: AI Senior Backend Architect & Enterprise Specialist
- **Mục tiêu phiên (Goals)**:
  - [Mục tiêu 1]
  - [Mục tiêu 2]

## 1. Các Thay Đổi Mã Nguồn & Kiến Trúc (Key Changes)
- `duong/dan/tep_1`: [Mô tả chi tiết lý do và nội dung thay đổi]
- `duong/dan/tep_2`: [Mô tả chi tiết lý do và nội dung thay đổi]

## 2. Tuân Thủ Chuẩn MinIO Object Storage
- [Xác nhận luồng lưu trữ file upload gốc và artifact đầu ra qua MinIO S3]

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)
- Lệnh kiểm tra Linter: `uv run ruff check .` -> [Kết quả]
- Lệnh kiểm tra Test Suite: `uv run pytest -v` -> [Kết quả]
- Kiểm thử chức năng: [Mô tả kịch bản test thực tế]

## 4. Trạng Thái & Công Việc Tiếp Theo (Next Steps)
- Trạng thái phiên: [HOÀN THÀNH / ĐANG TIẾN HÀNH]
- Đề xuất việc cần làm tiếp theo: [Nội dung]
```
