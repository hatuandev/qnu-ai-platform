# Context608 — Bản nháp rỗng và thời gian chưa đầy đủ

Ngày23/10/2026. Yêu cầu: sửa hai lỗi còn chặn compiler, thêm regression và chạy lại trên ba DOCX2024–2026 bằng Qwen hiện tại. Giữ nguồn, model, Quality Gate; không reindex/publish/commit/push. Ban đầu câu hỏi về Qwen/Luna chỉ yêu cầu nhận xét; sau đó người dùng cho phép chuyển primary sang đúng gh/gpt-6-luna và chạy lại ba DOCX, xác nhận đã tắt Token Saver. Đây là ngoại lệ cấu hình model có phạm vi rõ; không mở sang reindex/publish/Git writes.

## Nguyên nhân và sửa đổi

### Bản nháp rỗng

Trước sửa, engine vẫn gọi PacketCheck khi extraction trả entities/assertions rỗng. Schema buộc items=[] nhưng Qwen có lúc tự tạo assertion/check để trả lời nội dung nguồn. Một lần correction vẫn không giải quyết. Đây là gửi sai loại nhiệm vụ cho trạng thái pipeline, không phải bằng chứng nguồn không có nội dung.

Sau sửa, review_packet trả ledger cơ học items=[] và missed_evidence_ids=TOÀN BỘ primary proof khi không có assertion. Không gọi item verifier, không gán supported, không chấp nhận lời extractor rằng các proof không liên quan. Ledger chưa complete được chuyển cho cơ chế coverage hiện có: hai request độc lập phải đồng thuận; required thì chỉ một targeted extraction/repair; repair vẫn rỗng hoặc hai audit bất đồng thì giữ thiếu và machine_complete=false. Hai audit cùng unrelated mới có thể loại proof cho chủ đề đó. Bằng chứng vẫn nằm trong catalog/provenance; không xóa nguồn.

Regression kiểm repair thành công, repair vẫn rỗng không đệ quy, ambiguity, disagreement, hai audit unrelated, reload/validate_result và nguồn không đổi. Các audit là hai request cùng model, không phải hai model độc lập; không gọi chúng là kiểm định hoàn toàn độc lập về năng lực.

### Ngày chưa đầy đủ

Trước sửa, review gộp tình trạng giá trị với cờ temporal_roles; ca ngày/tháng trống nhưng có năm bị đánh temporal_roles=false. Navigation temporal_context cũng chứa trạng thái/vai trò phân loại, không phải vai trò có hiệu lực do nguồn xác nhận.

Sau sửa, packet_review_payload tạo từng temporal_review_target theo đúng assertion:

- claimed_scopes: bản sao các vai trò/năm thực sự được đề xuất, không được server tự bổ sung.
- source_year_literals: token năm trích nguyên văn, kèm đúng proof IDs đã bind với assertion. Đây là literal cue, không phải vai trò được gán hay ngày đầy đủ.
- Trích nguồn, value/null, scope, conditions/exceptions và hash vẫn giữ. Không đem năm từ proof khác chưa bind sang assertion này.

Reviewer không nhận navigation temporal_context ở bước này; raw evidence và claimed temporal scopes vẫn đầy đủ. Hướng dẫn yêu cầu kiểm cả time claims tường minh và ngầm trong assertion; thiếu scalar không tự là temporal failure, nhưng roles/scope sai vẫn phải chặn. Không tự đổi false thành true và không suy legal/issue/effective từ một token năm.

Ngày đầy đủ vẫn unknown/null trong dữ liệu bền vững, source_unspecified/null trên wire. Phần năm có trong nguồn giữ ở raw evidence/scope đã được model chọn; literal hint không tự trở thành fact hoặc temporal role. Không đoán ngày/tháng hoặc chuyển unknown thành0.

## File và tương thích

- Mới services/compilation_review.py: nhánh review theo trạng thái và payload kiểm thời gian tách trục.
- compilation_engine.py: dùng review_packet, thêm hướng dẫn thời gian và review_route để đọc dấu vết đường đi.
- compilation_modelops.py: configuration hash gồm review protocol và temporal guide; không tái dùng packet trước thay đổi.
- test_compilation_context_608.py:13test mới, gồm positive/negative và cache.
- test_wiki_snapshot_integration_600.py: cho phép prefix DB test608, vẫn kiểm exact environment/host/ownership comment, không mở DB thật.

Hai file app cũ đổi, một module app mới; các file Python app khác giữ hash. Không đổi schema lưu trữ, migration, enum unknown đã persist, parser, nguồn gốc, key/endpoint/timeout, source Quality Gate hoặc publication gate. Model chính được đổi riêng qua API theo chỉ đạo bổ sung; không ép model trong source code. Policy semantic vẫn v3; cache hash phân biệt protocol mới. Old bundle đọc/validate theo ledger đã có, không sửa lịch sử hoặc tự duyệt.

Không nới400ký tự reason, không bỏ validation, không cắt output model để làm PASS. Compiler hiện vẫn nhận JSON bằng prompt rồi validate tại server, không phải native constrained decoding cho mọi phase. Bổ sung native output contract qua ModelOps có thể là việc tiếp theo nhưng chưa làm trong608 vì đụng hợp đồng provider chung.

## Cấu hình runtime được cho phép

Thêm exact alias gh/gpt-6-luna vào danh mục provider9router sau probe chat thực. Giữ cx cũ, provider default model và các model role khác. System chat defaults và admissions primary chuyển sang gh/gpt-6-luna, single/no fallback; không đổi temperature/max_tokens/thinking_budget của admissions, các role embedding/rerank/OCR hoặc bốn trợ lý khác. Inference thực vẫn dùng resolver ModelOps; không có API key trong .env hoặc hardcode model mới ở app.
