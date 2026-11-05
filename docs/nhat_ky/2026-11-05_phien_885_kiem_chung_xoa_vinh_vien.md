# Phiên 885 — Kiểm chứng xóa vĩnh viễn

## Phạm vi

Kiểm tra lại độ ổn định luồng xóa sau phiên 883–884. Không sửa mã ứng dụng, xóa tài liệu thật, restart, reset, reindex hoặc push. Giữ các thay đổi đang có của người dùng.

## Kiểm chứng thực chạy

- Frontend, cwd `frontendV1`: `npm exec -- vitest run tests/delete-confirmation-709.test.tsx tests/use-mobile-884.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/legacy-source-deletions-718.test.tsx tests/v1-lifecycle-678.test.ts tests/knowledge-actions-708.test.tsx --reporter=dot` — **PASS**, exit 0, 68/68 ca, 15,78 giây. Bao gồm phản hồi chậm/cũ, khóa gửi lặp, lỗi mạng, thử lại cùng khóa, quyền và breakpoint.
- Backend, cwd root: đặt `QNU_TEST_WINDOWS_SELECTOR_LOOP=true`, `QUEUE_NAME=qnu:v1:qa885:jobs`, `CACHE_NAMESPACE=qnu:v1:qa885:cache:`, `LOG_LEVEL=WARNING`; chạy `backendV1/.venv/Scripts/python.exe -X utf8 backendV1/scripts/run_isolated_tests.py tests/unit/test_source_purge_716.py tests/integration/test_source_purge_716.py tests/integration/test_lifecycle_659.py -q` — **PASS**, exit 0, 25/25 ca, 2 cảnh báo deprecation thư viện. Dùng PostgreSQL tạm và tệp local tổng hợp, kiểm tra endpoint/worker xóa đúng dữ liệu liên quan, giữ tài liệu khác, lỗi lưu trữ, quyền và phụ thuộc xuất bản. Receipt xác nhận `db_dropped=true`, `legacy_sentinel_preserved=true`, `pytest_exit=0`.
- Chromium cô lập: `node tmp/fix-884-browser.mjs` — **PASS**, exit 0, viewport 390px/1280px. Menu mở đúng một hộp thoại, gửi đúng một accept và tự đóng khi hoàn tất. API trong harness là dữ liệu tổng hợp, không gọi API ứng dụng thật.
- Kiểm tra chỉ đọc app đang chạy: `GET http://127.0.0.1:8002/health/ready` — **HTTP 200**, database/Redis connected; `GET http://127.0.0.1:3001/` — **HTTP 200**.

Log tại root `tmp/check-885-frontend.log`, `tmp/check-885-backend.log`, `tmp/check-885-browser.log` (không đưa vào Git).

## Giới hạn và bước tiếp

Kết luận đạt trong phạm vi các ca trên, không chứng minh mọi tình huống production. Backend integration gọi worker thật qua harness, không kiểm toàn luồng daemon ARQ đang chạy của app; S3 phiên bản được kiểm bằng mock, chưa xóa tệp MinIO/vector thật. Full suite và build **NOT RUN** trong phiên này vì không sửa source; kết quả build phiên 884 là lịch sử. Không chạy lại để che failure.

Người dùng có thể kiểm tra bằng một tài liệu thử không còn dùng; không cần clear dữ liệu hay khởi động lại app cho phiên kiểm chứng này.
