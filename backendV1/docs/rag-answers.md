# Hỏi đáp có trích dẫn — Backend v1

Context648 nối [dense search](dense-indexing.md) với runtime chat ModelOps.
Luồng một câu hỏi: **search có quyền → evidence → prompt → model → kiểm citation
và nguồn hiện hành → câu trả lời cùng nguồn**. Chưa lưu hội thoại hoặc có bộ nhớ.

## API

Cập nhật772: `qnu.rag.answer/v9` và `qnu.answer-projection/v1`. Có ít nhất một
lookup hợp lệ thì đáp án là bản trích các ô đã chọn, backend bỏ toàn bộ statements
do model tự viết trước khi materialize. Model không còn vừa chỉ đúng ô vừa làm
hỏng lượt bằng một bản chép số dư thừa. Không kiểm bằng từ khóa ngành hoặc đáp
án fixture, không nhận số trong prose làm giá trị thay thế.

Schema/text/citation và selector vẫn phải hợp lệ trước projection; ô ngoài scope,
ID trùng và selector giả tiếp tục báo lỗi. Nếu không có selector mà prose dẫn số
từ bảng, vẫn `answer_cell_selection_required`. Trả lời văn bản không có lookup
giữ nguyên luồng hiện hữu. Trace `grounding.projection` ghi version, mode và
`omitted_model_statements`; phần prose bị bỏ không được trình bày như đã được
kiểm chứng. Không tự thêm request sửa câu trả lời hoặc bật verifier/fallback.

Đây là đáp án trích ô, không bảo đảm đủ mọi điều kiện văn bản ở ngoài ô. Câu hỏi
cần quy định/ngoại lệ phải dùng nhánh narrative với bằng chứng phù hợp hoặc từ
chối khi thiếu; không coi một ngưỡng điểm là toàn bộ điều kiện tuyển sinh.
Chọn ô đúng nguồn vẫn chưa chứng minh đúng ý định câu hỏi. Lượt F09 mới772 trả
selector thuần, đúng22,20.672s,mỗi capability1execution attempt1; không gộp với
cohort770/771 và không tuyên bố đủ19câu đạt.

Cập nhật phiên770: prompt `qnu.rag.answer/v8`, bộ đọc ô
`qnu.answer-cells/v2`. Model chọn `lookups[].cell_id` khi đọc số từ bảng; backend
kiểm tra ID trong catalog của đúng lượt truy xuất rồi lấy nguyên chủ thể, header,
giá trị và citation từ nguồn. Response công khai vẫn là `statements`/`sources`;
`lookups` là hợp đồng nội bộ, không nhận đường dẫn nguồn hoặc quyền do model đặt.

Catalog dựng vị trí cột từ `row_span`/`col_span`, không dùng vị trí trong danh sách
ô làm cột vật lý. Header nhiều tầng được giữ theo đường dẫn; chủ thể nhóm/hàng
được giữ khi có rowspan. Ô trống không thành0; dấu gạch không bị diễn giải lại.
Header chưa rõ, grid có lỗ/span sai hoặc thiếu citation ô thì không cấp selector.
Header từ bảng khác chỉ dùng quan hệ nguồn đã kiểm tra, cùng document/version/
publication. Hàng nối trang chỉ mượn chủ thể từ phần trước đã ghim; không ghép vì
hai trang liền nhau. Catalog không sửa raw text, bảng, bbox hay metadata năm.

Trace `grounding` giữ version, hash catalog, số ô, số bảng chưa rõ, selector và
`cell_proofs` (các citation ô/header/chủ thể). Backend chặn selector ngoài catalog
hoặc trùng bằng502 `answer_cell_invalid`. Model chép số từ bảng vào văn bản thay
vì selector bị502 `answer_cell_selection_required`; lỗi này không biến thành câu
trả lời “thiếu dữ liệu”, không tự gửi lại. Nội dung ô vi phạm hợp đồng text thuần
bị `answer_source_text_invalid`. Điều này kiểm tra tính nguyên bản của ô, **chưa
chứng minh model đã chọn đúng ô với ý định câu hỏi**. Văn bản diễn giải tiếp tục
qua verifier theo policy `off/observe/enforce`, không tự bật thêm lượt gọi model.

