# NHẬT KÝ PHIÊN #111 — TRIỂN KHAI GIAI ĐOẠN 1: KHẮC PHỤC KHOẢNG HỞ KẾT NỐI

> Thời gian: 2026-09-19 15:55 (UTC+7)  
> Mục tiêu: Hiện thực hóa Giai đoạn 1 khắc phục các lỗi đứt gãy kết nối hiển nhiên (P0-06 Chat Widget, P1-14 Contract Quota, P0-05 Facts Lifecycle) theo báo cáo rà soát kết nối toàn ứng dụng `docs/nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md`.

## 1. Phạm vi thực hiện

1. **Khắc phục P0-06 (Web Chat Widget & Embed Snippet)**:
   - Sửa `frontend/public/embed/qnu-chat-widget.js`: Đổi URL gọi API từ `/chat_stream` thành endpoint chuẩn `/chat`, truyền payload `{ message: question, stream: true }`.
   - Chuẩn hóa bóc tách `API_BASE`: Đọc `data-api-base` từ thẻ script và loại bỏ dấu gạch chéo cuối.
   - Bổ sung `data-api-base="${originUrl}"` vào mã nhúng trên trang Channels (`frontend/src/pages/channels-page.tsx`) và trang Chi tiết Trợ lý (`frontend/src/pages/assistant-detail-page.tsx`), bảo đảm widget hoạt động bình thường khi nhúng cross-origin trên cổng tuyển sinh và đào tạo ĐH Quy Nhơn.
2. **Khắc phục P1-14 (Contract Quota API Frontend ↔ Backend)**:
   - Sửa `frontend/src/services/modelops-api.ts`: Đổi URL gọi hạn ngạch từ `/models/quota?tenant_id=...` thành `/modelops/quotas/${tenantId}` khớp với router backend.
   - Bổ sung endpoint alias `GET /platform/v1alpha1/modelops/quota?tenant_id=...` trên `backend/app/modules/modelops/router.py` để tương thích ngược.
3. **Khắc phục P0-05 (Ràng Buộc Vòng Đời Tài Liệu Cho Structured Facts)**:
   - Cập nhật `FactRetriever.lookup_facts` tại `backend/app/modules/rag/facts.py`: Thực hiện `outerjoin` với `KnowledgeDocument`, lọc bỏ 100% facts từ tài liệu ở trạng thái `pending` (chưa duyệt) hoặc `archived` (đã thu hồi).
   - Đồng bộ tài liệu quy trình `docs/quy_trinh/03_hybrid_rag_truy_xuat.md` (Bước 3).
4. **Bổ Sung Test Suite**:
   - Thêm `test_api_get_quota_endpoints` trong `backend/tests/test_modelops.py`.
   - Thêm `test_fact_layer_filters_by_document_approval_lifecycle` trong `backend/tests/test_rag.py`.

## 2. Danh Mục Tệp Thay Đổi

| Tệp | Hành động | Lý do |
| :--- | :--- | :--- |
| [`frontend/public/embed/qnu-chat-widget.js`](../../frontend/public/embed/qnu-chat-widget.js) | Chỉnh sửa | Sửa endpoint `/chat`, body `stream: true`, xử lý SSE và `API_BASE` |
| [`frontend/src/pages/channels-page.tsx`](../../frontend/src/pages/channels-page.tsx) | Chỉnh sửa | Thêm `data-api-base` vào snippet embed script |
| [`frontend/src/pages/assistant-detail-page.tsx`](../../frontend/src/pages/assistant-detail-page.tsx) | Chỉnh sửa | Thêm `data-api-base` vào snippet embed script trong modal |
| [`frontend/src/services/modelops-api.ts`](../../frontend/src/services/modelops-api.ts) | Chỉnh sửa | Sửa URL gọi `/modelops/quotas/${tenantId}` |
| [`backend/app/modules/modelops/router.py`](../../backend/app/modules/modelops/router.py) | Chỉnh sửa | Bổ sung route alias `GET /quota?tenant_id=...` |
| [`backend/app/modules/rag/facts.py`](../../backend/app/modules/rag/facts.py) | Chỉnh sửa | Outerjoin `KnowledgeDocument` và áp dụng lifecycle filter |
| [`backend/tests/test_modelops.py`](../../backend/tests/test_modelops.py) | Chỉnh sửa | Test cả 2 route quota (path param và query param alias) |
| [`backend/tests/test_rag.py`](../../backend/tests/test_rag.py) | Chỉnh sửa | Test outerjoin và lifecycle filter của FactLayer |
| [`docs/quy_trinh/03_hybrid_rag_truy_xuat.md`](../../docs/quy_trinh/03_hybrid_rag_truy_xuat.md) | Chỉnh sửa | Ghi nhận Document Lifecycle Binding trong Bước 3 |
| [`docs/memory/snapshots/2026-09-19_session_111.md`](../../docs/memory/snapshots/2026-09-19_session_111.md) | Tạo mới | Snapshot phiên làm việc #111 |
| [`docs/WORK_LOG.md`](../../docs/WORK_LOG.md) | Cập nhật | Bổ sung phiên #111 vào mục lục |
| [`docs/memory/PROJECT_CONTEXT.md`](../../docs/memory/PROJECT_CONTEXT.md) | Cập nhật | Cập nhật ngữ cảnh dự án và kết quả test mới |

## 3. Kết Quả Kiểm Chứng (Verification)

- **Backend Ruff**: `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**.
- **Backend Pytest**: `uv run --extra dev pytest -v` $\rightarrow$ **218/218 passed (100%)** (+2 test cases mới) trong 56.50s.
- **Frontend Biome**: `npm run lint` $\rightarrow$ **0 lỗi (Checked 130 files)** trong 140ms.
- **Frontend Typecheck**: `npm run typecheck` $\rightarrow$ `tsc --noEmit` **0 lỗi**.
- **Frontend Build**: `npm run build` $\rightarrow$ **Vite v6.4.3 built thành công** trong 8.03s, 0 warnings.
- **Zero Mojibake**: `python scripts/check_mojibake.py` $\rightarrow$ **286/286 tệp UTF-8 sạch 100%**.
