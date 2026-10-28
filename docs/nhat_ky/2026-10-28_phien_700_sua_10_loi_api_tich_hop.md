# Context700 — Sửa10lỗi Providers/API tích hợp

Ngày: 2026-10-28. Yêu cầu: sửa toàn bộ10finding trong [review697](./2026-10-28_phien_697_review_provider_va_api_tich_hop.md).

## Phạm vi và quyết định

- Giữ batch chưa commit của người dùng; sửa backendV1 và frontendV1 tại module integration/ModelOps. Không chuyển sang backend/frontend cũ, không thêm framework hay cài dependency.
- Dùng skill QNU clean-code/backend/frontend/ModelOps, giữ workspace là biên quyền với machine membership thật.
- Gateway hiện là single-turn: xử lý đúng một user message, dùng cấu hình trợ lý. History/system/assistant messages và tham số chưa hỗ trợ trả400 tường minh; không nhận rồi bỏ qua. Hội thoại nhiều lượt vẫn có Conversations V1 riêng; phiên này không mở rộng nó qua gateway ngoài.
- URL lấy từ PUBLIC_BASE_URL do server cấu hình. Thiếu cấu hình trả503; không suy từ header hay frontend origin. Thêm giá trị ví dụ vào `.env.example`, không sửa `.env` đang chạy.
- Bản review697 đã tái hiện lỗi trước sửa. Ca regression được giữ thành test chính thức; không đổi assertion chỉ để xanh. Điều chỉnh fixture theo hợp đồng scope mới và dùng Redis fake khỏe cho ca không kiểm hạ tầng, Redis test thật cho limiter.
- Có công việc Context699 về seed tài khoản/workspace diễn ra đồng thời. Không sửa các tệp dev_accounts/dev_gate/identity router/seed script/.gitignore của công việc đó. Mọi cập nhật index đọc lại bản hiện tại và giữ nguyên nội dung đồng thời.

## Các lỗi đã sửa

| Finding | Thay đổi | Bằng chứng trọng tâm |
|---|---|---|
| F01 — mất cấu hình trợ lý | Snapshot AssistantResponse, truyền toàn bộ RagPolicy/persona/max_output_tokens, reranker container và checkpoint vào RAG hiện có; kiểm revision | test_review_assistant_policy_and_persona_are_preserved; kiểm tra pipeline thật riêng |
| F02 — thu hồi vẫn trả200 | check_access dùng populate_existing, kiểm lại key/app/expiry/workspace/membership và assistant active/revision/lifecycle | test_review_revocation_from_another_connection_stops_response;6biến thể đổi quyền trong lúc xử lý |
| F03 — xoay đồng thời tạo2khóa | SELECT FOR UPDATE + populate_existing trên khóa; rotate/suspend/revoke dùng cùng chuyển trạng thái được khóa, transaction nguyên tử | test_review_concurrent_rotation_cannot_mint_two_replacements; ca tạo cùng Idempotency-Key vẫn chỉ1khóa |
| F04 — scope rỗng thành tất cả | Create DTO yêu cầu allow_all_assistants=true rõ ràng hoặc danh sách không rỗng; FE chặn lựa chọn hạn chế rỗng | test_empty_scope_requires_explicit_all_permission; FE regression và browser |
| F05 — Redis lỗi bỏ limiter | None/exception trả503 trước RAG, vượt RPM/RPD trả429 kèm Retry-After, dùng namespace triển khai | test_review_redis_unavailable_does_not_disable_rate_limit; Redis thật và exception branch |
| F06 — bỏ history/params âm thầm | Contract single user message; history/system/tools/sampling/max_tokens/extra fields bị từ chối400; tài liệu và hướng dẫn FE nêu giới hạn | test_review_multiturn_is_processed_or_explicitly_rejected;8biến thể unsupported |
| F07 — quota429thành500/lỗi lộ thông tin | Giữ AppException status/code, HTTPException headers; error OpenAI cho validation400/Integrity409; redaction qnu_live; lỗi bất ngờ thông báo chung | test_review_provider_error_preserves_status;5status và redaction; real Redis Retry-After |
| F08 — DTO endpoint lệch | FE đọc đúng base_url/openai_endpoint/protocols/capabilities; bỏ fallback origin; hiện lỗi/loading thay vì mảng rỗng | FE actual backend DTO regression; browser endpoint8014 khác origin3004 |
| F09 — tin forwarded host | Cấu hình PUBLIC_BASE_URL là nguồn duy nhất; thiếu trả public_endpoint_unconfigured503 | test_review_endpoint_config_ignores_untrusted_host; test_missing_public_url_fails_without_origin_guessing |
| F10 — diagnostic thành công báo failed | Summary service batch dùng DiagnosticCheck thật và fingerprint chung với detail; success/failed/unsupported/untested/stale thống nhất BE/FE | test_review_summary_uses_actual_diagnostic_fields; test_summary_marks_old_fingerprint_stale; test diagnostic API |

