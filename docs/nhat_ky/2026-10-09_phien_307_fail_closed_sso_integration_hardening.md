# NHẬT KÝ LÀM VIỆC — PHIÊN 307 (2026-10-09)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
## Chủ Đề: Hoàn Thiện Tích Hợp QNU SSO Giữa Hai Repositories Theo Nguyên Tắc Fail-Closed, Validate Issuer/Audience & RBAC Least-Privilege

---

### 1. Mục Tiêu Phiên
- Sửa lỗi P0: Production cho phép anonymous dev admin (cưỡng chế HTTP 401 khi không có token trong production, tắt hoàn toàn Dev Access Gate khi `DEV_AUTH_ENABLED=false`).
- Validate OIDC JWT chuẩn xác: kiểm tra chữ ký JWKS, `exp`, `nbf`, `iss == clean_sso_authority`, `aud == "ai.api"`, thuật toán cố định `RS256`, cấm `verify_aud=False`, fail-closed không fallback UserInfo khi JWT lỗi.
- Xóa bỏ toàn bộ cơ chế tự cấp quyền: không cấp default permissions theo `user_type`, không dùng substring `admin`, bắt buộc có role `AI.*` và permission `ai.access.read` (trả 403 RFC 7807 nếu thiếu), cấm wildcard `*`.
- Chuẩn hóa semantic RBAC: exact match, `ai.access.admin` / `AI.Admin` cho `ai.*`, `ai.access.manage` không phải wildcard, `ai.access.read` không mở rộng.
- Đồng bộ danh mục permissions: thay thế toàn bộ `.edit` thành `.update` (`ai.assistants.update`, `ai.knowledge.update`) và thiết lập Contract Test tự động với `qnu-ai-permissions.json`.
- Bảo vệ token phía Frontend: chuyển `oidc-client-ts` sang `sessionStorage`, xóa bỏ token đọc trực tiếp từ `localStorage`, bảo toàn headers khi nhận `Request` object, xử lý single-flight silent renew và retry đúng 1 lần khi gặp HTTP 401.
- Đồng bộ `qnu-sso`: Client seed an toàn (kiểm tra `Uri`, fail-fast production, hỗ trợ cập nhật idempotent không ghi đè cấu hình admin), Docker Compose không truyền chuỗi rỗng, hoàn thiện bootstrap `AI.Admin` cho quản trị viên hệ thống.

---

### 2. Các Tệp Mã Nguồn Đã Thay Đổi

#### A. Repository `qnu-ai-platform`:
1. `backend/app/core/config.py`:
   - Thêm `SSO_ALLOWED_ALGORITHMS = ["RS256"]`.
   - Cập nhật `validate_production_security`: bắt buộc `SSO_ENABLED=True`, `DEV_AUTH_ENABLED=False`, `SSO_AUTHORITY` phải là HTTPS, `SSO_AUDIENCE` không được rỗng.
2. `backend/app/modules/auth/dependencies.py`:
   - Sửa P0 anonymous admin: request không token trong production luôn trả HTTP 401 `unauthorized`.
   - Dev admin actor chỉ được tạo khi: `ENVIRONMENT in ("development", "test") and DEV_AUTH_ENABLED is True and not enforce_auth`.
   - Production không decode cookie `qnu_session` và không fallback sang local dev JWT.
3. `backend/app/modules/auth/router.py`:
   - Endpoint `/auth/login` trả HTTP 403 `dev_auth_disabled` khi `DEV_AUTH_ENABLED=False` hoặc trong production.
   - Endpoint `/auth/me` không fallback local JWT trong production.
4. `backend/app/modules/auth/schemas.py`:
   - Chuẩn hóa semantic `AuthActor.has_permission`: exact match hoặc `AI.Admin`/`ai.access.admin` đối với `ai.*`.
   - Loại bỏ wildcard `*`, loại bỏ bypass generic `admin`/`administrator`/`super_admin`.
5. `backend/app/modules/auth/sso_validator.py`:
   - Fail-closed JWT validation: xác thực chữ ký JWKS, `iss == clean_sso_authority`, `aud == SSO_AUDIENCE`, `alg in SSO_ALLOWED_ALGORITHMS`.
   - Opaque token chỉ chấp nhận khi scope chứa `ai.api`.
   - Kiểm tra điều kiện tiên quyết: ít nhất một role bắt đầu bằng `AI.` và permission `ai.access.read`; nếu thiếu trả 403 RFC 7807.
   - Tuyệt đối không log nội dung access token.
6. Đồng bộ permission names (`.edit` → `.update`):
   - `backend/app/modules/assistants/router.py`: `ai.assistants.update`
   - `backend/app/modules/knowledge/router.py`: `ai.knowledge.update`
   - `backend/app/modules/jobs/router.py`: `ai.knowledge.update`
   - `backend/app/modules/documents/router.py`: `ai.knowledge.update`
   - `backend/tests/test_publishing_v2_hardening.py`: `ai.knowledge.update`
