# NHẬT KÝ LÀM VIỆC — Phiên #63
# Ngày: 2026-09-17 | Tiêu đề: Tạo seed taxonomy Platform và khắc phục lỗi không hiển thị dữ liệu

## 1. Bối cảnh

- Người dùng kiểm tra màn hình loại văn bản nhưng không thấy dữ liệu.
- Kiểm tra PostgreSQL cho thấy bảng `platform_document_types` đã có 37 dòng, nhưng API bị HTTP 500 vì schema cũ của `knowledge_documents` thiếu `document_type_code`.
- Session song song đang xử lý seed Provider/ModelOps; phiên này không chỉnh sửa các file Provider, ModelOps hoặc seed liên quan.

## 2. Thay đổi kỹ thuật

| Tệp | Hành động | Mô tả |
|---|---|---|
| [`backend/app/modules/document_types/seed_data.py`](../../backend/app/modules/document_types/seed_data.py) | Tạo mới | Manifest seed versioned `qnu-document-taxonomy.v1`, sinh 37 dòng vận hành từ catalog đã đối chiếu với `qnu-ai-core`, giữ Core là nguồn dữ liệu duy nhất. |
| [`backend/scripts/seed_document_types.py`](../../backend/scripts/seed_document_types.py) | Tạo mới | Lệnh seed idempotent: `uv run python scripts\\seed_document_types.py`. |
| [`backend/app/modules/document_types/service.py`](../../backend/app/modules/document_types/service.py) | Cập nhật | Sync dùng seed manifest và sửa so sánh audit fields, không còn `KeyError` khi đồng bộ lần hai. |
| [`backend/app/main.py`](../../backend/app/main.py) | Cập nhật | Startup tự bổ sung cột/index taxonomy cho database cũ trước khi tính `doc_count`. |
| [`backend/alembic/versions/20260917_document_types.py`](../../backend/alembic/versions/20260917_document_types.py) | Cập nhật | Migration idempotent cho index/FK kể cả khi cột đã có sẵn. |
| [`backend/tests/test_document_types.py`](../../backend/tests/test_document_types.py) | Cập nhật | Kiểm tra seed manifest bảo toàn đủ 37 loại Core. |

## 3. Kết quả vận hành

- Đã chạy `uv run alembic upgrade head` trên PostgreSQL hiện tại.
- PostgreSQL: `platform_document_types` có **37/37** dòng active.
- API `GET /platform/v1alpha1/document-types`: **HTTP 200**, trả **37** loại.
- API `POST /platform/v1alpha1/document-types/sync`: **HTTP 200**, `total=37`, `added=0`, `updated=0`.
- Script seed chạy thành công và idempotent: `total=37, added=0, updated=0`.

## 4. Kiểm thử

- `uv run ruff check .`: pass.
- `uv run --extra dev pytest -q`: **135 passed**, 27 warnings phụ thuộc/suite hiện hữu, không có failure.
- `git diff --check`: pass; chỉ còn cảnh báo line ending CRLF/LF của working tree hiện hữu.
