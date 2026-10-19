# Triển khai JSON output contract — phiên549

## Contract và provider

LLMGenerateRequest nhận OutputContract tùy chọn, chỉ chọn backend preset
qnu_semantic_selector_v1; không nhận JSON schema tùy ý. Chat không truyền contract
giữ payload cũ. ModelSemanticProposal vẫn là schema nghiệp vụ; compiler tạo wire
required đầy đủ, additionalProperties=false và bỏ default; không bỏ selector
unresolved/context_followups. Hash business/wire lưu riêng. Không đổi snapshot.

InferenceService resolve capability tại từng route bằng load_chat_capabilities
hiện có, ghim endpoint/model. Chưa có khai báo thì không coi là native support.
Policy semantic mặc định yêu cầu json_schema, cho phép json_object/prompt_only;
strict-required có thể cấu hình không cho weaker. Requested/effective/reason có
trace. Adapter chưa triển khai contract bị từ chối tường minh; hiện hỗ trợ đường
OpenAI Chat Completions adapter, không gửi payload đó vào API khác.

OpenAIAdapter gửi response_format json_schema/strict/schema hoặc json_object khi
mode đã được resolve. Prompt-only không gửi response_format. Thương lượng token/
temperature không bỏ format. Signature inspection thay catch TypeError rồi gọi
lại thiếu tham số; old adapter không có thinking_budget vẫn giữ output_contract.
Contract+stream từ chối rõ. HTTP400 có schema/request sai không làm key invalid
hoặc quay vòng key; unsupported rõ ràng có thể qua route fallback đã cho phép,
HTTP context/auth/quota vẫn phân loại qua taxonomy hiện có.

## Parser và ngân sách

semantic_selector kiểm refusal/finish/empty trước JSON. Finish thiếu là unknown,
không tạo stop. Schema/JSON modes chỉ nhận JSON trực tiếp; prompt-only cho đúng
một cặp fence bao toàn bộ JSON. Trace tách raw/normalized content SHA256; HTTP
body và payload có hash riêng. Không ghép choices/reasoning/tool args; contract
có nhiều choice bị chặn. Metadata ID upstream chỉ lưu hash để tránh echo dữ liệu.

json.loads kiểm toàn bộ content với duplicate-key/non-finite rejection, root
object và required fields mọi cấp; Pydantic strict kiểm kiểu/enum/bounds/extra.
Không tự thêm [], sửa số/chuỗi, ghép object, lấy prefix hoặc JSON repair. Chỉ JSON
syntax được retry tối đa1lần/packet gốc; expansion không reset counter. Feedback
chỉ nêu định dạng, giữ packet/registry/schema và trả lại toàn object. Sai binding,
scope/context, refusal, schema shape không được format retry.

Shared deadline548 và staging private-copy giữ nguyên. max_calls/tổng logical
input bytes tính schema/feedback/các logical attempts; transport retry dùng một
scope hiện có cho cả semantic run. HTTP input bytes của cả retry/fallback được
charge trước gửi vào budget tổng; metrics tách logical/provider/transport calls.
Max-packet bytes ở mức context/system/schema, HTTP wrapper bytes được đo riêng;
không gọi số byte logical là số byte HTTP thực. Không hạ output budget/crop
semantic catalog tại adapter khi request có contract.

## Quyền và phạm vi

Không đổi provider/model/default/endpoint/timeout DB ứng dụng. ModelOps config và
encrypted keys được copy READ ONLY sang DB test. Không schema migration trên
DB chung; reusable harness548 tạo DB nonce mới riêng cho phiên549. Dữ liệu thử
trỏ localStorage tạm, MinIO/Qdrant/Redis dead-port1; live chỉ gửi fixture mô phỏng
DOCX đã được phép. G4 dùng chính HTTP route UI qua ASGI, real services/DB/Storage/
ModelOps/provider; actor override chỉ cho generation TEST, không phải human review.

Không sửa parser/OCR/resolver/RAG hoặc làm yếu evidence validators để live đạt.
Xem [VALIDATION_REPORT](VALIDATION_REPORT.md); live chưa tạo được valid proposal,
không có review/apply thật và không tuyên bố E2E PASS.