7. Contract Test & Unit Tests:
   - `backend/tests/test_permission_contract.py`: Kiểm tra AST scan các literal `require_permission(...)` đối soát với `qnu-ai-permissions.json`.
   - `backend/tests/test_sso_auth.py`: 24 test cases bao phủ toàn diện Section 1, 2, 3, 4.
   - `backend/tests/test_auth.py`: Kiểm thử login dev gate bị tắt và role `AI.Admin`.
8. Frontend:
   - `frontend/src/app/auth/oidc.ts`: `userStore` dùng `sessionStorage`, xóa `localStorage` direct read, xóa quyền mặc định tự cấp, xóa substring `admin`.
   - `frontend/src/app/auth/fetch-interceptor.ts`: Bảo toàn headers từ `Request` object, giữ nguyên `Authorization`, single-flight silent renew, retry 1 lần với anti-loop guard.
   - `frontend/src/rbac/context.tsx`: Cập nhật hàm `can()` tuân thủ exact match và `AI.Admin`/`ai.access.admin`.

#### B. Repository `qnu-sso`:
1. `src/Infrastructure/Data/Seed/Clients/QnuAiClientSeed.cs`:
   - Bổ sung `ResolvePublicBaseUri`: xử lý null/empty/whitespace, fail-fast production, chuẩn hóa qua `Uri`.
   - Bổ sung `ReconcileExistingClientAsync`: cập nhật idempotent cho client đã tồn tại, đồng bộ 12 endpoints/scopes, bảo toàn custom URIs của admin, không tạo secret cho public SPA.
2. `src/Infrastructure/Data/Seed/AuthorizationSeed.cs`:
   - Hoàn thiện bootstrap `AI.Admin` cho `adminUsers` (`administrator@localhost`, `DefaultAdministratorEmail`).
   - Tạo `SsoUserAppRole` với lý do rõ ràng, kiểm tra trùng lặp idempotent.
3. `docker-compose.yml`:
   - Sửa `QnuAi__PublicBaseUrl: ${QNU_AI_PUBLIC_BASE_URL:-https://ai.qnu.edu.vn}` tránh truyền chuỗi rỗng.
4. Unit Tests:
   - `tests/Application.UnitTests/Admin/Clients/QnuAiClientDescriptorTests.cs`: 14 tests bao phủ validation base URL và reconcile existing client.
   - `tests/Application.UnitTests/Admin/Authorization/AiSeedDataTests.cs`: Bổ sung test kiểm chứng tính idempotent khi bootstrap `AI.Admin`.
5. Tài liệu:
   - `docs/integrations/qnu-ai-platform.md`: Chuẩn hóa UTF-8, dọn dẹp mojibake, checklist `[ ]` cho các bước chưa kiểm chứng thực địa.

---

### 3. Kết Quả Kiểm Thử Thực Tế

1. **`qnu-ai-platform/backend`**:
   - `ruff check app tests`: **All checks passed! (0 lỗi)**
   - `pytest tests/test_auth.py tests/test_sso_auth.py tests/test_permission_contract.py`: **34 passed, 100%**
2. **`qnu-ai-platform/frontend`**:
   - `npx @biomejs/biome check`: **Checked 3 files, 0 errors**
   - `npm run build`: **Vite build + TypeScript tsc --noEmit hoàn thành thành công (0 lỗi biên dịch)**
3. **`qnu-sso`**:
   - `dotnet build sso-qnu.slnx`: **Build succeeded. 0 Warning(s), 0 Error(s)**
   - `dotnet test tests/Application.UnitTests/Application.UnitTests.csproj`: **107 passed, 0 failed**
   - `dotnet test tests/Domain.UnitTests/Domain.UnitTests.csproj`: **8 passed, 0 failed**
   - `dotnet test tests/Infrastructure.IntegrationTests/Infrastructure.IntegrationTests.csproj`: **8 passed, 0 failed**
   - *Lưu ý về Functional Tests*: `Application.FunctionalTests` phụ thuộc Docker engine/Aspire host. Do Docker daemon trên máy đang offline, các bài test container tạm thời chưa chạy được và được ghi nhận đúng thực tế.

---

### 4. Ma Trận Role → Permission Sau Khi Sửa

| Role | Permissions Được Cấp | Ghi Chú |
| :--- | :--- | :--- |
| **`AI.User`** | `ai.access.read`, `ai.chat.access`, `ai.chat.export`, `ai.assistants.view`, `ai.knowledge.view` | Người dùng cơ bản, không có quyền tạo/sửa/xóa tài liệu hoặc trợ lý |
| **`AI.ContentManager`** | 12 permissions: `ai.access.read`, `ai.chat.*`, `ai.assistants.view/create/update/publish`, `ai.knowledge.view/create/upload/update/sync`, `ai.facts.manage` | Quản lý nội dung, không có quyền xóa trợ lý (`ai.assistants.delete`) hoặc quản lý model (`ai.models.manage`) |
| **`AI.ModelOpsAdmin`** | 6 permissions: `ai.access.read`, `ai.models.view`, `ai.models.manage`, `ai.evaluations.view`, `ai.evaluations.run`, `ai.audit.view` | Quản lý nhà cung cấp và mô hình, không có quyền sửa/xóa kho tri thức |
| **`AI.Admin`** | Toàn bộ 27 permissions `ai.*` | Quản trị viên toàn hệ thống QNU AI Platform |
