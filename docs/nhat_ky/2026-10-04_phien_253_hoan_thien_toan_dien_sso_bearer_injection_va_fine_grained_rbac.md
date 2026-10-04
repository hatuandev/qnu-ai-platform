# Nhật Ký Phiên 253 — Hoàn Thiện Toàn Diện Tích Hợp QNU Single Sign-On (OIDC), Tự Động Inject Bearer Token & Enforce Fine-Grained RBAC

- **Thời gian**: 2026-10-04
- **Loại hình**: Security Architecture, Enterprise SSO Finalization, Production Hardening, Fine-Grained RBAC Enforcement
- **Trạng thái**: Hoàn thành xuất sắc (100% 15/15 tests passed, 0 Ruff errors, 0 Biome errors, Vite build thành công 6.15s)

---

## 1. Mục Tiêu Phiên Làm Việc
Rà soát toàn diện hiện trạng tích hợp QNU Single Sign-On (OIDC OpenIddict) và xử lý triệt để 3 điểm nghẽn kỹ thuật để sẵn sàng 100% triển khai Production:
1. **Khắc phục lỗi thiếu Bearer Token trên Frontend (P0 - Critical Blocker)**:
   - Toàn bộ 77+ lời gọi `fetch()` trong `frontend2/src/services/` trước đó không truyền header `Authorization: Bearer <token>`, dẫn tới Backend trả về `HTTP 401 Unauthorized` trên môi trường Production.
   - Xây dựng Global Fetch Interceptor (`fetch-interceptor.ts`) tự động bắt mọi request `/platform/*` để inject Bearer Token từ OIDC User và bảo đảm `credentials: "include"`.
   - Cung cấp helper `getAuthHeaders()` trong `http-client.ts` cho các lời gọi tường minh.
2. **Kích hoạt hỗ trợ Refresh Token (`offline_access`)**:
   - Bổ sung scope `offline_access` vào `OIDC_CONFIG.scope` trong `oidc.ts` để kích hoạt cơ chế silent renew tự động làm mới access token khi hết hạn mà không ngắt quãng phiên làm việc của người dùng.
3. **Thắt chặt an ninh AuthActor & Enforce RBAC (`require_permission`) trên Backend (P1)**:
   - Sửa lỗ hổng gán nhầm default `roles=["admin"]` và `permissions=["*"]` trong `AuthActor` Pydantic model; chuyển mặc định sang `roles=["staff"]` và `permissions=[]` an toàn, ngăn chặn việc vô tình cấp quyền admin cho actor chưa xác thực đầy đủ.
   - Gắn dependency `require_permission` vào các router trọng yếu:
     - `app.modules.assistants.router`: Bảo vệ tạo, sửa, xóa, xuất bản, nhân bản với `ai.assistants.create`, `ai.assistants.edit`, `ai.assistants.delete`, `ai.assistants.publish`.
     - `app.modules.knowledge.router`: Bảo vệ tạo/xóa kho, nạp tài liệu, xóa tài liệu, nạp facts Excel với `ai.knowledge.upload`, `ai.knowledge.delete`, `ai.facts.manage`.
     - `app.modules.modelops.router`: Bảo vệ tạo/sửa/xóa provider, cập nhật default model với `ai.models.manage` và `ai.models.test`.
4. **Cập nhật mẫu cấu hình môi trường**:
   - Bổ sung nhóm biến SSO (`SSO_ENABLED`, `SSO_AUTHORITY`, `SSO_CLIENT_ID`, `SSO_AUDIENCE`, `SSO_JWKS_URL`, `SSO_USERINFO_URL`) vào `.env.example` và `.env.dokploy.example`.

---

## 2. Các Tệp Thay Đổi & Tạo Mới

