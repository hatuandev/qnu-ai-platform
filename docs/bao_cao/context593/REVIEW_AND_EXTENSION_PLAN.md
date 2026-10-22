# Context593 — Review các điểm cần mở rộng liên kết và ngữ cảnh

Ngày 22/10/2026. Phạm vi: review mã thật sau Context592 để chuẩn bị cho nhiều
đối tượng, năm, bảng và điều kiện hơn. **Chưa sửa app/test, chưa triển khai các
đề xuất dưới đây.** Giữ model, nguồn, Quality Gate, index/vector và publication;
không LLM/DB/network, reindex/restart/commit/push.

Kết luận: nên hoàn thiện kiểm chứng phạm vi trước khi tăng số liên kết. Đã tái
hiện tám trường hợp thành sáu nhóm phát hiện, cùng hai control hợp lệ. Các probe
chứng minh hành vi ở hàm kiểm chứng/đọc wiki, không chứng minh chatbot đã trả
sai qua toàn luồng. 8/8 follow-up Context592 chưa bao phủ các nhóm mới này.

## 1. [P1] Chưa chứng minh đủ các thành phần của câu hỏi viết lại

Vị trí: [conversation_resolution.py:275](../../../backend/app/modules/rag/conversation_resolution.py#L275),
[intent_contracts.py:39](../../../backend/app/modules/rag/intent_contracts.py#L39).

Validator kiểm các referent model đã gửi, nhưng không kiểm model có bỏ sót
referent bắt buộc cho đối tượng/nguồn trong câu hỏi độc lập hay không. Chỉ một
tham chiếu năm hợp lệ vẫn đủ qua đoạn này; các chữ khác trong câu hỏi chưa bị
ràng buộc vào nguồn hội thoại.

**R01:** lịch sử hỏi ngành Alpha năm 2030; câu hiện tại hỏi thời gian đào tạo.
Đề xuất đổi sang ngành Beta năm 2030 và chỉ gửi referent năm. Hàm trả `True`,
reference_errors rỗng, dù Beta không có trong lượt người dùng nào.

Tác động: đề xuất sai có thể vượt kiểm tra trước retrieval; citation đúng của
Beta sau đó cũng không chứng minh Beta là đối tượng người dùng muốn hỏi. Chưa
đo E2E để kết luận đáp án thực tế sẽ sai, vì còn các guard downstream.

Đề xuất: tạo hợp đồng coverage cho mọi thành phần kế thừa của câu hỏi độc lập,
gồm đối tượng/cơ quan, mã, nguồn/vị trí, vai trò thời gian, đại lượng và điều kiện.
Thiếu căn cứ thì sửa hoặc hỏi lại. Không chấp nhận bằng cách bỏ referent khó.
Quyền collection/binding/revision vẫn do server xác minh riêng.

Regression cần thêm: omitted program/institution/source, thêm tên không có trong
user turns, chỉ gửi năm, đổi mã sang tên, hai tài liệu có cùng tên bảng. Test cả
router đến request retrieval được tạo, không chỉ kiểm JSON hợp lệ.

## 2. [P1] Chưa bảo toàn đầy đủ điều kiện, phủ định và ngoại lệ

Vị trí: [conversation_resolution.py:304](../../../backend/app/modules/rag/conversation_resolution.py#L304).

Kiểm phủ định hiện chỉ yêu cầu câu hỏi viết lại còn một từ phủ định. Các điều
kiện kế thừa trong lịch sử cũng chưa có kiểm chứng coverage riêng.

- **R02:** hiện tại “không tính nhóm A”, viết lại thành “không tính nhóm B” vẫn
  được chấp nhận: còn từ “không” nhưng đối tượng bị loại trừ đã đổi.
- **R03:** lịch sử có “chỉ hệ chính quy và không tính cơ sở X”; câu nối tiếp
  chuyển từ chỉ tiêu sang ghi nhận. Đề xuất giữ ngành/năm nhưng bỏ hai điều kiện
  vẫn được chấp nhận.

Nhánh followup có nối câu hiện tại vào query, nên downstream có thể phát hiện
mâu thuẫn R02; đây chưa phải bằng chứng chắc chắn đáp án cuối sai. R03 đáng chú
ý vì các điều kiện nằm ở lịch sử, không xuất hiện trong câu hiện tại được nối.

Đề xuất: biểu diễn predicate có phạm vi/đối tượng/điều kiện/toán tử, phân biệt
điều kiện được giữ, thay rõ ràng hoặc xóa theo yêu cầu người dùng. So bảo toàn
ý nghĩa có quote nguồn; không so chỉ sự xuất hiện của một từ phủ định.

Regression: đổi A/B, thêm/bỏ “chỉ”, phủ định kép, AND/OR, ngoại lệ, điều kiện
qua nhiều lượt, người dùng chủ động bỏ bộ lọc, thời hạn và đơn vị tương tự chữ.

## 3. [P2] Vai trò năm học có thể mất khi người dùng đổi thời gian rõ ràng

Vị trí: [conversation_resolution.py:287](../../../backend/app/modules/rag/conversation_resolution.py#L287).

Khi câu hiện tại có năm tường minh, code so tập số năm. Kiểm bắt buộc giữ từ
“năm học” chỉ chạy trong nhánh không có năm tường minh.

**R04:** “Còn năm học 2031-2032?” được viết lại thành “Học phí ngành Alpha năm
2031-2032?”, kèm academic_year referent đúng quote. Hàm vẫn trả `True`, dù
standalone không còn thể hiện rõ năm học. Câu hiện tại được nối vào query có
thể giúp bước sau khôi phục vai trò; chưa kết luận E2E chọn sai cột/năm.

Đề xuất: giữ role, giá trị/range, đối tượng chi phối và source proof của thời
gian trong resolved scope. So theo role ngay cả khi người dùng nêu năm mới;
không suy vai trò chỉ từ tập chữ số.

Regression: năm học/năm dương lịch cùng chữ số, năm dữ liệu/ban hành/hiệu lực,
khoảng năm, nhiều năm được so sánh và câu sửa năm có vai trò rõ ràng.

## 4. [P2] Một field chưa biểu diễn được nhiều đối tượng hoặc nhiều bảng

Vị trí: [intent_contracts.py:57](../../../backend/app/modules/rag/intent_contracts.py#L57).

`fields[field]` chỉ lưu một giá trị. Referent thứ hai khác giá trị bị đánh dấu
CONFLICTING_FIELD_VALUES mà chưa xét quan hệ giữa chúng.

- **R05:** so sánh Alpha và Beta, cả hai có quote nguyên văn và đều có trong
  câu viết lại, bị từ chối ở field program.
- **R06:** đối chiếu Bảng 4 và Bảng 5, từng vị trí có quote đúng, bị từ chối ở
  field source_locator.

Cách gộp nguyên cụm “Alpha và Beta” thành một value chỉ dùng được khi cụm đó là
một đoạn liên tục trong một lượt. Nó không giải quyết hai đối tượng có căn cứ
ở các lượt khác nhau, hoặc quan hệ đối chiếu giữa nhiều nguồn.

Đề xuất: dùng tập referent gắn target/role/relation; chỉ coi là conflict khi
các giá trị cùng chi phối một vị trí loại trừ nhau. Cho phép so sánh/hợp/liệt
kê rõ ràng; vẫn chặn chủ thể cũ đã bị sửa và hai đích chưa phân giải được.

Regression: hai ngành/hai mã/hai cơ quan, hai metric, hai bảng cùng/khác tài
liệu, trường hợp so sánh hợp lệ và trường hợp sửa đối tượng cần loại cái cũ.

## 5. [P2] Chia đều ngân sách cho ba trang làm mất phần nguồn vẫn đủ chỗ

Vị trí: [wiki_context.py:183](../../../backend/app/modules/rag/wiki_context.py#L183),
[evidence_pipeline.py:137](../../../backend/app/modules/rag/evidence_pipeline.py#L137).

Mọi trang bị chuẩn bị với cap `max_page_chars // 3`, dù model chỉ cần mở một
trang. Caller còn dành navigation bằng một phần ba context tổng. Section có
closure lớn có thể bị bỏ trước khi chọn trang, dù toàn navigation budget đủ.

**R07:** một trang hợp lệ 5.743 ký tự, navigation budget 14.000. View theo cap
4.666 không có nội dung; view dùng cùng budget 14.000 giữ nguyên section được.
Không có cắt chuỗi hoặc bỏ điều kiện trong control.

Đề xuất: phân bổ theo số trang thực sự chọn và chi phí closure bắt buộc, giữ
nguyên từng nhóm bằng chứng trong tổng budget. Không tăng budget mù hoặc chia
nhỏ điều kiện để lấy đủ ba trang.

Regression: chỉ một trang có section lớn nhưng vẫn vừa tổng budget, nhiều
trang không cùng đủ chỗ, section vượt toàn budget, dependency vòng và note dùng
chung. Phải phân biệt mất recall với lỗi nguyên vẹn nguồn.

## 6. [P3] Cache đọc wiki chưa xét ngân sách navigation mới

Vị trí: [wiki_context.py:173](../../../backend/app/modules/rag/wiki_context.py#L173).

Key cache chỉ có snapshot và plan. Sau khi áp ngân sách mới, cache hit trả block
ngay mà không xem navigation budget/policy hiện tại.

**R08:** đọc trang 2.753 ký tự với budget 14.000, sau đó cùng request/snapshot/
plan gọi lại với budget 2.000. Cache vẫn trả block và chỉ có một navigation
action. Điều này bỏ qua giới hạn navigation mới của lời gọi thứ hai.

Đây là **khoảng hở khi mở rộng API sang ngân sách động**, chưa chứng minh caller
production hiện tại hạ budget trong cùng request: select_context hiện thường
dùng cùng policy. Pack_context phía sau vẫn kiểm tổng budget, nên không suy
thành bypass quyền hoặc đáp án đã được chấp nhận quá giới hạn tổng.

Đề xuất: cache nội dung canonical theo identity tách khỏi view/packing phụ thuộc
ngân sách. Khi hit phải revalidate view/closure theo policy và budget hiệu lực;
không reset model call counter vì thay ngân sách.

Regression: budget giảm/tăng, policy đổi, block/closure thiếu khi hit, snapshot
đổi, giữ cùng request call budget và không tái sử dụng nguồn ngoài snapshot.

## Thứ tự mở rộng đề nghị

1. Coverage đối tượng/nguồn và bảo toàn predicate/điều kiện/ngoại lệ (P1).
2. Vai trò thời gian; tập referent cho các quan hệ nhiều đối tượng/bảng (P2).
3. Allocation nguyên nhóm bằng chứng, rồi cache theo ngân sách hiệu lực (P2/P3).
4. Sau đó mới tăng liên kết xuyên tài liệu và chiều sâu quan hệ. Pin nguồn/
   revision/hash ở server; chưa có căn cứ thì giữ candidate/unknown.

Khi thiết kế vòng tiếp theo cần xem thêm lịch sử dài: hiện chỉ lấy tám lượt
user phù hợp và tối đa 12 referent. Đây là giới hạn rõ ràng, chưa coi là bug:
cần cơ chế anchor có provenance hoặc hỏi lại khi mất căn cứ, không tăng vô hạn
lịch sử và đưa câu trả lời assistant thành nguồn. Chưa triển khai bộ nhớ mới.

## Phương pháp và bằng chứng

- Helper offline đọc AST của đúng hàm và model Pydantic hiện hành, dùng
  InputGuardrail thật. Hàm wiki nhận page/canonical fixture tổng quát, action
  điều hướng giả định; không chạy compiler/model/provider hoặc DB thật.
- Tái hiện **8 gap**, **2 control đúng**; lệnh hoàn chỉnh exit0. Đây là
  diagnostic reproduction, không phải application regression đã sửa đạt.
- [Kết quả từng probe](../../../backend/storage/context593/offline-review.json).
- [Seal mã](../../../backend/storage/context593/code-seals.json): 1.235 file
  app/test/frontend giữ SHA trước/sau; 0 socket attempts, 0 LLM/DB calls.
- Lượt helper đầu exit1 do thiếu globals READ_INSTRUCTION/AppException khi
  trích hàm; bổ sung riêng harness rồi chạy hoàn chỉnh. Không sửa hàm ứng dụng.
- Cwd repo root; lệnh:
  `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context593_review.py`.
- Full Pytest/Ruff app/live benchmark/FE hiện tại **NOT RUN** vì review không
  sửa mã. Full 3.139 PASS/18 FAIL/17 SKIP và live8/8 là lịch sử Context592.
- Không có dữ liệu test DB/Storage dịch vụ để dọn. Chỉ giữ artifact review
  offline bị ignore; không thay checkpoint/corpus/nguồn/quan hệ đã duyệt.

Mọi phát hiện trên đều chỉ ra guard hoặc giới hạn tại đoạn mã cụ thể. Chưa
có benchmark mới cho nhiều nguồn hoặc E2E để khẳng định tỷ lệ ảnh hưởng thực tế.
