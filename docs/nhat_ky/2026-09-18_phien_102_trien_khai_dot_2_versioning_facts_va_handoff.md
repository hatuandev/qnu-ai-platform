# NHẬT KÝ LÀM VIỆC — PHIÊN #102
# Ngày: 18/09/2026 | Triển Khai Hoàn Tất Đợt 2: Quản Trị Phiên Bản Snapshot, Bảng Biểu Số Liệu Excel & Bàn Giao Cán Bộ Trực Tiếp

---

## 1. Mục Tiêu Phiên Làm Việc

Phiên làm việc này tập trung triển khai toàn diện **Đợt 2** theo định hướng nâng cấp QNU AI Platform thành nền tảng quản trị Trợ lý AI chuyên trách cấp trường:
1. **Quản trị Phiên bản Trợ lý AI & Khôi phục Snapshot 1-Click (Assistant Versioning & Rollback)**:
   - Lưu trữ lịch sử snapshot 7 lớp bất biến của Trợ lý AI khi có cập nhật hoặc xuất bản.
   - Hỗ trợ rollback 1-click về bất kỳ mốc phiên bản nào trong quá khứ.
   - Giao diện Modal Lịch sử Phiên bản trên `assistant-detail-page.tsx` kèm cảnh báo an toàn.
2. **Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV (Structured Facts Ingestion)**:
   - Bộ bóc tách chuyên dụng `excel_parser.py` bóc tách trực tiếp các bảng điểm chuẩn, chỉ tiêu, học phí từ tệp `.xlsx`, `.xls`, `.csv` thành facts số hóa với độ tin cậy tuyệt đối `confidence = 1.0`.
   - Endpoint `POST /knowledge/collections/{id}/facts/import-excel` và `GET /knowledge/collections/{id}/facts`.
   - Giao diện Tab "Bảng Biểu & Số Liệu" trên `collection-detail-page.tsx` với bảng tra cứu, bộ lọc tìm kiếm và Dialog upload bảng tính.
3. **Bàn Giao Trực Tiếp & Giám Sát Hội Thoại (Live Conversations & Staff Handoff Desk)**:
   - Module Backend `app.modules.conversations` quản lý hội thoại thời gian thực giữa người học và AI.
   - Hỗ trợ trạng thái `handoff_requested`, `staff_claimed`, `ai_active`, `resolved`.
   - Bàn trực Cán bộ `/conversations` với bố cục Master-Detail 2 cột, polling 8s, tiếp nhận xử lý, gửi phản hồi trực tiếp kèm mẫu câu trả lời nhanh (Canned Replies).

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Changes)

### Backend (FastAPI + SQLAlchemy + PostgreSQL):
1. [`backend/app/modules/assistants/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/models.py):
   - Thêm bảng `AssistantVersionRecord(Base)`: `assistant_id`, `version_number`, `change_summary`, `snapshot_data` (JSON chứa toàn bộ 7 lớp), `created_at`.
2. [`backend/app/modules/assistants/schemas.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/schemas.py):
   - Thêm `AssistantVersionItem`, `AssistantVersionListResponse`, `AssistantRollbackResponse`.
3. [`backend/app/modules/assistants/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/service.py):
   - Phương thức `create_version_snapshot`: Tự động đánh số phiên bản `v1.0`, `v1.1`,... và serialize snapshot.
   - Phương thức `list_assistant_versions`: Lấy danh sách phiên bản theo thứ tự mới nhất trước.
   - Phương thức `rollback_assistant_version`: Khôi phục 7 lớp cấu hình từ snapshot và ghi nhận mốc rollback mới.
   - Hook tự động tạo snapshot khi `update_assistant` hoặc `publish_assistant`.
4. [`backend/app/modules/assistants/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/router.py):
   - Thêm endpoints `GET /{ref}/versions` và `POST /{ref}/versions/{version_id}/rollback`.
5. [`backend/app/modules/knowledge/excel_parser.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/excel_parser.py):
   - Parser đọc file `.xlsx`, `.xls`, `.csv` bằng `openpyxl` / `csv.DictReader`.
   - Nhận diện linh hoạt các cột thực thể và số liệu học phí, điểm chuẩn, chỉ tiêu.
6. [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) & [`router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/router.py):
   - Thêm phương thức `import_facts_from_excel` và `get_collection_facts`.
   - Thêm endpoints `POST /collections/{collection_id}/facts/import-excel` và `GET /collections/{collection_id}/facts`.
7. [`backend/app/modules/conversations/`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/conversations/):
   - `models.py`: Bảng `ConversationThreadRecord` và `ConversationMessageRecord`.
   - `schemas.py`: `ConversationThreadItem`, `ConversationThreadDetail`, `ConversationStatusUpdateRequest`, `ConversationReplyRequest`.
   - `service.py`: `list_threads`, `get_thread_detail`, `update_thread_status`, `send_staff_reply`.
   - `router.py`: Endpoints `GET /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/status`, `POST /conversations/{id}/reply`.