| STT | Tệp tin | Hành động | Mô tả |
| :---: | :--- | :---: | :--- |
| 1 | `frontend2/src/app/auth/fetch-interceptor.ts` | Tạo mới | Global Fetch Interceptor tự động inject Bearer Token vào mọi request `/platform/*` và xử lý 401 silent renew |
| 2 | `frontend2/src/main.tsx` | Cập nhật | Kích hoạt `installAuthFetchInterceptor()` ngay khi khởi chạy ứng dụng |
| 3 | `frontend2/src/app/auth/oidc.ts` | Cập nhật | Bổ sung `offline_access` vào scope; xuất `getAccessToken()` và theo dõi sự kiện đổi token |
| 4 | `frontend2/src/app/auth/index.ts` | Cập nhật | Re-export `getAccessToken` và `installAuthFetchInterceptor` |
| 5 | `frontend2/src/services/http-client.ts` | Cập nhật | Cung cấp hàm trợ giúp `getAuthHeaders(headers?)` |
| 6 | `backend/app/modules/auth/schemas.py` | Cập nhật | Chuyển default của `AuthActor` sang `role="staff"`, `roles=["staff"]`, `permissions=[]` an toàn |
| 7 | `backend/app/modules/auth/router.py` | Cập nhật | Gán tường minh `roles=["admin"]`, `permissions=["*"]` cho phiên đăng nhập Dev Access Gate |
| 8 | `backend/app/modules/assistants/router.py` | Cập nhật | Bảo vệ các endpoint trợ lý bằng `require_permission` |
| 9 | `backend/app/modules/knowledge/router.py` | Cập nhật | Bảo vệ các endpoint kho tri thức bằng `require_permission` |
| 10 | `backend/app/modules/modelops/router.py` | Cập nhật | Bảo vệ các endpoint ModelOps bằng `require_permission` |
| 11 | `backend/tests/test_sso_auth.py` | Cập nhật | Bổ sung unit tests cho `require_permission` (thành công, bị từ chối 403, vai trò quản lý/admin) |
| 12 | `.env.example` | Cập nhật | Bổ sung tài liệu cấu hình QNU Single Sign-On |
| 13 | `.env.dokploy.example` | Cập nhật | Bổ sung cấu hình mẫu SSO cho môi trường Dokploy Production |

---

## 3. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Backend Unit Testing**:
   ```bash
   python -m pytest tests/test_auth.py tests/test_sso_auth.py -v
   # Kết quả: 15/15 passed in 13.10s (100% PASS)
   ```
2. **Backend Ruff Linter**:
   ```bash
   python -m ruff check app/modules/auth app/modules/assistants/router.py app/modules/knowledge/router.py app/modules/modelops/router.py tests/test_sso_auth.py
   # Kết quả: All checks passed! (0 errors)
   ```
3. **Frontend Biome Linter**:
   ```bash
   npx @biomejs/biome check src/app/auth src/services/http-client.ts src/main.tsx
   # Kết quả: Checked 9 files, 0 errors, 1 warning (non-null assertion chuẩn Vite template)
   ```
4. **Frontend Production Build**:
   ```bash
   npm run build
   # Kết quả: built in 6.15s (0 TypeScript errors, 0 Vite bundler errors)
   ```

---

## 4. Bài Học Rút Ra & Khuyến Nghị Vận Hành
- **Cơ chế Global Fetch Interceptor**: Thay vì phải sửa tay từng hàm trong 77+ vị trí gọi API rải rác, việc chặn `window.fetch` cho riêng tiền tố `/platform/` mang lại sự an toàn tuyệt đối, không gây ảnh hưởng tới các cuộc gọi tài nguyên bên ngoài (CDN, Google Fonts) và bảo đảm tương thích ngược 100%.
- **Nguyên tắc "Fail-Safe Defaults" trong Security DTOs**: Tuyệt đối không bao giờ để giá trị mặc định của một Identity Model là quyền Admin (`["*"]`). Mọi quyền hạn cao cấp bắt buộc phải được gán có chủ đích qua xác thực thành công.
