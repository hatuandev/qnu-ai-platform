# NHẬT KÝ LÀM VIỆC — PHIÊN #226
**Ngày**: 2026-09-26 | **Thời gian**: 00:20 (UTC+7)
**Tiêu đề**: Bịt Migrate Câm — Fail-Loud Khi Schema Thiếu Bảng Core

---

## 1. Phân Tích Log Vòng Lặp
- Alembic chỉ in context init, **0 dòng `Running upgrade`**, exit 0; seed chết ở `assistants`/`workflow_definitions` missing; container restart vô hạn.
- 5 cảnh báo workflow chỉ là 1 transaction poisoned cascade — không phải 5 lỗi riêng.
- Nguyên nhân no-op (stale stamp / versions lệch / env nuốt lỗi) chưa chốt được từ xa.

## 2. Thay Đổi
- `backend/app/cli.py::run_db_migrate`: sau `upgrade head`, gọi `check_db_schema()`; thiếu bảng core → return 1 kèm thông điệp rõ (soi `alembic_version` + `db check`) thay vì để seed chết khó hiểu.
- `backend/tests/test_cli_db_migrate.py`: 3 tests (pass → 0; thiếu bảng → 1; upgrade raise → 1).

## 3. Kết Quả
- Ruff 0 lỗi; 3/3 tests mới pass.
- Chưa sửa được data-plane trên server — cần ground truth:
  `docker exec qnu_backend ls /app/alembic/versions` và `docker exec qnu_backend python -m app.cli db check`.
