# Nhật Ký Phiên Làm Việc #97: Xử Lý Triệt Để Các Vấn Đề Còn Lại (P0 & P1 Remediation)

- **Thời gian**: 2026-09-18 20:55 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Thực thi toàn diện kế hoạch 4 giai đoạn xử lý các điểm P0 và P1 còn tồn đọng được nêu trong báo cáo review mã nguồn [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md).

---

## 1. Chi Tiết Các Hạng Mục Kỹ Thuật Đã Triển Khai

### 1.1. P0.7 — Chốt chặn Trích dẫn Nghiêm ngặt (Strict Citation Guardrail)
- **Tệp chỉnh sửa**: [`backend/app/modules/rag/citation_guard.py`](../../backend/app/modules/rag/citation_guard.py) & [`backend/app/modules/rag/service.py`](../../backend/app/modules/rag/service.py).
- **Giải pháp**:
  - Bổ sung tập từ dừng học thuật tiếng Việt `ACADEMIC_STOPWORDS` (`sinh viên`, `quy nhơn`, `đào tạo`, `tối đa` vs `tối thiểu`...) nhằm loại trừ việc các từ phổ thông này tạo ra false-positive lexical overlap.
  - Xử lý an toàn khi `cite.quote is None`.
  - Loại bỏ hoàn toàn nhánh fallback `citations[:2]` — khi không có citation nào vượt qua kiểm định bằng chứng, trả về mảng rỗng `[]` tuyệt đối và đánh dấu `status = "insufficient_context"`.
  - Bổ sung test kiểm thử: `test_citation_guard_strict_filtering_zero_false_positive` trong [`backend/tests/test_rag.py`](../../backend/tests/test_rag.py).

### 1.2. P0.2 — Xóa Bỏ Ground-Truth Fallback Trong Evaluation
- **Tệp chỉnh sửa**: [`backend/app/modules/evaluation/service.py`](../../backend/app/modules/evaluation/service.py).
- **Giải pháp**:
  - Xóa bỏ hoàn toàn 100% các dòng code tự gán `actual_answer = ground_truth` và chèn citation giả mạo khi RAG/Chat trả về rỗng hoặc từ chối.
  - Ghi nhận trung thực kết quả thực thi runtime (`actual_answer = actual_answer or ""`).
  - Bổ sung test âm: `test_evaluation_service_run_failed_rag_honest_rejection` trong [`backend/tests/test_evaluation.py`](../../backend/tests/test_evaluation.py).

### 1.3. P1.5 — Phân Giải Phiên Bản Workflow Bất Biến Fail-Closed
- **Tệp chỉnh sửa**: [`backend/app/modules/workflows/service.py`](../../backend/app/modules/workflows/service.py).
- **Giải pháp**:
  - Trong cả 2 hàm `execute()` và `resume()`, khi `workflow_version_id` được yêu cầu mà không tìm thấy bản ghi tương ứng trong bảng `workflow_versions`, hệ thống ném ngoại lệ HTTP 404 `workflow_version_not_found` thay vì âm thầm fail-open sang bản nháp mutable.
  - Bổ sung test: `test_workflow_execution_fail_closed_on_missing_version` trong [`backend/tests/test_workflows.py`](../../backend/tests/test_workflows.py).

### 1.4. P0.5 — Dense Retrieval Lọc Chặt Lifecycle Status, Tenant & Workspace
- **Tệp chỉnh sửa**: [`backend/app/modules/rag/vector_indexer.py`](../../backend/app/modules/rag/vector_indexer.py) & [`backend/app/modules/rag/retriever.py`](../../backend/app/modules/rag/retriever.py).
- **Giải pháp**:
  - Payload khi lập chỉ mục Qdrant bổ sung: `tenant_id`, `workspace_id`, `document_status`, `is_retrievable`.
  - Hàm `search_dense()` áp dụng bộ lọc `must` tenant/workspace và `must_not` đối với các tài liệu có `is_retrievable=False` hoặc trạng thái `pending`, `archived`, `rejected`, `failed`, `processing`.
  - Đồng bộ `tenant_id` xuyên suốt cả sparse FTS và dense search.

### 1.5. P1.3 — Dynamic Fallback Model & ModelOps Runtime Policy
- **Tệp chỉnh sửa**: [`backend/app/modules/rag/schemas.py`](../../backend/app/modules/rag/schemas.py), [`backend/app/modules/workflows/nodes/rag_answer_node.py`](../../backend/app/modules/workflows/nodes/rag_answer_node.py), [`backend/app/modules/rag/service.py`](../../backend/app/modules/rag/service.py).
- **Giải pháp**:
  - Bổ sung `fallback_model` và `tenant_id` vào `AskRequest`.
  - Node RAG trong Workflow DAG chuyển tiếp `fallback_model` từ cấu hình Trợ lý xuống RAG Service.
  - Khi primary model thất bại, `rag_service.ask()` tự động thử sinh phản hồi qua `fallback_model` trước khi rơi vào raw fallback.
  - Bổ sung test: `test_rag_ask_dynamic_fallback_model` trong [`backend/tests/test_rag.py`](../../backend/tests/test_rag.py).

