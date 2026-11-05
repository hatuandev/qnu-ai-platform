# Biên soạn chủ đề nhiều nguồn và quản lý dẫn xuất

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

Đợt3–4 bổ sung API quản trị cho compiler theo chủ đề. Ingestion phổ thông và
chatbot hiện tại giữ luồng cũ; bản compiler không tự thành fact có hiệu lực.
Không bắt người upload tài liệu xử lý mọi proposal trước nạp vector nguồn đã đạt
Quality Gate.

## Luồng

Preview nguồn hiện hành → source-set hash → request có idempotency → lưu intent
→ hai lượt chọn topic/kiểm phần bị loại → draft theo source → binding/independent
review → đối soát coverage có giới hạn → synthesis giữ nguồn/năm → kiểm độc lập
sections/relations và dựng lại chiều quan hệ → Storage
immutable/read-back → commit registry → người có quyền review quyết định.

Chỉ nhận source IDs trong collection do server kiểm, mới nhất của mỗi binding,
ready, raw/canonical/manifest còn khớp. Không nhận URL/secret/provider do model
chọn. Metadata ngày ban hành không tự trở thành năm dữ liệu; scope metadata và
condition nghiệp vụ giữ vai trò khác nhau. Source limitation/unknown không thành0.

Topic selection giữ ledger tất cả proof; hai lượt bất đồng hoặc bỏ sót phân loại
thì giữ cho extraction/review, chỉ loại khi cả hai khai báo không liên quan.
References dùng handle ngắn riêng trong request; server khôi phục proof có exact
revision/hash/offset. ID chưa được cấp bị từ chối. Phần tổng hợp có coverage
assertion; khám phá relation trong từng nhóm không bảo đảm mọi cặp xuyên nguồn.

ModelOps/defaults/capability/egress/quota hiện có quyết định tuyến thực thi. Toàn
request được đo ngân sách, giữ64calls/600s, không tự tăng context hoặc lặp vô hạn.
Provider/storage/JSON/budget errors là lỗi thực thi, không phải “không có tài liệu”.

Policy hiện hành `qnu-compilation-review/v3` yêu cầu scope nguyên tử có literal
anchor; section giữ một nguồn và data/effective profile tương thích. Navigation
metadata không chứng minh văn bản là dự thảo/chính thức. Ngày phiên bản là event
nếu nguồn không chứng minh role khác; so sánh các role năm cần đủ assertions.

Coverage giữ review gốc và hai lượt phân loại: thiếu fact, context hỗ trợ, không
liên quan hoặc chưa rõ. Bất đồng vai trò vẫn chặn; context chỉ liên kết các
assertions cùng nguồn đã đồng thuận. Association chưa xác minh chỉ là candidate,
không có hiệu lực. Thiếu fact chỉ repair một gói, không replay toàn nguồn.

Directed relations có quy ước subject → object. Supersedes là mới/thay thế →
cũ/bị thay thế, không suy chỉ từ ngày mới hơn. Reviewer riêng nhận endpoint
membership, không nhận chiều đề xuất; hướng dựng từ nguồn phải khớp đề xuất.
Không tự đảo relation để khớp. Bound qualifiers được mở rộng nguyên văn từ IDs
đã chọn để kiểm điều kiện; không tạo điều kiện mới hoặc bỏ qualifier thật.

## Vòng đời và quyền

`ready_for_review` chỉ báo machine ledger đạt; `needs_attention` không được
approval. Read/review phải kiểm quyền server, version/proposal hash, source-set,
artifact hash và lineage. Nguồn/pointer/epoch đổi trả stale, không cung cấp bundle
cũ cho sử dụng. Thu hồi giữ lịch sử và chặn reuse ở các dẫn xuất phụ thuộc.

Intent được commit trước inference; storage ghi/hash/read-back trước DB pointer.
Job gián đoạn có receipt uncertain, retry cùng key không tự gọi model. Concurrency
được kiểm bằng collection lock và optimistic version ở decision. Audit riêng
automated_verification và user_decision, không giả từng issue đã có người duyệt.

