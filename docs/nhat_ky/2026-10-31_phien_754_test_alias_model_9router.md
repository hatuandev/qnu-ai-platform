# Phiên 754 — Đối chiếu alias model trong E2E 9router

## Nguyên nhân và thay đổi

Log người dùng: provider-setup/discovery/embedding/rerank PASS; model-chat thất bại vì requested `ollama/gpt-oss:120b` nhưng observed `gpt-oss:120b`. Model-ocr còn đang chạy lúc tiếp nhận; không nhận xét kết quả trước khi có report.

Phép so sánh trong E2E yêu cầu hai tên giống nhau. Bổ sung `observed_model_aliases` trong đúng profile provider, ánh xạ model yêu cầu sang danh sách tên phản hồi được chấp nhận. Helper kiểm cả capability và requested khớp profile; không bỏ prefix tổng quát, không chấp nhận model khác và không đổi routing/capacity/provider. Giữ assertion requested, diagnostic current/ok và trace requested/observed. Null observed giữ quy tắc cũ; alias không tự chứng minh danh tính model upstream.

Chỉ sửa profile, E2E/helper/regression và docs. Không sửa backend hoặc DB/checkpoint, không restart/cleanup/init, không gửi thêm inference khi người dùng đang chạy OCR.

## Kiểm chứng

- frontendV1: `npx vitest run tests/e2e-provider-selection.test.ts tests/e2e-capacity-735.test.ts`: 14 PASS, exit 0. Kiểm alias cụ thể, sai requested, sai provider/capability/model, alias chưa khai báo, strict equality provider khác và null theo hợp đồng cũ.
- `npm run test:e2e:typecheck`: PASS, exit 0.
- Biome trên bốn file TS sửa: PASS; định dạng file regression. Profile JSON kiểm cấu trúc và Biome cuối task.
- `npm run build` (Vite + tsc): PASS, exit 0; còn cảnh báo configLoader/chunk size có sẵn.
- Live E2E model-chat sau sửa: NOT RUN, người dùng chạy lại sau OCR. Không chạy backend suite vì không đổi server; lỗi nền source_purge716 lịch sử753 vẫn FAIL, không coi gate toàn repo PASS.

## Bàn giao

Đợi model-ocr kết thúc rồi chạy lại `./test-v1-e2e.ps1 run model-chat --headed`. Giữ serve và các chặng đã PASS. Không cleanup/init hoặc provider-setup lại. Chặng mới vẫn FAIL nếu gateway báo model khác alias được khai báo.
