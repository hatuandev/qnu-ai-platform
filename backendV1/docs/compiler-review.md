# Review ngữ nghĩa sau Compiler

Cập nhật phiên767: giới hạn `max_seconds` của review chia phần cộng dồn thời gian
các claim đang chạy qua resume; khoảng đã dừng không tính thêm. Mỗi lần tiếp tục
lưu `execution_elapsed_seconds` và `execution_started_at`; hết ngân sách trả422
`compilation_review_budget_time_exceeded` trước request model tiếp theo. Trần lượt
gọi/token, artifact và fencing vẫn giữ. Run cũ thiếu ledger dùng cận trên thời gian
từ lúc tạo đến lúc dừng, ghi basis `legacy_wall_clock_upper_bound/v1`, không tự cấp
lại ngân sách đã mất dấu vết. Đây là giới hạn dispatch tổng, không bật lại timeout
300s hay hủy phản hồi đang chờ theo tùy chọn `wait_for_completion`.

Context666 nối báo cáo vào [xác nhận review trước duyệt](publication-review-gate.md).
Người có quyền phải xác nhận báo cáo/hash và giải trình từng finding. Review vẫn
không tự approve/publish hoặc sửa báo cáo gốc; các giới hạn batch cũ phía dưới là
lịch sử kiểm chứng của riêng phần reviewer.

Context658 thêm tùy chọn `structured_output:true` cho API review. Với Compiler
tự động, đặt `review_structured_output:true` khi tạo run; bản sửa con kế thừa
cấu hình review. Mặc định false giữ giao thức JSON object cũ.

API tạo Compiler cũng có `structured_output:true` riêng: schema bản nháp và
danh sách citation hợp lệ được ghim cùng config/hash. Đây là tùy chọn tường minh
cho provider hỗ trợ JSON Schema, không thay model hay cắt nguồn để ép vừa budget.

Tùy chọn mới gửi JSON Schema có mọi source/draft ID là khóa bắt buộc. Model chỉ
điền nhận xét; server chuyển hợp đồng keyed thành báo cáo hiện có và vẫn kiểm
đủ ID, refs, căn cứ/hash, quyền, provider. Thiếu/lặp ID hoặc trích dẫn không hợp
lệ trả lỗi, không được sửa âm thầm. Raw response giữ nguyên. Schema và budget
được ghim trong trace; schema được tính vào reservation bảo thủ. Provider không
hỗ trợ trả lỗi thật, không fallback hoặc resend.

