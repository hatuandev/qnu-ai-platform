# Trợ lý và hội thoại — Backend v1

Mở rộng hiện hành: [RAG policy, metadata, context và kiểm chứng](rag-policies.md).
Trợ lý có thể dùng dense/hybrid/rerank; snapshot cũ giữ mặc định dense. Metadata
scope có dẫn chứng, context window và judge đều được cấu hình tường minh ở BE.

Context649 nối API [hỏi đáp có nguồn](rag-answers.md) vào cấu hình trợ lý và lịch sử
bền vững trong PostgreSQL. Workspace vẫn là biên giới quyền riêng của v1 theo ADR;
không thay quyền/schema/runtime của `backend/`.

## Phạm vi

- Trợ lý có name/description/persona, **một collection**, chat provider hoặc default
  ModelOps, topK, history_turns và output budget. Workspace admin/platform admin
  quản lý; member có quyền workspace được chọn trợ lý để chat. Persona chỉ gợi ý
  giọng văn, không thay quy tắc bằng chứng, cấp tool hoặc quyền truy cập.
- Mỗi conversation có owner lấy từ actor server, assistant ID/revision/snapshot,
  collection và document scope cố định. Chỉ owner đang có quyền workspace được
  đọc/gửi; platform admin cũng không được tự đọc chat của người khác bằng ID.
- Mỗi `chat_turns` lưu **một cặp hỏi–kết quả**: question gốc, câu hỏi làm rõ,
  history IDs đã dùng, answer/statements/sources/trace hoặc status/error thật.
  Không tạo hai message row cho cùng cặp. API phân trang theo turn_no.
- Chưa chia sẻ/public/embed, nhiều collection, tools, streaming hoặc bộ nhớ dài hạn.

Sau khi kiểm tra quyền và giữ chỗ lượt hỏi, mọi lượt mới gọi model Chat qua
ModelOps để nhận diện ý định và làm rõ câu hỏi nối tiếp trong cùng một request.
Model tự viết lời chào, cảm ơn, giới thiệu hoặc từ chối tiết lộ thông tin nội bộ
theo tên/persona đã ghim. Không dùng regex hay câu trả lời mẫu cho nhánh này.
Kết quả `direct_reply` được lưu trong lịch sử, replay cùng khóa không gọi lại.
Lượt giao tiếp không truy vấn chỉ mục và không đưa vào history làm rõ nghiệp vụ.
Câu có nội dung cần dữ kiện, kể cả có lời chào, được phân sang `knowledge` rồi
đi qua RAG và kiểm dẫn chứng. Router không có bằng chứng nên không được trả lời
dữ kiện. Phân loại vẫn có thể sai do model và cần kiểm chứng bằng các ca thực tế.

## API

Prefix `/platform/v1alpha1/workspaces/{workspace_id}`.

| Method/path | Ý nghĩa |
|---|---|
| POST/GET `/assistants` | Tạo / danh sách phân trang |
| GET/PUT `/assistants/{assistant_id}` | Đọc / thay toàn cấu hình, PUT cần expected_revision |
| POST/GET `/conversations` | Mở / danh sách hội thoại của chính actor |
| GET/PUT `/conversations/{conversation_id}` | Đọc / đổi title và active/archived |
| POST `/conversations/{conversation_id}/turns` | Gửi câu hỏi, bắt buộc Idempotency-Key |
| GET `/conversations/{conversation_id}/turns` | Lịch sử theo thứ tự, limit/offset |
| GET `/conversations/{conversation_id}/turns/{turn_id}` | Trạng thái/kết quả một lượt |

Tạo trợ lý, ví dụ:

```json
{
  "name": "Trợ lý tuyển sinh",
  "description": "Trả lời từ tài liệu đã xuất bản",
  "persona": "Giải thích ngắn gọn bằng tiếng Việt.",
  "collection_id": "col_...",
  "chat_provider_id": "prv_...",
  "top_k": 5,
  "history_turns": 3,
  "max_output_tokens": 2048,
  "is_active": true
}
```

