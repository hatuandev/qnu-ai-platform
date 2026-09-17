# NHẬT KÝ LÀM VIỆC — LẬP KẾ HOẠCH ĐỒNG BỘ TAXONOMY LOẠI VĂN BẢN

**Thời gian**: 2026-09-17 20:43 (UTC+7)  
**Mục tiêu**: Lập tài liệu kế hoạch để người dùng duyệt trước khi triển khai đồng bộ loại văn bản từ `qnu-ai-core` sang `qnu-ai-platform`.

## Nội dung đã thực hiện

- Đối chiếu taxonomy 37 loại tại `qnu-ai-core/services/platform-api/.../document_taxonomy.py`.
- Phân biệt danh mục của Product Platform với `document_type` dạng chuỗi tự do trong AI Core engine.
- Ghi nhận các hạn chế của router cũ: in-memory, preset trùng ở Studio và `doc_count` hardcode.
- Đối chiếu với Platform mới: chưa có module/table/API Document Types; `KnowledgeDocument` chưa có `document_type_code`.
- Xây dựng lộ trình contract, sync, database, mapping legacy, ingestion, workflow/drafting, frontend và kiểm thử.

## Tệp tạo/cập nhật

| Tệp | Hành động | Mô tả |
|---|---|---|
| [`docs/ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`](../ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md) | Tạo mới | Kế hoạch chi tiết, trạng thái bản nháp chờ duyệt |
| [`docs/ke_hoach/README.md`](../ke_hoach/README.md) | Cập nhật | Thêm liên kết tới kế hoạch mới |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | Cập nhật | Ghi nhận phiên lập kế hoạch |
| [`docs/memory/PROJECT_CONTEXT.md`](../memory/PROJECT_CONTEXT.md) | Cập nhật | Ghi nhận kế hoạch mới trong trạng thái dự án/backlog |
| [`docs/memory/snapshots/2026-09-17_session_60.md`](../memory/snapshots/2026-09-17_session_60.md) | Tạo mới | Snapshot phiên làm việc |

## Kiểm thử

- Không chạy test/build vì phiên này chỉ tạo và cập nhật tài liệu kế hoạch.
- Chưa thay đổi code backend, frontend, database hoặc dữ liệu nghiệp vụ.
