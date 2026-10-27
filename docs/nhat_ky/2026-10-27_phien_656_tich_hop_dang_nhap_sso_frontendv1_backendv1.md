# Nhật ký phiên 656 — Tích hợp Đăng nhập QNU SSO cho frontendV1 và backendV1

- **Thời gian**: 2026-10-27
- **Mục tiêu**: Tích hợp quy chuẩn xác thực Single Sign-On (QNU SSO, OpenIddict + ASP.NET Core) cho frontendV1 và backendV1, thay thế luồng dev access key; bảo đảm phân tách ranh giới an toàn, token chỉ lưu trong bộ nhớ (in-memory), chống open redirect, xác minh transaction PKCE S256 và bảo đảm kiểm thử hồi quy đầy đủ.
- **Trạng thái**: Hoàn tất triển khai và kiểm thử. Toàn bộ test suite 36/36 PASS, Biome 0 errors / 0 warnings, TypeScript typecheck PASS, backend unit test SSO 7/7 PASS (100%).

---

## 1. Hiện trạng khảo sát & Đối chiếu Contract QNU SSO

1. **Client Registration QNU AI (`qnu-sso`)**:
   - `ClientId`: `qnu-ai-platform`.
   - `ClientType`: `Public` (SPA, không dùng client secret).
   - `GrantTypes`: `authorization_code`, `refresh_token`.
   - `ResponseTypes`: `code` (Authorization Code Flow with PKCE S256 requirement).
   - `Scopes`: `openid profile email roles offline_access ai.api`.
   - `Audience/Resource`: `ai.api`.
2. **Khảo sát Seed & Chênh lệch Origin cổng 3001**:
   - `QnuAiClientSeed.cs` trong `qnu-sso` đang chỉ khai báo redirect cho cổng 3000 và 5173. Cổng phát triển của `frontendV1` là 3001 (`http://localhost:3001/signin-oidc` và `http://127.0.0.1:3001/signin-oidc`).
   - Quyền trong `AiSeedData.cs` của SSO chưa có `ai.workspaces.view` và `ai.workspaces.manage` (trong khi catalog `qnu-ai-permissions.json` của repo AI đã định nghĩa).
   - Đã chuẩn bị sẵn patch/nội dung cập nhật cụ thể cho seed của `qnu-sso` (phân biệt rõ source code seed với DB registration đang chạy).

---

## 2. Các thành phần đã triển khai

### A. FrontendV1 — Quản lý OIDC & Giao thức PKCE (`frontendV1/src/app/auth/v1/oidc.ts`)
- **Tập trung hóa cấu hình OIDC**:
  - `authority`: Phân biệt môi trường phát triển (cho phép loopback HTTP `http://localhost:5000` hoặc `http://127.0.0.1:5000`) và production (bắt buộc HTTPS, cấm trỏ về loopback).
  - `clientId`: `qnu-ai-platform`.
  - `redirectUri`: `${origin}/signin-oidc`.
  - `postLogoutRedirectUri`: `${origin}/sign-in`.
  - `scope`: Bắt buộc chứa `openid` và `ai.api` (chuẩn hóa và deduplicate).
- **An toàn lưu trữ (Zero Token Persistence)**:
  - Cấu hình `userStore`: Dùng `new WebStorageStateStore({ store: new InMemoryWebStorage() })`. Tuyệt đối không lưu access token, refresh token hay id token vào `localStorage` hoặc `sessionStorage`.
  - Cấu hình `stateStore`: Dùng `window.sessionStorage` với namespace riêng `qnu_ai_oidc_txn_` chỉ để lưu các tham số giao dịch tạm thời (state, nonce, code_verifier) qua bước chuyển hướng trình duyệt. Sau khi hoàn tất callback, thư viện tự động dọn sạch.
  - Tắt `automaticSilentRenew` (không dùng iframe ẩn chưa được đăng ký).
