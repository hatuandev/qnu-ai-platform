# Context590 — Nguyên nhân lỗi RAG còn lại và phương án sửa

## Kết luận

Chưa có căn cứ cần bóc tách lại PDF hoặc tạo lại vector để sửa nhóm lỗi này.
Đã đối chiếu cả 24 gold spans của 9 câu còn lỗi: tất cả khớp nguyên văn canonical;
23 unit nguồn duy nhất đều được tham chiếu trong wiki đã lưu. Điều này chứng minh
nội dung cần thiết còn trong nguồn, không chứng minh mọi lần chạy đều chọn đủ nó.

Phần cần sửa chủ yếu nằm ở hợp đồng điều hướng, phân loại câu hỏi và cách kiểm
chứng câu trả lời. Metadata ô chưa rõ nghĩa vẫn còn hạn chế; cần xử lý đúng vai trò
của nó, không đổi thành dữ kiện định lượng đã xác minh.

Phân tích dựa trên mã hiện tại, artifacts Context589 và 12 probe offline. Không
gọi LLM thật, không chạy lại benchmark, không sửa app/tests hoặc ghi DB/vector.
Giữ revision `ks_rev_993a7ad91b32`, index `idx_rev_6bf0d6f86b1b` làm đối tượng
đối chiếu; không thay model, xuất bản, commit hoặc push.

## Đối chiếu từng lỗi

| Câu | Điểm dừng đã xác minh | Nguyên nhân và mức chắc chắn | Hướng sửa |
|---|---|---|---|
| P01 | Đã mở 2 trang/11 evidence blocks; lượt sau lỗi `ALL_PROVIDERS_UNAVAILABLE` | Lỗi ở biên ModelOps/adapter; chưa xác định được lỗi upstream cụ thể. Log có DomainException 502 nhưng `http_status=null`, không đủ để gọi là upstream HTTP 502 hoặc timeout. | Bổ sung diagnostic an toàn cho mã lỗi gốc, finish reason, stage và số lần gọi; phân biệt transport/protocol/output budget. Sau đó mới quyết định retry đúng loại lỗi. |
| P03 | Đã mở 1 trang/9 blocks; tiếp theo `KNOWLEDGE_WIKI_READ_INVALID` | `WikiReadAction` bị `extra_forbidden`; reader không có lượt sửa contract và lỗi làm mất kết quả điều hướng trong request. | Hợp đồng theo trạng thái, action/IDs hợp lệ cho từng bước, sửa định dạng có giới hạn trong cùng ngân sách. |
| P05 | Đã tìm đúng đoạn với rerank score khoảng 0,9988; đoạn nằm trong context; cuối cùng `PROSE_NOT_FULLY_VERIFIED` | Hai topic đều đạt, không lỗi binding; lần audit sau sửa phát sinh thiếu `e6.c3`. Vòng bổ sung chưa ổn định tập điều kiện liên quan. | Chốt tập điều kiện nguồn có phạm vi trước khi dựng câu trả lời; server giữ nguyên văn phần đã chọn và audit lại. |
| P07 | `YEAR_REQUIRED`, chưa đọc nguồn | Plan chọn `requires_year=true`; server trả clarify ngay trước retrieval. Câu hỏi yêu cầu nội dung ngoại lệ trong nguồn, không yêu cầu một kỳ tuyển sinh hiện tại. | Tách hỏi nội dung nguồn với hỏi hiệu lực/giá trị theo năm; chỉ đòi năm khi thực sự cần phân giải phạm vi. |
| P09 | `ROW_ANSWER_SOURCE_INVALID` trước selector/đọc chú giải | Tái hiện chính xác: ô `ambiguous` làm `_standard_fields` ném `Unresolved standard cell cannot answer`, bị bọc thành lỗi tọa độ. | Tách dữ liệu hỏng khỏi dữ liệu chưa rõ nghĩa; cho nhánh mô tả đọc nguyên văn/chú giải, vẫn chặn suy số hoặc đoán nghĩa. |
| P10 | Cùng lỗi P09 | Cả hàng bị loại chỉ vì một ô `ambiguous`, dù câu hỏi đang so ý nghĩa ký hiệu với số 0. Hàng số 0 độc lập đi qua catalog bình thường. | Giữ kiểm chứng ô và các trạng thái riêng; không để một ô hạn chế làm hỏng toàn bộ giải thích có nguồn. |
| P11 | `YEAR_REQUIRED`, chưa đọc nguồn | Cùng cơ chế P07; đang so ngưỡng/toán tử/đơn vị trong một bảng xác định nhưng bị hỏi năm tuyển sinh. | Cùng sửa phạm vi năm, giữ đúng toán tử, chủ thể và đơn vị; không tự chọn năm. |
| P13 | Đã mở 1 trang/8 blocks; lượt sau sai contract | Cùng nhóm P03. Nội dung hình đã xác nhận có trong canonical và wiki, không phải lần này mất OCR hình. | Sửa reader chung, kiểm lại liên kết hình và lời chú giải. |
| P14 | Đã mở 1 trang/9 blocks; lượt sau sai contract | Cùng nhóm P03. Hai ghi chú giống chữ vẫn có locator riêng trong nguồn. | Sửa reader chung; regression phải giữ hai chủ sở hữu bảng riêng biệt. |

