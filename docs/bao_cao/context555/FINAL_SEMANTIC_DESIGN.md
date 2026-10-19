# Thiết kế semantic review cuối — Context555

Ngày 19/10/2026. Đây là thiết kế cho proposal chờ người dùng duyệt, không phải quyết định nghiệp vụ đã có hiệu lực.

## Nguyên nhân A03 gắn sai

Checkpoint Context553 dùng `scope=column`, sáu dòng nhóm A và c10/c11/c12 để biểu diễn quy định hồ sơ thiết bị năm 2027. Cùng năm không chứng minh cùng đối tượng: ba cột này là chỉ tiêu, ước tính và tỷ lệ người học. `_apply_notes` trước đây chỉ có liên kết theo bảng/dòng/cột, nên khi proposal được duyệt, assertion này sẽ đi thẳng vào context của các fact số liệu.

Nguồn không có định danh riêng cho từng hồ sơ thiết bị. Vì vậy không tạo một đối tượng hồ sơ giả, không suy rằng mọi hồ sơ của sáu chương trình đều đủ điều kiện, và không sửa nguồn hoặc các cột dữ liệu để hợp thức hóa target.

## Thiết kế tối thiểu

`NoteScope` thêm `context_kind=data|workflow` và `context_label`. Giá trị mặc định không được ghi vào serialization để giữ assertion ID và seal của annotation cũ. Workflow phải có assertion v1, nhãn ngữ cảnh và scope không phải ô/cột. Dữ liệu thô, selector v1/v2 và schema snapshot `qnu-semantic-v1` không thay đổi.

A03 trở thành ngữ cảnh workflow có điều kiện: bảng t001, tập chủ thể r001–r006, không có column_ids. Trích đoạn l006 [218,520) và toàn l014 [0,438) được giữ nguyên. Các điều kiện bắt buộc gồm nhóm A, kế hoạch 2027, lịch kiểm định trùng thời điểm khóa dự kiến, văn bản thông báo lịch và quyết định gia hạn của Phòng Đào tạo; tối đa 15 **ngày làm việc từ hạn xác nhận ban đầu**. Giữ loại trừ nhóm B, dữ liệu người học 2025/ghi nhận 2026, chỉ tiêu tuyển sinh và thẩm quyền sử dụng ngân sách.

Workflow có đơn vị assertion và chunk riêng, có liên kết đến đoạn điều kiện. `_apply_notes` không gắn đơn vị đó vào row.context_refs hay field_context_refs. Các fact sinh viên vì thế không nhận A03 như điều kiện định lượng. Phạm vi nhóm và nguyên văn điều kiện vẫn có trong metadata của đơn vị/chunk workflow; không sinh giá trị, tính toán hoặc quyền gia hạn tự động.

## Reference mapping trước và sau

`ReferenceAssessment.links` bổ sung vai trò `direct`, `protective`, `conditional`, evidence có binding, lý do và điều kiện bắt buộc cho liên kết conditional. Assertion IDs trong links phải đúng và phủ chính xác tập assertion_ids đã khai báo. Evidence phải là thân văn bản có thật trong phạm vi assessment; heading không đủ. Mảng cũ không có links tiếp tục đọc được.

| Issue | Trước | Sau |
|---|---|---|
| O03 / s030 | Heading dẫn tới mapping phẳng A05,A02,A07,A08,A09 | Container dẫn đúng body l012/p084. Không tạo assertion từ heading. Vai trò cụ thể theo hai đoạn, gồm A03/A05 trực tiếp, các bảo vệ và điều kiện tương ứng O04/O05. |
| O04 / l012 | A05,A02,A07,A08 không tách khoản | Khoản 3 trực tiếp A05. Khoản 2 bảo vệ A06,A07,A08: thẩm định lại một lần/30 ngày từ thông báo, chứng cứ mới cùng kỳ, không đổi năm. A02/A11 chỉ liên quan có điều kiện khi thực hiện đúng quy trình Q. |
| O05 / p084 | Liên kết phẳng cả A01–A12 | Direct A03,A05; protective A04,A10,A12 và A06,A07,A08; conditional A02,A11 và A09. Bỏ liên kết độc lập tới A01 vì thiếu căn cứ. |
| O06 / p090 | A03,A05 | Hai ngoại lệ trực tiếp độc lập, có l014/l015; không hợp nhất quyền A/B. |
| O07 / s036 | A05 | Chỉ A05, có thân l015/p092; không tạo quyền thiết bị A03. |
| O08 / footnote_2 | A04,A10,A12 | Bảo vệ định danh ba quan hệ; giữ 0012,00027,AM-0007 là chuỗi. Không gộp quyết định O08 và S10. |

