# NHẬT KÝ LÀM VIỆC — PHIÊN #130
# Ngày: 2026-09-19 | Triển Khai Giai Đoạn B: Chuẩn Hóa Database, Migration & Seed Management

## 1. Mục Tiêu Phiên Làm Việc
Triển khai **Giai đoạn B: Chuẩn hóa Database và Migration** theo hướng dẫn tại [08_huong_dan_cai_thien_code_tang_diem_danh_gia.md](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md):
- Biến Alembic thành **nguồn sự thật duy nhất** (Single Source of Truth) cho database schema.
- Tháo gỡ nút thắt khiến các migration trước đây bị kẹt không lên được HEAD.
- Triệt tiêu 100% schema drift (`alembic check` sạch 0 diff).
- Loại bỏ hoàn toàn `Base.metadata.create_all()` và các lệnh auto-seed ra khỏi FastAPI lifespan startup.
- Xây dựng CLI quản trị database và seed độc lập, đảm bảo tính idempotent 100%.

---

## 2. Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Tháo Gỡ Nút Thắt Giới Hạn `VARCHAR(32)` Của `alembic_version`
- **Vấn đề**: Bảng `alembic_version` mặc định trong PostgreSQL chỉ có cột `version_num VARCHAR(32)`. Các migration mới như `20260919_facts_foreign_key_and_schema_sync` (42 ký tự) văng lỗi `StringDataRightTruncationError`, làm kẹt database live ở revision cũ (`20260917_document_types`).
- **Xử lý**:
  - Chạy ALTER TABLE mở rộng `alembic_version.version_num` lên `character varying(64)`.
  - Cập nhật [`backend/alembic/env.py`](../../backend/alembic/env.py): Bổ sung `version_num_length=64` cho cả hai hàm `run_migrations_offline()` và `do_run_migrations()`.
  - Bổ sung imports đầy đủ 100% models (`app.modules.conversations.models`, `app.modules.node_catalog.models`) vào `env.py`.

### 2.2. Migration Đồng Bộ Toàn Diện (`alembic check` 0 Diff)
- Tạo migration [`backend/alembic/versions/20260919_sync_missing_schema.py`](../../backend/alembic/versions/20260919_sync_missing_schema.py):
  - `knowledge_documents`: Bổ sung `index_status` (VARCHAR(32), server_default='pending'), `index_error` (TEXT) và index `ix_knowledge_documents_index_status`.
  - `assistants`: Bổ sung `published_workflow_version_id` (VARCHAR(36)), `workflow_ownership` (VARCHAR(20), server_default='private') và index `ix_assistants_workflow_ownership`.
  - `workflow_definitions`: Bổ sung `ownership` (VARCHAR(20), server_default='shared'), `assistant_id` (VARCHAR(36)) và các index tương ứng.
  - `evaluation_*`: Đồng bộ nullability cho `evaluation_result_items.is_refusal`, `execution_path`, `evaluation_runs.evaluation_method`.
- Chạy `uv run alembic upgrade head`: Database PostgreSQL live nâng cấp thành công lên HEAD.
- Chạy `uv run alembic check`: **No new upgrade operations detected (0 diff)**.

### 2.3. Xây Dựng CLI Quản Trị Database & Seed ([`backend/app/cli.py`](../../backend/app/cli.py))
Tạo module CLI hỗ trợ:
```bash
# Kiểm tra kết nối & tính toàn vẹn của schema
uv run python -m app.cli db check

# Chạy migration lên HEAD
uv run python -m app.cli db migrate

# Seed dữ liệu khởi tạo (Idempotent 100%)
uv run python -m app.cli db seed --all
# Hoặc chạy theo từng đối tượng:
uv run python -m app.cli db seed --assistants --knowledge --workflows --document-types --model-defaults --ingestion-jobs
```

### 2.4. Refactor Lifespan Startup Chuẩn Production ([`backend/app/main.py`](../../backend/app/main.py))
- **Xóa bỏ hoàn toàn**: `Base.metadata.create_all` và 6 hàm auto-seed tự động trong lifespan.
- **Thay thế bằng**: Hàm `verify_schema_readiness()`:
  - Kiểm tra kết nối DB.
  - Kiểm tra bảng `alembic_version` và các bảng cốt lõi (`assistants`, `knowledge_documents`, `workflow_definitions`, `model_provider_configs`).
  - Trong `ENVIRONMENT == "production"`: ném `RuntimeError` nếu schema chưa sẵn sàng (Fail-Fast).
  - Bổ sung cấu hình `DEV_AUTO_MIGRATE: bool = False` và `DEV_AUTO_SEED: bool = False` trong [`backend/app/core/config.py`](../../backend/app/core/config.py).

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Alembic Check**:
   - `uv run alembic check` -> `No new upgrade operations detected.` (0 diff)
2. **CLI Check**:
   - `uv run python -m app.cli db check` -> `Database schema check: PASSED.` (30 tables present)
3. **CLI Seed**:
   - `uv run python -m app.cli db seed --all` -> Thành công, không sinh bản ghi trùng lặp (Idempotent)
4. **Backend Linter & Test Suite**:
   - `uv run ruff check .` -> 0 lỗi (All checks passed)
   - `uv run --extra dev pytest -v` -> **257 passed, 0 warnings (100%)**
5. **Zero Mojibake**:
   - 335/335 tệp UTF-8 sạch, không lỗi ký tự rác.
