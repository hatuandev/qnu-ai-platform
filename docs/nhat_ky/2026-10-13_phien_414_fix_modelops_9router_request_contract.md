# Phiên 414 Sửa ModelOps tương thích 9router

## Mục tiêu và phạm vi

Người dùng đồng ý sửa đề xuất tại cuối phiên413: đồng bộ request test/runtime, phân loại lỗi chính xác, ghi nhận model thực sự phục vụ. Phạm vi là ModelOps chat/probe/usage, không triển khai thay đổi retrieval/readiness/nguồn của đề xuất tổng thể trước đó. Không reset DB/Redis, đổi tên model, thay endpoint/khóa của người dùng, đổi embedding, duyệt hay tái xuất bản.

Áp dụng skills qnu-modelops-resilience, qnu-backend-architect và qnu-clean-code-architect: bounded negotiation, async I/O, AppException, surgical changes và regression trước sửa. Không có thay đổi frontend.

## Giải pháp

### Contract chung cho OpenAI-compatible chat

`providers/chat_contract.py` xây dựng payload giữ nguyên model alias, endpoint, messages và auth. Generate luôn gửi stream=false; streaming gửi true. Probe dùng ngân sách nhỏ32 token thay cho1; khi upstream HTTP400 chỉ rõ minimum, probe có thể tăng tới bound trong trần256. Runtime không tự tăng hạn mức người dùng.

Chỉ HTTP400 có bằng chứng tham số rõ ràng mới được thương lượng, tối đa3 lần chỉnh trong một request: bỏ temperature khi upstream tuyên bố unsupported, đổi tên tham số token theo chỉ dẫn, hoặc đáp ứng minimum của probe. Không suy khả năng từ tên model, không hardcode GPT/9router aliases. 401/429/5xx, model không được cấp quyền và lỗi mạng không bị biến thành negotiation thành công.

`OpenAIAdapter` dùng chung contract cho generate/stream. HTTP200 phải có JSON completion nội dung thật hoặc SSE đúng định dạng; response rỗng/error/wrongmode bị AppException. Không dùng reasoning_content thay câu trả lời. Stream đã phát token mà lỗi không gọi lại generate để phát lại nội dung; parse errors/EOF bất thường phải lộ lỗi. Model/usage thực trong phản hồi được giữ lại.

### Capability trong DB và probe

`services/chat_probe.py` gọi cùng adapter, đúng provider/model đã chọn, không failover sang provider khác để báo model khả dụng. Phân biệt request rejected, credential/network/protocol errors; lưu upstream HTTPcode/message đã che secret và URL. Không phân loại401/403/400 thành model nonexistent;404 mới unavailable. Loại shortcut production fake healthy do thiếu key hoặc key chứa chữtest/mock ở nhánh probe còn lại; Custom không còn tự chèn key giảollama khi thiếu credentials.

`services/chat_capabilities.py` lưu quan sát đã thành công trong JSONB extra_config.chat_request_contracts, keyed exact alias và endpoint, kèm observed_at. Tải runtime theo đúng alias/endpoint; đổi endpoint không reuse quan sát cũ. Row lock + deep copy JSONB bảo toàn settings/keys/models hiện có; không migration CSDL. API test trả served_model/request_capabilities/error_code/http_status. UI hiện hữu dùng message nên thấy nguyên nhân thật và ghi chú temperature không áp dụng, không cần component mới.

### Model thực và quota

Generate API thêm requested_model, provider_id, fallback_reason; model hiện có lấy từ phản hồi thật. Runtime log các lỗi provider có model/endpoint identity và sanitized cause, success fallback ghi lý do trong usage error_message để truy vết (không ghi khóa). Streaming dùng served_model và usage từ SSE nếu có; adapters không trả usage vẫn giữ estimate cũ.

Assistant chat/stream không sinh thêm qnu_workflow usage dựa trên model config và chiều dài text. Workflow completion/timing ghi log riêng. Usage statistics bỏ các qnu_workflow estimates legacy khỏi aggregation nhưng không xóa dữ liệu lịch sử. Quota bỏ cộng ở cả inference và accounting: accounting là nơi cộng một lần; regression kiểm tra chính xác một lần.

## Các tệp thay đổi

