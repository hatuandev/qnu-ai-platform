# Context600 — Thiết kế tối thiểu Wiki 4–6

## Hợp đồng và giới hạn tin cậy

Giữ wiki v1 và MD/Structured JSON canonical. Bổ sung projection điều hướng có
version/hash riêng, tạo từ các bundle đã kiểm chứng trong cùng snapshot.
Projection không ghi DB/Storage từ GET và không sửa bundle đã đóng băng.

- Mỗi trang giữ collection/binding/source/index/hash; reference giữ unit, exact
  span/quote và locator. Hai đầu liên kết giữ phạm vi năm/điều kiện/ngoại lệ riêng.
- `source_reference` chỉ chứng minh trang dẫn xuất trỏ về nguồn; `co_mention`
  chỉ chứng minh cùng chuỗi nguyên văn được nhắc ở hai nguồn.
- `same_entity`, `applies_to`, `condition`, `exception`, `references`, `amends`,
  `replaces` phải có căn cứ tương ứng; thiếu thì candidate, không phục vụ như fact.
- Giữ node riêng theo revision; không hợp nhất bằng tên, fuzzy match, mã giống
  nhau hoặc năm. Không chuẩn hóa Unicode/mất số0 trong mã. Không viết lại số liệu.
- Candidate chỉ xuất hiện trong Advanced Review; không chặn source đạt gate.

Trong chế độ extractive, conditions/exceptions là phần chú giải tùy chọn. Mảng
rỗng không chứng minh nguồn vô điều kiện; căn cứ vẫn là toàn bộ trích đoạn và
closure heading/header/footnote được tham chiếu. Consumer không được suy quan hệ
ngữ nghĩa hoặc bỏ điều kiện từ việc thiếu chú giải.

Alias chưa có contract approval nguồn xuyên tài liệu trong schema wiki hiện tại.
Mã trùng kèm hai tên nguyên văn có thể tạo candidate alias có hai căn cứ, nhưng
không được xác nhận cùng thực thể. Trang cùng tên mang nhiều mã giữ nguyên node
và có cảnh báo nhập nhằng. Glossary hiện có chỉ là alias tìm kiếm được duyệt;
không nâng glossary thành bằng chứng identity hoặc tạo approval mới.

## Snapshot và phục vụ

Áp collection, binding active, publication và snapshot trước dựng/rank liên kết.
Candidate chỉ nhận snapshot đã được server xác minh qua luồng có quyền hiện có.
Không đọc bên ngoài snapshot hoặc mở URL/path theo nội dung nguồn.

RAG giữ nguyên lượt model; mở rộng liên kết bằng structural co-mention có literal
chứng minh ở cả hai nguồn, lọc plan trước mở rộng, BFS có visited/depth/node/edge
và context budget. Citation vẫn lấy canonical. Unknown không tự khớp một năm.
Không dùng candidate để mở rộng. Cache request phải tái kiểm dữ liệu/quyền phục
vụ và gắn snapshot/policy/evidence seals; không tạo global graph cache mới.

## Revision tăng dần

Tái dùng bundle chỉ khi cùng binding, canonical, source fingerprint, policy,
metadata và manifest tương thích; kiểm bundle cũ trước rebind identity/page ID,
render và hash cho revision mới. Không đổi source/bundle cũ hoặc active pointer.
Source đổi thì chỉ biên soạn nguồn đó; không biên soạn lại collection.
Unique chunk-set và khóa source hiện có ngăn retry/concurrency tạo bản trùng.
Job cũ chỉ được tạo derivative của revision cũ, không công bố nó thay revision mới.
Remove/rollback thay tập snapshot; projection cũ không được dùng lại.

Giới hạn reuse trong batch này là toàn bộ nguồn không đổi và đủ fingerprint;
không tái dùng đoạn một cách suy đoán khi unit/span/header/footnote hoặc scope
đổi. Vì pipeline vốn biên soạn theo source, nguồn thay đổi không kéo theo gọi
model cho các nguồn khác. Partial-packet reuse là tối ưu riêng khi có bằng chứng
tương thích đầy đủ, không phải điều kiện để phục vụ đúng revision.

## Kiểm tra nhất quán

Kiểm deterministic: identity/hash/span/revision/snapshot, missing endpoint,
backlink, trùng node/link, năm unknown, phạm vi không so sánh được, giá trị khác
nhau trong cùng scope, source limitation và stale. Tái sử dụng structural closure
để phát hiện mất điều kiện/footnote; không đoán nghĩa bằng từ khóa của benchmark.

Phân loại integrity/access blocker, warning cần đối chiếu, source limitation,
candidate chưa xác minh, provider/infrastructure và stale/not compiled. Cảnh báo
ngữ nghĩa không tự thành lỗi parser hoặc cản publication của nguồn đã hợp lệ.
Không tạo hành động ghi/approval mới khi chỉ cần giao diện xem và đối chiếu.

## Tiêu chí kiểm chứng

1. Fixture nhiều nguồn/năm gồm2027: đúng evidence, year role, mã/alias không gộp.
2. Qua handler/service và PostgreSQL test: draft/foreign/revoked không lộ;
   create/update/remove/rollback, cache và concurrent/late job đúng revision.
3. Graph có vòng/nhiều nhánh dừng đúng budget; injection không mở quyền.
4. Legacy không wiki/v1 tiếp tục đọc được; nguyên văn/conditions/unknown giữ.
5. Focused/Ruff, full một lần sau batch ổn định; exact18 lỗi599 là đối chiếu
   lịch sử, không mặc định full hiện tại có cùng lỗi.
6. FE hành vi/Biome/build; baseline64 và cuối64 cùng seals/config/rubric, chấm
   từng ID, retry riêng, target>=51/60 và>=43/50 positive; phân tích mọi loss.