Registry trong metadata hiện có chỉ do service quản lý; API metadata thông thường
không nhập hoặc sửa được registry. Không có bảng/migration/worker mới. Storage
orphan sau rollback giữ theo policy; chưa thêm GC tự động hoặc xóa chứng cứ.

Artifacts policy cũ vẫn đọc/reject/revoke theo lịch sử, nhưng không cấp approval
mới bằng policy cũ. Machine verdict phải khớp ledger đã tính lại. Cache bao gồm
topic/source/config/policy để không dùng kết quả trước khi thay hợp đồng.

Approved chỉ là quyết định cho bản dẫn xuất, không publication, không sửa nguồn,
không ghi facts/embeddings hoặc repoint active index. Compiler chưa tích hợp vào
context chatbot; UI/serving rollout thuộc các đợt sau.

## Sử dụng và kiểm chứng

[Hướng dẫn API](../bao_cao/context603/USER_GUIDE.md) ·
[Triển khai/giới hạn](../bao_cao/context603/IMPLEMENTATION_REPORT.md) ·
[Kết quả kiểm chứng](../bao_cao/context603/VALIDATION_REPORT.md).

Bổ sung604: [Bảo vệ scope/coverage/hướng](../bao_cao/context604/IMPLEMENTATION_REPORT.md)
· [Kiểm chứng và blocker còn lại](../bao_cao/context604/VALIDATION_REPORT.md)
· [Đối soát24 proof](../bao_cao/context604/RECONCILIATION_24.md).

P10 được giữ ngoài phạm vi Context603 theo yêu cầu. Kết quả benchmark602 là lịch
sử, không dùng test compiler mới để ghi thành điểm chatbot mới.

## Bổ sung606 — Giá trị nguồn và kết quả kiểm chứng

Trong hợp đồng gửi model của topic compiler, `value_state=source_unspecified`
nghĩa là nguồn chưa xác định giá trị được hỏi; giữ `value=null` và bằng chứng
chứng minh giới hạn đó. `verdict=unresolved` nghĩa là nhận định chưa đủ căn cứ
để kiểm chứng. Một giới hạn nguồn đúng phạm vi có thể được supported mà giá trị
vẫn chưa xác định; không tự chuyển nó thành0 hoặc thành một ngày đầy đủ.

Server chuyển `unknown` nội bộ sang `source_unspecified` trước inference, khôi
phục trước khi kiểm/persist. Dữ liệu và hash cũ không bị migrate. Chỉ đổi trường
value_state có cấu trúc, không đổi trích nguyên văn hoặc `temporal.role=unknown`.
Cache bao gồm wire version và hướng dẫn thực tế. Schema/reference/scalar checks
và quyền approval vẫn giữ; đổi nhãn không tự làm một review thành hợp lệ.

Packet chừa dung lượng đầu ra bằng cap4primary mặc định, vẫn giữ các dependency
proofs và ngân sách toàn request. Không tăng64calls/600s hoặc bỏ proof khi vượt
budget. Empty draft review không được tự tạo assertion/check; nội dung cần nhưng
bị bỏ sót phải giữ trong missed_evidence_ids cho coverage, không tự cho PASS.

[Triển khai606](../bao_cao/context606/IMPLEMENTATION_REPORT.md) ·
[Kiểm chứng và blocker606](../bao_cao/context606/VALIDATION_REPORT.md) ·
[Đối soát nguồn606](../bao_cao/context606/RECONCILIATION.md).

## Bổ sung608 — Review theo trạng thái và kiểm thời gian

Khi draft không có assertion, không gọi item verifier. Tất cả primary proofs giữ
trong missed ledger để hai coverage audits đối soát; chỉ một targeted repair,
repair vẫn rỗng hoặc bất đồng giữ incomplete. Không tự gán supported cho empty
hoặc dùng lời extractor rằng không liên quan để bỏ qua kiểm tra.