Bổ sung sát các lỗi này: cache summary được invalidate sau provider/key/probe; create/xoay trả no-store và mutation không giữ secret result; app tạo cùng key không commit riêng trước khi key hợp lệ; qnu_extensions có status/reason của RAG. Không tự thu hồi hay đổi scope các khóa đã tạo trước bản sửa; khóa cũ có [] vẫn giữ nghĩa all, hướng dẫn quản trị thu hồi/tạo mới khi cần.

## Tệp chính

- `backendV1/qnu/domains/integration/{access,gateway,router,schemas,service}.py`: quyền/limiter, execution, HTTP, DTO và lifecycle khóa.
- `backendV1/qnu/domains/modelops/diagnostics/{service,summary}.py`, ModelOps router/schemas: fingerprint và summary batch đúng dữ liệu.
- `backendV1/qnu/api/handlers.py`, `platform/{config,redaction}.py`, `.env.example`: error contract và trusted URL.
- `backendV1/tests/integration/test_application_api_keys.py`, `test_integration_gateway_regressions.py`, `test_integration_gateway_pipeline.py`: API/DB/concurrency/hạ tầng và pipeline.
- ORM integration khai báo đúng partial unique/composite indexes đã có trong0004; đồng bộ gate migration/head/readiness với0004, giữ bảo vệ downgrade không xóa dữ liệu.
- FE ModelOps types/queries/diagnostic-queries/provider-card-grid, endpoints components, route formatting; test_modelops_endpoints/test_modelops_integration_regressions/test_integration_secret_cache.
- [Quy trình41](../quy_trinh/41_api_tich_hop_ung_dung.md), mục lục quy trình, nhật ký/snapshot/index.

## Kiểm chứng

| Gate | Kết quả |
|---|---|
| Regression API integration + diagnostics | PASS:44ca,0FAIL/0SKIP |
| FE full suite sau batch code | PASS:406ca/42file |
| FE bổ sung kiểm secret mutation cache | PASS:1ca riêng; tổng đã chạy407ca |
| FE build + TypeScript | PASS; cảnh báo chunk/config loader hiện có |
| Ruff phạm vi | PASS |
| Biome19file thuộc phạm vi +1file test secret cache, diff check | PASS |
| Recovery bằng Proactor | PASS:4ca; DB thử dọn và sentinel giữ nguyên |
| Migration/schema/readiness regression sau đồng bộ0004 | PASS:7ca; Alembic compare_metadata không có diff |
| Browser API thật, DB riêng | PASS: desktop1366 sáng; mobile390 sáng/tối; URL8014 đúng, scope rỗng bị chặn, cuộn bảng trong container không tràn trang. Chưa kiểm desktop tối riêng |
| Full backend Selector, không gồm recovery | PASS:755ca/0FAIL/0SKIP;1776.08giây gồm chuẩn bị/dọn DB |
| Gateway → RAG → ModelOps thật với fake model HTTP local | PASS:1ca, có nguồn và giữ model/persona/max_output_tokens |
| Model server thật/corpus người dùng | NOT RUN; không cần live inference để sửa10lỗi này |

Lệnh từ repo root:

```powershell
uv run --project backendV1 --frozen --extra dev --no-sync python -X utf8 storage/artifacts/context695-modelops-resilience/run_checks.py selector -q tests/integration/test_application_api_keys.py tests/integration/test_integration_gateway_regressions.py tests/integration/test_modelops_diagnostics_api.py --tb=short --show-capture=no
uv run --project backendV1 --frozen --extra dev --no-sync python -X utf8 storage/artifacts/context695-modelops-resilience/run_checks.py selector tests -q --ignore=tests/integration/test_recovery_666.py --tb=short --show-capture=no
uv run --project backendV1 --frozen --extra dev --no-sync python -X utf8 storage/artifacts/context695-modelops-resilience/run_checks.py proactor -q tests/integration/test_recovery_666.py --tb=short --show-capture=no
uv run --project backendV1 --frozen --extra dev --no-sync python -X utf8 storage/artifacts/context695-modelops-resilience/run_checks.py selector -q tests/integration/test_integration_gateway_pipeline.py --tb=short --show-capture=no
```

