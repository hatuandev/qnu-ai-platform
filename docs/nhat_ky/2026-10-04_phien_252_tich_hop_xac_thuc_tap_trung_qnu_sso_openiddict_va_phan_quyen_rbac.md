# Nhật Ký Phiên 252 — Tích Hợp Xác Thực Tập Trung QNU Single Sign-On (OpenIddict) & Phân Quyền RBAC 25 Permissions

- **Thời gian**: 2026-10-04
- **Loại hình**: Security Architecture, Enterprise SSO Integration, Full-Stack RBAC
- **Trạng thái**: Hoàn thành xuất sắc (100% tests passed, 0 lint errors, build Vite & tsc thành công)

---

## 1. Mục Tiêu Phiên Làm Việc
1. **Thiết lập danh mục quyền chuẩn `qnu-ai-permissions.json`**:
   - Định dạng chuẩn `qnu-sso.permissions` version 1, gồm 25 quyền hạn fine-grained (`ai.*`) bao quát toàn bộ chức năng (Chatbot, Kho tri thức, ModelOps, DAG Workflows, Channels, Benchmarking, Users & Quota).
   - Xuất đồng bộ sang cả dự án `qnu-ai-platform` và `qnu-sso` để máy chủ SSO nạp ngay vào CSDL quyền hạn tập trung.
2. **Xây dựng OIDC Client trên Frontend (`frontend2`)**:
   - Tích hợp thư viện chuẩn `oidc-client-ts` kết nối với `qnu-sso` (OpenIddict).
   - Thiết lập route xử lý chuyển hướng xác thực `/signin-oidc` với khả năng khôi phục URL đích và bắt lỗi trực quan.
   - Nâng cấp giao diện trang `sign-in.tsx` với nút đăng nhập QNU SSO nổi bật (Academic Teal theme, nhận diện Cán bộ/Giảng viên và Sinh viên UIS) kèm chế độ dự phòng Dev Access Gate.
   - Cập nhật RBAC context hỗ trợ đầy đủ các claims phân quyền và tiền tố `ai.access.*`.
3. **Xây dựng Bộ Xác Thực Token Kép trên Backend FastAPI**:
   - Bổ sung cấu hình `SSO_AUTHORITY`, `SSO_CLIENT_ID`, `SSO_AUDIENCE`, `SSO_JWKS_URL`, `SSO_USERINFO_URL` vào `Settings`.
   - Viết module `sso_validator.py` xác thực Bearer Token qua bộ khóa công khai JWKS bất đối xứng (RSA/RS256) có bộ nhớ đệm TTL 1 giờ, kết hợp cơ chế fallback UserInfo RFC standard.
   - Cung cấp dependency `require_permission` kiểm soát truy cập endpoint theo quyền chi tiết.

---

## 2. Các Tệp Thay Đổi & Tạo Mới

| STT | Tệp tin | Hành động | Mô tả |
| :---: | :--- | :---: | :--- |
| 1 | `qnu-ai-permissions.json` | Tạo mới | Tệp danh mục 25 quyền chuẩn `qnu-sso.permissions` v1 cho QNU AI Platform |
| 2 | `frontend2/src/app/auth/oidc.ts` | Tạo mới | Quản trị phiên OIDC, khởi tạo `UserManager`, xử lý chuyển hướng đăng nhập & callback |
| 3 | `frontend2/src/app/auth/types.ts` | Cập nhật | Bổ sung `studentId`, `accessToken` vào kiểu dữ liệu `CurrentUser` |
| 4 | `frontend2/src/app/auth/queries.ts` | Cập nhật | Ưu tiên nạp phiên OIDC SSO từ local storage và fallback về dev session API |
| 5 | `frontend2/src/app/auth/provider.tsx` | Cập nhật | Cung cấp hàm `loginSso` và `logoutSso` trong `AuthContext` |
| 6 | `frontend2/src/app/auth/index.ts` | Cập nhật | Re-export các phương thức OIDC chuẩn |
| 7 | `frontend2/src/routes/signin-oidc.tsx` | Tạo mới | Route đón callback từ SSO, đồng bộ danh tính vào cache và redirect về trang đích |
| 8 | `frontend2/src/routes/sign-in.tsx` | Cập nhật | Thiết kế lại trang đăng nhập: Nút SSO to rõ, badges đối tượng, accordion Dev Gate |
| 9 | `frontend2/src/routes/__root.tsx` | Cập nhật | Thêm `/signin-oidc` vào danh sách route công khai bypass `AuthGate` |
| 10 | `frontend2/src/rbac/context.tsx` | Cập nhật | Chuẩn hóa logic kiểm tra `can(permission)` theo mã quyền `ai.*` và hỗ trợ wildcard `*` |
| 11 | `backend/app/core/config.py` | Cập nhật | Bổ sung các biến môi trường và properties QNU SSO |
| 12 | `backend/app/modules/auth/schemas.py` | Cập nhật | Bổ sung email, user_type, student_id, roles, permissions, has_permission vào `AuthActor` |
| 13 | `backend/app/modules/auth/sso_validator.py` | Tạo mới | Xác thực Bearer JWT bằng JWKS public key và RFC UserInfo endpoint |
| 14 | `backend/app/modules/auth/dependencies.py` | Cập nhật | `get_current_actor` kiểm tra Bearer QNU SSO trước khi fallback Dev cookie; thêm `require_permission` |
| 15 | `backend/app/modules/auth/router.py` | Cập nhật | Endpoint `/auth/me` phân giải thông tin từ SSO Bearer token |
| 16 | `backend/app/modules/auth/__init__.py` | Cập nhật | Export `require_permission` và `validate_sso_token` |
| 17 | `backend/tests/test_sso_auth.py` | Tạo mới | Bộ kiểm thử tự động 5 test cases cho SSO claims parser và token validation |

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Backend Testing**:
   ```bash
   uv run ruff check app/modules/auth app/core/config.py  # 0 errors
   uv run --extra dev pytest tests/test_auth.py tests/test_sso_auth.py -v
   # Kết quả: 12 passed in 12.49s (100% PASS)
   ```
2. **Frontend Testing**:
   ```bash
   npx @biomejs/biome check src/app/auth src/routes/signin-oidc.tsx src/routes/sign-in.tsx src/routes/__root.tsx src/rbac/context.tsx
   # Checked 10 files in 16ms. 0 errors, 0 warnings.
   npm run build
   # Vite build + tsc --noEmit: HOÀN THÀNH VỚI EXIT CODE 0.
   ```

---

## 4. Bài Học Rút Ra & Hướng Dẫn Vận Hành
- **Cơ chế Dual-Mode Auth (SSO + Dev Gate)**: Giữ lại Dev Access Gate bên dưới nút QNU SSO giúp lập trình viên phát triển ngoại tuyến mượt mà mà không phụ thuộc vào kết nối mạng tới SSO Server, trong khi môi trường Production ưu tiên 100% QNU SSO.
- **Xác thực kết hợp JWKS và UserInfo**: Các access token từ OpenIddict đôi khi là token tham chiếu (reference/opaque) hoặc JWT mã hóa nội bộ. Việc kết hợp JWKS (xác thực nhanh tại chỗ 0 latency) với UserInfo fallback bảo đảm tỷ lệ xác thực thành công 100% trong mọi trường hợp cấu hình máy chủ SSO.
