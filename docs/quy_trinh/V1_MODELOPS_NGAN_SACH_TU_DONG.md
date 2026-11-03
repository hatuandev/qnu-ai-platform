# ModelOps V1 — thông số model và ngân sách tự động

Context791, ngày 01/11/2026. Áp dụng `backendV1/`; FE có [prompt triển khai riêng](../ke_hoach/PROMPT_FE_MODELOPS_TU_DONG_791.md).

## Cách thêm model

Giữ luồng nhà cung cấp → khóa bảo vệ trong ModelOps → model/chức năng → cấp quyền workspace và quota. Khi thêm model, `token_limits` là tùy chọn. Không cần điền context/input/output để lưu model.

Khi tạo model con mà không gửi thông số tay hoặc `discovery_check_id`, backend tìm snapshot discovery mới nhất của đúng nhà cung cấp. Nếu chưa có metadata phù hợp, API thử lấy danh sách model bằng khóa dùng chung đang hoạt động. Chỉ sử dụng kết quả thành công có fingerprint hiện hành (endpoint/model/giao thức/key/config) và đúng model ID. Snapshot thất bại/stale/model không có không được thay bằng kết quả cũ; model vẫn được lưu với thông số chưa biết và ngân sách vận hành dự phòng.

Metadata mới chỉ áp dụng khi tạo model hoặc sync có chủ đích; không tự cập nhật model đang phục vụ theo catalog, không xóa khai báo tay, không đổi preferred model. `discovery_check_id` được gửi tường minh vẫn phải hợp lệ; không hạ thành fallback khi ID đó sai. Giữ kiểm tra embedding dimension và phạm vi credential.

## Hai lớp thông tin

Từ Context839, trợ lý mới có `max_output_tokens=null` cho chế độ tự động.
Để trống trường Token đầu ra trên giao diện để chọn chế độ này. Hội thoại và API
tích hợp truyền lựa chọn đã lưu qua ModelOps. Giá trị đã lưu trước migration0012
giữ nguyên. PUT không có trường token giữ giá trị cũ, còn null chọn tự động.
Compiler, review, hỏi đáp trực tiếp và kiểm chứng câu trả lời cũng dùng tự động khi
request để trống. Viết lại câu hỏi nối tiếp không còn tự gán 1.024 token. Ô token
kiểm chứng để trống gửi null; các mức cũ được lưu trong policy vẫn giữ nguyên.

Các biến môi trường COMPILER_MAX_OUTPUT_TOKENS, RAG_MAX_OUTPUT_TOKENS và
CONVERSATION_REWRITE_MAX_OUTPUT_TOKENS giữ để đọc cấu hình triển khai cũ, không còn
đặt trần cho request tự động mới. OCR ảnh cũ có OCR_MAX_OUTPUT_TOKENS tùy chọn;
không đặt biến này thì dùng ngân sách ModelOps. Run cũ giữ số đã ghim. MinerU
không dùng token LLM. Request chẩn đoán kết nối vẫn nhỏ có chủ đích, không phải
giới hạn cho công việc thực tế. Số mặc định trong planner review chỉ phục vụ
đọc kế hoạch cũ/helper; đường chạy mới truyền ngân sách đã phân giải.

Lỗi HTTP 400/422 chỉ cho phép điều chỉnh một lần nếu provider từ chối rõ ngân
sách đầu ra và trả mức thấp hơn hợp lệ, chưa có usage sinh được ghi nhận.
Managed chat lưu quan sát tối đa 10 phút trong tiến trình theo provider,
endpoint, model và dấu cấu hình. Giá trị quan sát không thay declaration.
Request do người dùng chỉ định mức và policy giao retry cho gateway giữ hợp
đồng riêng. Các trường token thực gửi và ngân sách đã đặt chỗ xuất hiện trong
trace và audit. Quota vẫn bao phủ request trước khi gọi.

Chỉ đọc trường lỗi có mã mức đầu ra cụ thể hoặc thông báo so sánh
`max_tokens: requested > allowed` có đủ số và ý nghĩa rõ ràng. Các lỗi khác
giữ nguyên mã lỗi. `finish_reason=length` báo phần đầu ra đã sinh bị cắt,
được luồng tài liệu chia nhỏ khi có thể. Việc tăng ngân sách một câu trả lời
đã sinh tốn thêm token cần một lượt đặt chỗ riêng, nên adapter không tự
thử lại lỗi này. Phản hồi không có usage vẫn giữ trạng thái usage chưa biết.

`token_limits`, `capacity_status` và `capacity_basis` vẫn mô tả khai báo đã lưu. Nếu chưa biết, `token_limits=null`, `capacity_status=unknown`. Chạy probe thành công không đổi thành capacity đã xác minh.

Provider detail/list và model response thêm `operational_budgets[capability]`:

- `version=qnu.operational-budget/v1`.
- `status=declared`: các giới hạn cần cho chức năng đã được khai báo; vẫn chưa đồng nghĩa đã đo trần thật.
- `status=provisional`: có sử dụng giá trị dự phòng của ứng dụng.
- `status=blocked`: không thể lập ngân sách hợp lệ; `reason_code` giải thích.
- `token_limits`: giới hạn áp dụng vào việc lập kế hoạch request; có thể khác khai báo thật.
- `sources`: nguồn từng trường (`operator_configured`, `server_reported`, `application_default`). Từ phiên này, sync giữ nguồn trường khai báo tay khi chỉ thay các trường server công bố. Bản ghi cũ thiếu nguồn từng trường dùng basis đã lưu, không được hiểu là mới đo lại.

