# Context602 — Thiết kế hợp đồng biên soạn tri thức xuyên nguồn

Ngày 22/10/2026. Phạm vi được giao: đợt 1 sửa nền và đợt 2 thiết kế hợp đồng.
Đây chưa phải bộ biên soạn xuyên nguồn của đợt 3 hoặc cơ chế phục vụ mới.

## 1. Mục tiêu và ranh giới

Giữ nguyên bytes tài liệu, QNU RAG Markdown Standard v1.0 và Structured JSON làm
nguồn có thể đối soát. Trang tổng hợp xuyên nguồn là dẫn xuất riêng. Các dữ kiện
vẫn có collection, binding, source revision, canonical hash và tọa độ nguồn.

Tái sử dụng Source Revision, StorageDriver, ModelOps, Semantic Store, Evidence
Binding, snapshot, Quality Gate và publication hiện có. Không thêm graph database,
framework hoặc worker. Không chạy migration, không tạo bảng và không sửa model
đang chạy trong đợt này.

`compilation_schemas.py` mô tả đề xuất chưa tin cậy. `compilation_contracts.py`
thực hiện một bước thuần bộ nhớ: kiểm quyền upload, đối chiếu snapshot nguồn và
gắn các ID bằng chứng vào trích đoạn thật. Không có router/API ghi mới hoặc hook
vào ingestion/RAG. Hợp đồng chưa phải endpoint cho client tự gửi source objects.

## 2. Đối tượng dữ liệu

| Đối tượng | Trường chính | Ý nghĩa |
|---|---|---|
| Entity | ID, nhãn, evidence IDs | Chủ thể đề xuất; nhãn giống nhau chưa chứng minh cùng danh tính |
| Assertion | Entity, thuộc tính, giá trị/đơn vị, trạng thái, scope, thời gian, điều kiện, ngoại lệ | Một nhận định của một nguồn; so sánh xuyên nguồn dùng các nhận định riêng |
| Temporal scope | Vai trò data/publication/effective/event hoặc unknown, năm, evidence IDs riêng | Năm xuất hiện đúng trích đoạn là điều kiện cần; chưa chứng minh vai trò ngữ nghĩa |
| Scope | Dimension, giá trị, evidence IDs | Phạm vi như nhóm, phương thức hoặc cột; chưa tự xác nhận suy luận của LLM |
| Relation | Hai endpoint, loại quan hệ, bằng chứng, thời gian, phạm vi, điều kiện/ngoại lệ | Gợi ý same_entity/alias/supports/contradicts/supersedes/prerequisite/exception |
| Section | Tiêu đề, diễn giải, assertion IDs | Phần trang tổng hợp; còn cần kiểm chứng diễn giải ở đợt 3 |
| Draft | Version, snapshot hash, các đối tượng trên | Đề xuất có giới hạn kích thước, cấm field ngoài schema |
| Binding receipt | Proposal hash, catalog, state, usage, publication, SHA | Biên nhận gắn nguồn; không có hiệu lực semantic/serving |

Không dùng năm từ tên file hoặc ngày upload làm phạm vi mọi dòng. `unknown` và
`conflict` giữ giá trị scalar là null; nguyên ký hiệu và các giá trị mâu thuẫn nằm
trong bằng chứng. Giá trị 0 có nguồn là `present`, khác hoàn toàn với unknown.
Một câu hỏi có thể tham chiếu nhiều năm nhưng các assertion phải giữ nguồn riêng.

Contract thử nghiệm v1 dùng temporal role ở độ chính xác năm. Ngày/tháng và
khoảng hiệu lực gốc được giữ nguyên trong assertion/evidence; không được lấy
trường `years` để quyết định hiệu lực theo ngày. Khi triển khai sử dụng ở đợt 3,
tái sử dụng các milestone/precision của TemporalScope hiện có thay vì viết bộ
chuẩn hóa lịch mới; bổ sung phiên bản contract nếu cần trường máy đọc riêng.

## 3. Bằng chứng và kiểm tra đã hiện thực

1. Caller phía server phải lấy tập source được actor phép đọc trong collection.
   `evidence_catalog` không tự thay thế truy vấn quyền hoặc publication filter.
   Hàm không nhận đường dẫn/URL do model chọn; kiểm lại collection và source hash.
2. Catalog tạo opaque ID từ identity, unit, start/end, quote và source locations.
   Unit manifest được kiểm theo canonical hiện có. Không tự gắn trích dẫn sang
   revision mới hoặc sang nguồn khác có đoạn chữ giống nhau.
3. Draft phải khớp snapshot hash của catalog hiện tại. Sai canonical hash, revision,
   scope collection, ID trùng, evidence thiếu hoặc endpoint lạ đều bị từ chối.
4. Evidence thời gian/phạm vi phải nằm trong evidence của chính item; năm phải có
   mặt trong các trích đoạn đã chọn. Assertion không được mượn điều kiện/ngoại lệ
   từ source revision khác. Quan hệ xuyên nguồn vẫn là đề xuất riêng.
5. Chặn model khai báo actor, approved hoặc published bằng schema `extra=forbid`.
   Actor chỉ được lấy từ trusted auth context.
6. Kết quả luôn là `state=evidence_bound`, `usage=review_only`,
   `semantic_verification=not_run`, `publication=unpublished`.

