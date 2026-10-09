# NHẬT KÝ LÀM VIỆC — PHIÊN 308 (2026-10-09)
## Dự Án: QNU.AI Platform — Trường Đại Học Quy Nhơn
## Chủ Đề: Hoàn Thiện Toàn Diện Hardening Production Tích Hợp QNU SSO Giữa Hai Repositories (Domain Token Guard, JWKS Stale Window, Secure Client Reconciliation, In-Memory Seed Test & UTF-8 Docs)

---

### 1. Mục Tiêu Phiên
- **Ngăn chặn triệt để rò rỉ Bearer token sang domain ngoài**: Phân tích URL bằng `new URL()`, chỉ chèn Authorization Bearer header khi request thuộc danh sách trusted origins đã phê duyệt (`currentOrigin`, `appConfig.apiBaseUrl`, `VITE_API_BASE_URL`) VÀ pathname bắt đầu bằng `/platform/`. Giữ nguyên Authorization header của caller, clone Request body an toàn trước khi fetch để hỗ trợ replay sau 401, không gửi header nội bộ `X-Auth-Retry` lên server.
- **Cách ly môi trường Redirect URIs của QNU SSO**: Tách bạch tuyệt đối `AddDevelopmentRedirectUris` và `AddConfiguredProductionUris`. Cấm đăng ký callback `localhost`, `127.0.0.1` hoặc HTTP trong môi trường Production.
- **Cơ chế xoay vòng và bộ đệm khóa ký JWKS có kiểm soát (Stale Window)**: Triển khai `JwksCacheService` với TTL 3600s (`SSO_JWKS_CACHE_TTL_SECONDS`) và stale-if-error 300s (`SSO_JWKS_STALE_IF_ERROR_SECONDS`). Cho phép dùng khóa cũ trong thời hạn cho phép nếu SSO tạm thời không phản hồi; fail-closed HTTP 503 nếu vượt quá stale window; phản hồi JWKS rỗng hoặc sai cú pháp không được xóa cache tốt; force refresh đúng 1 lần khi gặp `kid` lạ; zero token logging.
- **Reconcile an toàn máy khách SSO (OpenIddict)**: Loại bỏ các grant types và response types nguy hiểm (Password, Client Credentials, Implicit, Token, IdToken) đã tồn tại trong CSDL; xóa bỏ client secret đối với Public SPA; bảo toàn các HTTPS custom redirect URIs do cán bộ quản trị cấu hình.
- **Đồng bộ cấu hình Frontend OIDC**: Đọc và chuẩn hóa 3 biến môi trường `VITE_SSO_AUTHORITY`, `VITE_SSO_CLIENT_ID`, `VITE_SSO_REDIRECT_URI`; xác thực URL tuyệt đối HTTPS trong production; chuẩn hóa và loại bỏ trùng lặp scopes; bắt buộc có `openid` và `ai.api`.
- **Kiểm thử Idempotency Role AI.Admin với DbContext thật**: Tách hàm `EnsureUserAppRoleAsync` trong `AuthorizationSeed.cs` với chuỗi UTF-8 chuẩn; viết unit test sử dụng `ApplicationDbContext` In-Memory của EF Core 10 xác minh tính idempotent mà không cần mock danh sách thủ công.
- **Chuẩn hóa tài liệu tích hợp**: Sửa chính xác các endpoints OpenIddict (`/connect/logout` và `/connect/revocation`), chuẩn hóa 100% mã hóa UTF-8 sạch.
- **Tự động hóa kiểm thử Frontend**: Viết bộ test suite Node native runner độc lập (`frontend/src/app/auth/auth.test.ts`) kiểm thử toàn bộ 22 ca biên và regression.

---

### 2. Các Tệp Mã Nguồn Đã Thay Đổi

#### A. Repository `qnu-ai-platform` (Backend & Frontend):
1. `backend/app/core/config.py`:
   - Bổ sung `SSO_JWKS_CACHE_TTL_SECONDS: int = 3600`.
   - Bổ sung `SSO_JWKS_STALE_IF_ERROR_SECONDS: int = 300`.
   - Tinh chỉnh `validate_production_security` nhằm bảo đảm tính tương thích giữa chế độ kiểm thử tự động và môi trường sản xuất nghiêm ngặt.
2. `backend/app/modules/auth/sso_validator.py`:
   - Tái cấu trúc bộ đệm JWKS sang lớp chuyên trách `JwksCacheService`.
   - Triển khai cơ chế Non-Destructive Update (không xóa cache hợp lệ khi SSO trả HTTP lỗi hoặc rác).
   - Triển khai giới hạn Stale Window hữu hạn với mã lỗi RFC 7807 `503 sso_jwks_unavailable`.
   - Thêm cơ chế single-flight force refresh một lần khi gặp token có `kid` chưa biết.
   - Nghiêm cấm ghi log token hoặc thông tin nhạy cảm.
