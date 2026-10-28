# Context697 — Review Providers và API tích hợp sau prompt

Ngày: 2026-10-28. Phạm vi: review batch chưa commit của người dùng cho backendV1/frontendV1; không sửa mã ứng dụng.

Kết luận: chưa nên nghiệm thu gateway cho ứng dụng bên ngoài. Build và test của batch chạy đạt, nhưng kiểm tra độc lập tái hiện 10 lỗi hành vi. Cần ưu tiên quyền của khóa và việc giữ nguyên cấu hình trợ lý.

## Phương pháp và phạm vi thay đổi

- Đọc PROJECT_CONTEXT696, AGENTS, diff tracked và các tệp integration/endpoints chưa tracked; dùng skill clean-code, backend, frontend và ModelOps của QNU.
- Dùng TestClient, PostgreSQL thật được migration trong database dùng riêng `qnu_v1_test_*`; dữ liệu tổng hợp. Chỉ mock biên RAG để quan sát đối số, lỗi và thay đổi trạng thái giữa lượt gọi; không mock truy vấn quyền/membership của machine principal.
- Kiểm tra xoay khóa đồng thời dùng hai AsyncSession/kết nối thật và barrier tại lúc đọc khóa cũ. Đây là kiểm tra service concurrency, không phải hai HTTP request qua mạng.
- Kiểm tra Redis unavailable bằng override dependency trả None, đúng nhánh bỏ qua limiter; không ngắt Redis đang dùng.
- FE kiểm tra component thật qua jsdom; mock mutation để quan sát payload form, polyfill ResizeObserver cho Radix. Không đánh đồng với kiểm tra browser/layout.
- Chỉ thêm báo cáo/snapshot/index và artifact kiểm tra local. Bản test tạm đặt trong hai thư mục tests đã được gỡ sau khi lưu bản sao ở `storage/artifacts/context697-modelops-review/`.
- Không sửa .env, không migrate DB người dùng, không gọi AI server, không restart/deploy/push.

## Findings cần sửa

### F01 — P1: Gateway làm mất cấu hình của trợ lý