Prompt dùng catalog gọn: mỗi bảng dùng chung đường dẫn header, mỗi hàng dùng
chung chủ thể và các cặp `[column, value]`. Chỉ bỏ bản đọc hàng bị lặp khi xác nhận
được exact JSON suffix; structure gốc vẫn nguyên vẹn. Budget cuối tính cả evidence,
catalog và quan hệ đọc trước reserve/gọi chat. ModelOps kiểm thêm framing/schema/
output. Không tự cắt nguồn hoặc nâng budget/capacity/quota.

Chỉ mục tạo mới dùng `qnu.published-chunks/v3`, ghi `reading_quality` và
`source_dependencies` dẫn xuất trên fragment; config generation có số fragment
cần review theo input. Chỉ mục cũ vẫn đọc qua nguồn đã ghim; không tự reindex.
Report chất lượng là chẩn đoán, chưa thay gate phê duyệt publication. PDF/DOCX đã
có parser; upload XLSX chưa có luồng extraction hoàn chỉnh nên không được coi là
đã hỗ trợ end-to-end chỉ vì bộ đọc grid dùng được cho bảng có cấu trúc.

Nghiệm thu770: synthetic/API kiểm contract và provenance; live3câu riêng trên
cùng index, không retry: F12/F17PASS, F09FAIL `answer_cell_selection_required`.
Đây chưa là PASS toàn19 hoặc benchmark độc lập đa định dạng. Cần đo riêng độ đúng
retrieval, chọn hàng/cột, giá trị, năm/nguồn, điều kiện và citation; không chỉ kiểm
ID hoặc số xuất hiện trong câu. Xem [nhật ký770](../../docs/nhat_ky/2026-10-31_phien_770_rag_chon_o_nguon.md).

Cập nhật phiên769: prompt `qnu.rag.answer/v7` dùng bản đọc bảng theo hàng bên cạnh
`structure` nguyên vẹn. Reranker nhận text đã chuẩn hóa khoảng trắng, không nhận
chuỗi JSON lặp của ô; trace ghi `rerank_presentation=qnu.evidence-reading/v1`.
Không thay text/structure/citation đã lưu hoặc thứ hạng nguồn bằng đáp án test.

Context bảng bổ sung tối đa bốn chunk phụ thuộc ngoài top20, dùng chung ngân sách
byte/token. `context_window=0` tắt cửa sổ lân cận, không tắt phụ thuộc cấu trúc này.
Các chunk hỗ trợ vẫn qua manifest, quyền, metadata filter và kiểm lại publication
trước/sau model. Không bỏ primary để nhường chỗ; thiếu chỗ ghi `table_support=no_room`.

Nhánh `native_numbered_table_boundary/v1` chỉ áp dụng cho bảng native đã parsed,
không requires_review, không ô gộp. Header ứng viên là hàng đầu toàn chữ trước chuỗi
số thứ tự liên tục. Nối qua trang cần đồng thời: cùng snapshot/binding, hai trang
kề nhau, cuối/đầu trang không xen block, khung ngang sai khác tối đa0.005 theo tọa
độ chuẩn hóa, mép dưới≥0.90/mép trên≤0.12, cùng số cột và số thứ tự tiếp đúng.
Các ngưỡng là heuristic giới hạn cho nhánh này, không phải quy tắc cho mọi PDF.
Header có số, bảng phức tạp/OCR hoặc thiếu dấu hiệu vẫn unresolved; không đổi
`header=false` trong canonical. Hàng đầu trống chỉ được dẫn hàng cuối trước đó
khi cả chuỗi cấu trúc được xác lập. `table_links` lưu basis, chain và support IDs;
prompt nhận mapping sang evidence IDs. Không suy năm hay ưu tiên pháp lý từ liên kết.

