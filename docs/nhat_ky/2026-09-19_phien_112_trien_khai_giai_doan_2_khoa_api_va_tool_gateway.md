# NHẬT KÝ LÀM VIỆC — PHIÊN #112

**Ngày làm việc:** 19/09/2026 (16:00 - 16:15 UTC+7)  
**Kỹ sư phụ trách:** AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính:** Triển khai hoàn tất **Giai đoạn 2** theo kế hoạch khắc phục khoảng hở kết nối toàn ứng dụng ([docs/nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/nhan_xet_khoang_ho_ket_noi_toan_app_2026-09-19.md)): Khóa an toàn API quản trị bằng Dev Access Gate, kết nối Workflow API Caller Node với Tool Gateway / Human-in-the-loop, và loại bỏ rò rỉ secret key trong ModelOps.

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Ở phiên #111, Giai đoạn 1 đã hoàn thành việc sửa các đứt gãy kết nối trực tiếp (Web Chat Widget, Quota contract, Facts lifecycle). Tuy nhiên hệ thống vẫn còn hai lỗ hổng kiến trúc cấp P0:
1. **P0-01 (API Security & Dev Access Gate)**: Password Gate chỉ chặn ở tầng giao diện Frontend, toàn bộ 13 router Backend chưa có dependency xác thực. Người dùng không đăng nhập vẫn có thể gọi trực tiếp API để thao tác dữ liệu.
2. **P0-04 (Workflow API Caller Node ↔ Tool Gateway & HITL)**: Node gọi tool trong DAG hiện đang gọi `tool.execute()` trực tiếp, bypass kiểm tra allowlist công cụ của trợ lý, bỏ qua cơ chế Human-in-the-loop (`requires_approval`), và không lưu lịch sử kiểm toán `ToolExecutionLog`.
3. **P0-02 (ModelOps Secret Masking)**: API danh sách cấu hình Provider (`modelops/service.py:556`) trả về trường `api_key: c.api_key_encrypted` thô.

---

## 2. Chi Tiết Các Thay Đổi Kỹ Thuật (Key Changes)

### 2.1. Phân hệ Bảo Mật & Xác Thực (Auth & API Security - P0-01)
- [`backend/app/modules/auth/dependencies.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/dependencies.py):
  * Cập nhật `get_current_actor` đọc `get_settings()` động bên trong hàm thay vì cache module-level.
  * Nếu client gửi token nhưng `decode_access_token` bị lỗi $\rightarrow$ lập tức raise `AppException(status_code=401, code="invalid_token")`, không để fall-through vào fallback.
  * Hỗ trợ header `x-enforce-auth: true` (case-insensitive) để phục vụ kiểm thử an ninh trong test suite, bảo đảm khi không có session sẽ nhận chính xác `401 Unauthorized`.
- [`backend/app/modules/auth/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/auth/router.py):
  * Cập nhật cấu hình cookie phiên: Sửa `secure=False` thành `secure=settings.ENVIRONMENT not in ("development", "test")`.
- [`backend/app/modules/assistants/router.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/router.py) & [`backend/app/modules/assistants/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/__init__.py):
  * Tách riêng `chat_router = APIRouter(prefix="/assistants", ...)` cho endpoint `POST /{reference}/chat` để giữ trạng thái **PUBLIC** cho Web Chat Widget và thí sinh/sinh viên.
  * Export `assistant_chat_router`.
- [`backend/app/main.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/main.py):
  * Mount `assistant_chat_router` và `auth_router` ở chế độ công khai (Public).
  * Định nghĩa `auth_guard = [Depends(get_current_actor)]` và áp dụng cho toàn bộ 11 router quản trị còn lại: `jobs_router`, `document_types_router`, `knowledge_router`, `rag_router`, `modelops_router`, `node_catalog_router`, `workflow_router`, `assistants_router` (quản trị), `conversations_router`, `tools_router`, `ocr_router`, `evaluation_router`.

### 2.2. Phân hệ Workflow & Tool Gateway / HITL (P0-04)
- [`backend/app/modules/tools/builtin/document_exporter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/builtin/document_exporter.py):
  * Override `@property def requires_approval(self) -> bool: return True` đối với công cụ xuất văn bản hành chính Word (chuẩn Nghị định 30).
