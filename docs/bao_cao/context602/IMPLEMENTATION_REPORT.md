# Context602 — Sửa nền và thiết lập hợp đồng biên soạn

Ngày 22/10/2026. Triển khai đợt 1 và 2 theo kế hoạch người dùng chấp thuận.
Không triển khai compiler tổng hợp xuyên nguồn, persistence mới hoặc thay chatbot.

## Đợt 1 — Nguyên nhân và phương pháp

### DOCX bị chia theo run

Docling có thể tách một paragraph thành nhiều text items do định dạng/run. Các
fragment như dấu ngoặc, phần ngày hoặc phần trăm vẫn là dữ liệu nguồn. Bỏ chúng
hoặc nối theo khoảng cách sẽ mất nội dung hoặc gán sai cấu trúc.

`docx_paragraphs.reconcile_paragraphs` đối chiếu chuỗi text items liên tiếp, cùng
level và parent, với một paragraph OOXML đầy đủ duy nhất. Không dùng khoảng cách
hay từ khóa chủ đề. Không nối qua table/list/header hoặc paragraph native khác.
Nguồn trùng chữ, đoạn thiếu chữ, fragment bắt đầu có nhiều occurrence hoặc đã có
paragraph native độc lập khớp trọn vẹn thì giữ nguyên. Giới hạn đối chiếu 64 item.

Builder dùng bản copy của item, giữ raw engine text/ref/index, locator và hash
paragraph trong `source_data.native_paragraph_reconciliation`. Không sửa nguồn
hoặc engine document. Nội dung nguồn mới vẫn có thể khác canonical cũ do ranh
giới đoạn, nên chỉ tạo dẫn xuất thử nghiệm local; không sửa revision đang phục vụ.

### Năm sát chữ và mã định danh

Validator cũ dùng word boundary nên `năm2027` không được nhận diện, còn mã có dấu
nối hoặc số phiên bản có thể cho phép suy năm nhầm. Tách literal candidates của
câu hỏi khỏi regex kiểm chứng năm trong nguồn. Hỗ trợ chữ sát năm, khoảng năm và
ngày đầy đủ; loại ứng viên trong số dài, mã nối, underscore và prefix dạng mã viết
hoa. Vai trò data/publication/event vẫn do planner phân loại và kiểm chứng nguồn;
nhận diện literal không tự xác nhận hiệu lực. History chỉ được dùng theo policy
hiện có, search variant không được bịa thêm năm.

### Inventory dài và ký hiệu ngắn

Compiler trước đó gộp mọi section của trang nguồn rồi kiểm giới hạn 512, khiến
cẩm nang 1.301 unit thất bại sau 19 gói. `wiki_inventory` chia thành các trang có
giới hạn, ID/part/count/previous/next xác định và kiểm lại toàn bộ chuỗi. Validation
đòi đủ inventory nguồn trong extractive mode, không mất hoặc lặp primary unit.

Ký hiệu nguồn 1–2 ký tự chỉ được giữ bằng reference có `literal_only=true`, do
server trích nguyên văn trong excerpt và đối chiếu lại với unit thật. Reference
ngữ nghĩa thông thường vẫn yêu cầu ít nhất 3 ký tự. Generated mode không được dùng
nhãn literal này. Không diễn giải ký hiệu thành 0 hoặc fact; usage vẫn navigation_only.

Trang nguồn nhiều phần được liên kết continuation; source_reference trỏ phần đầu.
Reuse tạo lại các ID/continuation theo identity revision mới. API đọc trang giữ
metadata phân phần. Các bundle cũ không phân phần vẫn giữ ID/render tương thích.

### Chọn bằng chứng và phục hồi điều kiện

Trace601 của P07 cho thấy đã chọn derived fact row và bị từ chối vì không giữ
đúng entity; không phải mất PDF hoặc thiếu context window. Khi một derived fact
đã có đúng một canonical owner trong tập bằng chứng cùng binding/index/revision/
hash/unit, selector dùng canonical owner và giữ header/context hiện có. Fact
không có owner duy nhất, legacy hoặc khác revision không bị bỏ theo quy tắc này.
Guard của reviewed fact và verifier giữ nguyên.