P06 không còn thuộc 9 lỗi trên: lượt bổ sung riêng đã PASS. Record gián đoạn của
bộ chính vẫn giữ nguyên. Điểm tham khảo lịch sử là 51/60, positive 41/50; không
phải kết quả đo mới của Context590. Chưa đủ ngưỡng positive 43/50 và chưa APPROVED.

## 1. Reader đang làm điều hướng trở thành điểm chặn chung

Ở [wiki_context.py](../../../backend/app/modules/rag/wiki_context.py), sau
`read_pages`, server đã lấy được các block canonical hợp lệ. Vòng lặp tiếp tục
gọi model cho đến khi model báo `done` hoặc hết lượt. Lần hai sai shape thì
exception thoát ra trước khi `_wiki_context` lưu được tập bằng chứng. Probe D09
tái hiện cơ chế này với response giả có field thừa: có 2 lần gọi stub, trace chỉ
đếm 1, không trả được bằng chứng đã đọc. Đây là probe contract, không phải gọi
Luna thật hay khẳng định field giả chính là field Luna đã sinh.

Các request trong [evidence_model.py](../../../backend/app/modules/rag/evidence_model.py)
đang dùng hướng dẫn tên trường rồi validate sau sinh; call này không truyền
`output_contract` của ModelOps. `preserve_structured_output` không tự biến
request thành schema được provider cưỡng chế. Lỗi extra field bị chặn là đúng;
đổi `extra=ignore` sẽ che lỗi thay vì sửa.

Đề nghị giữ reader như nguồn candidate bổ sung trong scope đã ghim. Action tiếp
theo phải giới hạn theo trạng thái thực: trang nào đã mở, ID nào được phép đọc,
còn bao nhiêu budget. Có một lần sửa hình dạng nếu budget cho phép, không nhân
số lần gọi qua retry lồng nhau. Ghi số lần đã thử cả khi thất bại. Có thể kết
thúc sớm khi server đã có bộ nguồn cần thiết; bước kiểm đủ chứng cứ vẫn phải
diễn ra ở answer verification. Nếu có cơ chế degradation thì phải là policy rõ,
giữ trace lỗi và kiểm chứng canonical đầy đủ, không tự gọi là đọc wiki thành công.

Điểm gắn wiki tại [service.py](../../../backend/app/modules/rag/service.py) còn
khiến câu narrative chuyển sang toàn bộ `evidence_pipeline` chỉ vì snapshot có
wiki. Giữ fact-first đã cứu các câu ô, nhưng chưa bảo toàn hành vi narrative cũ.
Nên tách quyền dùng wiki khỏi quyền thay toàn bộ answer pipeline: cùng một
nguồn không nên thay chính sách yêu cầu năm chỉ vì có thêm trang điều hướng.

## 2. P09/P10: integrity và khả năng dùng làm số đang bị gộp

[row_answer_contract.py](../../../backend/app/modules/rag/row_answer_contract.py)
đang kiểm raw/header/coordinates và trạng thái `ambiguous` trong cùng hàm.
`build_catalog` bọc mọi ValueError thành `ROW_ANSWER_SOURCE_INVALID`.
[row_answer.py](../../../backend/app/modules/rag/row_answer.py) gọi catalog trước
khi selector được quyết định câu hỏi có thực sự cần lấy giá trị ô hay không.

Probe D03/D04 dùng artifact thật đã lưu và tái hiện đúng lỗi. D05 kiểm số 0 vẫn
qua; D06 đổi raw trên bản sao RAM bị chặn do lệch canonical. Cần giữ D06 làm
negative control sau sửa: nới xử lý unknown không được nới integrity.

