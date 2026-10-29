# Phiên 723 — Sửa assertion trạng thái API key trong E2E permissions

Ngày: 2026-10-29.

## Bằng chứng

Log người dùng: navigation/upload/extraction/compilation/publication/chat mỗi chặng 1 passed; permissions failed tại assertion khóa cũ sau rotate (expected401, received403), lifecycle chưa chạy do prerequisite. Đây là kết quả do người dùng thực chạy, không phải lần nghiệm thu độc lập của agent.

Đọc backendV1/qnu/domains/integration/access.py xác nhận check_access từ chối key/app inactive bằng Forbidden(code=api_key_inactive) HTTP403. authenticate_api_key trả HTTP401/invalid_api_key cho token không tồn tại. service.rotate_key giữ hàng khóa cũ với status=revoked; không xóa hash. api/handlers.py giữ status/code và trả envelope error.code tại gateway. Log API chỉ đọc xác nhận rotate200 rồi models403. Vì vậy test kỳ vọng mọi khóa cũ đều401 là sai hợp đồng hiện có.

## Sửa phạm vi

- frontendV1/e2e/stages/workflow.spec.ts: helper kiểm đồng thời status và error.code; sau rotate/revoke phải đúng403/api_key_inactive, không chấp nhận403 chung hoặc nới thành bất kỳ lỗi4xx.
- Kiểm tra khóa mới gọi models thành công và chỉ thấy trợ lý được cấp sau rotate; khóa không tồn tại vẫn phải401/invalid_api_key. Giữ yêu cầu secret không xuất hiện trong danh sách metadata.
- Bổ sung hướng dẫn chạy lại riêng permissions rồi lifecycle; không đổi backend, khóa runtime, cấu hình model/quota hay checkpoint phiên thử. Không restart/reseed/cleanup/create session.

## Kiểm chứng thực chạy

PASS: Biome scoped1file, TypeScript tsc --noEmit -p tsconfig.e2e.json, UTF-8 không BOM/LF và git diff --check.
NOT RUN: permissions/lifecycle sau sửa và backend test/runtime. Không gọi inference hay API ghi; người dùng tiếp tục tự chạy từng chặng. Không kết luận toàn bộ workflow PASS.
