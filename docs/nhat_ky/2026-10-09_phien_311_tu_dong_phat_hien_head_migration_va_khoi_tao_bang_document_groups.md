# Nhật Ký Phiên Làm Việc — Phiên 311: Tự Động Phát Hiện Alembic HEAD Migration & Hoàn Tất Cấu Trúc Bảng Document Groups

**Thời gian thực hiện**: 2026-10-09  
**Người thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu phiên**: Xử lý triệt để lỗi runtime `UndefinedTableError: relation "document_groups" does not exist` khi uvicorn khởi động và gọi API `GET /platform/v1alpha1/documents/groups`, nâng cấp cơ chế kiểm tra schema database trong `app.cli` để tự động đối soát revision hiện tại với Alembic HEAD, bảo đảm 100% migrations luôn được áp dụng tự động mà không bị bỏ sót.

---

## 1. Bối Cảnh & Nguyên Nhân Gốc Rễ (Root Cause Analysis)

- **Hiện tượng**:
  - Khi khởi động hệ thống qua `./make dev`, console báo:
    - `Current Alembic revision: 20261008_publishing_v2_hardening [qnu-cli]`
    - `All required core tables are present (39 total tables). [qnu-cli]`
    - `Database schema check: PASSED. [qnu-cli]`
  - Tuy nhiên khi Frontend gọi `GET /platform/v1alpha1/documents/groups` (Port 8001), Backend ném ngoại lệ:
    `asyncpg.exceptions.UndefinedTableError: relation "document_groups" does not exist`.
- **Nguyên nhân cốt lõi**:
  - Tệp migration `backend/alembic/versions/20261009_document_groups.py` đã tồn tại trong repository để tạo bảng `document_groups` và `document_group_memberships`.
  - Nhưng trong `backend/app/cli.py`: hàm `check_db_schema()` trước đây chỉ kiểm tra danh sách cứng 10 bảng lõi sơ khai và KHÔNG kiểm tra xem `current_rev` của database có khớp với `Alembic HEAD` hay không.
  - Kết quả là CSDL đang ở bản ghi cũ (`20261008_publishing_v2_hardening`) vẫn vượt qua bước kiểm tra (`PASSED`), khiến `ensure_db_ready()` lầm tưởng CSDL đã sẵn sàng và **bỏ qua hoàn toàn lệnh chạy `migrate_database()`**.

---

## 2. Giải Pháp Triển Khai (Production-First)

### A. Backend CLI Schema Check (`backend/app/cli.py`)
1. **Đối soát động với Alembic HEAD**:
   - Sử dụng `ScriptDirectory.from_config(_get_alembic_config()).get_heads()`.
   - Nếu `current_rev not in alembic_heads`: ghi nhận cảnh báo `Database revision is behind Alembic HEAD. Migration required.` và trả về `False`.
   - Điều này đảm bảo mỗi khi có bất kỳ migration mới nào được thêm vào dự án, `ensure_db_ready` sẽ tự động phát hiện và kích hoạt chạy `migrate_database()` lên HEAD ngay trong quá trình khởi động.
2. **Bổ sung bảng vào danh sách kiểm tra lõi**:
   - Bổ sung `"document_groups"` và `"document_group_memberships"` vào tập `required_tables`.
3. **Thực thi Migration lên CSDL Thực Tế**:
   - Đã chạy thành công migration `20261008_publishing_v2_hardening -> 20261009_document_groups`.
   - CSDL PostgreSQL nâng tổng số bảng lên **41 tables**.
   - Current revision hiện tại: `20261009_document_groups`.

---

## 3. Kết Quả Kiểm Thử (Verification Suite)

1. **Kiểm tra Schema CLI**:
   - `python -m app.cli db check` $\rightarrow$ Kết nối OK, Current Alembic revision: `20261009_document_groups`, 41 bảng đầy đủ, Schema check: `PASSED`.
2. **Kiểm tra API Thực Tế (Live HTTP Integration)**:
   - Request: `GET http://127.0.0.1:8001/platform/v1alpha1/documents/groups`
   - Phản hồi: `HTTP 200 OK`, JSON: `{"items": [], "total": 0}` (Hết hoàn toàn lỗi 500 UndefinedTableError).
3. **Backend Linter & Pytest**:
   - `python -m ruff check app/cli.py` $\rightarrow$ `All checks passed!` (0 lỗi).
   - `pytest tests/test_document_groups_and_knowledge_attach.py tests/test_cli_db_migrate.py -v` $\rightarrow$ **17/17 PASSED 100%**.
   - `pytest tests/test_sso_auth.py tests/test_permission_contract.py -v` $\rightarrow$ **38/38 PASSED 100%**.
4. **Frontend Linter, Typecheck & Test**:
   - `biome check src/app/auth src/app/config` $\rightarrow$ 0 lỗi format / lint.
   - `node --test src/app/auth/auth.test.ts` $\rightarrow$ **46/46 PASSED 100%** (bao gồm 16 kịch bản Interceptor).
   - `tsc --noEmit` $\rightarrow$ **0 lỗi TypeScript**.
   - `vite build` $\rightarrow$ **0 lỗi biên dịch**, bundle thành công trong 5.22s.
5. **QNU SSO Backend Tests**:
   - **120/120 tests PASSED** trên toàn bộ các projects (`Application.UnitTests`, `Domain.UnitTests`, `Infrastructure.IntegrationTests`).

---

## 4. Tệp Tin Thay Đổi
- `backend/app/cli.py`: Bổ sung đối soát Alembic HEAD động và thêm 2 bảng `document_groups`, `document_group_memberships`.
- `docs/nhat_ky/2026-10-09_phien_311_tu_dong_phat_hien_head_migration_va_khoi_tao_bang_document_groups.md`: Tạo mới nhật ký phiên.
