# NHẬT KÝ LÀM VIỆC — 2026-09-19 (Phiên #132)
# Triển Khai Giai Đoạn E: Trust Boundary, Dev Access Gate & HITL Approval

## 1. Thời Gian & Mục Tiêu
- **Thời gian**: 2026-09-19 23:30 (UTC+7)
- **Mục tiêu chính**: Triển khai Giai đoạn E theo kế hoạch [`docs/ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md`](../ke_hoach/08_huong_dan_cai_thien_code_tang_diem_danh_gia.md):
  1. Chuẩn hóa Server-Signed Session Cookie (`qnu_session`) với đầy đủ claims: `actor_id`, `display_name`, `role`, `tenant_id`, `workspace_id`, `session_version`.
  2. Mở rộng `WorkflowApprovalRequest` với 4 cột mới: `tool_name`, `payload_hash` (SHA-256), `requested_by`, `expires_at`.
  3. Củng cố `ToolService.execute_tool`: Triệt tiêu hoàn toàn lỗ hổng bypass `is_approved: true` trong request body. Side-effect tool chỉ chạy khi consume atomically (`status = "consumed"`) một approval hợp lệ có payload hash khớp trong CSDL (chống replay attack).
  4. Viết test suite mới `backend/tests/test_trust_boundary_and_hitl.py` và bảo đảm toàn bộ backend test pass 100%, 0 warnings, linter 0 lỗi.

## 2. Thay Đổi Kỹ Thuật (Key Changes)
- **Database Model & Migration**:
  - [`backend/app/modules/workflows/models.py`](../../backend/app/modules/workflows/models.py): Bổ sung 4 cột mới vào model `WorkflowApprovalRequest`: `tool_name` (VARCHAR(100), index), `payload_hash` (VARCHAR(64), index), `requested_by` (VARCHAR(128)), và `expires_at` (DateTime, index).
  - [`backend/alembic/versions/20260919_approval_payload_hash.py`](../../backend/alembic/versions/20260919_approval_payload_hash.py): Migration nâng cấp schema CSDL. Chạy `alembic upgrade head` thành công; `alembic check` trả về 0 diff.
- **Authentication & Claims**:
  - [`backend/app/modules/auth/schemas.py`](../../backend/app/modules/auth/schemas.py): Mở rộng `AuthActor` thêm `actor_id`, `display_name`, `session_version`.
  - [`backend/app/modules/auth/router.py`](../../backend/app/modules/auth/router.py): Nâng cấp endpoint `login` và `get_current_user` để phát hành và giải mã JWT token với đầy đủ các claims bảo mật.
  - [`backend/app/modules/auth/dependencies.py`](../../backend/app/modules/auth/dependencies.py): Cập nhật `get_current_actor` đọc `actor_id`, `display_name`, `session_version` từ JWT token.
- **Tool Execution & HITL Enforcement**:
  - [`backend/app/modules/tools/schemas.py`](../../backend/app/modules/tools/schemas.py): Thêm trường `approval_id: str | None` vào `ToolExecuteRequest`.
  - [`backend/app/modules/tools/service.py`](../../backend/app/modules/tools/service.py):
    * Loại bỏ kiểm tra cờ client `is_approved: true`.
    * Bắt buộc phải có `approval_id` trong DB với `status == "approved"`, `expires_at` còn hiệu lực.
    * Đối soát SHA-256 `payload_hash` giữa tham số thực tế và tham số đã duyệt (`approval_payload_mismatch`).
    * **Atomic Consumption**: Ngay khi tool thực thi thành công, chuyển trạng thái `approval_rec.status = "consumed"` và `commit()`. Nếu bị gọi lại, từ chối với `approval_already_consumed` (status 409).
- **Workflow Approval Enhancements**:
  - [`backend/app/modules/workflows/schemas.py`](../../backend/app/modules/workflows/schemas.py): Bổ sung `tool_name`, `payload_hash`, `requested_by`, `expires_at` vào `WorkflowApprovalResponse`.
  - [`backend/app/modules/workflows/service.py`](../../backend/app/modules/workflows/service.py):
    * `_create_approval_request`: Tự động băm SHA-256 các tham số của node/tool (dùng `ensure_ascii=False`) và gán `expires_at` mặc định 24h.
    * `decide_approval`: Bổ sung kiểm tra hết hạn `expires_at` (hỗ trợ cả timezone-aware lẫn naive UTC).
- **Testing**:
  - [`backend/tests/test_trust_boundary_and_hitl.py`](../../backend/tests/test_trust_boundary_and_hitl.py): 8 test cases mới phủ toàn diện: actor claims, rejection khi thiếu approval, bypass attempts bị chặn, pending rejection, hash mismatch, expired rejection, atomic consumption và replay rejection.
  - [`backend/tests/test_tools.py`](../../backend/tests/test_tools.py): Đồng bộ các test case có `requires_approval` sang mô hình `approval_id` và payload hash.

## 3. Kết Quả Kiểm Thử (Verification)
- **Backend Lint**: `uv run ruff check .` -> 0 errors.
- **Backend Pytest**: `uv run --extra dev pytest -v` -> **271 passed in 50.44s** (100% PASS, 0 warnings, 0 regressions).
- **Frontend Lint**: `npm run lint` -> Checked 164 files, 0 errors.
- **Frontend Typecheck**: `npm run typecheck` -> 0 errors.
- **Frontend Build**: `npm run build` -> 2575 modules transformed, built in 9.38s.