Reviewer nhận riêng claimed temporal scopes và token năm từ đúng proof đã bind;
literal token không là role hay ngày đầy đủ. Navigation classifier không phải
căn cứ authored temporal và không được lẫn vào đánh giá này. Nguồn có năm nhưng
thiếu ngày/tháng vẫn giữ phần năm; full date có thể null. Cờ false/unresolved từ
reviewer không bị server ghi đè, implicit time claims vẫn phải kiểm.

Model chính được phân giải từ ModelOps. Alias trong request và served model name
có thể khác qua router; phải ghi cả hai và fallback trace, không tự kết luận đổi
model hoặc mất kết nối chỉ từ chuỗi alias. HTTP200/usage success không bảo đảm
JSON hoặc semantic PASS. [Báo cáo608](../bao_cao/context608/VALIDATION_REPORT.md).

## Bổ sung611 — Đóng gói và checkpoint

CompilerPolicy dùng chung cho packing, preflight, ModelOps request và configuration
hash. Reasoning effort được truyền riêng, không suy từ thinking_budget dạng số.
Trích xuất/review có ngân sách riêng; review quá lớn được chia assertions nhưng
giữ toàn bộ raw packet evidence, dependency context và ledger kiểm chứng.

Mỗi logical call lưu started trước inference và completed sau khi contract/object
checksum hợp lệ. Hai lượt audit độc lập có ordinal khác nhau dù cùng payload.
Candidate checkpoint không đồng nghĩa approved. Started/uncertain không tự gửi
lại; source/config/hash hoặc quyền không khớp phải chặn.

Paused hoặc job uncertain có đủ prefix completed/rejected (không có inference
stage started/uncertain) được tiếp tục bằng CompilationRequest có resume_from_job_id,
expected_resume_version và idempotency_key mới. Nguồn/topic/hash giữ nguyên,
parent chỉ có một child, tổng calls kế thừa và không reset. Gửi lại cùng key chỉ
đọc receipt. Audit checkpoint tách khỏi audit quyết định và giữ actor/checksum.
Packet cache được ghim để cache mới không làm lệch thứ tự giai đoạn. Khi assertion
lặp scope/time/qualifier, có thể dùng shared contexts mở rộng ngược khớp hoàn toàn;
không bỏ raw evidence hoặc coi dữ liệu chia sẻ là bằng chứng đã duyệt.

Mặc định tổng vẫn64calls; lượt thử611 cấp server-side tổng128, mỗi lần thực thi
vẫn64calls/600s. Không tự tăng vô hạn, không approve/publish hoặc ghi vector.
[Thiết kế611](../bao_cao/context611/DESIGN.md).

## Bổ sung613 — Ngân sách model và tổng hợp theo nhóm

Tách dung lượng request khỏi dung lượng bản biên soạn. ModelOps nhận profile
token_limits cho đúng alias/endpoint: context, output và cơ sở cấu hình. Compiler
dùng giao ngân sách của primary/fallback đã cấu hình; thiếu profile phải ghi rõ
fallback server chưa xác minh, không suy context từ tên model. Cấu hình token
không tự đổi khi triển khai mã. [Hướng dẫn](../bao_cao/context613/MODEL_LIMITS_GUIDE.md).

Trích xuất và kiểm từng packet như trước; nhóm tổng hợp giữ closure của raw proof,
header/condition/exception đã có liên kết. Request tổng hợp và review được đo
riêng; review lớn được chia mà không cắt raw context. Correction vẫn giới hạn và
không resend stage chưa rõ kết quả.

Draftv1 giữ giới hạn và đọc lại theo hợp đồng cũ. Bản lớn dùng manifestv2 chứa đầy
đủ thực thể, assertion, relation, section và danh mục nhóm có ID/hash/snapshot.
Mỗi nhóm vừa request; toàn bản chịu chính sách objects/calls/time/Storage riêng.
Binding/đọc lại kiểm nguồn, ID toàn cục, thành viên nhóm và coverage; không tự
gộp nhãn trùng hoặc bỏ facts để vừa cap.