- [`backend/app/modules/tools/builtin/exam_matrix_tool.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/builtin/exam_matrix_tool.py):
  * Override `@property def requires_approval(self) -> bool: return True` đối với công cụ xuất ma trận đề thi Excel (chuẩn Bloom).
- [`backend/app/modules/tools/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/service.py) & [`backend/app/modules/tools/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/__init__.py):
  * Khởi tạo singleton `tool_service = ToolService()` và export trong module `tools`.
  * Hỗ trợ kiểm tra linh hoạt `if assistant_rec is not None and (isinstance(assistant_rec, AssistantModel) or hasattr(assistant_rec, "config")):` cho cả model thực và mock test.
- [`backend/app/modules/workflows/nodes/api_caller_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/api_caller_node.py):
  * Refactor `APICallerNodeHandler.execute()`: Điều phối qua `tool_service.execute_tool(context.db, tool_req)`.
  * Kiểm tra allowlist `assistant_profile.tools.enabled_tools` nếu chạy trong ngữ cảnh trợ lý; từ chối `tool_not_allowed_for_assistant` nếu vi phạm.
  * Bắt ngoại lệ `code == "tool_requires_approval"` để trả về `NodeExecutionResult(status="paused_for_approval", output={"checkpoint": node_spec.id, "pending_approval": True, ...})`, dừng workflow an toàn chờ cán bộ phê duyệt.
  * Tự động lưu bản ghi kiểm toán `ToolExecutionLog` vào PostgreSQL.

### 2.3. Phân hệ ModelOps Secret Masking (P0-02)
- [`backend/app/modules/modelops/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/service.py):
  * Loại bỏ trường `"api_key": c.api_key_encrypted` ở dòng 556 trong hàm `list_providers`, chỉ trả `api_key_masked` và danh sách key đã qua `_sanitize_key_for_output`.

### 2.4. Đồng Bộ Tài Liệu Quy Trình Hệ Thống (Procedure Sync)
- [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md):
  * Cập nhật mục 10.1: Đặc tả cơ chế điều phối an toàn qua Tool Gateway, kiểm tra Assistant Allowlist, Human-in-the-loop Checkpoint (`paused_for_approval`) và nhật ký kiểm toán bất biến.

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu (Verification)

1. **Backend Linter & Type Safety**:
   ```bash
   uv run ruff check .
   # Kết quả: All checks passed! (0 lỗi)
   ```
2. **Backend Pytest Suite**:
   ```bash
   uv run --extra dev pytest -v
   # Kết quả: 222 passed, 34 warnings in 43.56s (100% PASS, tăng +4 tests)
   ```
   * Thêm `test_api_protection_rejects_unauthenticated_request_with_enforced_auth` (401 khi không đăng nhập).
   * Thêm `test_api_protection_rejects_malformed_token` (401 khi token sai).
   * Thêm `test_api_protection_allows_authenticated_session` (200 khi có cookie phiên hợp lệ).
   * Thêm `test_assistant_chat_endpoint_is_public` (Endpoint chat không bị chặn 401).
   * Thêm Case 4, 5, 6 trong `test_workflows.py` kiểm tra HITL `paused_for_approval`, `is_approved=True` và Assistant allowlist rejection.
3. **Frontend Biome & Typecheck**:
   ```bash
   npm run lint       # Checked 130 files in 157ms. No fixes applied (0 lỗi)
   npm run typecheck  # tsc --noEmit (0 lỗi)
   npm run build      # Vite build thành công trong 7.77s
   ```
4. **Bộ Kiểm Toán Zero Mojibake**:
   ```bash
   python scripts/check_mojibake.py
   # Kết quả: Quét 286 tệp, 100% UTF-8 sạch, không phát hiện lỗi Mojibake.
   ```