Mở hội thoại bằng `{ "assistant_id": "ast_...", "title": "..." }`, có thể thêm
`document_ids` không trùng, thuộc collection. Bỏ document_ids nghĩa là collection;
không có cơ chế tự mở rộng khi ít kết quả. Không nhận owner_ref/history/system
prompt hoặc provider URL từ client. Đổi collection phải tạo trợ lý mới. Mỗi PUT
trợ lý tăng revision; chat cũ vẫn đọc được theo quyền/nguồn, nhưng muốn gửi lượt
mới phải mở conversation mới với config mới. PUT dùng expected_revision để tránh
ghi đè thay đổi đồng thời.

Gửi lượt đầu, header `Idempotency-Key: turn-001`:

```json
{ "question": "Ghi chú của bảng chỉ tiêu tuyển sinh ghi gì?", "expected_turn_no": 0 }
```

Lượt tiếp theo dùng key mới và expected_turn_no bằng last_turn_no từ GET conversation.
Chỉ một turn running/conversation; cặp key/body cũ replay không gọi model lại.
Key cũ khác body trả409; sequence cũ hoặc conversation busy trả409. Failed/uncertain
replay trả conflict và yêu cầu xem trạng thái, không tự gửi lại. Khi sửa câu hỏi hoặc
chủ động thử lượt mới cần key mới/sequence mới, và có thể phát sinh usage mới.

## Luồng thực thi

1. Resolve workspace, owner, collection, active assistant và revision; chụp request
   hash, tăng sequence, lưu turn running/lease và audit trong transaction trước HTTP.
2. Chọn tối đa history_turns **câu hỏi người dùng** của các lượt completed trước,
   đúng conversation. Không dùng assistant text hoặc citation cũ làm dữ kiện.
   Không lấy failed/uncertain turn hoặc lịch sử client tự gửi.
3. Gọi model điều phối một lần, kể cả lượt đầu. Chỉ gửi tên, persona và cửa sổ
   câu hỏi người dùng, không gửi credential hoặc cấu hình quyền. JSON schema
   `qnu.conversation.route/v2` phân biệt knowledge và giao tiếp. Câu dữ kiện có
   `answer=null`, dùng standalone_question để tìm nguồn. Model báo cần làm rõ
   thì trả409. Các nhánh giao tiếp có answer do model sinh và kết thúc tại đây.
4. Với knowledge, gọi pipeline answer648 bằng câu hỏi gốc và query đã làm rõ;
   persona chỉ thêm style. Search/evidence/citation/source checks vẫn dùng mã cũ.
   History không chứng minh dữ kiện và không thay document/collection scope.
5. Checkpoint trước generation và trước hoàn tất: owner/membership, conversation
   active, assistant revision, lease. Answer pipeline kiểm lại source/publication/
   active index/model sau HTTP. Archive/config/quyền đổi thì không lưu đáp án completed.
6. Persist result cùng audit, trả turn. Lỗi provider/validation vẫn là RFC7807;
   row failed giữ mã lỗi để đọc lại, không tạo câu trả lời thay thế.

Ledger riêng cho routing và generation, embedding vẫn được accounting như search.
Giao tiếp cần một chat call, knowledge tối đa một routing + một answer call
(chưa tính các bước kiểm chứng cấu hình riêng). `rewrite_trace` lưu version,
route, model/provider, reasoning, usage và ngân sách đã áp dụng. Routing dùng
chính sách tác vụ `answer`, gồm lựa chọn model và reasoning của ModelOps.
Ngân sách theo caller hoặc ModelOps tự động, lỗi provider/JSON vẫn báo lỗi thật.
Không tự tạo câu trả lời mẫu khi model lỗi. Không có worker hay cron mới.

## Lịch sử, phục hồi và giới hạn

Tắt trợ lý qua API cập nhật (`is_active=false`) hủy bền vững các lượt đang chạy
thuộc trợ lý đó. Lưu trữ hội thoại qua API cập nhật (`status=archived`) chỉ hủy
lượt của hội thoại do người gọi sở hữu. Cả hai dùng cơ chế hủy của lifecycle;
thay trạng thái, hủy và audit cùng transaction. Nếu transaction lỗi thì không
giữ riêng việc hủy. Đổi tên hội thoại đang active không hủy lượt.

