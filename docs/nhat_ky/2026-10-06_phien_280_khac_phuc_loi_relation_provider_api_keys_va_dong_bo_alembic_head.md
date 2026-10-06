# Nhật Ký Phiên Làm Việc #280: Khắc Phục Triệt Để Lỗi UndefinedTableError "provider_api_keys", Nâng Cấp Alembic Head & Bảo Vệ Provider RTX 5090

**Thời gian**: 2026-10-06 16:30 (UTC+7)  
**Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Khắc phục lỗi HTTP 500 `UndefinedTableError: relation "provider_api_keys" does not exist` khi truy cập `/platform/v1alpha1/modelops/providers/prov_rtx5090_ollama/keys`, nâng cấp toàn bộ chuỗi migration Alembic lên HEAD và thiết lập cơ chế tự động bảo vệ schema DB.

---

## 1. Hiện Tượng & Nguyên Nhân Gốc Rễ (Root Cause Analysis)

### 1.1 Hiện tượng
Trên nhật ký runtime backend ghi nhận nhiều lỗi HTTP 500 liên tiếp:
```text
2026-10-06T09:15:31.196217Z [error] Unhandled internal server error [corr=corr_3ec8bf3be7f5]: 
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "provider_api_keys" does not exist
[SQL: SELECT provider_api_keys.id, ... FROM provider_api_keys WHERE provider_api_keys.provider_id = $1 ...]
[parameters: ('prov_rtx5090_ollama',)]
path=/platform/v1alpha1/modelops/providers/prov_rtx5090_ollama/keys
```

### 1.2 Nguyên nhân gốc rễ
1. **Database bị tụt hậu so với migration code**:
   - Kiểm tra `alembic current` trên PostgreSQL phát hiện DB đang dừng ở phiên bản `20260922_conversation_feedback`.
   - Các migration tạo bảng pool khóa quan hệ (`20261002_provider_api_keys.py`, `20261002_provider_key_events.py`, `20261002_normalize_provider_key_status.py`, `20261002_remove_local_model_providers.py`) đã được viết nhưng chưa được migrate vào container CSDL PostgreSQL hiện tại.
2. **Cơ chế kiểm tra schema ban đầu (`check_db_schema`) chưa bao quát**:
   - Hàm `check_db_schema()` trong `app/cli.py` chỉ kiểm tra tập hợp 6 bảng cốt lõi ban đầu (`assistants`, `knowledge_collections`, `knowledge_documents`, `workflow_definitions`, `model_provider_configs`, `platform_document_types`).
   - Do 6 bảng này đều có mặt, `check_db_schema()` trả về `True`, khiến hàm `ensure_db_ready` bỏ qua bước tự động gọi `migrate_database()`.
3. **Rủi ro tiềm ẩn trong migration `20261002_remove_local_model_providers.py`**:
   - Migration cũ viết vào 02/10 có mệnh đề `DELETE FROM model_provider_configs WHERE lower(provider_type) IN ('ollama', ...)`.
   - Vào các phiên #266-#269 (05/10), dự án đã tích hợp máy chủ GPU nội bộ NVIDIA RTX 5090 (`prov_rtx5090_ollama`) sử dụng `provider_type='ollama'`.
   - Nếu chạy migration cũ mà không có điều kiện bảo vệ, `prov_rtx5090_ollama` và mô hình `qwen3-vl:8b` trong chuỗi OCR sẽ bị xóa nhầm!

---

## 2. Giải Pháp Triển Khai & Các Thay Đổi Kỹ Thuật

### 2.1 Hiệu chỉnh Migration `20261002_remove_local_model_providers.py`
- Bổ sung điều kiện loại trừ bảo vệ an toàn 100% cho `prov_rtx5090_ollama`:
  ```sql
  DELETE FROM model_provider_configs
  WHERE (
      id IN ('prov_local', 'prov_ollama', 'prov_sentence_transformers', 'prov_docling', 'prov_easyocr')
      OR lower(provider_type) IN ('local', 'local_vllm', 'sentence_transformers', 'docling', 'easyocr')
  )
  AND id != 'prov_rtx5090_ollama'
  AND id NOT LIKE 'prov_rtx%'
  ```
