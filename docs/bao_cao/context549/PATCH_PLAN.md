# JSON output contract ModelOps — phiên549

Phạm vi: nối output contract tùy chọn vào đường ModelOps/Chat Completions hiện có;
schema selector do backend kiểm soát, parser toàn bộ final content, format retry
tối đa1lần/packet gốc, shared deadline/calls/input budget và trace an toàn.
Giữ parser/Markdown/RAG/unknown-policy/persistence và6nhóm sửa547/548.

G0 xác minh working tree sạch, HEAD `ebd68292`; bản ZIP slim nêu trong prompt
không có ở Downloads. Code hiện tại mới ghép Pydantic schema vào system prompt,
không gửi response_format; parser gỡ fence đơn giản và dùng default lists.
Test đỏ đi qua generate/binder/stage cũ: missing/duplicate không raise; extra data
bị chặn:2FAIL/1PASS. Raw response548 đã xóa theo cleanup được yêu cầu, không
dựng lại bằng chứng cũ; hash lưu lịch sử không chứng minh nguyên nhân phần dư.

1. Schema preset duy nhất, compiler từ ModelSemanticProposal; required mọi field,
additionalProperties=false, giữ $defs/$ref/bounds/enum, bỏ default ở wire.
2. Capability qua registry chat_request_contracts theo provider/endpoint/model;
không suy từ alias hoặc endpoint compatible. Strict-required unsupported thì
từ chối; weaker chỉ khi policy server cho phép, ghi requested/effective/reason.
3. Adapter không bỏ contract khi negotiate temperature/token param; không crop
context hoặc tự hạ format. Non-streaming, giữ finish/refusal/HTTP hashes.
4. Parser không repair/prefix extraction/default-fill/coerce. JSON syntax mới có
1format retry; refusal/schema/binding/context lỗi không dùng retry định dạng.
5. FakeHTTP ở ranh giới provider; test toàn đường service/adapter/parser/binder,
Context548 regressions và full trước/sau theo exact IDs/causes.
6. Live một bảng và API toàn tài liệu trong owned testDB/localStorage tạm;
không đổi model/config, không duyệt thay người dùng, export allowlist rồi cleanup.
