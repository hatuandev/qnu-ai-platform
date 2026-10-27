# Hỏi đáp có trích dẫn — Backend v1

Context648 nối [dense search](dense-indexing.md) với runtime chat ModelOps.
Luồng một câu hỏi: **search có quyền → evidence → prompt → model → kiểm citation
và nguồn hiện hành → câu trả lời cùng nguồn**. Chưa lưu hội thoại hoặc có bộ nhớ.

## API

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
6. JSON model chỉ có status/statements. Chặn extra field, schema sai, ý không có
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