Bật hoặc mở lại không nhận lại phản hồi của lượt đã hủy, dù model vừa trả về.
Replay key/body của lượt đó báo `conversation_turn_cancelled`; gửi câu hỏi mới
với key mới và `expected_turn_no` hiện hành. Dừng/bật không đổi revision cấu hình
trợ lý. Các câu trả lời đã hoàn tất được giữ; token đã quan sát vẫn được ghi nhận.

GET history kiểm lại các source được dẫn mà không gọi model/vector search thêm.
Nếu source/publication/index không còn hợp lệ, trả result=NULL và
`source_status=unavailable`, giữ status/sequence/question của bản ghi. Lỗi storage/
provider hạ tầng chưa phân giải được vẫn trả lỗi, không giả đánh dấu nguồn đã mất.
Raw row trong DB không bị xóa/chỉnh bằng chứng. HTTP conversation/history là
`private, no-store`; không có raw DB dump endpoint.

Turn running hết lease chuyển uncertain khi đọc turns hoặc trước gửi lượt tiếp;
không tự chạy lại HTTP. Worker/request cũ trả muộn không vượt checkpoint để lưu
completed. Nếu client mất response, dùng GET theo ID hoặc gửi lại đúng key/body;
không đổi key để retry mù. Nếu process chết, chưa có background recovery heartbeat;
lease chỉ fence kết quả, không là cơ chế tự nối tiếp tác vụ.

Mặc định lease900s, history tối đa3cặp câu hỏi đã hoàn tất (config0–10), budget
history16000UTF-8byte. Routing/output theo cấu hình trợ lý và ModelOps. History quá budget trả422, không
cắt âm thầm. Model capacity/quota vẫn lấy DB ModelOps; đây không phải trần model
hardcode. Chuỗi hội thoại dài lưu đầy đủ trong DB nhưng chỉ cửa sổ history được gửi.

Baseline `0001_initial_schema` gồm `chat_assistants/chat_conversations/chat_turns`
với FK scope, unique sequence/key và partial unique running. Không chạm bảng
assistants/conversation legacy. Downgrade từ chối giữ evidence. Chỉ DB thử đã migrate;
DB phục vụ chưa migrate/config/start/restart/deploy.

## Kiểm chứng và phần chưa đạt

Live BGE-M3/Qwen3.5-9B/Qdrant qua ModelOps trên PDF tổng hợp: hai turn completed/
answered, khoảng1,453s và2,266s; lượt2 có rewrite320token, history1, nguồn đúng
revision; GET lịch sử2turn và replay cùng usageID PASS. OCR/Compiler fixture mock.
Original “Bảng đó…” được làm rõ thành “Bảng chỉ tiêu tuyển sinh…”.

Có một lượt live đầu bị schema validator chặn502; lượt sau có abstain và rewrite
chưa độc lập hoàn toàn. Đã giữ báo cáo, bổ sung hướng dẫn làm rõ chủ thể rồi thử
hai câu hỏi đọc ghi chú/header. Đây là kiểm chức năng nhỏ, không benchmark chất
lượng. Lượt trả lời header còn diễn giải ghi chú gắn vào cột năm cụ thể dù nguồn
chưa chứng minh liên hệ đó: citation ID đúng **không bảo đảm ngữ nghĩa đúng**.
Chưa semantic verifier/benchmark nhiều lượt, kiểm chính xác rewrite đổi năm/metric,
prompt-injection coverage hoặc chất lượng trên corpus QNU thật.

Không tải/cài skill NVIDIA vào runtime. Bài học từ [multi-turn NVIDIA](https://github.com/NVIDIA-AI-Blueprints/rag/blob/main/docs/multiturn.md)
là tách history và query xử lý; quyền, lưu DB và kiểm source vẫn do QNU thực hiện.
[Báo cáo649](../../docs/bao_cao/context649/REVIEW.md).
