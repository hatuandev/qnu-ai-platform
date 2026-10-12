# Phiên #374 — Chặn xóa nguồn chưa ngừng dùng

- Ngày: 2026-10-12.
- Yêu cầu: Không xóa nguồn đang xuất bản; chỉ xóa sau Ngừng dùng.
- Skills backend/frontend/clean-code/admin-frontend-design: guard ở service chứ không chỉ khóa UI, tái sử dụng Button/ConfirmDialog và regression lifecycle trước sửa.

## Thay đổi

- `source_purge.request_purge`: sau actor scope và lock collection/binding, từ chối mọi trạng thái ngoài paused/deleting bằng 409 SOURCE_NOT_PAUSED. Chỉ paused tạo tác vụ mới; deleting chỉ lấy/retry tác vụ tồn tại. Không mất chức năng retry lỗi storage/vector.
- `DeleteSourceButton`: nhận status bắt buộc, khóa nút kèm hướng dẫn Ngừng dùng, chặn mutation/confirm nếu props không hợp lệ. Danh sách và trang chi tiết truyền binding status thật; không nhầm trạng thái Markdown với trạng thái nguồn.
- `source_pause`/`PauseSourceButton`: cho nguồn pending đã hết công việc chuyển sang paused, vẫn chặn parse/job/index bận, để văn bản lỗi/chưa xuất bản không bị kẹt bởi quy tắc xóa mới.
- Tests purge dùng nguồn paused; giữ nguồn khác active. Thêm 3 ca từ chối active/pending/detached không dispatch/mất dữ liệu và một ca pause→purge→retry. Test pause thêm pending.

## Kiểm chứng

- Trước sửa: 3 ca active/pending/detached thất bại; đường cũ đã gọi enqueue thay vì từ chối (stub broker ban đầu trả AsyncMock làm DB báo sai kiểu, đã chỉnh stub return None).
- Sau sửa: 30 tests purge/pause/vector-load đạt; Ruff toàn BE đạt. Fixture PostgreSQL/savepoint rollback, không xóa nguồn thật.
- Biome 4 tệp FE đạt; Vite build + TypeScript typecheck đạt, exit code 0. Full FE lint còn lỗi cũ ngoài phạm vi.
- Full BE: 917 passed, 11 failed, 2 skipped (32,29s). Cùng 11 lỗi cũ như #373: consulting export, publishing auth/canary/GC, reconciliation, facts tool và session actor role; không lỗi mới ở guard xóa. Chưa browser E2E.
- Không reset/migration/restart, không xóa/ngừng các văn bản người dùng, không đổi qnu-sso/providers/credentials.

## Tệp

BE source_purge.py/source_pause.py, tests test_knowledge_source_purge.py/test_source_pause.py; FE delete-source-button.tsx/pause-source-button.tsx/collection-bindings-tab.tsx/source-detail-page.tsx. Cập nhật quy trình 02, nhật ký/mục lục, context/worklog/snapshot.