Nguồn: [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng254–271; đối chiếu [conversations/execution.py](../../backendV1/qnu/domains/conversations/execution.py), dòng62–87.

Gateway chỉ truyền question/top_k/chat_provider_id vào AnswerRequest; không truyền persona, max_output_tokens, rag_policy, checkpoint hoặc reranker. Trợ lý cấu hình hybrid/enforce/context_window=2 lại gọi pipeline với dense/off/0. Điều này làm kết quả API ngoài khác chat của chính trợ lý, bỏ kiểm chứng và bộ lọc đã cấu hình.

Bằng chứng: `test_review_assistant_policy_and_persona_are_preserved` FAIL: dense != hybrid. Các đối số còn lại đã đối chiếu trực tiếp trong mã. Hướng sửa: tái dùng orchestration có snapshot/policy/authorization checkpoints của trợ lý và luồng hội thoại, giữ runtime ModelOps hiện có.

### F02 — P1: Thu hồi khóa giữa lượt gọi vẫn trả kết quả

Nguồn: [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng291–299; [database.py](../../backendV1/qnu/platform/database.py), expire_on_commit=False.

`db.get` dùng lại đối tượng key/app trong identity map, không ép đọc lại DB. Một kết nối khác thu hồi khóa trong khi inference chạy nhưng gateway vẫn thấy active và trả200. Phần kiểm tra cuối cũng chưa kiểm lại hạn dùng, membership/workspace và trạng thái/revision trợ lý.

Bằng chứng: `test_review_revocation_from_another_connection_stops_response` FAIL: nhận200 thay vì403 sau khi kết nối khác commit revoked. Hướng sửa: truy vấn fresh có populate_existing/refresh và kiểm lại toàn bộ điều kiện truy cập trước khi trả dữ liệu, với checkpoint trong pipeline phù hợp.

### F03 — P1: Hai yêu cầu xoay một khóa tạo hai khóa mới cùng active

Nguồn: [service.py](../../backendV1/qnu/domains/integration/service.py), dòng276–326.

Đọc khóa cũ và chuyển trạng thái không có row lock/conditional transition. Hai worker cùng thấy khóa cũ active rồi đều tạo bản thay thế; UI hiện không gửi Idempotency-Key cho thao tác này.

Bằng chứng: `test_review_concurrent_rotation_cannot_mint_two_replacements` FAIL: hai session đều tạo thành công. Hướng sửa: khóa/kiểm tra nguyên tử khóa cũ trong transaction, ràng buộc một bản thay thế hợp lệ và xử lý retry/idempotency rõ ràng.

Lưu ý: migration đã có partial unique index cho workspace_id/idempotency_key. Kiểm tra tạo khóa cùng Idempotency-Key chặn được tạo đôi. Không báo nhầm thiếu unique index chỉ vì ORM model chưa khai báo index đó.

### F04 — P1: Form giới hạn trợ lý có thể cấp quyền gọi tất cả

Nguồn: [create-key-dialog.tsx](../../frontendV1/src/features/modelops/endpoints/create-key-dialog.tsx), dòng85–87; [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng175 và235.

Bỏ chọn “Tất cả trợ lý trong workspace”, không chọn trợ lý cụ thể rồi submit vẫn gửi allowed_assistant_ids=[]. BE hiểu mảng rỗng là không giới hạn. Ý định hạn chế của admin bị đổi thành quyền rộng nhất, bao gồm trợ lý thêm về sau.

Bằng chứng: FE `restricted scope with zero selected assistants...` FAIL, mutation nhận []. Hướng sửa: không cho submit phạm vi hạn chế rỗng; hợp đồng BE biểu diễn rõ all so với allowlist/none, không suy quyền rộng từ mảng rỗng ngoài ý muốn.

### F05 — P1: Redis lỗi làm vô hiệu giới hạn lượt gọi

Nguồn: [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng100–135.

Redis None bỏ qua cả RPM/RPD; exception của Redis cũng chỉ ghi warning rồi tiếp tục. Khi hạ tầng limiter lỗi, mọi worker đều cho phép gọi không giới hạn dù key đang có hạn mức.

Bằng chứng: `test_review_redis_unavailable_does_not_disable_rate_limit` FAIL: key RPM=1 nhận liên tiếp [200,200,200]. Hướng sửa: báo503 rõ ràng hoặc cơ chế dự phòng có tính nhất quán được thiết kế tường minh; không tiếp tục bỏ giới hạn.

### F06 — P2: Lịch sử hội thoại và một số tham số bị bỏ qua âm thầm

Nguồn: [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng242–257; [schemas.py](../../backendV1/qnu/domains/integration/schemas.py), OpenAIChatCompletionRequest.

Gateway chỉ lấy user message cuối. Câu hỏi nối tiếp mất ngữ cảnh; system/assistant messages không được xử lý hoặc từ chối. temperature/top_p/max_tokens được nhận nhưng không áp dụng; extra fields mặc định bị bỏ qua.

Bằng chứng: `test_review_multiturn_is_processed_or_explicitly_rejected` FAIL: request lịch sử nhận200 nhưng chỉ câu cuối đến RAG. Phần tham số là đối chiếu mã, chưa có test độc lập riêng. Hướng sửa: hỗ trợ history qua luồng đã có, hoặc trả400 cho hợp đồng chưa hỗ trợ; không công bố hỗ trợ bằng việc nhận rồi bỏ qua.

### F07 — P2: Lỗi quota/provider bị đổi thành500 chung

Nguồn: [gateway.py](../../backendV1/qnu/domains/integration/gateway.py), dòng272–289; [handlers.py](../../backendV1/qnu/api/handlers.py), validation handler.

Catch Exception gộp mọi lỗi pipeline thành inference_error500 và log status500, kể cả quota429. Client không thể phân biệt cần đợi quota với sự cố server. Chuỗi exception thô còn được đưa vào response/log, khác cơ chế redaction hiện có. Validation lỗi422 của gateway vẫn trả RFC7807 thay vì error envelope OpenAI.

Bằng chứng: `test_review_provider_error_preserves_status` FAIL: exception429 trả500. Redaction và validation envelope là đối chiếu mã, chưa test độc lập riêng. Hướng sửa: map lỗi theo loại/status, giữ retry metadata, che thông tin nội bộ và dùng error envelope thống nhất.

### F08 — P2: FE đọc sai tên trường cấu hình endpoint

Nguồn: [endpoint-card.tsx](../../frontendV1/src/features/modelops/endpoints/endpoint-card.tsx), dòng23–31; [integration-guide.tsx](../../frontendV1/src/features/modelops/endpoints/integration-guide.tsx), dòng22–30; [schemas.py](../../backendV1/qnu/domains/integration/schemas.py), IntegrationConfigResponse.

BE trả base_url/openai_endpoint/supported_protocols/capabilities, FE đọc server_base_url/openai_base_url/supported_capabilities/supported_endpoints. Không có adapter chuyển đổi. Vì thế card và mẫu mã dùng window.location.origin, có thể là host frontend/static không phục vụ API.

Bằng chứng: FE `endpoint card uses actual backend IntegrationConfigResponse` FAIL với payload đúng DTO backend. Test của batch trước đó dùng payload giả theo kiểu FE nên không phát hiện. Hướng sửa: thống nhất DTO và test qua request layer; bỏ fallback origin khi cấu hình chưa tải hoặc lỗi.

### F09 — P2: Endpoint “tin cậy” vẫn lấy trực tiếp từ header request

Nguồn: [router.py](../../backendV1/qnu/domains/integration/router.py), dòng49–54.

Endpoint config ưu tiên X-Forwarded-Host/X-Forwarded-Proto mà không kiểm nguồn proxy hoặc dùng public URL được quản trị cấu hình. Một request mang host tùy ý làm API quảng bá URL tùy ý. Đây chưa phải bằng chứng đã khai thác người dùng khác; cần sửa hợp đồng URL tin cậy trước khi phát hành tích hợp.

Bằng chứng: `test_review_endpoint_config_ignores_untrusted_host` FAIL: response chứa domain .invalid do test gửi. Hướng sửa: public base URL từ cấu hình server; chỉ dùng forwarded headers sau ranh giới proxy tin cậy rõ ràng.

### F10 — P2: Provider đã kiểm tra thành công vẫn bị báo thất bại

Nguồn: [modelops/router.py](../../backendV1/qnu/domains/modelops/router.py), dòng179–192; [diagnostics/schemas.py](../../backendV1/qnu/domains/modelops/diagnostics/schemas.py); [provider-card-grid.tsx](../../frontendV1/src/features/modelops/provider-card-grid.tsx), dòng139–144.

History thật lưu outcome/tested_at/latency_ms/identity; summary đọc success/created_at/duration_ms nên outcome=ok bị biến thành failed, thời gian/latency rỗng. Ngay cả khi có success giả, BE trả passed trong khi FE đợi success. Summary chưa tính stale từ fingerprint hiện tại.

Bằng chứng: `test_review_summary_uses_actual_diagnostic_fields` FAIL: outcome=ok được tổng hợp thành failed. Hướng sửa: dùng DTO lịch sử thật, tính current/stale và chia sẻ enum trạng thái BE/FE.

## Các điểm còn thiếu khi đối chiếu mã

Các điểm dưới đây chưa có bài kiểm tra độc lập riêng trong phiên này; không gộp vào số10 lỗi đã tái hiện:

- EndpointsPage chuyển query lỗi/loading thành mảng rỗng; thiếu trạng thái lỗi quyền/hạ tầng trung thực. Summary dùng query key mới nhưng các mutation tạo/sửa provider và khóa chưa invalidate key này.
- Mutation tạo/xoay key giữ raw secret trong mutation result; đóng modal chỉ xóa local state, không reset mutation/cache. Response secret chưa đặt no-store tại router. Cần kiểm tra chính sách lưu secret một lần trên toàn client/cache.
- App status có trong DB nhưng chưa có API/UI suspend/revoke app. Log mới chỉ bao quanh inference và lượt thành công, chưa ghi đủ auth/rate/models/validation; chưa có liên kết request/key với các usage record của từng chặng.
- Insufficient_evidence trả content rỗng, còn qnu_extensions chưa đưa status/reason của AnswerResponse cho client phân biệt nguyên nhân.

## Kiểm chứng thực chạy

| Kiểm tra | Kết quả |
|---|---|
| FE `npm run build` gồm Vite và TypeScript | PASS; có cảnh báo chunk size/config loader hiện có |
| FE test batch `test_modelops_endpoints.test.tsx`, maxWorkers4 | PASS: 4/4 |
| BE test batch `test_application_api_keys.py`, DB riêng | PASS: 2/2 |
| BE batch + review, lượt cuối | FAIL: 3PASS/8FAIL; 2 ca batch và ca tạo cùng Idempotency-Key đạt, 8 ca review lỗi hành vi |
| FE review độc lập | FAIL: 0PASS/2FAIL sau khi bổ sung ResizeObserver cho môi trường test |
| Ruff phạm vi integration, migration, router/schema/handlers và test batch | PASS |
| Biome17 tệp thuộc batch | FAIL: dư dòng trống ở routes/modelops.endpoints.tsx:8; không auto-fix |
| Full BE/FE suite, live model inference, browser desktop/mobile/light/dark | NOT RUN |

Database lượt cuối: `qnu_v1_test_ef07bc05e7374b29`; receipt xác nhận db_dropped=true, legacy_sentinel_preserved=true. Các DB thử trước cũng đã được runner dọn.

Lệnh chính đã chạy từ repo root:

```powershell
uv run --project backendV1 --frozen --extra dev --no-sync python -X utf8 storage/artifacts/context695-modelops-resilience/run_checks.py selector -q tests/integration/test_application_api_keys.py tests/integration/test_review_context697.py --tb=short --show-capture=no --junitxml=D:/DuAnPhanMem/qnu-ai-platform/storage/artifacts/context697-modelops-review/backend-results.xml
```

Từ frontendV1:

```powershell
npm run build
npm test -- --maxWorkers=4 tests/test_modelops_endpoints.test.tsx
npm test -- --maxWorkers=4 tests/test_review_context697.test.tsx --reporter=default --reporter=json --outputFile=D:/DuAnPhanMem/qnu-ai-platform/storage/artifacts/context697-modelops-review/ui-results.json
npx biome check src/features/modelops/endpoints src/features/modelops/providers-page.tsx src/features/modelops/provider-card-grid.tsx src/features/modelops/provider-detail.tsx src/features/modelops/queries.ts src/features/modelops/requests.ts src/features/modelops/types.ts src/components/ui/view-mode-toggle.tsx src/routes/modelops.endpoints.tsx tests/test_modelops_endpoints.test.tsx --max-diagnostics=5
```

Để tái chạy review, copy hai test artifact vào các đường dẫn tests tạm tương ứng rồi dùng runner trên. Không chạy test integration bằng DB phát triển. Artifact local: `test_gateway_review.py`, `test_ui_review.test.tsx`, `backend-results.xml`, `ui-results.json` dưới storage/artifacts/context697-modelops-review; chỉ chứa dữ liệu tổng hợp.

Giới hạn: kiểm tra này chứng minh wiring/quyền/lifecycle/error contract trong phạm vi nêu trên; không đánh giá chất lượng RAG hay tốc độ model thực. Chưa sửa app; bước tiếp theo là sửa F01–F05, sau đó F06–F10 và bổ sung test đầu-cuối đúng contract.
