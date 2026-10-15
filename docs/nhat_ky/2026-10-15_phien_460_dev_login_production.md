# Phiên 460 — Dev Access Gate trên production theo yêu cầu người vận hành

## Phạm vi và quyết định

Người dùng chủ động muốn giữ DEV_AUTH_ENABLED trên server demo, thay cho yêu cầu cũ luôn tắt Dev trong production. Không chuyển ENVIRONMENT sang development. Thêm DEV_AUTH_ALLOW_IN_PRODUCTION mặc định false; chỉ bật đường mật khẩu khi cả hai cờ true. Không thay đổi môi trường thật, không commit/push/deploy/reset DB.

## Thay đổi

- backend/app/core/config.py: ngoại lệ opt-in, password 24–128 ký tự, signing key >=32/HS256, origin HTTPS chính xác; cho phép không SSO khi gate hợp lệ.
- backend/app/modules/auth/dev_access.py: token purpose/issuer/audience riêng, phiên bản mật khẩu HMAC, cookie lifetime tối đa 60 phút; Redis atomic throttle 10/peer và 100/toàn cài đặt trong 5 phút, timeout 3 giây, lỗi fail-closed.
- backend/app/modules/auth/router.py và dependencies.py: đăng nhập production opt-in, dùng cùng bộ xác thực cho /me và API, kiểm tra Origin khi dùng cookie để thay đổi dữ liệu; tuyệt đối không anonymous admin ở production. Giữ local shortcut ngoài production như cũ.
- docker-compose.yml, .env.dokploy.example: chuyển tiếp cờ mới, mặc định tắt; hướng dẫn demo riêng không dùng secret thật trong repo.
- tests/test_dev_auth_production_460.py, tests/test_dev_auth_redis_460.py, tests/test_deployment_contract_456.py: regression, HTTP auth, Redis cô lập và Compose contract.
- docs/trien_khai/02_quy_trinh_trien_khai_dokploy.md, docs/quy_trinh/01_khoi_dong_nen_tang.md: đồng bộ cách bật và giới hạn bảo mật.

## Kiểm chứng và điểm dừng

- Trước sửa: regression 3 failed/9 passed, chặn Settings và login đúng lỗi.
- Sau sửa: focus auth/SSO/Compose 87 passed.
- Redis Docker tạm riêng: 1 passed; lần kiểm chứng bổ sung bao gồm HTTP login → Redis thật → cookie → /me → API protected cũng 1 passed. Container tự dọn; không dùng Redis ứng dụng.
- Khi gửi yêu cầu dừng, full Pytest đã tự hoàn tất: 1370 passed, 11 failed, 16 skipped trong 213,45 giây. Tên 11 ca lỗi trùng baseline đã ghi nhận trước (consulting/publishing/reconciliation/actor role/universal tools); không sửa lan. Không chạy thêm kiểm thử theo yêu cầu người dùng, không tuyên bố toàn suite xanh hoặc đã nghiệm thu server.
- Ruff phạm vi đạt trước bổ sung test Redis; lần quét cuối phát hiện import-order của fixture re-export, đã chỉnh import theo gợi ý nhưng không chạy lại theo yêu cầu người dùng. Cảnh báo quyền đọc các artifact cũ không sửa.
- Không sửa FE nên không chạy Vite. Không thay đổi mật khẩu thật hay cấu hình server. User cần đưa code mới lên repository/deploy rồi bật cờ trong Dokploy.

## Lưu ý

Đây là mật khẩu quản trị dùng chung, không thay thế danh tính từng người. Chỉ dùng demo HTTPS có kiểm soát; đổi mật khẩu đã lộ trong ảnh. Logout xóa cookie, không thu hồi riêng JWT đã sao chép; đổi mật khẩu và tạo lại mọi API container để chặn phiên cũ. Redis lỗi đăng nhập trả 503; proxy có thể khiến nhiều người chung hạn mức peer. Kỹ thuật tuân thủ skill qnu-clean-code-architect và qnu-backend-architect: regression trước sửa, thay đổi có phạm vi, production luôn fail-closed.