Cập nhật phiên767: `context_max_bytes` kiểm cả evidence chính khi `context_window=0`;
0 chỉ tắt lấy thêm đoạn lân cận. Vượt ngân sách trả422
`answer_context_budget_exceeded` trước model chat, không cắt chunk để vừa trần.
Trace có `context.bytes_used` là cận trên byte của JSON evidence, không phải token.

Trace trả thêm `reasoning` (directive/policy hash đã áp dụng hoặc lý do giữ mặc định)
và `inference_configuration_hash` gắn với task answer. Guard trước/sau inference và
usage reservation dùng danh tính này để nhận biết thay đổi reasoning. Trường
`configuration_hash` cũ vẫn giữ nghĩa cũ để đọc run/index lịch sử. Prompt không đổi
trong767, vẫn là `qnu.rag.answer/v5`; kết quả cũ không được gán trace mới.

Rerank lỗi giữ số token hợp lệ do provider báo, kể cả0; chỉ missing/không hợp lệ
hoặc kết quả chưa rõ mới giữ reservation unknown. Không tự resend để đo usage.

`POST /platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/answers`

```json
{
  "question": "Trong bảng, ô ở hàng X và cột Y ghi gì?",
  "top_k": 5,
  "document_ids": ["document-id"],
  "provider_id": "chat-provider-id",
  "max_output_tokens": 2048
}
```

Chỉ `question` bắt buộc. Câu hỏi trim,1–8000 ký tự; `top_k`1–20. Document scope
tùy chọn,1–100ID không trùng, không được mở rộng khi ít kết quả. `provider_id`
là chat provider được workspace cấp, bỏ trống dùng default chat. Embedding tiếp
tục dùng đúng model/config của active index, không dùng chat provider này.

Kết quả có:

- `id`, `index_run_id`, `generation`: định danh lượt trả lời và snapshot index.
- `status`: `answered` hoặc `insufficient_evidence`.
- `answer`: văn bản ghép từ các statement và marker `[E1]` do BE gắn; NULL nếu abstain.
- `statements`: mỗi ý có `text` và `evidence_ids` thuộc evidence được cấp.
- `sources`: chỉ nguồn được dẫn; mỗi `evidence_id` ánh xạ chunk/document/version/
  publication receipt, text/structure và citation revision/page/path/hash của search.
- `trace`: prompt version, evidence digest, provider/model/config hash, usage ID,
  token quan sát và thời gian retrieval/generation/validation. Không trả secret,
  endpoint riêng, raw provider hoặc toàn bộ prompt.

`reason` khi thiếu căn cứ: `no_match`, `no_eligible_content` hoặc `model_abstained`.
Hai trường hợp search không có evidence không gọi model chat. Model abstain phải
trả statements rỗng; không lấy văn bản tự do thiếu nguồn làm câu trả lời thay thế.
Response là `private, no-store`; không có semantic cache.

## Ranh giới xử lý

1. Tái sử dụng search647, gồm membership/collection scope, publication/source/hash,
   model embedding và filter trước TopK. Không đổi thuật toán hoặc thứ hạng retrieval.
2. BE cấp `E1/E2/...` theo kết quả, chỉ gửi loại/text/structure cùng ID và câu hỏi
   cho chat. Không nhờ model tự viết source URL, trang hoặc vị trí OCR; ánh xạ nguồn
   được giữ tại server. Chunk/bảng không bị cắt để vừa prompt; vượt capacity trả lỗi.
3. Prompt phân biệt question/evidence là dữ liệu không tin cậy, giữ năm/header/
   footnote, không dùng kiến thức ngoài, không suy TopK là danh sách đầy đủ hoặc
   để model tự tính số liệu chính thức. Thiếu/mâu thuẫn căn cứ thì abstain.
