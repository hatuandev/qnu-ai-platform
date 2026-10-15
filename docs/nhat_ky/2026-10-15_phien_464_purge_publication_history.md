# Phiên 464 — Xóa nguồn có lịch sử xuất bản

## Mục tiêu và nguyên nhân

Người dùng gặp ForeignKeyViolationError khi Ngừng dùng rồi Xóa nguồn. run_purge đang DELETE knowledge_index_revisions trước binding trong khi knowledge_index_activations.to_index_revision_id RESTRICT. Ràng buộc đã có từ migration20261008 nhưng ORM chưa mô tả FK from/to; test cũ chỉ dùng nguồn chưa có lịch sử.

## Phương án đã thông báo và triển khai

- Có lịch sử: giữ sự kiện nguyên vẹn và binding detached; index pruned, point_ids rỗng, clear source/chunk links, lưu ID artifact đã dọn cùng job vào parity_report. Chỉ dọn payload Knowledge sau external cleanup. Không xóa Repository, source khác hoặc Qdrant collection. Nguồn chưa có history giữ hard-delete cũ.
- Phát hiện cross-source activation từ cả from/to trước external cleanup và báo SOURCE_ARTIFACT_SHARED409.
- Đồng bộ ORM FK với migration sẵn có, không thêm migration, không tắt ràng buộc.
- Re-import binding detached sang pending trước parse để lỗi/review vẫn hiển thị, không tự phục vụ pruned artifacts.
- Worker không trả raw SQL/driver parameters trong Job.error; log server giữ exception đầy đủ. Tác vụ failed có thể retry sau khi deploy, không tự thao tác DB/server thật.

## Tệp thay đổi

backend/app/modules/knowledge/services/source_purge.py; models.py; services/source_ingestion_service.py; backend/app/workers/tasks.py; tests/test_knowledge_source_purge.py; test_knowledge_source_ingestion.py; test_workers.py. Đồng bộ docs/quy_trinh/02_nap_tri_thuc_minio.md, memory/snapshot/chỉ mục.

## Kiểm chứng

- Trước sửa: 3 regression PostgreSQL thật fail đúng FK_RESTRICT trong ảnh. Fixture commit dùng savepoint trong outer transaction rồi rollback, external storage/vector bị cô lập; không xóa nguồn người dùng.
- Sau sửa: focus đầu34pass. Lần mở rộng có43pass/1fail do tên method rollback sai trong test; sửa test đúng rollback_index_revision.
- Cuối: 56passed/11,49s, artifact backend/storage/pytest464_verified.xml. Bao gồm publication history/rollback pruned/ẩn danh sách, vector/storage failures, retry, replay idempotent, scope tenant, cross-source from/to, re-import passed/review-required và worker-error sanitization.
- Ruff phạm vi và toàn Backend đạt, quét toàn có 2 cảnh báo quyền đọc artifact cũ nhưng không lỗi lint. Không full Pytest/Vite/Docker/server verify; giữ yêu cầu kiểm tra gọn của người dùng, không khẳng định toàn suite xanh.

## Bàn giao và giới hạn

Chưa commit/push/deploy/restart/retry job thật; không sửa docs/tai_lieu, không cleanupGit/force-push/reset DB/config model. Cần deploy Backend và worker cùng code mới rồi thử lại job xóa failed trong Tác vụ hoặc dialog còn mở. Binding/index còn lại chỉ là metadata lịch sử, không phải payload có thể phục hồi; tài liệu gốc Repository vẫn giữ. Nguồn đang deleting do lần cũ được retry theo cơ chế job hiện hành, không sửa tay DB.

Skill qnu-backend-architect và qnu-clean-code-architect định hướng fix theo lifecycle, kiểm thử thật có rollback và giữ transaction/audit; không giải quyết bằng cách bỏ FK hay xóa lịch sử để test qua.
