# Chẩn đoán đã chứng minh — phiên549

## Lần548

Raw final content/HTTP body cũ: NOT_AVAILABLE. Cleanup548 đã xóa owned runtime
sau export; dossier chỉ có hashes và JSONDecodeError Extra data, không bytes phần
dư. Không thể kết luận model thêm giải thích, hai object, truncation hay proxy.
Không gán suffix trong test tổng hợp thành raw lịch sử. Không gọi lỗi548 là
timeout/evidence sai vì selector chưa được parse.

## Mã hiện tại và tái hiện trước sửa

OpenAI decoder chọn choices[0].message.content, không nối reasoning/choices;
LLMResponse chưa giữ finish/refusal trừ length được reject. Request semantic
chỉ ghép schema vào prompt, không có response_format. ModelSemanticProposal có
default_factory cho lists; parse_json trực tiếp chấp nhận thiếu lists và duplicate
keys. Qua service sinh đề xuất thật với TEST model adapter:2redFAIL đúng nguyên
nhân missing/duplicate được stage,1PASSextra data bị chặn, effective mutation
được so snapshot. Đây là probe tổng hợp, không raw lần548.

## Trace mới

G3 Bảng1: provider custom/gpt-6-luna trả1choice/content, finish_reason=stop;
JSON toàn bộ và strict selector schema PASS trong mode prompt_only được policy
cho phép. Evidence binder FAIL `EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN`.
Không format retry, không stage hoặc áp dụng annotation. Không quy lỗi này thành
JSON syntax; không đổi scope/evidence hoặc hardcode fixture để vượt validator.

G4 HTTP route toàn tài liệu:22packet được build, mới1packet được gửi; provider
trả JSON/selector hợp lệ có needs_context. ContextBuilder từ chối expansion vượt
ngân sách:SEMANTIC_CONTEXT_INCOMPLETE/CONTEXT_EXPANSION_BUDGET. Evidence binding
NOT_RUN, proposal không stage. Trace là yêu cầu toàn tài liệu bị chặn, không phải
toàn tài liệu đã đủ annotation. G4setup đầu thiếu origin_document_id trong fixture
test, DB từ chối trước inference; sửa fixture rồi chạy API lần thực, không gọi
đó là semantic/format retry. Không xuất traceback SQL có corpus vào dossier.

Raw response mới chỉ lưu nội bộ trong runtime trong lúc chẩn đoán. Dossier xuất
summary/hashes/packet/schema/source identity/attempt counts đã lọc; không raw
response/corpus/credential. Native schema capability chưa được khai báo cho
primary, việc trả JSON lần này không chứng minh schema cưỡng chế upstream.

Tài liệu API dùng để đối chiếu dạng payload và strict schema:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).
Đây không phải bằng chứng capability của provider trung gian.
