# NHẬT KÝ LÀM VIỆC — PHIÊN 312 (2026-10-09)
## Dự Án: QNU.AI Platform & QNU SSO — Trường Đại Học Quy Nhơn
## Chủ Đề: Hoàn Thiện Dứt Điểm Toàn Diện Tích Hợp QNU SSO Giữa Hai Repositories Theo Hướng Production-First

---

### 1. Mục Tiêu Phiên
Giải quyết triệt để và đồng bộ toàn bộ 8 hạng mục tồn đọng của tích hợp QNU SSO giữa hai hệ thống:
1. **Truyền `environment.EnvironmentName` từ `OpenIddictApplicationSeed` sang `QnuAiClientSeed.SeedAsync`**: Lấy runtime environment làm nguồn chân lý (Source of Truth) duy nhất, phân biệt rạch ròi Production vs Development/Testing, kích hoạt fail-fast khi thiếu `PUBLIC_BASE_URL` trong Production.
2. **Frontend `resolveOidcAuthority` bảo mật đa môi trường**: Nhận diện toàn diện các loopback hostnames (`localhost`, `127.0.0.1`, `::1`), loại bỏ dấu gạch chéo cuối (`trailing slash`), cấm HTTP và loopback trong môi trường sản xuất; đồng bộ 5 biến môi trường mẫu trong `frontend/.env.example`.
3. **Chống JWKS Refresh Stampede bằng `asyncio.Lock` và Double-Checked Locking**: Nâng cấp `JwksCacheService` với cơ chế khóa bất đồng bộ, tracking thế hệ (`_refresh_count`), stale window 300s, fail-closed HTTP 503 khi quá hạn và bảo đảm đúng 1 lượt gọi HTTP khi gặp hàng loạt request đồng thời.
4. **Viết test production thật cho Fetch Interceptor (16 Scenarios)**: Đóng gói factory `createAuthFetchInterceptor(deps)` và kiểm thử đầy đủ 16 kịch bản thực tế (relative, same-origin, trusted origin, external, spoofed host, query string, caller auth preserved, headers merged, body preserved, 401 replay body, 5 concurrent 401 calling silent renew once, max retry 1, new token used, zero internal headers, renew failed clean session, caller auth 401 no renew).
5. **Đổi tư duy sang Allow-List cho Production Callback URIs**: Trong `QnuAiClientSeed.cs`, chỉ chấp nhận schema HTTPS với host hợp lệ (loại bỏ toàn bộ `localhost`, `127.0.0.1`, `::1`, `http:`, `ftp:`, custom schemes), cơ chế đối soát (`ReconcileExistingClientAsync`) hoàn toàn idempotent không gọi `UpdateAsync` dư thừa.
6. **Tuân thủ quy chuẩn Biome, TypeScript và Node 24 Native ESM Runner**: Giữ nguyên `tsconfig.json` chuẩn, không nới lỏng `allowImportingTsExtensions`, tạo custom ESM resolver hook (`test-loader.mjs`) giúp Node 24 native test runner giải quyết import TypeScript mượt mà.
7. **Tính nhất quán OIDC Issuer (Issuer Consistency)**: Đồng bộ cấu hình `options.SetIssuer(issuerUri)` trên OpenIddict (`qnu-sso`), `clean_sso_authority` và `verify_iss: True` trên FastAPI backend, và `resolveOidcAuthority` trên Frontend.
8. **Đồng bộ hóa tài liệu tích hợp và bộ nhớ dự án**: Cập nhật `qnu-ai-platform.md` trong `qnu-sso`, cập nhật `PROJECT_CONTEXT.md`, `WORK_LOG.md` và `docs/nhat_ky/README.md`.

---

### 2. Các Thay Đổi Chi Tiết

#### A. Repository `D:\DuAnPhanMem\QLKTX\qnu-sso` (ASP.NET Core 10 / OpenIddict)
1. `src/Infrastructure/DependencyInjection.cs`:
   - Bổ sung cấu hình `options.SetIssuer(issuerUri)` từ `PUBLIC_BASE_URL` hoặc `OpenIddict:Issuer`.
   - Bổ sung guard `hasConfiguredConnectionString && !DesignTimeHostDetection.IsApiDescriptionTool()` bảo đảm không kích hoạt khi chạy EF migration tools.
2. `src/Infrastructure/Data/Seed/OpenIddictApplicationSeed.cs`:
   - Truyền trực tiếp `logger, environment.EnvironmentName, configuration` vào `QnuAiClientSeed.SeedAsync`.