- Giữ nguyên cấu hình mặc định đang áp dụng (`bge-m3:latest` trên `prov_rtx5090_ollama`), chỉ điều chỉnh defaults nếu trước đó nó trỏ vào các provider local cũ đã bị loại bỏ.
- Bảo toàn `qwen3-vl:8b` trong `ocr_combo_chain` và `vision_adapter`.

### 2.2 Thực Thi Chuỗi Migration Alembic Lên HEAD
- Chạy lần lượt các bước nâng cấp:
  1. `20260926_reconcile_core_schema`: Reconcile schema cốt lõi.
  2. `20261002_provider_api_keys`: Tạo bảng `provider_api_keys` và chuyển đổi khóa từ `extra_config` / `api_key_encrypted`.
  3. `20261002_provider_key_events`: Tạo bảng `provider_key_events` ghi nhận lịch sử xoay vòng khóa.
  4. `20261002_normalize_provider_key_status`: Chuẩn hóa trạng thái khóa (`active`, `rate_limited`, `exhausted`, `invalid`, `inactive`).
  5. `20261002_remove_local_models`: Dọn dẹp provider cũ nhưng bảo vệ an toàn máy chủ RTX 5090.
- Kết quả: `uv run alembic current` đạt `20261002_remove_local_models (head)`.

### 2.3 Nâng Cấp Bộ Kiểm Tra Schema Tự Động (`app/cli.py`)
- Bổ sung `provider_api_keys`, `provider_key_events`, `conversation_feedbacks` vào tập `required_tables` của `check_db_schema()`.
- Nhờ đó, bất cứ khi nào khởi động backend trên môi trường mới hoặc DB bị thiếu bảng quan hệ, hệ thống sẽ phát hiện ngay lập tức và tự động kích hoạt `migrate_database()` lên HEAD trước khi đón nhận request.

---

## 3. Kết Quả Kiểm Thử & Xác Nhận (Verification)

1. **Kiểm tra Schema & CLI**:
   ```bash
   uv run python -m app.cli db check
   # -> All required core tables are present (33 total tables).
   # -> Database schema check: PASSED.
   ```
2. **Kiểm tra Endpoint HTTP Thực Tế**:
   - Gọi `GET /platform/v1alpha1/modelops/providers/prov_rtx5090_ollama/keys`:
   - Kết quả: **HTTP 200 OK**, trả về khóa on-premise `key_rtx5090_primary` (`Tailscale WireGuard On-Premise`, `ON-PREMISE (NO KEY REQUIRED)`).
   - Kiểm tra các provider khác (`prov_gemini`, `prov_openai`, `prov_cloudflare`): Đều trả về HTTP 200 OK với danh sách mảng rỗng (chưa gán key) an toàn, 0 lỗi 500.
3. **Kiểm tra Pytest & Linter**:
   - `uv run ruff check app alembic`: 0 lỗi.
   - `uv run --extra dev pytest tests/test_cli_db_migrate.py`: 3/3 passed.
   - `uv run --extra dev pytest tests/test_provider_key_rotation_service.py tests/test_provider_key_status.py`: 6/6 passed.
   - `uv run --extra dev pytest tests/test_multiturn_and_provider_safety.py`: 5/5 passed.

---

## 4. Tệp Tin Thay Đổi
- `backend/alembic/versions/20261002_remove_local_model_providers.py`: Bảo vệ `prov_rtx5090_ollama` và defaults của hệ thống.
- `backend/app/cli.py`: Mở rộng `required_tables` với `provider_api_keys`, `provider_key_events`, `conversation_feedbacks`.
- `docs/nhat_ky/2026-10-06_phien_280_khac_phuc_loi_relation_provider_api_keys_va_dong_bo_alembic_head.md`: Tài liệu chi tiết phiên 280.
- `docs/nhat_ky/README.md`: Cập nhật bảng tổng hợp phiên.
- `docs/WORK_LOG.md`: Ghi nhận tiến trình tổng thể.
- `docs/memory/PROJECT_CONTEXT.md`: Đồng bộ bộ nhớ ngữ cảnh kiến trúc.
