# Phiên 776 — Ngân sách E2E 20.000.000 token

Người dùng yêu cầu tăng quota test lên20.000.000. Ngoại lệ được phép: profile E2E QNU và validator tương ứng; navigation sẽ cấu hình ngân sách này qua ModelOps cho workspace của phiên, theo cơ chế đã có. Không thay context/output model, key, usage/reservation, provider hay dữ liệu.

Nguyên nhân navigation BLOCKED: profile cũ5M nhưng live-defaults vẫn giới hạn1M. Đã đổi scripts/e2e_profiles/qnu-server.json thành20M và validator finite maximum20M; giữ Number.isSafeInteger, >0 và chặn mức vượt trần. Không mở quota vô hạn.

Thêm regression e2e-quota-profile-776: đọc profile thật20M; gọi liveDefaults xác nhận5M/20M vượt validation đến ranh giới API;0/âm/thập phân/>20M/string/null bị chặn trướcAPI. Fake API dừng ở catalog, không gọi upstream hay ghi DB.

Kiểm chứng thực tại frontendV1:
- npx vitest run tests/e2e-quota-profile-776.test.ts tests/e2e-provider-selection.test.ts: PASS14/14, exit0.
- npm run test:e2e:typecheck: PASS, exit0.
- npx biome check --write e2e/stages/live-defaults.ts tests/e2e-quota-profile-776.test.ts ../scripts/e2e_profiles/qnu-server.json: PASS sau sửa formatter, exit0.
- npm run build: PASS, exit0; vẫn có warning chunk>500kB/Vite native config như trước.
- git diff --check: PASS, exit0.

Không chạy lại full frontend/backend hoặc live inference cho sửa profile này. Full frontend ở phiên775 còn539PASS/33FAIL ngoài scope, không thay bằng14test PASS. Chưa chạy navigation để xác nhận DB đã nhận20M; chỉ xác nhận profile/validator. Không cleanup/init/restart.

Log người dùng cung cấp xác nhận provider-setup, discovery và4model PASS ở phiên93faa11f0caf; navigation dừng vì validator cũ, admissions chưa chạy. Bước tiếp theo: .\test-v1-e2e.ps1 run navigation --headed, rồi các chặng admissions theo hướng dẫn đã cập nhật. Không cần nhập lại key.