Frontend cwd `frontendV1`: `npm run build`, `npm test -- --maxWorkers=4`, test_secret_cache riêng. Biome chỉ file thuộc phạm vi; không sửa lint toàn repo. Full suite ban đầu chưa có file test cache/pipeline thêm sau đó; các ca này có lượt kiểm riêng.

Ca pipeline bổ sung ban đầu FAIL ở assertion của probe tìm persona trong system message. Đối chiếu `rag/answer/drafting.py` xác nhận contract hiện có đặt persona trong JSON `assistant_style`, không nâng dữ liệu này thành quyền/system policy. Chỉ sửa probe đọc đúng trường JSON; lượt chạy lại PASS, không sửa prompt ứng dụng để làm test xanh. Preview ban đầu đổi cách chạy Uvicorn sang cùng loop của TestClient để tránh dùng AsyncSession pool qua hai loop; cả DB preview đều đã dọn, không ảnh hưởng dịch vụ người dùng.

Lượt full đầu bị ngắt khi turn bị gián đoạn: hoàn thành239ca, có1failure tại downgrade test do0004 chưa giữ wording bảo vệ và gate còn ghim0003. Không gọi lượt này PASS. DB `qnu_v1_test_a941a03eaca84ec7` không còn tiến trình/session; đã kiểm sentinel legacy rồi dọn đúng DB đó bằng script cleanup_interrupted_test.py, không terminate session hay đụng DB khác. Kiểm tra tập trung schema/readiness sau đó tái hiện6FAIL/1PASS (ORM index mismatch và gate cũ), sửa khai báo index và cập nhật expected head/chain cho0004, rồi7PASS. Full chạy lại sau batch này PASS755ca; recovery chạy riêng4PASS, tổng backend759ca khác nhau đều đã chạy đạt. FE full406PASS cộng test mới secret-cache1PASS =407ca đã chạy đạt.

Receipt cuối: `qnu_v1_test_056e5a8b1d4a44af`, pytest_exit=0, db_dropped=true, legacy_sentinel_preserved=true. Artifact `full755-results.xml`/`full755-receipt.json` cùng các receipt focused44/schema7/pipeline1/recovery4 trong `storage/artifacts/context698-integration-fixes/`. Không lặp full suite sau khi đạt; các thay đổi sau lượt này chỉ là hoàn tất tài liệu.

Artifact local trong `storage/artifacts/context698-integration-fixes/` (nhãn tạm của phiên khi bắt đầu): ảnh desktop/mobile, preview test/config Vite riêng; build/FE-full log ở `storage/artifacts/context697-modelops-review/fix-*.log`. Không đưa dữ liệu thử/model/secret vào Git.

## Vận hành và giới hạn

- Tất cả ca DB dùng namespace qnu_v1_test_* và migration riêng, không sao chép row/key của người dùng. Redis test dùng DB15 và key ngẫu nhiên, dọn đúng key của bài kiểm.
- Preview8014/3004 chỉ của phiên này, đã dừng; tab thử đóng và viewport/theme trả về mặc định. Không restart API/worker/FE người dùng. Test preview tạm đã gỡ khỏi thư mục tests, giữ bản artifact để tái hiện.
- Không migrate DB live, không sửa env runtime, không gọi upstream AI server, không deploy/commit/push.
- Trước khi dùng bản mới: áp migration V1 đã chuẩn bị nếu môi trường chưa có0004, cấu hình PUBLIC_BASE_URL đúng địa chỉ backend, rồi dùng quy trình khởi động V1 được quản trị.
- Các hạng mục mở rộng ngoài10finding (app-wide status UI/API, toàn bộ auth/models/validation audit, liên kết usage mỗi chặng, OpenAI multi-turn/streaming/tools) chưa bổ sung. Không gọi đây là gateway OpenAI đầy đủ mọi tính năng.