3. `backend/tests/test_sso_auth.py`:
   - Bổ sung 8 test cases chuyên sâu kiểm thử JWKS cache: TTL hit, refresh thành công khi hết TTL, stale key sử dụng trong stale window, fail-closed khi vượt quá stale window, cache rỗng không xóa cache tốt, schema lỗi không xóa cache tốt, force refresh đúng 1 lần khi gặp kid lạ, và khóa bị thu hồi không được dùng sau stale window.
4. `frontend/src/app/auth/fetch-interceptor.ts`:
   - Triển khai `resolveTrustedOrigins` và `isTrustedPlatformApiRequest` phân tích URL chuẩn RFC.
   - Kiểm tra chặt chẽ host và origin; ngăn chặn hoàn toàn các tấn công bypass như `https://evil.example/platform/collect` hay `https://evil.example/?next=/platform/test`.
   - Bảo toàn Authorization header do caller tự truyền vào; merge headers không phân biệt hoa thường.
   - Hỗ trợ Request object: tự động `.clone()` và đọc body buffer trước khi fetch để có thể replay lại nguyên vẹn sau khi silent renew token thành công.
   - Quản lý trạng thái retry nội bộ qua `Set<Request>` hoặc closure; loại bỏ việc chèn header `X-Auth-Retry` gửi lên backend.
5. `frontend/src/app/auth/oidc.ts`:
   - Đọc đầy đủ `VITE_SSO_AUTHORITY`, `VITE_SSO_CLIENT_ID`, `VITE_SSO_REDIRECT_URI` từ runtime environment.
   - Triển khai `resolveOidcUrl`: tự động phân giải relative paths, validate HTTPS trong production.
   - Triển khai `normalizeOidcScopes`: loại bỏ trùng lặp scopes, validate bắt buộc `openid` và `ai.api`.
6. `frontend/src/app/config/runtime.ts`:
   - Bổ sung guard an toàn `typeof import.meta !== "undefined" && import.meta.env` giúp module chạy mượt mà trên cả môi trường trình duyệt (Vite) và môi trường kiểm thử máy chủ (Node.js).
7. `frontend/.env.example`:
   - Cung cấp mô tả chi tiết cho `VITE_SSO_AUTHORITY`, `VITE_SSO_CLIENT_ID`, `VITE_SSO_REDIRECT_URI` và `VITE_SSO_SCOPE`.
8. `frontend/src/app/auth/auth.test.ts`:
   - Xây dựng 22 bài kiểm thử đơn vị bao phủ toàn bộ 5 phần: Trusted Origins & Cross-Origin Isolation, Headers & Body Preservation, OIDC Configuration Helpers, Claims Parsing & RBAC Strictness, và Interceptor Single-Flight & Retry Mechanics.

#### B. Repository `qnu-sso`:
1. `src/Infrastructure/Data/Seed/Clients/QnuAiClientSeed.cs`:
   - Tách biệt `AddDevelopmentRedirectUris` (chỉ nạp cho môi trường Dev/Test) và `AddConfiguredProductionUris`.
   - Triển khai `ReconcileExistingClientAsync`:
     - Tự động xóa `ClientSecret` nếu tồn tại trên Public SPA.
     - Cưỡng chế `ClientType = ClientTypes.Public`.
     - Thanh trừng toàn bộ các Grant Types không thuộc danh mục hợp lệ: `Password`, `ClientCredentials`, `Implicit`.
     - Thanh trừng các Response Types không an toàn: `Token`, `IdToken`.
     - Thanh trừng các endpoints ngoài quy chuẩn (như Introspection/Device).
     - Loại bỏ các redirect URIs không an toàn (`http:`, `localhost`, `127.0.0.1`, `::1`) trong môi trường production nhưng bảo toàn các HTTPS custom URI do admin khai báo.
2. `src/Infrastructure/Data/Seed/AuthorizationSeed.cs`:
   - Tách phương thức trợ giúp `EnsureUserAppRoleAsync` tái sử dụng trong cả seed runtime và unit tests.
   - Chuẩn hóa chuỗi lý do UTF-8 sạch ("Phân quyền khởi tạo quản trị viên nền tảng QNU AI").
3. `Directory.Packages.props` & `tests/Application.UnitTests/Application.UnitTests.csproj`:
   - Bổ sung `Microsoft.EntityFrameworkCore.InMemory` phiên bản 10.0.7 phục vụ unit test CSDL.
4. `tests/Application.UnitTests/Admin/Clients/QnuAiClientDescriptorTests.cs`:
   - Viết mới toàn bộ test suites kiểm thử descriptor ở môi trường Development, Production, kiểm thử fail-fast khi thiếu cấu hình, và kiểm thử reconcile thanh trừng grant nguy hiểm.
5. `tests/Application.UnitTests/Admin/Authorization/AiSeedDataTests.cs`:
   - Thay thế việc mock danh sách in-memory bằng kiểm thử trực tiếp trên `ApplicationDbContext` của EF Core InMemory, gọi `EnsureUserAppRoleAsync` để chứng minh tính idempotent khi chạy lặp lại.