Thiết kế phù hợp là có trạng thái khả năng sử dụng riêng: ô nguyên vẹn nhưng
chưa rõ nghĩa được trích để mô tả hạn chế; không được làm toán hoặc làm fact số.
Lỗi hash/row/header/span vẫn là lỗi cứng. Chú giải có nghĩa phải được viện dẫn
theo đúng bảng/hàng; việc trả lời từ chú giải không tự duyệt annotation hoặc sửa
state đã lưu. Nguồn chưa định nghĩa thì trả đúng sự chưa định nghĩa, không suy
ra số 0, không gán một nghĩa cho mọi dấu gạch.

## 3. P07/P11: yêu cầu năm quá sớm

[evidence_pipeline.py](../../../backend/app/modules/rag/evidence_pipeline.py)
trả `YEAR_REQUIRED` ngay sau planning và trước `select_context`. D07/D08 replay
đúng plan đã lưu; số lần gọi đọc nguồn bằng 0. `retrieval_executed=true` trong
trace service đang phản ánh chọn nhánh, không chứng minh retrieval đã chạy.

Cần phân biệt nội dung được nêu trong một nguồn xác định với câu hỏi về giá trị
hoặc hiệu lực cho một năm cụ thể. Với nội dung nguồn, tìm nguồn trong snapshot
đã xác thực rồi trả lời giới hạn theo nguồn đó. Nếu nhiều revision/năm mâu thuẫn
hoặc người dùng hỏi hiệu lực hiện tại mà thiếu căn cứ, vẫn clarify. Không đặt
`requires_year=false` cho mọi câu, không mặc định năm máy, năm file hoặc năm mới nhất.

Plan lịch sử còn thêm QNU vào truy vấn của tài liệu mô phỏng; đó là identity từ
assistant, không phải bằng chứng tài liệu áp dụng tại QNU. Chưa có bằng chứng
đây là nguyên nhân trực tiếp của hai lỗi, nhưng regression cần giữ ranh giới này.

## 4. P05: đủ văn bản, nhưng chu trình kiểm điều kiện chưa khép kín

Lần kiểm đầu: hai topic đều true, audit.complete=true nhưng còn thiếu qualifier.
Repair chọn `source_condition_completion`. Lần cuối: 3 claims được chấp nhận,
topic vẫn đủ, verifier.complete=true, audit.complete=false do `e6.c3`.
Đối chiếu thứ tự context cho thấy đây là điều kiện nguồn về tính dự kiến của
cột năm kế hoạch; không phải lỗi thiếu đoạn hoặc context window.

Không lưu raw claims/audit đầy đủ của lần đó, nên chưa thể kết luận field
`retained_by` nào sai, model chọn thêm điều kiện không cần thiết hay câu trả lời
thực sự bỏ phần thiết yếu. Không nên kết luận Quality Gate sai chỉ vì đáp án
có vẻ đúng. Giữ gate, bổ sung trace tối thiểu gồm clause IDs, source span IDs,
retained_by, các verdict và vòng kiểm; không ghi prompt/corpus vào application log.

Có thêm lỗi cấu trúc tái hiện được ở
[source_scope_audit.py](../../../backend/app/modules/rag/source_scope_audit.py):
regex tách sau năm trước liên từ làm danh sách hai năm thành hai clause, trong
đó clause sau chỉ còn liên từ và năm, mất chủ ngữ/phủ định. D11 chứng minh lỗi
tách này; chưa đủ để coi nó là nguyên nhân duy nhất của P05. Cần giữ nguyên danh
sách/range năm trong một mệnh đề, chỉ tách khi có hai vị ngữ độc lập. Trường hợp
không chắc thì giữ cả câu. Không thêm từ điển theo mã câu hỏi.

Đề nghị xác định tập điều kiện có liên quan trên nguồn đóng băng, rồi server
trích toàn bộ các mệnh đề được chọn với chủ thể/phủ định/phạm vi đầy đủ. Nếu
audit phát hiện một điều kiện mới thì bổ sung theo tiến triển của tập ID và
giới hạn cứng, sau đó kiểm lại; hết budget vẫn partial/block. Không thêm mọi
đoạn lân cận và không bỏ audit cuối để lấy điểm PASS.

## 5. P01 và khoảng hở chẩn đoán

Lỗi gốc chưa được lưu đủ trong runner: exception chỉ giữ type/code và kiểu
chuỗi nguyên nhân. Log ModelOps giữ `reason=provider_request_failed` và
`http_status=null`. `describe_provider_failure` có thể in HTTP 502 từ status
của DomainException nội bộ; adapter cũng sinh 502 khi protocol/output không hợp
lệ. Vì vậy cách gọi “upstream HTTP 502” trong báo cáo trước là quá chắc chắn.