- `backend/app/modules/modelops/providers/chat_contract.py` (mới).
- `backend/app/modules/modelops/providers/openai_adapter.py`.
- `backend/app/modules/modelops/providers/__init__.py`.
- `backend/app/modules/modelops/services/chat_probe.py` (mới).
- `backend/app/modules/modelops/services/chat_capabilities.py` (mới).
- `backend/app/modules/modelops/services/provider_service.py`.
- `backend/app/modules/modelops/services/inference_service.py`.
- `backend/app/modules/modelops/services/usage_accounting_service.py`.
- `backend/app/modules/modelops/schemas.py`.
- `backend/app/modules/assistants/services/assistant_chat_service.py`.
- `backend/tests/test_chat_request_contract.py` (mới), `test_modelops.py`, `test_modelops_usage.py`, `test_assistants.py`.
- Nhật ký, README, PROJECT_CONTEXT và WORK_LOG.

Giữ nguyên các thay đổi dirty từ phiên khác, gồm provider_key_rotation_service/model_runtime_resolver/knowledge/worker/FE. Không formatter bulk các module cũ.

## Kiểm thử

Regression trước sửa:6fail/3pass, tái hiện payload không có streamfalse, probe1token và HTTP200 rỗng bị coi thành công. Sau sửa:16 contract cases, cả đường lỗi/transport thực qua MockTransport với keyfixture không kích hoạt production mock path, kiểm tra alias nguyên vẹn, runtimebudget không tăng, HTTP400 unrelated,401/429/500, JSON/SSE malformed/empty, streampartial không replay, bí mật đượcche và JSONBcopy-on-write/endpointbinding.

Scoped suite ModelOps/assistant/RAGcontract/keyrotation: **92 passed**. Kiểm tra cuối contract+usage sau tinh chỉnh phân loại401/403: **21 passed**. Ruff toàn backend **đạt**, chỉ có cảnh báo không đọc được một số thư mục temp cũ. Full backend: **1028 passed, 11 failed, 4 skipped**,82.83s. Mười một lỗi thuộc cùng danh sách baseline các phiên trước: consulting dispatcher2, publishing/APIpermission6, reconciliation1, authcookie1, universaltools1; không mở rộng sửa. Log `backend/storage/pytest414_verified.log`. Ca cũ yêu cầu assistant ghi config model giả đã cập nhật thành regression không ghi inference khi workflow không gọi model.

## Xác minh runtime thật trên máy người dùng

- API đúng nút Test tất cả cho provider `prov_20261013041934`, local localhost20128:2/2available, cả `gh/gpt-5.4-mini` và `gh/gpt-6-luna[1m]` trả completion thật; không fallback. Kết quả cho biết temperature_supported=false, lưu DB sau probe thành công.
- `/modelops/generate`: requested gh/gpt-5.4-mini, served gpt-5.4-mini, provider custom/qnu9router, HTTP200/OK, is_fallbackfalse, fallback_reasonnull, usage2820tokens.
- Chatbot admissions hỏi hotline: HTTP200/answered,1800.55.88.49, citations; usage đúngcustom/gpt-5.4-mini,8902tokens, không có record qnu_workflow mới trong conversation test.
- Streaming qua ModelOps với requested gh/gpt-6-luna[1m]: trảOK, servedgpt-6-luna, custom,2794tokens, fallbackfalse.
- Bằng chứng `backend/storage/modelops414_live.json` và `backend/storage/modelops414_stream.json`; không chứa credentials.

Live probes tạo records chat/usage/workflow/keyevents và capability observations theo workflow bình thường. Không xóa/cập nhật source/index publication pointers hoặc reset dữ liệu; không cam kết corpus hiện tại vẫn cùng IDs phiên413 vì người dùng có thể tiếp tục test/reset giữa các lượt.

## Giới hạn và bước tiếp

Chưa chạy lại full82Q&A/Ragas vì nhiệm vụ này chỉ sửa ModelOps. Không khẳng định chất lượng RAG đã đạt. Cảnh báo readiness đếm legacy, bảo toàn reranker provider khi lưu trợ lý, evidence prose5.173 và nhầm năm/đợt/phủ định vẫn là hạng mục riêng đã nêu ở phiên413; không tự gỡ gate/tắtguard/publish.

Model profile hiện vẫn cho phép người dùng nhập temperature dù model không hỗ trợ; runtime/probe bỏ nó theo observation xác minh và APItest giải thích rõ. UI quản trị capability tùy chỉnh, provider tuple pin và các cải tiến toàn diện về pricing/telemetry là bước riêng, không thêm trong phiên này.

## Bài học

Test/model runtime phải chia sẻ transport contract. HTTP200 và tên cấu hình không đủ làm bằng chứng inference; cần payload hợp lệ, protocol đúng, nội dung thật và servedmodel/usage từ upstream. Không reset DB để chữa lỗi tương thích request.