4. `prepare_chat_request` kiểm provider/capacity, text budget bảo thủ và max output.
   Quota reserve qua ledger hiện có trước HTTP; không fallback/retry tự động.
   `RAG_MAX_OUTPUT_TOKENS=2048` chỉ là budget mặc định của tác vụ; giới hạn thật vẫn
   do ModelOps quyết định. Người gọi có thể chọn budget nhỏ hơn.
5. Sau reservation kiểm lại snapshot/provider, thả transaction lock trong lúc gọi
   chat. Trước khi trả kết quả kiểm lại quyền, active index, receipt, revision/hash,
   chunk/manifest và model. Thu hồi/thay đổi trong lúc inference loại câu trả lời,
   không trả đáp án vừa sinh từ evidence cũ.
6. JSON model có status/statements và tùy chọn lookups (từ770). Chặn extra field, schema sai, ý không có
   citation, ID ngoài danh sách/trùng, marker citation chèn trong text, Markdown link
   và HTML trong statement. BE gắn marker và lấy nguồn từ bản đồ đã giữ.

Lỗi citation/schema trả502 `answer_citation_invalid/answer_response_invalid`;
nguồn/index đổi trả409 `answer_evidence_changed` hoặc lỗi index/publication tương
ứng; revoked membership trả404/403 theo resolver. Auth/quota/capacity/provider/
timeout giữ mã lỗi hiện có, không đổi thành “không có dữ liệu”. Truncated output
bị từ chối. Chi phí chưa biết giữ NULL; số token lấy provider, timeout giữ unknown.
Nếu dừng sau reserve nhưng trước HTTP, settle0token vì chưa gọi chat.

Đây là endpoint đồng bộ: mỗi POST mới là một lượt có thể tính usage mới; chưa có
idempotent replay hoặc retry endpoint. Không lưu raw câu trả lời/prompt trong
artifact hay hội thoại ở bước này. Ledger giữ usage và trace log chỉ có ID/count/
status/timing, không có nội dung câu hỏi/nguồn. Không thêm bảng hoặc migration.
Môi trường phục vụ cần baseline `0001_initial_schema` và cấu hình quyền/provider/quota/index
đúng trước khi dùng; phiên648 chưa thay cấu hình đang chạy hoặc publish/index corpus.

## Bằng chứng và giới hạn

Live API trên dữ liệu tổng hợp: BGE-M3 → Qdrant → Qwen3.5-9B qua ModelOps,
HTTP200/answered,2statement/1source,1.979token,2,891s. Trả đúng ô mẫu150 và giữ
ghi chú năm2023, citation đúng revision. `/tokenize` của chat báo max_model_len131072;
đây là quan sát server tại thời điểm thử, không là trần mặc định mọi model.
OCR/Compiler fixture giả lập; index dùng worker domain thật, không chạy ARQ mới
cho endpoint đồng bộ này. Validator cuối replay kết quả live thành công.

Kiểm citation chứng minh ID/nguồn hợp lệ, **không chứng minh mọi phát biểu được
nguồn hỗ trợ về ngữ nghĩa**. Chưa có semantic verifier, benchmark corpus thật,
chống prompt injection đã đo, year filter có cấu trúc, enumeration coverage hoặc
engine tính toán. Đó là giới hạn tại Context648; hội thoại và hybrid/rerank đã
được nối ở các batch sau. [RAG policy](rag-policies.md) mô tả metadata filter,
context window và kiểm chứng hiện hành; streaming/tính toán vẫn chưa triển khai.

Thiết kế tham khảo: [Haystack AnswerBuilder](https://docs.haystack.deepset.ai/docs/answerbuilder)
ở ranh giới generation/response, [Kotaemon](https://github.com/Cinnamon/kotaemon#key-features)
ở citation/nguồn, [RAG From Scratch](https://github.com/langchain-ai/rag-from-scratch)
ở retrieval/context/generation và [Vanna](https://github.com/vanna-ai/vanna#how-it-works)
ở identity xuyên luồng. Thực hiện bằng cấu trúc QNU sẵn có, không thêm dependency.

[Báo cáo648](../../docs/bao_cao/context648/REVIEW.md).