Lượt lỗi không được ghi usage thành công; không có token/finish reason để chứng
minh hết 600 output tokens ở reader. Đây chỉ là một khả năng cần phân biệt với
transport. Không có bằng chứng lỗi context 32K; benchmark đang dùng Luna, 0
fallback Qwen được chấp nhận. Không đề nghị tăng context hay đổi model để chữa
nhóm lỗi hợp đồng này.

Đề nghị ghi allowlist metadata: app error code, actual upstream status nếu có,
stage, request-ID hash, finish reason, input/output token nếu thực sự quan sát,
attempt count và fallback policy. Retry chỉ khi loại lỗi phù hợp và trong deadline;
schema/credential/context rejection không được retry mù. Benchmark Luna-only
phải giữ restriction đó; không dùng Qwen để âm thầm biến ca lỗi thành PASS.

## Thứ tự triển khai và nghiệm thu đề nghị

1. Bổ sung trace tối thiểu ở các biên lỗi để phép đo sau xác định đúng nguyên
   nhân; giữ riêng lỗi provider, schema, source integrity và source limitation.
2. Sửa reader và điểm tích hợp wiki trước: tác động trực tiếp P03/P13/P14 và
   giảm việc wiki thay hành vi pipeline. Test action sai, trang ngoài quyền,
   revision/hash sai, hết budget, partial page, lần gọi sau lỗi và cache.
3. Tách unknown/ambiguous khỏi integrity ở row catalog. Test dấu chưa định nghĩa,
   chú giải có phạm vi, số 0, ô trống, unreadable, một ô bị hạn chế giữa nhiều ô
   hợp lệ; raw/header/span giả vẫn bị chặn. Kiểm P09/P10 sau sửa.
4. Sửa điều kiện hỏi lại năm và cách xác lập phạm vi nguồn. Test câu hỏi nội dung
   không năm, so toán tử/đơn vị, năm dữ liệu khác năm ban hành, nhiều năm mâu
   thuẫn, follow-up và câu hỏi đòi năm thật. Kiểm P07/P11.
5. Sửa tách mệnh đề và chu trình bổ sung điều kiện P05. Test danh sách/range năm,
   phủ định, điều kiện chung và ngoại lệ, hai note giống chữ khác bảng, audit
   phát hiện điều kiện ở vòng sau; không chỉ test một câu benchmark.
6. Chạy focused regression, Ruff rồi full gate một lần khi batch ổn định. Sau
   đó cùng model/source/index/gold chạy frozen64; đối chiếu từng ID với Context589
   và Context588. P01 cần đo lại với diagnostic đã đủ, không suy PASS từ probe.

Không cần sửa parser, biên soạn lại wiki hay nạp vector mới cho các thay đổi
reader/answer này. Chỉ xem lại extraction nếu kiểm sau sửa đưa ra bằng chứng
mới về nội dung/locator sai. Chưa chuyển sang ưu tiên wiki 4–6 trong lượt phân tích.

## Bằng chứng và giới hạn của lượt này

- Lệnh: `backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context590_diagnosis.py`, cwd repo root.
- Lượt probe đầu exit 1 vì guard chặn cả socketpair nội bộ của asyncio Windows;
  không phải lỗi ứng dụng. Đã tạo trước kênh wakeup nội bộ, vẫn chặn kết nối dịch vụ.
- Lượt hoàn chỉnh: 12/12 diagnostic checks PASS, exit 0. PASS nghĩa là tái hiện/
  kiểm chứng kết luận; các lỗi sản phẩm vẫn chưa sửa.
- Network service bị chặn bằng Python audit hook; 1 thử compatibility check lúc
  import bị chặn. Không DB/LLM thật; không thao tác MinIO/Qdrant.
- 743 file app/tests/artifacts đầu vào giữ nguyên SHA-256 trước/sau probe.
- Artifacts private: [offline-diagnosis.json](../../../backend/storage/context590/offline-diagnosis.json).
- Full Pytest, frontend build, LLM live và benchmark mới: NOT RUN; không cần cho
  phân tích không đổi mã app. Full 3.086 PASS/18 FAIL/17 SKIP là lịch sử Context589,
  không phải kết quả hiện tại và không được đổi thành full PASS.
- Exact extra field của ba lỗi wiki, chi tiết gốc P01 và final claims/audit P05
  không có trong log lưu; cần trace ở lượt triển khai tiếp, không đoán lại dữ liệu.

Chỉ thêm báo cáo, nhật ký và helper offline bị ignore. Mọi thay đổi app/tests
Context587–589 đang có được giữ nguyên. Không tự sửa dữ liệu hay trạng thái duyệt.