Đối chiếu liên nguồn chỉ dùng nhãn trùng/gần nhau tìm ứng viên, chưa phải bằng
chứng identity. Phải có raw evidence, kiểm độc lập và blind direction cho quan
hệ có hướng. Giới hạn tìm cặp CPU tách khỏi số cặp gọi model; chưa kiểm hết thì
giữ coverage chưa hoàn tất. Review/direction không vừa giữ proposal candidate_only,
effective=false/NOT_RUN, không nhập làm quan hệ có hiệu lực.

Vượt dung lượng được báo capacity422 và stage rõ ràng, status capacity_blocked;
khác với inference uncertain và không tự retry. Hoàn thành Markdown vẫn có thể
needs_attention; machine_complete hoặc human approval không cấp publication.
Luồng nạp nguồn thông thường và Quality Gate nguồn giữ độc lập như trước.
[Thiết kế613](../bao_cao/context613/DESIGN.md),
[thử compiler thật](../bao_cao/context613/LIVE_COMPILER_REPORT.md).

## Bổ sung614 — Ngữ cảnh cấu trúc và giới hạn kiểm chứng

Compiler giữ nguyên catalog proof/canonical. Navigation dẫn xuất liên kết mục,
bảng, header, vị trí ô và context/field note đã có refs. Mục đánh số hoặc hàng
body đầu của bảng header rỗng chỉ là ứng viên, không tự trở thành role đã xác
nhận. Không nối chú thích bằng chữ giống nhau hoặc suy năm từ tên file.
`source_structure` có protocol riêng; đọc lại phải khớp nguồn và dependency graph.

Phần metadata bảng dùng chung được gửi một lần, literal ô vẫn nằm trong quote
nguyên gốc. Giữ override riêng của ô, unknown và locator chưa xác định. Model phải
kiểm vai trò từ raw proof; navigation không cấp quyền, approval hoặc fact có hiệu lực.

Ngân sách thực tế của request được đo riêng với ngân sách lập kế hoạch. Planner
tính đầy đủ source hashes, navigation, prior selection và phong bì báo lỗi JSON
tối thiểu cho một lần correction. Không dùng reserve token lớn tùy ý hoặc cắt
nguồn để vừa request. API đo request thực vẫn khớp đúng schema/transport gửi đi.

Audit/repair coverage tùy chọn không vừa thì ghi NOT_RUN, giữ toàn bộ proof còn
thiếu trong coverage debt và complete=false; các gói khác có thể tiếp tục. Việc
tạo được bundle không xóa blocker đó. Diagnostic review tối đa 4.096 ký tự để lưu
đủ lý do; các kiểm tra entailment/scope/year/condition/proof không thay đổi.
Protocol này tham gia configuration hash, không âm thầm nâng cấp checkpoint cũ.

Số packet mặc định vẫn 30; server có thể cấp giới hạn vận hành lớn hơn, tối đa
256, đồng thời chịu tổng calls/thời gian đã cấu hình. Không cho client/model tự
đặt chính sách hoặc bỏ Quality Gate. Thử nghiệm Context614 dùng fixture riêng;
replay receipt trong fixture không phải migration checkpoint production.
[Thiết kế614](../bao_cao/context614/DESIGN_AND_IMPLEMENTATION.md).

## Binding tên chỉ số và cột — Context615

Policy review v4 bổ sung `source_metric` và `source_column` cho giá trị chứa số
lấy từ bảng. Hai scope giữ literal nguồn và trích dẫn riêng; entity/attribute
không được đổi nhãn để khớp câu hỏi. Giá trị phải có ô duy nhất và đúng cột.
Header ứng viên vẫn unresolved; literal trùng không tự chứng minh ngữ nghĩa.
`metric_binding_targets` chỉ đưa lựa chọn bằng chứng, không cấp xác nhận.

