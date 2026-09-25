# NHẬT KÝ LÀM VIỆC — PHIÊN #224
**Ngày**: 2026-09-25 | **Thời gian**: 23:59 (UTC+7)
**Tiêu đề**: Fix Crash Loop Production Thiếu DEV_ACCESS_PASSWORD + Chặn Bypass Login Rỗng

---

## 1. Triệu Chứng (log Dokploy)
- Backend restart loop tại entrypoint bước migrate:
  `Value error, Production security violation: Default/insecure secrets detected for ['DEV_ACCESS_PASSWORD']`.
- Nguyên nhân: validator production (`config.py:251-267`) từ chối giá trị default `"QNU@2026"`, nhưng `docker-compose.yml` không hề truyền biến này → luôn dùng default → crash trước cả migrate.

## 2. Thay Đổi
- `docker-compose.yml`: thêm `DEV_ACCESS_PASSWORD=${DEV_ACCESS_PASSWORD:-}` cho cả backend và worker (rỗng qua validator vì falsy; không hardcode secret vào git).
- `backend/app/modules/auth/router.py`: `/login` fail-closed 503 `auth_not_configured` khi password rỗng — chặn bypass `compare_digest(" ", "") == True` (do `access_key` chỉ yêu cầu `min_length=1` nhưng bị `.strip()` sau đó).
- Tests: `test_production_security_allows_empty_dev_access_password` (test_core), `test_auth_login_rejects_when_password_unconfigured` (test_auth).

## 3. Kết Quả
- Ruff 0 lỗi; `test_auth.py` 7/7 pass; test mới pass.
- `test_core.py::test_production_security_validation_fails_on_default_secrets` vẫn rớt — lỗi có sẵn từ commit team `471bb00` (tự sinh `PROVIDER_ENCRYPTION_KEY` thay vì raise), không liên quan phiên này, chờ quyết định chính sách.
- Khuyến nghị: đặt `DEV_ACCESS_PASSWORD` mạnh trong Dokploy env để dùng khi bật `DEV_AUTH_ENABLED`.
