# NHẬT KÝ LÀM VIỆC — Phiên #61
# Ngày: 2026-09-17 | Tiêu đề: Triển khai đồng bộ taxonomy loại văn bản từ qnu-ai-core

## 1. Bối cảnh & phạm vi

- Triển khai kế hoạch đã được duyệt để chuẩn hóa 37 loại văn bản/28 mã NĐ30 từ `D:\DuAnPhanMem\qnu-ai-core` sang `qnu-ai-platform`.
- Session song song đang xử lý seed Provider/ModelOps; phiên này không chỉnh các file provider, modelops hoặc seed liên quan.
- Vì `qnu-ai-core` hiện chưa có manifest/HTTP endpoint taxonomy versioned, Platform dùng catalog đã đối chiếu làm nguồn import tương thích và ghi source hash/version để mở đường cho sync HTTP sau này.

## 2. Thay đổi kỹ thuật

| Tệp | Hành động | Mô tả |
|---|---|---|
| [`backend/app/modules/document_types/catalog.py`](../../backend/app/modules/document_types/catalog.py) | Tạo mới | Catalog 37 loại, 28 mã NĐ30, category, alias legacy, NFC và source hash ổn định. |
| [`backend/app/modules/document_types/models.py`](../../backend/app/modules/document_types/models.py) | Tạo mới | Model `platform_document_types`, source audit, active/custom flags. |
| [`backend/app/modules/document_types/schemas.py`](../../backend/app/modules/document_types/schemas.py) | Tạo mới | DTO CRUD, response và sync result bằng Pydantic v2. |
| [`backend/app/modules/document_types/service.py`](../../backend/app/modules/document_types/service.py) | Tạo mới | Async CRUD, active-code validation, count thật từ KnowledgeDocument và sync idempotent. |
| [`backend/app/modules/document_types/router.py`](../../backend/app/modules/document_types/router.py) | Tạo mới | API list/detail/create/update/deactivate/sync. |
| [`backend/app/modules/knowledge/models.py`](../../backend/app/modules/knowledge/models.py) | Cập nhật | Thêm FK/index `document_type_code`. |
| [`backend/app/modules/knowledge/router.py`](../../backend/app/modules/knowledge/router.py) | Cập nhật | Upload nhận loại văn bản; list hỗ trợ filter theo code. |
| [`backend/app/modules/knowledge/service.py`](../../backend/app/modules/knowledge/service.py) | Cập nhật | Validate code active trước ingestion và lưu nguồn gán nhãn. |
| [`backend/app/modules/knowledge/schemas.py`](../../backend/app/modules/knowledge/schemas.py) | Cập nhật | Trả `document_type_code` trong document DTO. |
| [`backend/app/modules/workflows/nodes/extract_fields_node.py`](../../backend/app/modules/workflows/nodes/extract_fields_node.py) | Cập nhật | Heuristic nhận diện trả canonical code hoặc `unclassified`, không gán `general_draft` giả. |
| [`backend/app/modules/tools/builtin/document_exporter.py`](../../backend/app/modules/tools/builtin/document_exporter.py) | Cập nhật | OpenAPI enum dùng 37 code; export tách code và label, reject loại không hỗ trợ. |
| [`backend/app/main.py`](../../backend/app/main.py) | Cập nhật | Import model, startup sync và mount router taxonomy. |
| [`backend/alembic/env.py`](../../backend/alembic/env.py) | Cập nhật | Đăng ký model taxonomy, loại bỏ import `app.modules.rag.models` không tồn tại. |
| [`backend/alembic/versions/20260917_document_types.py`](../../backend/alembic/versions/20260917_document_types.py) | Tạo mới | Migration có guard cho schema hiện hữu. |
| [`backend/tests/test_document_types.py`](../../backend/tests/test_document_types.py) | Tạo mới | Kiểm tra catalog, alias, NFC/hash, extractor và exporter invalid type. |
| [`frontend/src/services/document-types-api.ts`](../../frontend/src/services/document-types-api.ts) | Tạo mới | API client typed, không fallback mock cho taxonomy. |
| [`frontend/src/components/admin/document-type-form.tsx`](../../frontend/src/components/admin/document-type-form.tsx) | Tạo mới | Form dùng chung cho create/edit. |
| [`frontend/src/pages/document-types-page.tsx`](../../frontend/src/pages/document-types-page.tsx) | Tạo mới | Master list, filter, KPI, create và sync. |
| [`frontend/src/pages/document-type-detail-page.tsx`](../../frontend/src/pages/document-type-detail-page.tsx) | Tạo mới | Dedicated detail route, edit/deactivate và source audit. |
| [`frontend/src/App.tsx`](../../frontend/src/App.tsx) | Cập nhật | Tách `/document-types` khỏi KnowledgePage và hỗ trợ deep link. |
| [`frontend/src/pages/document-ingest-page.tsx`](../../frontend/src/pages/document-ingest-page.tsx) | Cập nhật | Select loại văn bản lấy từ taxonomy API và truyền code khi upload. |
| [`frontend/src/services/api-client.ts`](../../frontend/src/services/api-client.ts) | Cập nhật | Truyền/nhận document type code và filter documents theo code. |
| [`docs/ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md`](../ke_hoach/03_ke_hoach_dong_bo_taxonomy_loai_van_ban.md) | Cập nhật | Ghi quyết định v1, trạng thái triển khai và phần còn lại. |

## 3. Kết quả kiểm thử

- `uv run ruff check .`: pass.
- `uv run --extra dev pytest -q`: **134 passed**; có cảnh báo phụ thuộc/AsyncMock từ suite hiện hữu, không có failure.
- `npm.cmd run lint`: pass, Biome kiểm tra 83 files.
- `npm.cmd run typecheck`: pass.
- `npm.cmd run build`: pass; Vite cảnh báo chunk JavaScript lớn hơn 500 kB.
- OpenAPI kiểm tra có đủ các route `/platform/v1alpha1/document-types`, detail, deactivate và sync.

## 4. Ghi chú vận hành

- Startup sync chỉ upsert catalog chuẩn; custom type được bảo vệ và loại cũ chỉ deactivate.
- `doc_count` không lấy từ preset Core; luôn đếm document thật trong PostgreSQL.
- Bước tiếp theo là bổ sung Core manifest/endpoint versioned, auto-classification có confidence/evidence và E2E CRUD/sync.
