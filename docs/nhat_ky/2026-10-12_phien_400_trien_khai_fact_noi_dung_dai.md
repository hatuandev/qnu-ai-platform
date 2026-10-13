# Phiên #400 — Triển khai Fact cho nội dung dài và chặn job treo

## Mục tiêu

Triển khai đề xuất phiên #399 để dữ liệu bảng có thực thể dài không còn lỗi `VARCHAR(512)`, vẫn giữ nguyên nội dung và bảo đảm job dựng chỉ mục kết thúc minh bạch khi transaction lỗi.

## Thay đổi chính

- Thêm hợp đồng Fact gồm `entity_key` ổn định, `entity_label` tối đa 512 ký tự và `entity_text` đầy đủ; chuẩn hóa Unicode NFC và khoảng trắng bằng thuật toán tổng quát, không dùng từ điển hardcode.
- Giữ `entity_name` làm projection tương thích ngược nhưng chuyển sang `TEXT`; `attribute_value` tiếp tục là `TEXT`, `raw_data` tiếp tục giữ provenance đầy đủ.
- Artifact nguồn nâng lên `structured-source-v5-long-fact-identity`; candidate parity kiểm cả ba trường mới đối với artifact v5 và vẫn đọc artifact cũ.
- Migration `20261012_fact_long_text_identity` thêm/backfill ba trường, bỏ B-tree trên nội dung dài, thêm index `entity_key` và GIN full-text; downgrade chặn nếu có dữ liệu dài để tránh mất dữ liệu.
- Fact retrieval tìm cụm bằng PostgreSQL FTS và render nhãn gọn, còn nội dung đầy đủ luôn tồn tại để đối chiếu.
- Worker `task_knowledge_index_build` rollback session, tải lại `JobRecord`, rồi mới kiểm tra hủy/cập nhật `failed`; không còn mắc `PendingRollbackError` làm job đứng ở 10%.

## Tệp chính

- `backend/app/modules/knowledge/services/fact_identity.py`
- `backend/app/modules/knowledge/models.py`
- `backend/app/modules/knowledge/services/source_artifact.py`
- `backend/app/modules/knowledge/services/generation_candidate.py`
- `backend/app/modules/rag/facts.py`
- `backend/app/workers/tasks.py`
- `backend/alembic/versions/20261012_fact_long_text_identity.py`
- `backend/tests/test_long_fact_identity.py`

## Kiểm thử

- `uv run ruff check .`: đạt.
- Focused regression: 54 test đạt.
- Long-fact regression cuối: 4/4 đạt, gồm ghi–đọc thật PostgreSQL với `entity_text` dài hơn 512 ký tự và rollback job.
- Full backend: 980 đạt, 3 bỏ qua, 13 fail và 9 error ngoài phạm vi thay đổi. Các lỗi còn lại thuộc dữ liệu seed rỗng, quyền API cũ và `PermissionError` thư mục tạm Windows; toàn bộ test mới của phiên đạt.
- Alembic đang ở head `20261012_fact_long_text_identity`; PostgreSQL round-trip xác nhận schema mới hoạt động.

## Giới hạn và bước vận hành

- Không tự động retry/nạp lại hai tài liệu cũ, không publish, không reset dữ liệu và không restart dịch vụ trong phiên này.
- Sau khi backend/worker nhận mã mới, người dùng có thể nạp lại hai file; lỗi dữ liệu dài sẽ không còn và mọi lỗi khác sẽ chuyển job sang `failed` có thông báo thay vì treo im lặng.
