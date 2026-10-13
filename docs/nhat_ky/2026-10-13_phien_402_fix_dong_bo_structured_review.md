# Phiên #402 — Fix đồng bộ trạng thái duyệt dữ liệu có cấu trúc

## Mục tiêu

Khắc phục lỗi 8 nguồn có structured artifact yêu cầu cán bộ đối soát nhưng `KnowledgeSourceRevision` lại mang trạng thái `ready`, khiến giao diện không hiện nút duyệt trong khi Quality Gate xuất bản vẫn chặn bằng `FACT_SET_REVIEW_REQUIRED`.

## Thay đổi

- Bổ sung một invariant dùng chung trong `source_ingestion_service.py`: artifact có `review.status = required` hoặc còn `issues` luôn chuyển Quality Gate sang `warning`, kể cả khi dùng lại artifact theo cơ chế parse-once/embed-many.
- Áp cùng invariant cho luồng bóc tách lại để trạng thái nguồn và structured artifact không thể lệch nhau.
- Làm endpoint duyệt tương thích với bản ghi legacy bị lệch `ready + artifact required`; không tự duyệt và vẫn yêu cầu quyết định của cán bộ.
- Thêm migration `20261012_sync_structured_review` để sửa dữ liệu hiện có một chiều, không thay active pointer, generation hoặc vector index.
- Sau migration, kho `col_admissions` có đúng 8 nguồn `review_required` và 11 nguồn `ready`; cả 8 nguồn chờ duyệt đều có marker artifact `required`.

## Tệp thay đổi

- `backend/app/modules/knowledge/services/source_ingestion_service.py`
- `backend/alembic/versions/20261012_sync_structured_review.py`
- `backend/tests/test_knowledge_source_ingestion.py`
- `docs/nhat_ky/2026-10-13_phien_402_fix_dong_bo_structured_review.md`
- `docs/nhat_ky/README.md`
- `docs/memory/PROJECT_CONTEXT.md`
- `docs/WORK_LOG.md`

## Kiểm thử

- Ruff tập trung: đạt.
- `tests/test_knowledge_source_ingestion.py`: 8/8 đạt, gồm regression cho artifact tái sử dụng và bản legacy lệch trạng thái.
- Alembic current/head: `20261012_sync_struct_review`.
- Truy vấn hậu migration: `ready=11`, `review_required=8`, marker required khớp `8/8`.
- Full backend: `985 passed, 11 failed, 9 errors, 3 skipped`. Các lỗi còn lại là baseline ngoài phạm vi (quyền API test 403, Windows temp permission, local provider seed, exporter và một số test legacy); regression mới đều đạt.

## Quyết định và bài học

- Trạng thái được phép xuất bản phải được suy ra từ cùng một invariant với structured artifact, không chỉ từ nhánh parse mới.
- Migration không tự phê duyệt 8 nguồn và không đổi dữ liệu đang phục vụ. Cán bộ vẫn phải mở từng nguồn, đối soát rồi duyệt trước khi xuất bản.
- Downgrade migration là no-op vì không thể suy luận an toàn bản ghi nào từng `ready` sau khi có thể đã xảy ra duyệt thủ công.
