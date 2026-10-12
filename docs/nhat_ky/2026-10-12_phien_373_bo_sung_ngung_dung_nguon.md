# Phiên #373 — Bổ sung Ngừng dùng nguồn Kho tri thức

- Ngày: 2026-10-12.
- Yêu cầu: Giữ nút Xóa hiện hữu, thêm Ngừng dùng từng tài liệu trước khi xóa/thay văn bản.
- Skills: backend/frontend/clean-code/RAG/admin-frontend-design; tái sử dụng Button/ConfirmDialog, trạng thái rõ, test-first cho lifecycle/cache/scoping.

## Thay đổi

- Backend: service `source_pause.py` và endpoint POST bindings/{id}/pause, quyền knowledge.delete; actor scope, lock collection→binding, chặn nguồn không active hoặc parse/index/job bận, idempotent, tăng epoch. Status paused là String hiện có, không migration.
- Pause không xóa snapshot/Markdown/chunks/facts/vector và giữ pointers/artifacts. Snapshot mới chỉ lấy active, cache gắn epoch không reuse cache cũ; requests đã pin có thể hoàn tất với dữ liệu cũ. Không có nút Bật lại trong phạm vi yêu cầu.
- vector_generation_service chặn paused, source_ingestion_service giữ paused qua import/reparse/review/save Markdown, group_source_sync_service không tự bật paused, gc_service bảo toàn artifacts paused. Publish generation đã lọc active; không cần sửa thuật toán RAG.
- Frontend: `PauseSourceButton` dùng primitives sẵn có, confirmation/pending/error/invalidation; thêm cạnh Xóa ở collection-bindings-tab. Vector-workflow hiển thị Đã ngừng dùng, loại paused khỏi điều kiện publish. Checkbox/nạp vector nguồn paused bị chặn, Markdown vẫn có trạng thái riêng. Studio chặn nạp nếu indexStatus paused. API client và type KnowledgeBinding thêm paused.
- Tests: `test_source_pause.py` và `vector-workflow.test.ts`. Quy trình 02/03 cập nhật semantics.

## Kiểm chứng

- Test-first 5 ca thất bại do chưa có pause service. Regression DB thật tiếp theo phát hiện save Markdown biến paused→active; đã sửa đúng nhánh SQL và xác nhận lại.
- Backend trọng tâm: 41 passed (pause, vector load, purge, RAG ModelOps).
- Test DB thật fixture transaction/savepoint rollback: ownership sai bị từ chối, ngừng một nguồn không ảnh hưởng nguồn khác, đổi cache fingerprint, snapshot cũ bị từ chối, pointers/tệp gốc/revisions còn, lặp pause không tăng epoch, lưu Markdown không bật lại.
- Ruff toàn backend: đạt (cảnh báo đọc thư mục quyền Windows).
- Full backend cuối: 912 passed, 11 failed, 2 skipped; lỗi cũ ở consulting export, legacy publishing auth/canary/GC, reconciliation, facts tool và session actor role. Không lỗi mới trong 7 tests pause.
- Frontend logic: 4 passed; scoped Biome 7 tệp đạt. Full lint 15 lỗi ngoài phạm vi (format các tệp khác); không tự sửa lan.
- Build Vite + TypeScript typecheck: đạt, exit code 0. Chưa browser E2E. Không click Ngừng/Xóa trên 4 nguồn thực của người dùng, không reset/restart/publish/đổi provider/key/qnu-sso.

## Bài học

Chỉ thêm nút chưa đủ: cần lifecycle trạng thái không ẩn nguồn, epoch/cache, guard các đường tự activate và bảo toàn artifact. Ngừng dùng áp dụng lượt tra cứu mới, không thể thu hồi nội dung đã gửi.