3. `src/Infrastructure/Data/Seed/Clients/QnuAiClientSeed.cs`:
   - Triển khai `IsProductionEnvironment(environment, config)` kiểm tra cả `IHostEnvironment.EnvironmentName` và `ASPNETCORE_ENVIRONMENT`.
   - Triển khai `IsValidProductionCallbackUri(uri)` theo tư duy Allow-List nghiêm ngặt (chỉ chấp nhận HTTPS, loại trừ mọi host loopback và scheme không an toàn).
   - Tối ưu hóa `ReconcileExistingClientAsync` bảo đảm tính idempotent tuyệt đối (sử dụng `HashSet<Uri>.SetEquals` trước khi cập nhật).
4. `tests/Application.UnitTests/Admin/Clients/QnuAiClientDescriptorTests.cs`:
   - Bổ sung 13 unit tests bao phủ các kịch bản môi trường, allow-list callback URI, reconcile idempotency và fail-fast production.
5. `docs/integrations/qnu-ai-platform.md`:
   - Chuẩn hóa tài liệu tích hợp song ngữ / tiếng Việt UTF-8 sạch, cập nhật các endpoint chuẩn (`/connect/logout`, `/connect/revocation`), hướng dẫn cấu hình môi trường và bảng quyền hạn RBAC.

#### B. Repository `D:\DuAnPhanMem\qnu-ai-platform` (FastAPI Backend + React Frontend)
1. `backend/app/modules/auth/sso_validator.py`:
   - Nâng cấp `JwksCacheService` với `asyncio.Lock()`, `_refresh_count` và Double-Checked Locking trong cả `get_keys()` và `get_key_for_kid()`.
   - Bảo đảm an toàn tuyệt đối khi xảy ra HTTP request stampede: hàng loạt worker đồng thời chỉ sinh đúng 1 request ra mạng ngoài.
2. `backend/tests/test_sso_auth.py`:
   - Bổ sung 6 test cases mới kiểm thử:
     - 4 kịch bản concurrent stampede: 10 worker đồng thời khi cache hết TTL, 10 worker gặp unknown kid, stale cache fallback khi lỗi mạng trong stale window, và fail-closed 503 khi vượt quá stale window.
     - 2 kịch bản issuer strict matching: chấp nhận exact issuer, từ chối trailing slash, từ chối subdomain giả mạo và từ chối HTTP.
3. `frontend/src/app/auth/oidc.ts`:
   - Triển khai `resolveOidcAuthority(rawAuthority, fallbackAuthority, isProduction)` và `isLoopbackHostname(hostname)`.
   - Chuẩn hóa loại bỏ trailing slash, cấm HTTP và loopback trong môi trường sản xuất.
4. `frontend/src/app/auth/fetch-interceptor.ts`:
   - Đóng gói factory `createAuthFetchInterceptor(deps)` hỗ trợ Dependency Injection hoàn hảo cho unit test.
   - Giữ nguyên logic bảo vệ an toàn: chỉ inject cho trusted origin + `/platform/`, clone và buffer Request body phục vụ replay sau 401, single-flight silent renew và không gửi header nội bộ.
5. `frontend/src/app/auth/test-loader.mjs`:
   - Tạo custom ESM resolver hook cho Node 24 native runner hỗ trợ nạp các module TypeScript không có đuôi file mà không cần sửa `tsconfig.json`.
6. `frontend/src/app/auth/auth.test.ts`:
   - Bổ sung 16 test cases cho `createAuthFetchInterceptor` và 9 test cases cho `resolveOidcAuthority` / `isLoopbackHostname`.
   - Đạt tổng cộng 46 tests passed 100%.
7. `frontend/.env.example`:
   - Đầy đủ 5 biến môi trường OIDC chuẩn.

---

### 3. Kết Quả Kiểm Thử & Kiểm Định Chất Lượng

1. **Repository `qnu-sso` (.NET 10)**:
   - `Application.UnitTests`: **104/104 PASSED (100%)**.
   - `Domain.UnitTests`: **8/8 PASSED (100%)**.
   - `Infrastructure.IntegrationTests`: **8/8 PASSED (100%)**.
   - Tổng cộng: **120/120 tests PASSED (0 failed, 0 skipped)**.

2. **Repository `qnu-ai-platform` (Backend)**:
   - Pytest `test_sso_auth.py` + `test_permission_contract.py`: **38/38 PASSED (100%)**.
   - `uv run ruff check .`: **All checks passed (0 errors)**.

3. **Repository `qnu-ai-platform` (Frontend)**:
   - Node 24 native tests `src/app/auth/auth.test.ts`: **46/46 PASSED (100%)**.
   - Biome linter / formatter: **Checked, 0 errors**.
   - `npm run build` (Vite build + TypeScript typecheck): **Hoàn thành trong 4.54s, 0 lỗi biên dịch**.