8. [`backend/app/main.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py):
   - Đăng ký router `conversations.router` vào hệ thống tại `/platform/v1alpha1/conversations`.
9. Unit Tests Mới (Pass 100%):
   - [`backend/tests/test_assistant_versions.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_assistant_versions.py): 5 bài test cho version snapshot, listing, rollback, API endpoints.
   - [`backend/tests/test_excel_facts_ingestion.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_excel_facts_ingestion.py): 7 bài test cho excel parser, CSV parser, error handling, service và API router.
   - [`backend/tests/test_conversations_handoff.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_conversations_handoff.py): 8 bài test cho conversation lifecycle, handoff status, staff claim, staff reply, và API endpoints.

---

### Frontend (React 19 + Vite + Tailwind + TanStack Query):
1. [`frontend/src/types/assistants.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/assistants.ts):
   - Định nghĩa `AssistantVersionItem`, `AssistantVersionListResponse`.
2. [`frontend/src/types/knowledge.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/knowledge.ts):
   - Định nghĩa `FactItem`, `CollectionFactsResponse`, `ExcelImportFactsResponse`.
3. [`frontend/src/types/conversations.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/conversations.ts):
   - Định nghĩa `ConversationStatus`, `ConversationMessage`, `ConversationThreadItem`, `ConversationThreadDetail`.
4. [`frontend/src/services/assistants-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/assistants-api.ts):
   - Thêm `getAssistantVersions(ref)` và `rollbackAssistantVersion(ref, versionId)`.
5. [`frontend/src/services/knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts):
   - Thêm `getCollectionFacts(collectionId)` và `importFactsExcel(collectionId, file)`.
6. [`frontend/src/services/conversations-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/conversations-api.ts):
   - Thêm `listConversations`, `getConversationDetail`, `updateConversationStatus`, `replyConversation`.
7. [`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx):
   - Nút **[Lịch sử phiên bản]** trên top toolbar mở Dialog hiển thị danh sách snapshot theo thứ tự thời gian.
   - Huy hiệu phiên bản hiện hành `v1.x` kèm nút **[Khôi phục]** có `ConfirmDialog` xác nhận an toàn.
8. [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx):
   - Thêm tab thứ 4 **"Bảng Biểu & Số Liệu"** (`facts`) vào `TabsList`.
   - Hiển thị bảng số liệu Facts chuẩn định lượng: Thực thể, Phân loại, Tên thuộc tính, Giá trị số liệu, Độ tin cậy (100%), Thời điểm nạp.
   - Nút **[+ Nạp Bảng Biểu Excel/CSV]** mở Dialog chọn tệp và tải lên trực tiếp.
9. [`frontend/src/pages/conversations-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/conversations-page.tsx):
   - Tái thiết kế toàn diện theo kiến trúc Master-Detail 2 cột: Cột trái danh sách hội thoại có bộ lọc trạng thái và tìm kiếm; Cột phải bàn trực cán bộ live.
   - Cơ chế polling 8s cập nhật trạng thái mới nhất; hiển thị huy hiệu cảnh báo khi có câu hỏi cần tiếp quản.
   - Nút **[Tiếp nhận hỗ trợ]**, **[Chuyển lại cho AI]**, **[Đã giải quyết]**.
   - Hộp trả lời cán bộ kèm 4 mẫu câu trả lời nhanh (Canned Replies) hướng dẫn người học tới đúng phòng ban.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

1. **Backend Verification**:
   - `uv run ruff check .`: **0 lỗi**, All checks passed!
   - `uv run --extra dev pytest -v`: **213/213 passed (100%)**, 0 lỗi, 34 warnings (tăng từ 193 lên 213 tests).
2. **Frontend Verification**:
   - `npm run lint`: **130 files checked, 0 lỗi**, No fixes applied!
   - `npm run typecheck`: **0 lỗi** (`tsc --noEmit`).
   - `npm run build`: **Thành công trong 7.69s** (Vite build 2545 modules, sinh ra đầy đủ các chunk).
3. **Mã Hóa Văn Bản (Zero Mojibake)**:
   - 100% tệp mới và chỉnh sửa tuân thủ chuẩn UTF-8 sạch, không lỗi font hay ký tự thay thế.

---

## 4. Đồng Bộ Quy Trình Hệ Thống (`docs/quy_trinh/`)

- [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/02_nap_tri_thuc_minio.md): Bổ sung **Bước 10: Nạp Trực Tiếp Bảng Biểu Số Liệu Excel/CSV (Structured Facts Ingestion)**.
- [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md): Bổ sung **Mục 9: Quản Trị Phiên Bản Trợ Lý AI & Khôi Phục Snapshot (Assistant Versioning & Rollback)** và **Mục 10: Giám Sát Hội Thoại Thời Gian Thực & Bàn Giao Cán Bộ (Live Conversations & Staff Handoff)**.