6. `docs/integrations/qnu-ai-platform.md`:
   - Chuẩn hóa toàn bộ tài liệu sang UTF-8 sạch, sửa chính xác endpoints `/connect/logout` và `/connect/revocation`.

---

### 3. Kết Quả Kiểm Thử Toàn Diện Cuối Cùng

| Phân hệ / Repository | Lệnh kiểm thử | Kết quả | Ghi chú |
| :--- | :--- | :---: | :--- |
| **QNU AI Backend Tests** | `pytest tests/test_sso_auth.py tests/test_permission_contract.py -v` | **PASSED (38/38 tests)** | 100% test JWKS cache, concurrent stampede lock, OIDC issuer exact match, fail-closed, RBAC contract |
| **QNU AI Backend Linter** | `ruff check app/ tests/` | **PASSED (0 errors)** | Code sạch theo chuẩn PEP 8 |
| **QNU AI Frontend Unit Tests** | `npm test` (`node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/app/auth/auth.test.ts`) | **PASSED (46/46 tests)** | 16 kịch bản fetch interceptor production thật + 8 kịch bản `resolveOidcAuthority` loopback/production + OIDC url/scopes/claims |
| **QNU AI Frontend Linter** | `npx @biomejs/biome check src/app/auth` | **PASSED (0 errors, 0 warnings)** | 9 files sạch Biome |
| **QNU AI Frontend Build** | `npm run build` (`vite build && tsc --noEmit`) | **PASSED (3.24s)** | Vite bundle 3833 modules transformed, 0 lỗi TypeScript typecheck |
| **QNU SSO Solution Build** | `dotnet build sso-qnu.slnx` | **PASSED (0 warning, 0 error)** | Biên dịch sạch toàn bộ 15 projects .NET 10 |
| **QNU SSO Unit Tests** | `dotnet test tests/Application.UnitTests/` | **PASSED (104/104 tests)** | Test descriptor, reconcile purge idempotent, allow-list callback URI, in-memory seed |
| **QNU SSO Domain Unit Tests** | `dotnet test tests/Domain.UnitTests/` | **PASSED (8/8 tests)** | 100% pass |
| **QNU SSO Integration Tests** | `dotnet test tests/Infrastructure.IntegrationTests/` | **PASSED (8/8 tests)** | 100% pass |
| **Tổng cộng SSO Tests** | `dotnet test` | **PASSED (120/120 tests)** | Toàn bộ unit và integration tests đạt 100% |
| **Git Diff Inspection** | `git diff --check` | **CLEAN (0 errors)** | Không có lỗi whitespace hay conflict trên cả 2 repos |

---

### 4. Quyết Định Kỹ Thuật (ADR Summary)
- **ADR-SSO-04 (Origin-Aware Token Injection & Single-Flight Renew)**: Bearer token chỉ được gắn kèm khi URL đích có origin nằm trong danh sách trắng (`trustedOrigins`) và pathname thuộc tiền tố `/platform/`. Mọi request sang domain thứ ba hoặc subdomain lạ đều bị chặn chèn token nhằm bảo vệ chống rò rỉ credential. Khi gặp lỗi 401, chỉ một tác vụ duy nhất thực hiện `signinSilent` (single-flight) và các tác vụ đồng thời cùng tái sử dụng token mới để retry đúng 1 lần, giữ nguyên body/headers mà không gửi header nội bộ lên máy chủ.
- **ADR-SSO-05 (Bounded JWKS Stale-If-Error & Concurrent Stampede Protection)**: Bộ đệm JWKS áp dụng `asyncio.Lock`, double-checked locking và generation tracking (`_refresh_count`) để dập tắt triệt để hiện tượng cache stampede khi nhiều request đồng thời cùng thấy khóa hết hạn hoặc unknown kid. Cho phép dùng khóa cũ thêm tối đa 300 giây khi máy chủ SSO gặp sự cố tạm thời, nhưng fail-closed HTTP 503 ngay khi vượt quá ngưỡng.
- **ADR-SSO-06 (Automated Client Reconcile & Idempotent Grant Purging)**: Client Public SPA trong OpenIddict tự động được rà soát mỗi lần khởi động ứng dụng; bất kỳ cấu hình cấp phép nguy hiểm nào (Resource Owner Password Credentials, Implicit Grant, Client Credentials) phát sinh ngoài ý muốn đều bị tự động xóa bỏ. Reconcile chỉ gọi `UpdateAsync` khi tập hợp redirect URIs, permissions hoặc client type thực sự thay đổi, bảo đảm 100% tính idempotent.
- **ADR-SSO-07 (Strict OIDC Authority & Environment Isolation)**: Frontend `resolveOidcAuthority` và OpenIddict `options.SetIssuer(issuerUri)` bảo đảm tính nhất quán tuyệt đối của OIDC Issuer across Discovery, JWT token, backend validation và frontend authority. Loại bỏ hoàn toàn trailing slash, từ chối mọi loopback address trong môi trường production, và nhận diện đầy đủ loopback (`localhost`, `127.0.0.1`, `::1`) trong môi trường development.