Lỗi cơ học chặn complete ngay cả khi model nói supported. Synthesis giữ nhãn
nguồn; đọc lại bundle mới tái dựng structure để tính guard. Bundle cũ giữ policy
đã lưu và không được âm thầm nâng cấp. [Kết quả và giới hạn615](../bao_cao/context615/REVIEW.md).


## Compiler literal/native và ngân sách theo giai đoạn — Context616 đang thực hiện

Bản nháp dùng source span/record, native witness và review truth tách coverage; không tự duyệt hoặc đổi nguồn. Tổng hợp phải lập kế hoạch cả request generation lẫn nội dung server-rendered sẽ gửi review. Candidate semantic được sửa tối đa một lần và cần binding thực sự khác; ID mới/đảo proof/verdict mới cho cùng assertion thất bại không được chấp nhận.

Giới hạn24000/2500 hiện là fallback phần mềm, không phải capacity model đã xác minh. User yêu cầu bỏ cách ghim token; chưa triển khai capacity động trong lượt kiểm kê. Không coi model profile chưa khai báo là vô hạn hoặc đổi sang một trần tùy ý khác. Lượt thật/final full còn phải tiếp tục trước nghiệm thu. [Trạng thái616](../bao_cao/context616/REVIEW.md).

## Capacity endpoint tự động — Context617

Route compiler mới ưu tiên profile operator hiện có, hoặc tự đọc capacity tại endpoint đang cấu hình bằng credential ModelOps. Không cần nhập tay form để chạy. Primary được khám phá khi lập kế hoạch; fallback chỉ được khám phá nếu thực sự dispatch, giữ cùng toàn bộ đầu vào. Không lấy capacity nhỏ của fallback làm trần primary.

Với tokenizer được hỗ trợ, calibration tổng hợp đo framing của hai message system/user. Ngân sách đầu ra từng request là giá trị nhỏ hơn giữa output capacity và phần context còn lại sau input/framing/dự phòng. Thinking dùng chung output theo hợp đồng đã chọn. Unknown tokenizer dùng ước lượng có ghi nhãn; unsupported template/schema transport bị từ chối rõ ràng. Tài liệu có chuỗi giống special token vẫn là văn bản không tin cậy.

Metadata công bố, giới hạn từ lỗi runtime có số rõ ràng và lower bound inference thành công là ba loại bằng chứng khác nhau. Không suy capacity từ tên model, hỏi model tự khai, hay coi một probe thành công là chứng minh exact maximum. Thiếu metadata thì báo chưa xác định; không âm thầm về24K/2500. Các typed policy cũ còn để đọc/tương thích. Không đổi profile DB, source, Quality Gate hoặc quyền publication.

Protocol capacity và kết quả calibration tham gia fingerprint checkpoint. Cache trong process10phút, gắn provider/endpoint/model/configuration. Test thật617 đã xử lý120002input token; native cloud metadata chỉ được fake-HTTP test. [Báo cáo617](../bao_cao/context617/REVIEW.md) ghi riêng giới hạn và lỗi semantic compiler chưa đạt.

## Span ID tường minh — Context618

Menu nguồn gửi model có `span_id`, `evidence_id`, literal, vị trí Unicode trong quote và `allowed_roles`. Model chỉ chọn span_id cho đúng trường, không viết lại binding hoặc dùng proof/record ID thay span. Dữ liệu bảng có record nguồn sẵn thì chọn record_ids; không tạo free claim bằng scalar đã thuộc record ấy.

Role eligibility là điều kiện chọn kỹ thuật, không phải phê duyệt ngữ nghĩa. Enum/materialization vẫn kiểm đúng source, primary proof và role. Correction chỉ nhận phản hồi ID/role thuộc menu; chuỗi lạ không bị log nguyên văn. q-ID chỉ thuộc một request; provenance bền vững vẫn dùng canonical proof/source hash/revision. Menu protocol tham gia configuration hash, không sửa checkpoint cũ. [Báo cáo618](../bao_cao/context618/REVIEW.md).


## Nhận bản sửa có đối soát — Context622

