# Phiên #407 — Fix lưu trạng thái duyệt và phạm vi nguồn

## Mục tiêu

Sửa hai lỗi quan sát được khi người dùng chọn một nguồn để nạp vector: giao diện lại hiển thị toàn bộ 8 nguồn cần duyệt của kho, và thao tác duyệt báo chạy nhưng trạng thái `Cần duyệt` không biến mất.

## Bằng chứng và nguyên nhân

- PostgreSQL cho thấy cả 8 revision có `updated_at=2026-10-13 02:17:28.829934+00` và `revision.status=ready`, chứng minh lần duyệt trước đã chạy transaction.
- Tuy nhiên `parse_provenance.structured_artifact.review.status` của cả 8 vẫn là `required`. Publish gate đọc artifact làm nguồn chuẩn nên tiếp tục chặn đúng; Redis không tham gia trạng thái này.
- `_apply_review_decision` lấy artifact là object con của JSONB rồi sửa `artifact["review"]` tại chỗ. Sau đó gán một dict mới có giá trị đã bằng object đang được SQLAlchemy theo dõi, khiến ORM không nhận biết `parse_provenance` thay đổi và không phát lệnh cập nhật cột JSONB.
- Frontend tạo `reviewBlockers` từ toàn bộ bindings của collection thay vì tập `targets` người dùng vừa chọn.

## Thay đổi

- Backend deep-copy artifact trước khi ghi quyết định duyệt, sau đó thay thế toàn bộ `parse_provenance` để SQLAlchemy đánh dấu JSONB dirty và persist `approved/rejected` thật sự.
- Thêm regression test dùng `set_committed_value` và SQLAlchemy attribute history, bảo đảm object JSONB gốc không bị mutate và thuộc tính mới có thay đổi cần flush.
- Frontend thêm `getSelectedReviewBlockers`, giao tập duyệt với đúng `binding_id` trong lựa chọn nạp vector; chọn một nguồn chỉ hiện một nguồn.
- Thêm regression test với 8 blocker nhưng một target, kết quả chỉ có đúng target đã chọn.
- Không reset DB, không tự duyệt lại 8 nguồn, không publish và không xóa Redis.

## Tệp chính

- `backend/app/modules/knowledge/services/source_ingestion_service.py`
- `backend/tests/test_knowledge_source_ingestion.py`
- `frontend/src/features/knowledge/components/vector-load-controls.tsx`
- `frontend/src/features/knowledge/utils/vector-workflow.ts`
- `frontend/src/features/knowledge/utils/vector-workflow.test.ts`

## Kiểm thử

- Ruff toàn backend: đạt.
- Source ingestion module: `10 passed`.
- Regression backend tập trung: `3 passed`.
- Frontend vector/auth tests: `52 passed`.
- Biome bốn tệp frontend: đạt.
- Vite + TypeScript build: đạt, 5092 modules.
- Full backend: `987 passed, 11 failed, 9 errors, 3 skipped`; 11 failure và 9 error là baseline ngoài phạm vi (quyền Windows temp, API permission/role, exporter/seed/reconciliation/consulting), regression của phiên đạt đầy đủ.

## Bài học

Với JSON/JSONB không dùng mutable extension, không được mutate object lồng trực tiếp rồi gán lại giá trị bằng nhau. Write path phải copy-on-write hoặc dùng explicit mutable tracking; test phải kiểm tra ORM dirty history hoặc round-trip DB, không chỉ assert trạng thái in-memory.