Giao thức dựa trên [structured outputs của vLLM](https://docs.vllm.ai/en/stable/features/structured_outputs/).
Ràng buộc cấu trúc không chứng nhận nhận xét ngữ nghĩa của model đúng.

Prompt v2 gửi đầy đủ `source_units`, `draft_units`, chủ đề và metadata tài liệu
(gồm text version/hash); không gửi lặp nội dung pages/evidence và toàn draft.
Snapshot đầu vào vẫn giữ nguồn đầy đủ. Thay đổi này giảm dữ liệu trùng, không
cắt mục hoặc bỏ header/span/footnote đã có trong units. Mỗi mục vẫn phải được
kiểm đúng một lần trước khi báo cáo hoàn tất.

BackendV1 có bước review độc lập cho một lượt Compiler đã hoàn tất. Review đối
chiếu đúng nguồn và bản nháp đã ghim, phát hiện ứng viên bỏ sót ý, mất điều kiện/
ngoại lệ, sai diễn giải hoặc thêm ý chưa có căn cứ. Báo cáo trả nguyên văn nguồn,
trang/ô và đoạn biên soạn để giao diện sau này trình bày dễ đọc.

Đợt này chỉ backend. Baseline `0001_initial_schema` đã bao gồm hai bảng
`kb_compilation_reviews`, `kb_compilation_review_artifacts`. Chỉ migrate DB test;
không migrate DB phục vụ, đổi ModelOps hoặc restart dịch vụ.

## Chỗ nối trong quy trình

1. Chờ Compiler có `status=completed`.
2. Gọi API tạo review với Idempotency-Key mới. API chạy một request chat và lưu
   kết quả; nếu còn running thì đọc trạng thái, không tạo key mới để retry ngầm.
3. Đọc báo cáo JSON hoặc Markdown; người dùng xem nguồn và gợi ý xử lý.
4. Việc chỉnh bản biên soạn, tạo phiên bản mới và duyệt/xuất bản vẫn là bước riêng.

Từ Context654, Compiler mới mặc định tạo intent review tự động sau hoàn tất;
API tạo review thủ công vẫn có thể dùng riêng. Xem [workflow Compiler](compiler-workflow.md)
để chọn reviewer, đọc trạng thái job và lưu bản sửa thành phiên bản mới.
Không tự sửa lặp hoặc tự phê duyệt.

Nguồn review là `input_snapshot` của chính lượt Compiler, không phải tài liệu
mới nhất hoặc kết quả tìm kiếm RAG. Trước và sau model, kiểm bundle/hash, revision
và nguồn hiện hành. Revision mới khiến báo cáo cũ không còn được phục vụ như
báo cáo hợp lệ cho nguồn hiện tại; metadata và raw vẫn đọc được trong quyền.

Compiler có thể chọn chính xác text version hậu OCR. Review dùng cùng ID/hash
đã ghim; các run trước đây vẫn dùng OCR gốc, không bị chuyển sang bản sửa mới nhất.

## Phạm vi đối chiếu

- Nguồn → bản nháp: `covered`, `omitted`, `out_of_scope`, `uncertain`.
- Bản nháp → nguồn: `supported`, `contradicted`, `unsupported`, `uncertain`.
- Kiểm đủ khối có text hoặc từng ô của bảng đã tái dựng, kể cả ô rỗng/0/dấu gạch.
  Giữ thứ tự, header, spans và các đoạn chú thích. Bảng chưa tái dựng giữ text
  nguyên khối. Bbox ô trong báo cáo là bbox khối bảng, không phải tọa độ ô đã đo.
- Bản nháp gồm title, heading, paragraph, từng ô nguồn đính kèm và unknowns.
- Ô đã đính kèm nguyên văn không được coi là bỏ sót chỉ vì không lặp trong prose;
  review vẫn xem ý nghĩa của header/chú thích và các câu diễn giải liên quan.
- Tóm tắt hợp lệ khác với bỏ mất ý quan trọng thuộc chủ đề. `out_of_scope` cần
  lý do, không đòi Compiler sao chép hết tài liệu không liên quan.

Server cấp danh sách ID cho hai chiều và yêu cầu mỗi ID xuất hiện đúng một lần.
Thiếu/trùng/ID lạ hoặc covered/supported thiếu tham chiếu bị từ chối502. Model
không được tự trả trích đoạn thay cho nguồn: server tự lấy nguyên văn theo ID.
Kiểm đủ ID là đầy đủ hợp đồng đánh giá, không chứng minh đầy đủ mọi ngữ nghĩa.

## API

Tiền tố `/platform/v1alpha1/workspaces/{workspace_id}/collections/{collection_id}/compilation-runs/{run_id}/reviews`.

| Method | Phần sau tiền tố | Nội dung |
|---|---|---|
| POST | rỗng | Tạo một lượt review; bắt buộc Idempotency-Key |
| GET | rỗng | Danh sách mới nhất trước; limit1..100, offset>=0 |
| GET | `/{review_id}` | Trạng thái, verdict, hashes, usage và trace an toàn |
| GET | `/{review_id}/report` | JSON có nguyên văn nguồn/bản nháp, findings và coverage |
| GET | `/{review_id}/markdown` | Báo cáo đọc như văn bản |
| GET | `/{review_id}/raw` | Nguyên bytes model, kể cả response không hợp lệ |

Body POST tối thiểu `{}`: dùng default chat hiện hành của workspace, output budget
mặc định8192. Có thể gửi `provider_id` và `max_output_tokens` để chọn reviewer
khác đã được cấp quyền. Capacity thực giải quyết theo provider/model trong DB;
8192 là mặc định workflow, không phải trần cố định của mọi model. Không ép reviewer
trùng model Compiler và không thay model của lượt Compiler đã ghim.

Admin/editor/reviewer được tạo. Thành viên đọc theo READ_ROLES của kho. Mọi route
đi qua `resolve_workspace_access`, scope workspace → collection → Compiler → review;
đây là ngoại lệ quyền của backendV1, không đổi phạm vi backend cũ. Body không nhận
URL, key, actor, source hay draft do client tự đưa vào.

POST trả metadata hoàn tất khi thành công. Cùng actor/workspace/key/body trả cùng
lượt, không gửi lại model dù trạng thái failed/uncertain/running; key trùng khác
body/scope trả409. Key mới tạo lượt mới và có thể tính usage lần nữa.

## Kết quả dễ đọc

Mỗi finding có hướng kiểm tra, loại nhận xét, giải thích, nguyên văn nguồn kèm
trang/ô, nguyên văn bản biên soạn nếu có, và gợi ý xử lý. Ví dụ tổng hợp:

> Có thể bỏ sót ngoại lệ. Nguồn: “Áp dụng cho sinh viên chính quy, trừ sinh viên
> năm cuối.” Bản biên soạn: “Áp dụng cho sinh viên chính quy.” Gợi ý: đối chiếu và
> bổ sung ngoại lệ. Đây là ví dụ minh họa, không phải kết quả model thật đã đo.

Verdict do server tổng hợp từ các nhận xét:

- `needs_attention`: có omitted/contradicted/unsupported/uncertain cần xem lại.
- `no_issues_detected`: chưa phát hiện vấn đề trong phạm vi đã kiểm tra.

Không có verdict approved/PASS/100% hoặc tỷ lệ chính xác tự tính. Mảng findings
rỗng vẫn kèm giới hạn. Mỗi loại nhận xét và tổng số đơn vị được kiểm chỉ là số
đếm; có thể có hai nhận xét ở hai chiều về cùng một vấn đề, chưa tự gộp ngữ nghĩa.

## Độ bền và lỗi

Trước khi reserve quota (service này tự commit), ghi durable unique request cùng
input snapshot có hash trong cùng khóa workspace. Nhờ vậy hai request cùng key
không gọi model hoặc reserve hai lần. ModelOps giải quyết grant, active, credential
được bảo vệ, capacity và quota; không .env key, retry hoặc fallback ngầm.

`running → completed | failed | uncertain`. Không thêm queue/worker. POST hiện
giữ kết nối trong khi model chạy; nếu client mất phản hồi, đọc lại trạng thái hoặc
replay cùng key. Lượt hết hạn (ít nhất900giây hoặc timeout model+60) được đánh dấu
uncertain khi đọc. Kết quả muộn sau expiry/fence không được commit thành completed.
Review nhiều phần có thể tiếp tục phần chưa xong hoặc đọc lại raw đã nhận khi
claim trước đã dừng và còn ngân sách. Phần completed không gọi lại; phần uncertain
không được tự gửi lại. Resume giữ tổng thời gian đã dùng như cập nhật phiên767 ở trên.

Ghi thời điểm bắt đầu HTTP, usage theo quan sát; token không biết giữ NULL và
reservation, không giả0. Quyền/provider/source/bundle kiểm lại trước và sau HTTP.
Lỗi hạ tầng/provider là RFC7807, không biến thành báo cáo “không có vấn đề”.
Truncated dùng hợp đồng chat hiện có422; review sai schema/coverage trả502.

Artifact gồm input_snapshot, raw_response, report_json, markdown. Blob content-
addressed được đọc kiểm trước ghi DB; raw được commit trước xử lý review. Hai
artifact báo cáo phải có đủ trước khi commit completed. Lỗi lưu report giữ raw
và chặn đọc báo cáo dở; blob mồ côi có thể tồn tại, chưa GC. Reads kiểm size/hash.
Không ghi văn bản tài liệu, credential hoặc model response vào log/audit.

## Giới hạn kiểm chứng

Regression dùng PostgreSQL/BlobStore thật và HTTP OCR/chat loopback giả lập. Nó
chứng minh quyền, scope, persistence, coverage contract và báo cáo, chưa chứng
minh model phát hiện đúng lỗi ngữ nghĩa. Chưa gọi model thật, so ảnh gốc hoặc đo
recall/precision của review. LLM có thể đồng thuận sai với Compiler; chọn model
khác không tự chứng minh độc lập hoặc đúng. Tài liệu dài gửi toàn bộ trong một
request; vượt budget hoặc model không trả đủ assessments thì lỗi rõ, không cắt
ngầm. Chưa chia nhiều vòng và chưa nhận xét/duyệt sửa bản biên soạn qua API này.

[Báo cáo652](../../docs/bao_cao/context652/REVIEW.md).