Không ghi các giá trị application_default vào declaration DB, không nhận application_default như capacity do client tự công bố.

## Chính sách v1 khi thiếu thông tin

| Chức năng | Ngân sách ứng dụng ban đầu khi hoàn toàn chưa biết |
|---|---|
| Chat / compiler / review / answer qua chat | Envelope 32.768 token, output tối đa 4.096 token mỗi request; ngân sách đầu vào phải trừ phần output |
| Embedding | 2.048 đơn vị cận trên token cho từng text, không đặt output hoặc dimension giả |
| Rerank | 2.048 đơn vị cận trên cho từng cặp query–document; không cộng cả batch vào một context giả |
| OCR ảnh | Không tạo cận trên token ảnh từ byte/Base64; thiếu envelope ảnh/prompt thì blocked |

Đây là mức khởi đầu hữu hạn của QNU, không phải capacity được công bố hay bảo đảm mọi model nhận được. Với giới hạn có phần đã biết, giữ giá trị đó và chỉ bổ sung phần thiếu. Nếu context đã biết nhưng thiếu output, lấy `min(4096, max(1, context // 4))`. Nếu chỉ có output, dùng cận input riêng tạm tính 28.672 thay vì tự gán shared context có thể mâu thuẫn. Input/output độc lập đã khai báo đủ vẫn giữ độc lập.

Model đã khai báo context163840/output32768 vẫn dùng đúng hai giá trị đó; không bị cắt xuống mặc định. Giá trị người dùng báo trong chat không tự thay DB đang chạy; cần discovery/sync hoặc cập nhật được phép.

Phép tính đầu vào giữ cận UTF-8/framing hiện có, bao gồm schema cho chat. Usage thật chỉ lấy từ phản hồi server. Compiler dùng envelope hiệu lực để lập phần và ngân sách output đã ghim; request thực vẫn kiểm lại. Đầu vào/output tường minh vượt budget trả lỗi, không tự cắt nguồn, không bỏ bảng hay giảm số output người dùng yêu cầu trong im lặng.

## Danh tính, quyền và phục hồi

- Stale do đổi endpoint/model vẫn chặn: không dùng default để vượt qua declaration hết hiệu lực. Khai báo lại hoặc xóa khai báo có chủ đích bằng `PATCH token_limits:null` để quay về tự động. PATCH không gửi token_limits phải giữ giá trị cũ.
- Configuration hash ghi cả policy khi provisional. Hai lần resolve lúc chuẩn bị request phải khớp; tác vụ đã ghim không được đổi budget giữa chừng. Hash cho runtime đã khai báo đầy đủ giữ cơ chế cũ.
- Giữ `resolve_workspace_access`, capability/grant, trạng thái nhà cung cấp/model, credential mã hóa, egress, quota và usage reservation/settlement. Không thêm `.env` runtime key hoặc tự tăng quota.
- Trace runtime provisional chứa policy/nguồn hiệu lực, không chứa credential; quota vẫn được đặt chỗ trước gửi và chỉ quyết toán bằng usage quan sát. Timeout/unknown không được tính 0 hoặc gọi lại tự động.
- HTTP400/422 từ server không mặc định là lỗi token. Từ Context839, chỉ lỗi giới hạn output rõ ràng mới được điều chỉnh một lần theo hợp đồng ở trên. Output truncated, schema sai, 429 và timeout giữ luồng lỗi riêng; không đổi provider. Compiler refinement tiếp tục giữ giới hạn và lịch sử.
- Không có thay đổi OCR/tokenizer native mới, registry model bên ngoài hoặc adapter mới cho giao thức chưa hỗ trợ. Embedding chưa biết dimension và OCR chưa biết cách tính ảnh vẫn cần kiểm tra riêng.

## Bài học từ llm_wiki và điểm điều chỉnh

Đã đối chiếu mã upstream tại commit `e08cfce65aad8b76b13546a081c1a8d4422b70c3`:

- [Preset resolver](https://github.com/nashsu/llm_wiki/blob/e08cfce65aad8b76b13546a081c1a8d4422b70c3/src/components/settings/preset-resolver.ts): override → preset → cấu hình dự phòng.
- [Context budget](https://github.com/nashsu/llm_wiki/blob/e08cfce65aad8b76b13546a081c1a8d4422b70c3/src/lib/context-budget.ts): mặc định204800 ký tự, response15%, index5%, page50%; đây không phải token capacity đo trên server.
- [Wire providers](https://github.com/nashsu/llm_wiki/blob/e08cfce65aad8b76b13546a081c1a8d4422b70c3/src/lib/llm-providers.ts): nhánh TS OpenAI không tự thêm max_tokens nếu caller không đưa; Anthropic suy ngân sách output từ reserve, có cap16384. [Rust agent](https://github.com/nashsu/llm_wiki/blob/e08cfce65aad8b76b13546a081c1a8d4422b70c3/src-tauri/src/agent/provider.rs) có mặc định output2048.
- [Connection tests](https://github.com/nashsu/llm_wiki/blob/e08cfce65aad8b76b13546a081c1a8d4422b70c3/src/lib/connection-tests.ts) dùng request mẫu nhỏ, không đo trần context.

QNU học cách giảm yêu cầu nhập tay và dùng ngân sách dự phòng. QNU vẫn gửi output hữu hạn vì cần quota và artifact có danh tính; không sao chép cơ chế bỏ max_tokens hoặc coi giới hạn ký tự upstream là token.
