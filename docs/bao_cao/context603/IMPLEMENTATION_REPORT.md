# Context603 — Compiler chủ đề và vòng đời dẫn xuất, đợt3–4

Ngày 22/10/2026. Người dùng yêu cầu triển khai đợt3–4, để P10 xử lý sau. Không sửa
pipeline trả lời P10, không chạy lại bộ64 để ghép điểm mới vào kết quả602.

## Phạm vi đã hiện thực

Luồng backend nâng cao:

1. Preview tập source revision hiện hành, raw/canonical/manifest và source-set hash.
2. Ghi intent có actor/idempotency vào registry trong transaction trước inference.
3. Chọn bằng chứng theo topic và kiểm lại độc lập toàn bộ tập bị loại. Phần hai
   lượt bất đồng hoặc chưa phân loại được giữ để extraction/review; chỉ loại khi
   cả hai lượt khai báo không liên quan. Có ledger riêng cho unclassified retained.
4. Bóc assertion theo từng nguồn, kiểm binding và kiểm độc lập entity/metric,
   temporal role, coverage, condition/exception. Không trộn hai năm vào một giá trị.
5. Tổng hợp section/quan hệ trong các nhóm vừa ngân sách; kiểm lại diễn giải và
   quan hệ độc lập, giữ trích nguồn chính xác. Quan hệ chỉ là proposal.
6. Lưu JSON/Markdown/proof catalog, dependency map, review ledgers và usage thành
   object bất biến qua StorageDriver, đọc lại kiểm hash trước ghi pointer DB.
7. Người có quyền review có thể duyệt/từ chối/thu hồi theo version/proposal hash.
   Approval không ghi facts nguồn, không chuyển active index, không cấp publication.
8. Mỗi lần đọc/duyệt kiểm lại nguồn và lineage. Nguồn, quyền collection hoặc
   publication pointer đổi làm dẫn xuất stale; thu hồi lan tới dẫn xuất tái sử dụng.

Đây là compiler **theo chủ đề do người dùng chọn**, không phải tự xây một bách
khoa toàn collection hoặc tự viết lại toàn bộ wiki sau mỗi upload. Khám phá quan
hệ trong từng nhóm tổng hợp có giới hạn, chưa exhaustive xuyên mọi assertion.

## Ranh giới mã

| Thành phần | File mới/chỉnh chính |
|---|---|
| API nâng cao | `compilation_router.py`, tích hợp trong router knowledge |
| DTO và review ledger | `compilation_runtime_schemas.py`, tái sử dụng schema602 |
| Source set, quyền, raw hash, manifest | `services/compilation_catalog.py` |
| Topic selection, extraction, synthesis, cache | `services/compilation_engine.py` |
| Kiểm review IDs/coverage, render, dependency map | `services/compilation_validation.py` |
| Dynamic ModelOps/defaults, config seal | `services/compilation_modelops.py` |
| Immutable artifacts, audit chain | `services/compilation_store.py` |
| Intent/OCC/idempotency/read/decision | `services/compilation_service.py` |
| Chặn metadata import vượt review | `services/collection_service.py` |
| Binding602 | Tách helper nội bộ kiểm toàn vẹn để GET không giả quyền upload |

Các file nằm trong module knowledge hiện có; không thêm framework, worker, graph
database, bảng SQL hoặc migration. Tái sử dụng StorageDriver và pattern snapshot
bất biến đã dùng ở Semantic Store. Semantic Store theo từng source revision không
đủ biểu diễn một tập nhiều nguồn, vì vậy compiler dùng namespace artifact riêng
và registry trong JSONB collection hiện có, không sửa semantic annotations nguồn.

Registry chỉ ghi qua service khóa collection, không nhận object từ client/model.
PUT/POST metadata collection thông thường bị chặn với key registry. Actor chỉ
đến từ auth server. Tenant/workspace legacy không làm căn cứ cấp quyền hoặc lọc
nguồn mới; collection/binding/revision được kiểm tường minh ở server.

## Scope, thời gian, unknown và bằng chứng

Source bytes/canonical được đọc và hash lại; manifest unit có start/end/quote
đúng canonical. Không suy năm từ tên file hoặc ngày upload. Bản TemporalScope
hiện có được giữ nguyên cùng milestone/precision trong temporal context; trạng
thái proposed/unknown không được đổi thành verified. Contract assertion602 vẫn
biểu diễn year roles; chưa có bộ quyết định hiệu lực theo ngày mới.

Scope metadata hỗ trợ nhận diện năm/chủ thể khác với condition nghiệp vụ phải
giữ khi diễn giải. Hai lượt model đánh giá role và completeness, không dùng
từ điển heading hoặc từ khóa câu benchmark. Khi thiếu bằng chứng, reviewer trả
unresolved/contradicted; kết quả needs_attention không được admin vượt qua bằng
approval. Unknown/conflict scalar vẫn null, ký hiệu nguồn nằm trong evidence.

Mọi assertion thuộc một source revision. Relation xuyên nguồn giữ endpoint và
proof riêng, không tự xác nhận same-entity/supersedes vì trùng tên hoặc upload
sau. Server namespace ID theo packet; reviewer phải trả đủ đúng IDs, không được
mượn proof có trong collection nhưng không có trong gói đã cấp.