Trace P08 có qualifier bị phục hồi từ phần sau dấu chấm phẩy, rồi verifier báo
đoạn bị cắt giữa câu. Recovery lấy toàn bộ sentence envelope trong đúng block và
kiểm lại độc lập. Quote có nhiều occurrence hoặc envelope vượt budget bị từ chối;
không mượn câu từ nguồn khác hoặc chấp nhận tự động.

Các lần phục hồi điều kiện ở cùng block giữ signature theo quote hash để không
nhầm một điều kiện mới với lần lặp trước. Prose recovery chỉ tiếp tục phục hồi ở
vòng hai khi có gap cụ thể hoặc tiến triển cùng owner; gap owner khác vẫn đi qua
reselection như contract599. Giữ tối đa hai vòng, không tăng call budget hoặc
hạ các yêu cầu topic/condition/verifier. Bổ sung trace ID/count/reason không chứa
raw prompt, nội dung nhạy cảm hay credential.

P16/M08 cần kết quả live theo từng ID để đánh giá selection/coverage thực tế.
Không dùng unit test để kết luận các câu này đã đạt; xem VALIDATION_REPORT.md.

Lượt live đầu trong602 đạt58/60 nhưng P06/P08 còn thất bại. Trace mới và regression
hai ca tái hiện cho thấy khi vòng cuối chuyển sang reselection vì qualifier có
owner khác, draft mới có thể bỏ điều kiện vừa được audit xác định. Việc giữ claim
cũ không đủ, vì điều kiện đó chưa từng có trong claim được chấp nhận.

Bổ sung `retain_recovered_conditions`: sau reselection, phục hồi chính gap đã
được xác định, giữ đúng block/source/offset và đưa vào lần verifier/audit vốn có.
Không tăng hai vòng/số lần gọi hoặc tự coi điều kiện đã được chấp nhận. Hai chú
thích giống chữ ở block khác không được coi là đã giữ thay nhau; ID trùng được
đổi ở draft, không thay bằng chứng. Verifier trả incomplete vẫn chặn.

Prose recovery dùng cùng literal-year lexer với validation, gồm năm sát chữ,
khoảng năm và năm học dạng slash; không tự biến mã có năm thành scope. Các test
thêm kiểm trực tiếp ranh giới trước inference để tránh chỉ sửa validator mà bỏ
sót nhánh fallback.

## Đợt 2 — Kết quả thiết kế

Đã tạo hợp đồng Pydantic, JSON Schema và hàm binding thuần cho entity, assertion,
temporal role, scope, condition, exception, relation và synthesis section.
Biên nhận gắn proposal/source-set hash nhưng luôn `review_only`; chưa có endpoint,
quyết định semantic, ghi DB, vector hoặc publication mới.

Chi tiết trong [COMPILATION_DESIGN.md](./COMPILATION_DESIGN.md) và
[COMPILATION_SCHEMA.json](./COMPILATION_SCHEMA.json). Thiết kế trình bày phần đã
hiện thực và phần vòng đời/persistence/concurrency dành cho đợt sau riêng biệt.

## Phạm vi và tương thích

Không sửa thay đổi Context600/601 đang có ngoài các điểm tích hợp trực tiếp của
nhiệm vụ này. Snapshot app trước sửa được lưu riêng để đối chiếu; không dùng Git
HEAD làm đại diện cho trạng thái bắt đầu phiên. Không sửa frontend, model/config,
nguồn/index/vector/publication đang có, không restart hoặc commit/push.

Fixture integration600 nhận DB test602 kèm kiểm comment sở hữu như600/601; không
mở quyền vào DB ứng dụng. Mọi test tự động dùng Storage riêng và network guard.
Các phép thử ModelOps thật được tách khỏi pytest và có kiểm source/model/vector
trước/sau; usage/audit hợp lệ được giữ lại.
