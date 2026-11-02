# Phiên 812 — Bỏ ngắt phản hồi Qwen ở 300 giây

## Yêu cầu và nguyên nhân

Người dùng yêu cầu bỏ ngắt compiler sau 300 giây vì tài liệu có thể cần lâu hơn. Mã V1 đã hỗ trợ `wait_for_completion`, gồm HTTP read không deadline, bỏ deadline tổng của CredentialExecutor và gia hạn lease key/admission. Tuy nhiên policy Qwen trong phiên E2E hiện tại là `default`, wait=false; profile tạo lại phiên cũng chưa khai báo lựa chọn này. Vì vậy lượt 811 vẫn bị ngắt ở 300 giây.

## Thay đổi cấu hình và runner

- Qua API ModelOps có xác thực, bật wait=true cho provider chat mặc định Qwen `prv_1d0f8b0c2079` trong phiên `93faa11f0caf`. GET trước/sau và resolver runtime xác minh effective=true. Không đọc/xuất khóa và không sửa timeout thành 0; timeout kết nối/gửi vẫn hữu hạn.
- Giữ nguyên key-pool/retry/fallback/cooldown, model, capacity, reasoning và grants. Cờ này là chính sách của provider Qwen, áp dụng cho các tác vụ chat dùng provider đó, bao gồm compiler; không phải chỉ một run.
- Profile QNU và 9router thêm model_runtime.chat.wait_for_completion=true. Helper E2E sau sync-capacity đọc policy, chỉ thay cờ cần thiết, lưu qua API resilience rồi GET xác minh. Profile không khai báo cờ không thay policy. Lỗi quyền/lưu được báo ngay, không retry. Sau cleanup/init, provider-setup sẽ áp lại lựa chọn từ profile.
- Hướng dẫn test thêm vị trí công tắc **Chờ model xử lý xong**, phân biệt timeout kết nối với thời hạn phản hồi và yêu cầu không resend uncertain tự động.

Không đổi mã backend, DB schema hoặc cấu hình worker; không restart serve chính. Run cmp_5701d4554c0e giữ uncertain, attempt1. Không dispatch inference mới hoặc chạy lại benchmark.

## Kiểm chứng

- API PUT/GET thật và runtime resolver PASS: policy configured, effective wait=true; các trường policy khác giữ nguyên. Receipt trong tmp/timeout812/; dùng ASGI handlers và DB thật, đóng lifespan sau kiểm.
- Backend: từ backendV1, `.venv/Scripts/python.exe -m pytest tests/unit/test_chat_wait_760.py -q --basetemp ../tmp/timeout812/pytest` → exit0, 5 PASS. Mock adapter chậm hơn deadline cũ vẫn hoàn tất khi wait=true; giữ timeout connect/write và hủy tác vụ; không retry.
- E2E regression trước sửa: 3 FAIL / 1 PASS, helper không gửi PUT policy. Sau sửa: `npx vitest run tests/e2e-chat-wait-812.test.ts tests/e2e-capacity-735.test.ts tests/e2e-provider-selection.test.ts --reporter=dot` → exit0, 19 PASS / 3 suites.
- `npm run test:e2e:typecheck` và Biome 4 tệp → exit0. Lượt kiểm đầu bị type import kéo module UI vào tsconfig E2E; đã sửa bằng hợp đồng response tối thiểu, kiểm lại đạt, không nới tsconfig.
- Không chạy full BE/FE vì thay đổi cấu hình/runner, không đổi app behavior/backend code. Không tuyên bố live compiler đã hoàn tất sau 300 giây; chưa gửi lượt mới.

## Giới hạn còn lại

HTTP đọc phản hồi Qwen không còn ngắt ở 300 giây trong lượt mới. ARQ worker vẫn có job_timeout=1800 (30 phút); các ngân sách refinement/queue nếu được cấu hình vẫn độc lập. Do đó đây chưa phải cam kết không có thời hạn ở mọi tầng. Không tự refactor worker hoặc bỏ mọi ngân sách vận hành trong lần chỉnh policy này. Main v1.0.2 và các diff trước giữ nguyên; chưa commit/push thay đổi 812.