## Ngân sách và ModelOps

Model/provider/fallback lấy từ defaults DB, không cho client chọn endpoint/key.
Cấu hình và credential rotation chỉ tham gia opaque hash trong bộ nhớ; không
ghi plaintext/ciphertext vào bundle. Config đổi giữa build thì từ chối finish.
Reuse packet gắn compiler/policy/config/topic/source/raw/artifact/context hash.

Chọn topic có phân trang, extraction theo nguồn, synthesis xen kẽ nguồn để thấy
các năm trong cùng nhóm khi vừa ngân sách. Đo toàn request serialized theo bộ
đếm byte upper bound hiện có, gồm instruction/field guide/metadata/output reserve.
Reserve cho review ngay khi đóng packet, sau đó vẫn đo lại request thực. Quá
giới hạn báo lỗi trước inference; không cắt lặng assertion hoặc tăng model context.

Giới hạn server mặc định:16 source revisions từ16 binding khác nhau,2000units,
30 extraction packets,64 calls,600s,128assertions/64entities và64sections theo
contract602. Một unit hoặc assertion quá lớn vẫn có thể bị chặn, không bảo đảm
mọi tài liệu đều biên soạn thành công. Không tăng timeout/provider hoặc tắt Quality Gate.

## Tính bền vững và concurrency

Collection lock + refresh bảo vệ registry, intent và decision. Inference ở ngoài
transaction khóa dài; finish khóa lại source/binding, so snapshot rồi mới ghi
pointer. Request cùng signature đang chạy chỉ có một inference owner; mỗi key
được gắn biên nhận. Retry cùng intent uncertain không tự gọi model lại.

Storage ghi trước DB, key theo hash, read-back xác minh. Nếu DB rollback sau ghi,
object không được tham chiếu có thể còn; không tự xóa Storage ngoài policy. Hủy
tác vụ/lỗi provider/lỗi Storage có receipt uncertain khi ghi được; không đổi lỗi
thành “nguồn không có dữ liệu”. Process chết có thể để running, GET hiển thị
uncertain sau deadline; không giả một job đã hoàn tất hoặc tự resend.

Decision gắn version/proposal hash/idempotency và actor. Hai reviewer cùng version
chỉ một transaction thắng; audit append-only phân biệt automated_verification
với user_decision. Thu hồi stale artifact vẫn được phép khi bản artifact/audit
đủ toàn vẹn; không yêu cầu nguồn còn hiện hành để chặn việc thu hồi.

Packet có review hoàn chỉnh mới được reuse. Dẫn xuất bị rejected/revoked hoặc
có lineage bị thu hồi không được dùng lại. Registry giới hạn1000 jobs/4000request
tokens; chưa có màn hình/quy trình GC registry hay xóa artifact tự động mới.

Topic classification và extraction đều có cache theo gói/source/config/topic.
Các source khác không bị phân gói lại chỉ vì một source đổi revision. Sau reuse,
synthesis vẫn chạy kiểm lại; không dùng bản tổng hợp cũ cho source set mới.

Một output đã hoàn tất nhưng sai JSON/schema được sửa định dạng tối đa một lần,
với feedback chỉ gồm mã lỗi/field an toàn; lượt sửa vẫn tính trong64 calls và
deadline. Không áp dụng retry này cho lỗi mạng/quota/quyền/cancellation hoặc
semantic binding. Không lưu raw output sai vào log để tạo vòng prompt riêng.

Các proof scope/time đã được model chọn được gộp tường minh vào evidence chính
trước binding; server không tự suy role/condition hoặc thêm proof chưa được cấp.
Verifier vẫn phải kiểm tính đúng và completeness. Unknown time thiếu căn cứ có
thể bỏ entry, không được khai years/evidence như một scope đã xác định.

Ledger input được server đối soát tường minh: proof scope/time đã được gắn vào
assertion thì không còn nằm trong deferred; unit chưa có assertion được ghi là
unassigned, không được đổi thành “đã chứng minh không liên quan”. Reviewer nhận
nguyên tập primary/deferred và unassigned; nếu bỏ sót nội dung cần thiết thì
machine_complete=false, approval vẫn bị chặn. Không tạo scalar hoặc assertion
mới từ bước kế toán inventory này.

## Tương thích và phần chưa làm

Ingestion phổ thông, Quality Gate, semantic review nguồn, index/vector/publication
và chatbot giữ luồng hiện có. Không hook các trang compiler vào RAG hoặc kích
hoạt dữ kiện chỉ vì máy review đạt. UI, serving integration và rollout là đợt
sau theo thiết kế602; API nâng cao là giao diện sử dụng hiện tại của đợt3–4.

Kiểm chứng thực tế, kết quả model thật và mọi giới hạn nằm trong
[VALIDATION_REPORT.md](./VALIDATION_REPORT.md). Không dùng unit/ASGI test model
giả để tuyên bố đã đạt chất lượng nội dung với model thật hoặc production E2E.