Trích đoạn có thật không chứng minh diễn giải đúng, cùng danh tính, đúng vai trò
năm hoặc đủ điều kiện. Một receipt có hash hợp lệ cũng không phải giấy phép ghi.
Không được thêm receipt này vào facts có hiệu lực hay truy hồi chatbot chỉ vì
bước binding đã đạt.

## 4. Vòng đời dự kiến cho đợt 3–4

| Từ trạng thái | Kiểm tra cần có | Trạng thái tiếp theo |
|---|---|---|
| Draft | Binding, snapshot, quyền, contract | Evidence bound hoặc rejected |
| Evidence bound | Entailment, vai trò năm, danh tính, đủ điều kiện/ngoại lệ | Semantic candidate đã kiểm hoặc unresolved/conflict |
| Candidate đủ căn cứ | Chính sách phiên bản hóa; quyết định người dùng khi cần theo Semantic Store | Dẫn xuất có chứng nhận tương ứng |
| Dẫn xuất đã kiểm | Source/index/current snapshot và policy phục vụ còn hợp lệ | Có thể được chọn khi hỏi |
| Bất kỳ dẫn xuất nào | Nguồn đổi, thu hồi, mất quyền hoặc hash lệch | Stale/revoked; ngừng sử dụng và biên soạn lại phần bị ảnh hưởng |

Các bước sau `evidence_bound` là **thiết kế**, chưa hiện thực trong Context602.
Chứng nhận tương lai phải gắn proposal hash, toàn bộ source revisions, policy
version, phương pháp kiểm, actor/decision hợp lệ và thời điểm; phải được xác minh
lại trước sử dụng. Publication tiếp tục là thao tác riêng qua cơ chế hiện có.

Kết quả thực nghiệm602 làm rõ một ranh giới bắt buộc cho đợt 3: **metadata hỗ trợ
phạm vi** (nhận diện tài liệu, năm dữ liệu, năm ban hành) khác với **điều kiện áp
dụng phải giữ trong câu trả lời**. Temporal/scope có evidence riêng để chứng minh
vai trò; condition/exception phải có bằng chứng rằng chúng thực sự chi phối
assertion. Không bắt chép toàn bộ tên tài liệu như một điều kiện nghiệp vụ nếu
chính phát biểu nguồn đã chứng minh năm/chủ thể. Đồng thời không dùng nhãn
"metadata" để lược bỏ điều kiện nhóm, ngành, kỳ hoặc ngoại lệ thật.

M08 cho thấy cả mã/kỳ thi/năm2026 có trong cùng paragraph nguồn, nhưng audit bắt
giữ tiêu đề, còn verifier loại tiêu đề vì không trả lời mã/kỳ thi. Cần kiểm chứng
riêng vai trò và cách giữ scope trước khi nhận định có hiệu lực. Binding thuần
trong đợt 2 không giải quyết hoặc tự phê duyệt mâu thuẫn này.

Tự động ingestion vẫn dùng AUTO_READY / READY_WITH_LIMITATIONS / NEEDS_ATTENTION.
Đề xuất semantic chưa giải quyết không chặn phần nguồn đã đạt kiểm tra hiện hành.
Không tự phê duyệt semantic hoặc publish để làm thử nghiệm thành công.

## 5. Persistence, transaction và khả năng phục hồi

Đợt này chỉ có hàm thuần; gọi lặp tạo cùng biên nhận, không tạo record. Chưa tuyên
bố đã kiểm concurrency hoặc idempotency của một endpoint/persistence mới.

Đợt 3–4 cần tận dụng snapshot/StorageDriver/Semantic Store sau khi audit khả năng
tái sử dụng thực tế. Khóa công việc dự kiến gồm collection + source-set hash +
compiler/policy/config hash. Ghi draft và chứng nhận theo revision, optimistic
concurrency với snapshot nguồn; xung đột không ghi đè phiên bản mới. Audit chỉ
append; lưu retry intent/receipt và chỉ thử lại bước xác định chưa thành công.

Registry phụ thuộc ngược từ source unit → assertion → section/relation giúp đánh
dấu stale và cập nhật từng phần. Chỉ gọi LLM cho gói bị ảnh hưởng, có budget và
coverage ledger. Không tự suy văn bản tải sau thay thế văn bản cũ.

## 6. Kiểm chứng và điều kiện chuyển sang đợt 3

Regression đợt này kiểm quyền, schema tự duyệt, unknown→0, năm bịa, sai revision/
hash/collection, ID thiếu/trùng, endpoint lạ và điều kiện khác nguồn. Không có
LLM hoặc ghi dữ liệu trong các test hợp đồng.

Đợt 3 phải bổ sung entailment/role/coverage độc lập, catalog theo topic, điều phối
ModelOps, lưu dẫn xuất, handler kiểm quyền và các ca failure. Đợt 4 mới nghiệm thu
persistence/concurrency/revocation của lớp mới. UI, vector generation, publication
và thay luồng chatbot giữ nguyên phạm vi các đợt sau.

Các con số PASS/FAIL thực tế và giới hạn nằm trong VALIDATION_REPORT.md; không
dùng thiết kế hoặc unit test của hợp đồng làm chứng cứ nghiệm thu chatbot mới.