Giá trị chỉ áp dụng trong một phạm vi vẫn là present khi nguồn đã nêu giá trị ấy; source_unspecified cần bằng chứng thiếu chính giá trị đó. Prose dùng metric và temporal/scope, không biến năm thành cột bảng.

Repairv3 có thể đề xuất tập gồm các assertion đã được truth review hỗ trợ và giữ các assertion cũ đã đạt. Candidate gốc và phần bị cách ly không mất đi. Tập này chỉ có hiệu lực sau audit độc lập mapping từng target bị từ chối sang fact thay thế đúng nguồn/phạm vi và kiểm đủ coverage. Không vừa request thì NOTRUN; thiếu mapping, scope hoặc coverage vẫn chặn. Đọc lại kiểm membership, review, coverage hash và verdict, không đổi fact cũ thất bại thành PASS bằng ID mới.

Protocol/schema/instruction tham gia fingerprint; không nâng cấp checkpoint cũ hoặc tự phê duyệt/publish. [Kết quả622](../bao_cao/context622/REVIEW.md) phân biệt test gói2026 với nghiệm thu toàn compiler.


## Ledger theo giai đoạn — Context623

Bản nháp rỗng ghi toàn bộ primary proof là debt, không giả lập một review đã đạt. Khi coverage bổ sung assertion, đọc lại kiểm riêng ledger ban đầu và ledger của phần thêm. Semantic candidate đã bị từ chối vẫn bị từ chối; các thay đổi coverage không được nhầm thành kích hoạt candidate đó. Fact cũ/mới và hash phải còn nguyên sau JSON persistence.

Phân biệt named field được nguồn để trống với layout/header trống hoặc danh mục chỉ có tên/mã. Shared year/subject không tự làm một dòng thành dữ kiện của thuộc tính được hỏi. ReadTimeout chưa rõ kết quả vẫn là uncertain và không được tự gửi lại. [Kết quả623](../bao_cao/context623/REVIEW.md) chưa đạt nghiệm thu toàn compiler; user giữ checkpoint để kiểm tra provider.

## Ràng buộc coverage tại JSON boundary — Context625

`supporting_context` phải chỉ ra assertion được hỗ trợ; `unrelated` phải có danh sách assertion rỗng. Bất biến này được kiểm tra ngay khi đọc JSON model để lỗi hợp đồng đi vào correction có giới hạn sẵn có. Server vẫn kiểm membership, cùng nguồn và coverage đầy đủ; không tự đổi role, thêm liên kết hoặc xem candidate là quyết định duyệt. Wire schema không đổi.

Recovery Context625 chỉ thuộc bộ kiểm thử, kiểm hash request/config/source và receipt trước khi tái sử dụng candidate. Không thay trạng thái job uncertain cũ hoặc thêm khả năng retry production. Lỗi provider chưa rõ kết quả phải giữ checkpoint; không suy nguyên nhân cụ thể từ mã chung. [Báo cáo625](../bao_cao/context625/REVIEW.md).

## Chiều quan hệ trong grounded prompt — Context627

Prompt source-grounded thực sự gửi tới ModelOps dùng chung `DIRECTION_RULES` với blind verifier. Directed edge giữ SUBJECT(source_id) → OBJECT(target_id); không suy vai trò từ thứ tự assertion/ID hoặc độ lớn số. Giữ authored link có đủ endpoint/căn cứ, đồng thời không suy supersession chỉ từ ngày muộn hơn.

Đây là hướng dẫn tạo candidate, không phải phép tự đổi chiều hoặc duyệt quan hệ. Semantic check và blind witness vẫn phải thống nhất, cùng guard nguồn/phạm vi/điều kiện. Prompt tham gia configuration hash sẵn có; không nâng cấp checkpoint cũ âm thầm. [Báo cáo627](../bao_cao/context627/REVIEW.md) phân biệt chiều đã kiểm chứng đúng với toàn nhóm còn lỗi heading và toàn compiler chưa đạt.