Các assessment là phân tích để người dùng đối chiếu. Cả ba loại vai trò **không tự sinh effective graph edges**. Một reference có liên quan không buộc người dùng chọn “không áp dụng”; sử dụng action `related_context_reviewed` hiện có và đủ supporting evidence.

A09 chưa chứng minh tỷ lệ Bảng 1 là đầu vào Q. Conditional chỉ ghi rõ điều kiện chưa được xác lập; không tạo liên kết tính toán hoặc khẳng định điều kiện đã thỏa. Hai mốc 30 ngày của thẩm định lại và hồ sơ thực tập cũng không thay mốc 15 ngày làm việc của thiết bị.

## Ranh giới offline và ứng dụng

Adapter nhập yêu cầu contract `qnu-semantic-checkpoint-v1`, source_artifact và proposal. Server kiểm actor/quyền, collection/binding/revision, draft và lease; đọc cặp MD/JSON của revision bằng loader hiện có. Phải khớp cả hai hash nguồn và toàn cấu trúc/ô/manifest, rồi mới đổi document/revision trong binding một cách xác định. Tên file không được dùng để matching.

Proposal offline phải là pending đúng hash/input hash; chuỗi approved/verified và review từ ngoài không cấp quyền. Annotation nhập phải có binding và assertion version được hỗ trợ. Server tạo binding, assertion ID, issue ID và proposal hash mới; lưu ánh xạ ID/hash offline và actor staging để audit. Không chuyển quyết định cũ sang proposal mới. Nhập lặp cùng gói là idempotent; proposal khác không âm thầm thay proposal đang mở. Sau yêu cầu sửa/từ chối, nhập bản thay thế phải chỉ đúng hash hiện hành.

Pending dùng JSON artifact trên revision hiện có. Duyệt tiếp tục qua `semantic-review`, snapshot immutable và rebuild hiện có, không có persistence/annotation store mới, không migration. Một issue chưa có quyết định hợp lệ vẫn chặn apply toàn proposal; đó là chính sách giao dịch, không phải chứng cứ rằng reference chi phối toàn bảng.

## Kiểm tra với revision thật

Audit DB dùng transaction chỉ đọc tìm bằng hash DOCX gốc. Có một revision nháp cùng file gốc nhưng **khác cả hash MD và Structured Document**. Không có cặp khớp checkpoint. Việc stage thật bị chặn; không ghi DB/Storage ứng dụng, không copy trạng thái offline sang bản này. Chi tiết và bước tiếp theo ở [REVIEW_READY](REVIEW_READY.md).

## Tác động graph/facts/chunks

- A03 không có dependency vào c10/c11/c12 ở bất kỳ dòng nào; giữ riêng subject group và evidence.
- 11 assertion còn lại giữ nguyên payload; AM-0007 vẫn r003, không mở A04/A10 sang AM-0070/r004. AM-0070 vẫn có thể là chủ thể nhóm A khi đủ điều kiện A03.
- Raw tables không thay đổi; mã có số 0 đầu, ba nhóm năm và tính dự kiến của 2027 được giữ.
- Reference role metadata không thay graph của dữ liệu số. Dữ liệu hiệu lực không đổi khi chỉ stage, yêu cầu sửa hoặc từ chối.
- Test có actor TEST xác nhận snapshot sống qua đóng session, đọc lại Storage và rebuild. Đây không phải approval thật hoặc chứng cứ E2E đã đạt.