- **Chống Open Redirect**:
  - Hàm `sanitizeReturnUrl(returnUrl)` kiểm tra chặt chẽ: chỉ chấp nhận đường dẫn nội bộ bắt đầu bằng `/`, cấm protocol-relative (`//evil.com`), cấm backslash (`/\`), cấm scheme nguy hiểm (`javascript:`, `data:`), và tự động loại trừ các path lặp auth (`/signin-oidc`, `/sign-in`), mặc định trả về `/workspaces`.

### B. Callback Route `/signin-oidc` (`frontendV1/src/routes/signin-oidc.tsx`)
- Được đăng ký trên TanStack Router độc lập, nằm ngoài KTX auth gate, không render `TemplateNotice` để tránh nhầm lẫn bản mẫu.
- **Bảo vệ Re-entrancy / React StrictMode**: Dùng `processedRef` ngăn chặn việc gọi `signinCallback()` hai lần với cùng một `code` (tránh lỗi reuse code của OpenIddict).
- **Xử lý toàn diện các trạng thái**:
  - Trạng thái chờ: Hiển thị spinner và thông báo đang đối soát giao dịch PKCE.
  - Bị từ chối: Nhận diện `error === "access_denied"` từ SSO và hiển thị thông báo thân thiện.
  - Lỗi giao dịch / SSO không sẵn sàng: Hiển thị lỗi rõ ràng cùng nút "Thử đăng nhập lại" và "Về trang chủ".
- **Xác minh kép Token & Actor**:
  - Sau khi `handleSsoCallback()` nhận được access token, nạp token vào `session-token.ts` trong bộ nhớ.
  - Ngay tại callback, gọi `GET /platform/v1alpha1/auth/me` để backendV1 xác minh chữ ký RSA, issuer, audience và trả về actor. Nếu backend từ chối (401/503), token lập tức bị xóa và giao diện dừng lại ở màn hình báo lỗi, không cho phép mở trang bảo vệ.
  - Dọn sạch `code` và `state` khỏi URL history bằng `window.history.replaceState`.
  - Chuyển hướng tới `returnUrl` an toàn.

### C. Cổng đăng nhập & Đăng xuất v1 (`gate.tsx`, `provider.tsx`, `account-menu.tsx`)
- `LoginScreen`: Chuyển sang nút hành động chính "Đăng nhập QNU SSO" kích hoạt `signInWithSso()`. Dev access key được đưa vào mục mở rộng tùy chọn chỉ xuất hiện ở chế độ development (`!import.meta.env.PROD`), tuyệt đối không tự fallback sang dev gate khi SSO lỗi.
- `signOut`: Xóa token bộ nhớ tab hiện tại (`clearAccessToken`), hủy query pending, xóa sạch query cache v1 và mutation cache, sau đó kích hoạt quy trình end-session của SSO (`logoutSso()` trỏ về endpoint logout discovery của SSO).

### D. BackendV1 — Xác minh Token & Ánh xạ Actor (`backendV1/qnu/domains/identity/sso.py`)
- **Thuật toán chữ ký & Audience**: Duy trì allowlist nghiêm ngặt `RS256` và audience `ai.api`. Lỗi JWKS trả về mã lỗi hạ tầng 503 (`sso_unavailable`).
- **Trích xuất Claim linh hoạt**: Hàm `_extract_claims` xử lý cả claim dạng đơn (string) và dạng mảng (list), hỗ trợ cả `role`/`roles` và `permission`/`permissions`.
- **Ánh xạ `user_type` & `role`**: Đọc `user_type` từ claim JWT (giá trị thực như `Student`, `Staff`, `Lecturer`), chuẩn hóa chữ thường thay vì mặc định mọi tài khoản là `staff`. Trích xuất vai trò chính `role` từ danh sách roles hợp lệ.
- **Giữ nguyên `sub`**: Sử dụng chính xác `payload["sub"]` có phân biệt hoa thường làm `actor_id`.

---

## 3. Kết quả kiểm thử & Nghiệm thu

1. **FrontendV1 Unit & Regression Suite (`bun test`)**:
   - `tests/template-boundary.test.ts`: 5/5 passed (bao gồm kiểm tra phân định ranh giới v1, token không bao giờ bị lưu bền vững, và route `routes/signin-oidc` thuộc v1).
   - `tests/v1-contract.test.ts`: 14/14 passed.
   - `tests/v1-session-secret-regression.test.ts`: 7/7 passed.
   - `tests/v1-sso.test.ts`: 10/10 passed (kiểm tra authority HTTPS/loopback, URLs callback, scopes `openid` + `ai.api`, chống open redirect, `InMemoryWebStorage`, actor validation, 401 unauth session isolation, và logout cleanup).
   - **Tổng cộng: 36 passed, 0 failed (100% PASS)**.
2. **Frontend Typecheck & Linter**:
   - `bun ./node_modules/typescript/bin/tsc --noEmit`: 0 errors (PASS).
   - `bun ./node_modules/@biomejs/biome/bin/biome check`: 6 files checked, 0 errors, 0 warnings (PASS).
3. **BackendV1 Test Suite (`pytest`)**:
   - `tests/unit/test_sso.py`: 7 passed in 3.84s (100% PASS).
   - `ruff check`: All checks passed.
   - `ruff format --check`: All formatted.

---

## 4. Các tệp thay đổi

- `frontendV1/package.json`: Bổ sung dependency `"oidc-client-ts": "^3.5.0"`.
- `frontendV1/.env.example`: Bổ sung hướng dẫn các biến môi trường SSO (`VITE_SSO_AUTHORITY`, `VITE_SSO_CLIENT_ID`, `VITE_SSO_REDIRECT_URI`, `VITE_SSO_POST_LOGOUT_REDIRECT_URI`, `VITE_SSO_SCOPE`, `VITE_DEV_AUTH_ENABLED`).
- `frontendV1/README.md`: Cập nhật mô tả luồng xác thực thực tế QNU SSO.
- `frontendV1/src/app/auth/v1/oidc.ts`: Thư viện cấu hình và hàm tiện ích OIDC client (mới).
- `frontendV1/src/app/auth/v1/index.ts`: Re-export các tiện ích OIDC và `isValidActor`.
- `frontendV1/src/app/auth/v1/provider.tsx`: Thêm `signInWithSso`, tích hợp `logoutSso` trong `signOut`.
- `frontendV1/src/app/auth/v1/gate.tsx`: Cập nhật `LoginScreen` với nút "Đăng nhập QNU SSO", bản địa hóa thông báo lỗi SSO.
- `frontendV1/src/routes/signin-oidc.tsx`: Route callback xử lý PKCE exchange và xác minh danh tính backend (mới).
- `frontendV1/src/routes/__root.tsx`: Cho phép `/signin-oidc` đi qua trực tiếp trước auth gate.
- `frontendV1/tests/template-boundary.test.ts`: Thêm `routes/signin-oidc` vào `V1_ROUTE_PREFIXES`.
- `frontendV1/tests/v1-sso.test.ts`: 10 kịch bản kiểm thử toàn diện cho SSO OIDC (mới).
- `backendV1/qnu/domains/identity/sso.py`: Cải tiến trích xuất claim dạng đơn/mảng và mapping `user_type`.
- `backendV1/tests/unit/test_sso.py`: Bổ sung test kiểm thử singular/array roles/permissions và user_type.
- `backendV1/.env.example`: Bổ sung biến và hướng dẫn cấu hình SSO backend.