### 1.6. P1.4 — Phân Vùng Semantic Cache Theo Tenant
- **Tệp chỉnh sửa**: [`backend/app/core/redis.py`](../../backend/app/core/redis.py) & [`backend/app/modules/rag/service.py`](../../backend/app/modules/rag/service.py).
- **Giải pháp**:
  - Định dạng key cache Redis nâng cấp thành `rag:cache:{tenant_id}:{collection_id}:{model}:{h}`.
  - Hỗ trợ xóa cache linh hoạt theo collection và tenant qua wildcard pattern scanning.

### 1.7. P0.6 — Triệt Tiêu Approval Bypass & Chốt Chặn Tool Gateway
- **Tệp chỉnh sửa**: [`backend/app/modules/assistants/service.py`](../../backend/app/modules/assistants/service.py) & [`backend/app/modules/tools/service.py`](../../backend/app/modules/tools/service.py).
- **Giải pháp**:
  - Trong luồng chat trợ lý, cờ `is_approved` được ép cứng thành `False` từ server, ngăn chặn người dùng tự chèn cờ duyệt.
  - Trong `execute_tool()`, hệ thống kiểm tra danh sách `enabled_tools` được phép của Assistant và kiểm tra cờ duyệt HITL cho các công cụ có `requires_approval=True`.
  - Bổ sung test: `test_tool_service_assistant_allowlist_enforcement` và `test_tool_service_requires_approval_enforcement` trong [`backend/tests/test_tools.py`](../../backend/tests/test_tools.py).

### 1.8. Cổng Truy Cập Nhà Phát Triển Phía Server (Dev Access Gate)
- **Tệp tạo mới**: [`backend/app/modules/auth/`](../../backend/app/modules/auth/) (`schemas.py`, `dependencies.py`, `router.py`, `__init__.py`) & [`backend/tests/test_auth.py`](../../backend/tests/test_auth.py).
- **Giải pháp**:
  - Cung cấp API `/platform/v1alpha1/auth/login`, `/logout`, `/me`.
  - Xác thực mật khẩu với biến môi trường `DEV_ACCESS_PASSWORD` thông qua `hmac.compare_digest`.
  - Cấp phát cookie bảo mật `qnu_session` với các cờ `HttpOnly=True`, `SameSite="Lax"`.
  - Dependency `get_current_actor` cung cấp principal tin cậy (`role=admin`, `tenant_qnu`, `workspace_qnu`).

### 1.9. P0.1 & P1.2 — Lưu Trữ Tệp Gốc & Tự Hồi Phục Qdrant Trong Seeder
- **Tệp chỉnh sửa**: [`backend/app/modules/knowledge/seeder.py`](../../backend/app/modules/knowledge/seeder.py) & [`backend/app/modules/rag/vector_indexer.py`](../../backend/app/modules/rag/vector_indexer.py).
- **Giải pháp**:
  - Viết 2 hàm tiện ích tái sử dụng: `_ensure_seed_storage()` (lưu file raw bytes lên `storage_service`) và `_ensure_qdrant_points()` (tự động đếm point qua `vector_indexer.count_points()`, nếu = 0 sẽ re-index lại chunks từ CSDL).
  - Tích hợp 2 hàm tiện ích này vào toàn bộ 5 hàm seeder tri thức chuẩn của ĐH Quy Nhơn (Quy chế học vụ, NĐ 30, Tuyển sinh, Thư viện, Ngân hàng câu hỏi).

---

## 2. Kết Quả Kiểm Thử Toàn Diện

- **Backend Linting**:
  ```bash
  uv run ruff check .
  # Kết quả: All checks passed! (0 errors)
  ```
- **Backend Test Suite**:
  ```bash
  uv run --extra dev pytest -v
  # Kết quả: 182 passed, 0 failed, 19 warnings in 86.13s (100% pass)
  ```
- **Frontend Linting & Typecheck**:
  ```bash
  npm run lint       # Checked 124 files, 0 errors
  npm run typecheck  # tsc --noEmit, 0 errors
  npm run build      # built in 12.52s, 0 errors
  ```

---

## 3. Đồng Bộ Tài Liệu Quy Trình
- Đã đồng bộ chi tiết kỹ thuật vào [`docs/quy_trinh/03_hybrid_rag_truy_xuat.md`](../quy_trinh/03_hybrid_rag_truy_xuat.md) (Lifecycle filter, Tenant Semantic Cache, Strict Citation Guard).
- Đã đồng bộ Mục 8.4 vào [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md) (Dev Access Gate & Server-side Session Security).
- Đã cập nhật trạng thái RESOLVED cho toàn bộ các mục P0/P1 tại [`docs/nhan_xet_sau_cai_thien_platform_2026-09-18.md`](../nhan_xet_sau_cai_thien_platform_2026-09-18.md).
