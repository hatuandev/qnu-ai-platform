# Phiên760 — Cấu hình Qwen giảm suy luận và bỏ thời hạn300s của phản hồi chat

## Phạm vi được giao

- User cho phép cấu hình trước Qwen và bỏ giới hạn300s sau run `cmp_19756498812d` có2/3phần completed, phần2uncertain đúng300.1s.
- Đọc AGENTS, Git/diff, PROJECT_CONTEXT và skill ModelOps/backend/clean-code; khi thêm điều khiển UI đọc frontend skill/AGENTS/UI standards. Giữ toàn bộ sửa757–759.
- Chỉ thay chế độ chờ của model được chọn qua ModelOps; không đổi capacity/output/key/endpoint, không reset DB hoặc gửi lại request uncertain.
- Không có quyền điều khiển máy chủ AI/Nginx/router từ workspace này; không tuyên bố đã sửa timeout ở các lớp đó.

## Xác minh reasoning trước khi cấu hình

- Tham khảo [vLLM reasoning outputs](https://docs.vllm.ai/en/stable/features/reasoning_outputs/) và [Qwen vLLM deployment](https://qwen.readthedocs.io/en/latest/deployment/vllm.html); không mặc định mọi checkpoint có cùng tham số.
- Probe tổng hợp512output qua managed ModelOps/usage/key hiện có, không gửi PDF/corpus:
  - Server default: JSON đúng,2.09s, reasoning288ký tự, completion91/prompt73/total164.
  - `chat_template_kwargs.enable_thinking=false`: JSON đúng,0.67s, reasoning0, completion9/prompt33/total42.
- Sau đó lưu reasoning policy có verified theo quan sát trên: modechat_template_kwarg, parameterenable_thinking, off_valuefalse, taskscompiler/compiler_review, đúng providerQwen `prv_b8eba1466634` của phiên `1da945adac7c`.
- Probe cuối đọc trực tiếp policy đã lưu từ prepare_chat_request: wait_for_completiontrue, reasoningoff, JSON đúng, reasoning0,0.8s/46token. Đây là probe nhỏ, không phải benchmark PDF hay xác nhận hai GPU độc lập.
- Metadata không chứa prompt/corpus/key ở `tmp/v1-e2e/1da945adac7c/reasoning-probe-760.json`.

## Thay đổi triển khai

- ResiliencePolicy thêm `wait_for_completion=false` mặc định, lưu qua ModelOps service có quyền và audit; chỉ cho provider có capabilitychat.
- ChatRuntime/ChatRequest mang policy và trace; configuration hash thêm cờ khi bật để lượt cũ không bị đổi contract âm thầm. prepare_chat_request chuyển đúng policy server cho adapter.
- Khi bật: managed executor không áp tổng deadline cho request chat; HTTP read timeoutNone, vẫn giữ finite connect/write/pool. Các capability khác và model chưa bật giữ chính sách cũ. Không hardcode Qwen trong adapter.
- Vì request không còn deadline, thêm heartbeat cho lease Redis admission và key poolDB; chỉ gia hạn token đang sở hữu/chưa hết hạn, giữ TTL hữu hạn và ownership fence. Mất quyền/gia hạn thất bại hủy chờ với uncertain; cancellation không tự retry.
- Giới hạn request/token/tree, thời hạn toàn job và hàng đợi không bị xóa. Compiler policy1500s vẫn hiện có; không đánh đồng bỏ300s/request với bỏ mọi giới hạn hệ thống.
- Frontend panel có switch **Chờ model xử lý xong**, chỉ hiện cho chat, giải thích giới hạn còn lại; giữ form/primitives hiện có. Cập nhật test selector theo nhãn vì nay có hai switch, thêm test lưu policy rõ ràng.
- Không migration hoặc thêm dependency.

## File của phiên760

Backend: `ports/chat_model.py`, `adapters/providers/openai_compatible.py`, `domains/modelops/public_api.py`, `inference/service.py`, `resilience/{schemas,service,execution,admission,key_pool,heartbeat}.py`.

Test: `tests/unit/test_chat_wait_760.py`, `tests/integration/test_chat_wait_760.py`.

Frontend: `src/features/modelops/resilience-{panel.tsx,queries.ts}`, `tests/modelops-resilience-695.test.tsx`. Hướng dẫn PDF và nhật ký/memory.

## Kiểm chứng đã chạy

| Kiểm tra | Kết quả |
|---|---|
| Unit760 trước thêm policy | Exit1,3FAIL đúng contract chưa có wait_for_completion |
| Unit760/admission747/reasoning746 sau sửa | Exit0,28PASS,1.84s |
| Full backend unit, basetemp tmp/pytest-all-760 | Exit1,527PASS/1FAIL nền,27.05s |
| Integration ModelOps/resilience695 + wait760 + admission751, DB cô lập | Exit1,34PASS/1FAIL vì thiếu CACHE_NAMESPACE test ở harness invocation |
| Rerun wait760/admission751 với CACHE_NAMESPACE riêng qnu:test:760:UUID, PostgreSQL riêng và Redis loopback | Exit0,4PASS,9.10s; DB đãdrop/sentinel giữ, egress nonloopback bị chặn |
| Ruff toàn bộ Python sửa/thêm760 | Exit0,PASS |
| Vitest resilience695/admissions-recovery/progress-budget | Sau cập nhật selector và thêm test mới: Exit0,26PASS,3file |
| Biome3file frontend760 | Exit0,PASS |
| Frontend npm run build | Exit0,PASS; warning Vite/bundle còn có |
| Browser thật Playwright desktop/read-only | Switch hiển thị và checkedtrue trên providerQwen; ảnh wait-policy-760.png đã xem |
| Live probe sau lưu policy | JSON đúng,0.8s, không reasoning; không chạy lại PDF |

Full unit lỗi nền exact ID: `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`, invalid_identity. Tổng suite vẫn FAIL, không sửa ngoài scope.

Các integration mới chứng minh API admin lưu/đọc policy, prepare request, managed request chờ vượt deadline cũ trong test, DB key renew đúng owner/từ chối owner khác, LuaRedis không gia hạn token lạ/hết hạn. Unit còn kiểm cancellation và mất lease. Thời gian thử được rút ngắn bằng timeout test0.01s; không chờ300s chỉ để kiểm cùng nhánh.

## Vận hành và bàn giao

- Đã lưu cấu hình bằng ModelOps domain service sau khi xác thực bearer của user qua resolve_actor/require_model_admin; không sửa secret/env/DB bằng SQL.
- Xác minh không có compilation/review queued/running trước reload. Xác minh runner PID30712 là `scripts/v1_e2e_session.py serve`, rồi dừng đúng cây con E2E để runner tựfinally; không dừng Docker hay tiến trình user khác.
- Lần mở serve đầu bị guard chặn PIDtest đang nối Postgres; đợi test kết thúc, không xóa lock/bypassguard. Serve mới đã ready với backend code mới. Sau kiểm chứng, agent dừng serve mình mở; user mở lại serve ở cửa sổ của mình.
- Run `cmp_19756498812d` giữ uncertain; hai phần hoàn tất và lịch sử/raw/usage không bị ghi đè. Không tự replay phần2 hoặc tạo lượt PDF mới trong phiên760.
- Chạy tiếp: `.\test-v1-e2e.ps1 serve`, chờ ready; cửa sổ khác `.\test-v1-e2e.ps1 run admissions-compilation --headed --recover`. Đây là chủ động tạo run mới từ OCR sẵn có, giữ lượt cũ trong lịch sử; khôngcleanup/init.
- Phiên ModelOps mới sau cleanup không tự kế thừa policy đã xác minh trên phiên này. P2 tổng thời gian review758 chưa sửa.
