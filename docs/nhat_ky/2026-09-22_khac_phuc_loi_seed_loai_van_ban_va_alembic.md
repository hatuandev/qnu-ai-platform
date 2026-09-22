# NHẬT KÝ LÀM VIỆC — 2026-09-22
## Khắc Phục Lỗi Thiếu Bảng `platform_document_types` & Tối Ưu Hóa Chuỗi Migration Alembic Cho Seed Data

- **Thời gian**: 2026-09-22 10:15 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Xử lý triệt để lỗi `UndefinedTableError: relation "platform_document_types" does not exist` khi chạy các lệnh seed database (`uv run python -m app.cli db seed --document-types`, `uv run python -m app.cli db seed --all`, `uv run python scripts/seed_document_types.py`).

---

### 1. Hiện Tượng & Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)

Khi người dùng chạy lệnh nạp dữ liệu loại văn bản hoặc toàn bộ dữ liệu mẫu hệ thống:
```powershell
uv run python -m app.cli db seed --document-types
uv run python -m app.cli db seed --all
uv run python scripts/seed_document_types.py
```
Hệ thống báo lỗi:
```text
sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError: <class 'asyncpg.exceptions.UndefinedTableError'>: relation "platform_document_types" does not exist
[SQL: SELECT ... FROM platform_document_types WHERE platform_document_types.code = $1::VARCHAR]
```

Quá trình điều tra và truy vết chuỗi migration phát hiện 4 nguyên nhân kỹ thuật liên hoàn:
1. **Chưa áp dụng Migration**: CSDL PostgreSQL chưa chạy migration tạo bảng `platform_document_types` (được định nghĩa trong migration `20260917_document_types.py`).
2. **Lỗi Ràng Buộc Dữ Liệu Rác (Orphan Facts)**:
   Khi cố gắng chạy migration tự động qua `db migrate`, migration `20260919_facts_foreign_key_and_schema_sync.py` cố tạo Foreign Key `CASCADE` giữa `knowledge_facts(document_id)` và `knowledge_documents(id)`. Tuy nhiên, trong CSDL thực tế có 772 records facts bị mồ côi (document_id không tồn tại), khiến PostgreSQL từ chối tạo constraint và abort transaction.
3. **Lỗi Alembic Giới Hạn Chiều Dài Cột `version_num` (VARCHAR 32)**:
   Revision ID `20260919_facts_foreign_key_and_schema_sync` có độ dài 43 ký tự. Mặc định trong Alembic, bảng `alembic_version` tạo cột `version_num` kiểu `VARCHAR(32)`, dẫn đến lỗi `StringDataRightTruncationError: value too long for type character varying(32)` khi lưu revision ID.
4. **Thiếu DDL Tạo Bảng `conversation_threads`**:
   Migration mới nhất `20260922_conversation_feedback.py` tạo Foreign Key trỏ tới `conversation_threads.id`, nhưng bảng `conversation_threads` và `conversation_messages` trước đó chưa từng có migration DDL `create_table`.
5. **Thiếu `await connection.commit()` Trong Async Alembic Engine**:
   Trong `backend/alembic/env.py`, hàm `run_async_migrations()` sử dụng `async with connectable.connect()` nhưng thiếu lời gọi `await connection.commit()` tường minh, khiến transaction DDL bị rollback khi kết thúc context.

---

### 2. Các Thay Đổi Kỹ Thuật (Key Technical Changes)

1. **[`backend/alembic/env.py`](backend/alembic/env.py)**:
   - Override `DefaultImpl.version_table_impl` để Alembic luôn tạo bảng `alembic_version` với `version_num VARCHAR(64)`, hỗ trợ không giới hạn các revision ID mang tên mô tả dài.
   - Thêm lệnh an toàn tự động mở rộng cột: `ALTER TABLE IF EXISTS alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)`.
   - Bổ sung `await connection.commit()` trong `run_async_migrations()` đảm bảo transaction DDL được commit chắc chắn.

2. **[`backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py`](backend/alembic/versions/20260919_facts_foreign_key_and_schema_sync.py)**:
   - Bổ sung câu lệnh tiền xử lý tự động dọn dẹp các facts mồ côi (`DELETE FROM knowledge_facts WHERE document_id IS NOT NULL AND document_id NOT IN (SELECT id FROM knowledge_documents)`) trước khi thiết lập ràng buộc khóa ngoại.

3. **[`backend/alembic/versions/20260922_conversation_feedback.py`](backend/alembic/versions/20260922_conversation_feedback.py)**:
   - Bổ sung kiểm tra và tự động khởi tạo bảng `conversation_threads` và `conversation_messages` với đầy đủ indexes trước khi tạo bảng phản hồi `conversation_feedbacks`.

---

### 3. Kết Quả Kiểm Thử & Nghiệp Vụ (Verification)

1. **Trạng thái Migration**:
   - `uv run alembic current` -> `20260922_conversation_feedback (head)`.
2. **Thực thi Seed Data Loại Văn Bản**:
   - `uv run python -m app.cli db seed --document-types`:
     `Synchronized document taxonomy version=qnu-document-taxonomy.v1 added=37 updated=0 deactivated=0` (Thành công 100%).
   - `uv run python scripts/seed_document_types.py`: Chạy an toàn, đạt tính idempotent (`total=37, added=0`).
3. **Thực thi Seed Data Toàn Bộ Hệ Thống (`--all`)**:
   - `uv run python -m app.cli db seed --all`:
     - 37 loại văn bản theo NĐ 30/2020.
     - 5 workflows chuẩn hóa.
     - 5 trợ lý AI chính thức (Tuyển sinh, Quy chế, Thư viện số, Soạn thảo văn bản, Ngân hàng đề thi).
     - 5 kho tri thức nạp đầy đủ documents, chunks, facts và khởi tạo vector Qdrant collections.
     - 7 ingestion job records được đồng bộ.
     - `Database seed completed successfully`.
4. **Kiểm tra Chất lượng Mã Nguồn**:
   - `uv run ruff check .` -> `All checks passed!` (0 lỗi).
   - `uv run --extra dev pytest tests/test_document_types.py` -> 8/8 passed (100%).
   - `uv run --extra dev pytest -v` -> **394/394 passed (100% trong 39.74s)**.
