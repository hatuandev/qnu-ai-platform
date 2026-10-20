# Context574 — Nguyên nhân 8 câu RAG chưa đạt và hướng xử lý

**Nội dung cần cho cả 8 câu vẫn có trong DOCX, Markdown đang xuất bản và JSON của revision mới. Chưa thấy lỗi bóc tách làm mất các dữ kiện này. Các lỗi tập trung ở chọn bằng chứng, nối điều kiện, kiểm chứng câu trả lời và một lần timeout provider.**

Vì vậy, chưa cần dọn kho, tải lại tài liệu, tăng context hoặc sửa parser. Có một thiếu hụt về liên kết bằng chứng phục vụ RAG: dòng tóm tắt E-A chưa dẫn tới quy định đầy đủ ở Phụ lục II. Đây là khoảng hở của dữ liệu dẫn xuất và luồng trả lời, không phải nội dung bị mất khỏi Markdown.

## Phạm vi đối soát

- Kết quả gốc: Context572, 52/60 câu tri thức, 8 FAIL. X07 retry Context573 được phân tích riêng, không thay kết quả gốc.
- Nguồn đang phục vụ: `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`.
- Revision mới dùng đối chiếu cấu trúc: `ks_rev_d5135c27d130`, index staging `idx_rev_91267ceb54ff`, chưa xuất bản.
- Đọc lại DOCX gốc, artifact đã đóng băng, log, response và mã hiện hành. Hash 1.289 tệp app/test/frontend khớp lượt573 và không đổi trong điều tra.
- Không gọi lại LLM, không truy vấn/ghi DB, không reindex, publish, sửa cấu hình hoặc mã ứng dụng. Các kết luận vận hành dựa trên lần chạy thật đã lưu; probes mới là kiểm chứng offline.

## Đối soát từng câu

| Câu | Nguồn có đủ không? | Điểm lỗi đã quan sát | Hướng xử lý |
| --- | --- | --- | --- |
| **N19 — Giá trị và ý nghĩa CT-01** | Có: cùng dòng chứa `0` và cột mô tả phạm vi của giá trị. | Selector chọn đúng hai ô, nhưng auditor từ chối vì định nghĩa chỉ nằm trong ô mô tả cùng dòng, không ở phần mở đầu/header. Fallback sau `ROW_AUDIT_REJECTED` loại hàng bảng, nên mất đường dùng chính bằng chứng đó. | Cho phép một ô mô tả cùng dòng làm căn cứ giải thích giá trị khi quan hệ hàng/cột được xác minh; giữ kiểm tra hash, trạng thái ô và phạm vi. Không dùng giá trị tự chứng minh ý nghĩa của nó. |
| **M05 — Liệt kê 12 mã và tên** | Có: hàm hiện tại đọc được đủ 12 cặp; số 0 đầu và dấu nối giữ nguyên. Caption bảng cũng có. | Cả hai selector chọn `t0`; trace dừng tại `independent_selection`, chưa tới `source_validation`. Guard loại vì một cờ `all_rows`/`identity_only` hoặc `missing_constraints`, nhưng các trường này chưa được ghi vào trace. Nhánh RAG sau đó không giữ bộ 12 dòng. | Làm rõ contract chọn schema, ghi lý do dừng và số hàng do server đếm. Khi chọn hợp lệ, liệt kê trực tiếp đủ các dòng với provenance; không phụ thuộc TopK. Không bỏ guard khi bộ chọn bất đồng. |
| **P03 — Thứ tự ưu tiên chứng cứ** | Có, gồm câu giới hạn bản tổng hợp không được vượt chứng cứ gốc. | Câu trả lời trích đúng thứ tự nhưng bỏ câu giới hạn. Toàn khối và câu giới hạn đã tới audit; audit vẫn báo hoàn tất. | Kiểm tính đầy đủ từ các điều kiện nguồn liên quan tới câu hỏi, độc lập với những câu model đã chọn. Giữ giới hạn gắn với quy tắc được hỏi; không mặc định mọi câu liền kề đều bắt buộc. |
| **P05 — Ước tính 2027 và Ghi nhận 2026** | Có: chú thích `qnu:p051` xác định rõ phạm vi từng cột. | Ban đầu đi nhánh facts do câu có năm/metric. Fallback đã lấy đúng chú thích, chấp nhận 2 claims, verifier báo đủ cả 2 ý; audit cuối lại báo thiếu điều kiện và bỏ đáp án. Log chỉ giữ lý do chung, chưa có ID điều kiện bị loại. | Phân biệt hỏi ý nghĩa/phạm vi cột với hỏi giá trị số. Ghi trace điều kiện cụ thể, rồi chỉnh kiểm chứng theo đúng quan hệ cột/năm được hỏi. Chưa đủ bằng chứng để chỉ tên chính xác điều kiện gây false rejection. |
| **P06 — Ngoại lệ E-A** | Có cả dòng tóm tắt và quy định đầy đủ `qnu:l014`. | Trả ngay `VERIFIED_ROW_COORDINATES` từ Bảng10. Closure của dòng chỉ có header, không có quy định đầy đủ: mốc tính gia hạn và điều kiện chứng từ bị bỏ. Trả lời đã được coi supported nên không chạy prose recovery. | Câu hỏi về điều kiện/ngoại lệ cần kiểm đủ các ý, không chỉ đủ tọa độ ô. Tìm quy định liên quan trong đúng phụ lục/nguồn, kiểm quan hệ đối tượng và năm, rồi ghép bằng chứng nguyên văn trước khi trả lời. |
| **P09 — Dấu `/` và cách lưu CT-06** | Có: chú giải và footnote đều còn, hai khối đã tới fallback. | Chọn/trả một phần ý “không tự diễn giải” nhưng chưa bảo toàn đủ yêu cầu “giữ nguyên dấu”; verifier ghi rõ claim thiếu cách lưu, sau đó hệ thống từ chối toàn bộ. | Giữ đủ hai ý của yêu cầu. Nếu thiếu một ý, phục hồi có giới hạn từ đoạn nguồn đã có và kiểm chứng lại, không suy diễn ý nghĩa ký hiệu. |
| **P15 — Ngày ban hành và bắt đầu áp dụng** | Có cả hai ngày và vai trò rõ ràng. | Audit xác nhận các assertions được nguồn hỗ trợ nhưng yêu cầu thêm ngày kết thúc kỳ đánh giá. `source_clauses` gộp ngày bắt đầu và kết thúc thành một clause; `condition_gaps` đòi giữ nguyên toàn chuỗi. | Tách phạm vi chứng minh tới mệnh đề có offset; chỉ yêu cầu điều kiện ảnh hưởng tới hai mốc đang hỏi. Vẫn phải giữ phủ định “ngày ban hành không phải ngày có hiệu lực”. |
| **X07 — Dấu `/` có bao nhiêu giờ, bằng 0 không?** | Có bằng chứng nguồn chưa định nghĩa ký hiệu; không có con số hợp lệ để trả lời. | Lượt572: `ReadTimeout` → HTTP503. Lượt573: HTTP200, hai claims được chấp nhận nhưng topic coverage vẫn coi việc không có số giờ là thiếu đáp án; hệ thống trả lại `METRIC_UNVERIFIED`. | Tách lỗi hạ tầng khỏi kết quả tri thức. Kiểm chứng phải cho phép “nguồn chưa xác định, không có căn cứ quy đổi giờ/0” trả lời đầy đủ câu hỏi có tiền đề sai, kèm trích dẫn. |

## Cấu trúc bóc tách đã kiểm đến đâu

Tám bộ gold spans vẫn khớp chính xác canonical đang xuất bản. Nội dung tương ứng được tìm trong XML của DOCX và giữ ở revision mới. Kiểm thêm lưới ô thực của Bảng1, Bảng5 và Bảng10: các ô trong `source_data` khớp tọa độ và văn bản OOXML; các hàng logic đang phục vụ cũng khớp lưới đã mở rộng ô gộp.

Bảng1 có 12 dòng định danh và một dòng khác không phải bản ghi định danh. Hàm enumeration hiện tại trả đúng 12 cặp, gồm mã có số 0 đầu và hai mã gần nhau AM-0007/AM-0070. Không cần sửa parser để tạo lại các cặp này.

Việc kiểm trên chỉ chứng minh nội dung/cấu trúc liên quan 8 câu. Không coi đó là chứng nhận mọi quan hệ ngữ nghĩa trong tài liệu đều hoàn chỉnh, hoặc kiểm chứng mới cho mọi PDF.

Riêng Bảng10 nằm sau mục II.2 nên có section path theo vị trí đó, trong khi hàng E-A tóm tắt quy tắc ở II.1. Không nên sửa toàn bảng sang II.1: cùng bảng còn có E-B. Cần liên kết theo hàng/đối tượng khi phục vụ RAG; vị trí dưới heading không tự chứng minh phạm vi ngữ nghĩa của từng hàng. Quan hệ chưa xác minh không được materialize thành fact đã duyệt.

## Vì sao tăng context hoặc đổi model chưa giải quyết gốc

- P05 đã giữ đúng đoạn cần thiết trong context 16.870 ký tự; P09/X07 retry dùng 5.459 ký tự. Trần cấu hình của các lượt này là 36.000 **ký tự**, không phải token.
- P06: thử đặt quy định đầy đủ và dòng tóm tắt vào đầu tập bằng chứng thì cả hai vừa cùng giới hạn K5/36.000 ký tự. Đây là phép thử bằng thứ tự biết trước đáp án, không phải kết quả tuning hoặc benchmark PASS.
- P03/P15 bị sai ở quyết định về tính đầy đủ dù đoạn nguồn đã có.
- X07 gốc ghi `ReadTimeout` ở lời gọi Luna qua provider; không ghi lỗi vượt cửa sổ context. Không có timing/request ID phía upstream để phân biệt chính xác model, router hay mạng chậm.

Luna có thể tạo ra quyết định lựa chọn/kiểm chứng không ổn định, nhưng server đang phụ thuộc quá nhiều vào cờ do model quyết định và chưa có trace đủ chi tiết. Chuyển model hoặc tăng timeout không sửa được việc thiếu liên kết E-A, guard liệt kê bị dừng hay kiểm điều kiện sai phạm vi.

## Thứ tự xử lý đề xuất

### 1. Ngăn câu trả lời thiếu điều kiện nhưng vẫn báo đúng

Ưu tiên P06 và P03. Tái sử dụng evidence closure hiện có; bổ sung kiểm đủ các ý được hỏi ở nhánh trả lời bằng ô. Nếu hàng chỉ là tóm tắt thì tìm/kiểm quy định đầy đủ cùng nguồn trước khi kết luận supported. Không gắn mọi ghi chú của phụ lục cho mọi hàng.

Regression cần có: thiếu mốc bắt đầu tính hạn; thiếu một trong hai chứng từ; ngoại lệ nhóm A/B không áp chéo; giới hạn số liệu SV không bị mở rộng; không có quan hệ chắc chắn thì không trả kết luận đầy đủ.

### 2. Sửa kiểm chứng quá mức và cách xử lý unknown

Xử lý P15/P05/P09/X07. Tái sử dụng passage IDs, offset, source hash; tách câu hỏi thành ý cần trả lời và các điều kiện thực sự chi phối ý đó. Tránh đòi nguyên một câu dài nếu chỉ một mệnh đề thuộc phạm vi câu hỏi.

Cho phép đáp án có trích dẫn xác nhận “nguồn không định nghĩa” hoàn thành một câu hỏi về giá trị chưa xác định. Phân biệt rõ trạng thái đó với không tìm thấy nguồn, thiếu bằng chứng và lỗi provider. Không đổi unknown thành 0, không bỏ audit, không đánh dấu mọi câu từ chối là đúng.

Khi đã có bằng chứng nhưng thiếu một ý, dùng phục hồi có giới hạn trên tập nguồn hiện có. Không mở vòng gọi model không giới hạn. Ghi ID điều kiện thiếu/lý do loại, tránh chỉ trả `PROSE_NOT_FULLY_VERIFIED`.

### 3. Hoàn thiện trả lời dữ liệu có cấu trúc

Xử lý N19/M05. N19 cần cặp giá trị–mô tả cùng hàng có nguồn, không ép mọi bảng phải định nghĩa metric trong phần mở đầu. M05 cần contract schema nhất quán, số hàng do server đếm và lý do guard từ chối. Không dùng LLM sinh lại mã/tên đã có chính xác.

Regression cần có bảng khác cùng caption, yêu cầu subset, sai số lượng, trùng mã, mã có 0 đầu, ô unresolved và câu hỏi thêm metric. Các ca này phải tiếp tục chặn hoặc yêu cầu làm rõ.

### 4. Kiểm chứng sau khi sửa

Giữ nguyên model, nguồn xuất bản, index và câu hỏi/gold. Chạy focused regressions sau batch ổn định, đối chiếu theo từng ID, rồi chạy lại đúng64 câu theo phạm vi đã thống nhất. Tách HTTP error khỏi nội dung sai. Không dùng retry X07 để thay điểm lịch sử.

Timeout cần trace theo từng bước/correlation ID và chính sách retry hiện có; không tự tăng timeout hay bật Qwen trong phép so sánh Luna-only. Hiện chưa có đủ dữ liệu để đề xuất một con số timeout mới.

## Mã liên quan và giới hạn kết luận

| Điểm sửa dự kiến | Vị trí hiện tại |
| --- | --- |
| Chọn schema và guard enumeration | `backend/app/modules/rag/source_identity_enumeration.py:49`, guard tại dòng90 |
| Tách điều kiện và kiểm giữ nguyên | `backend/app/modules/rag/source_scope_audit.py:19`, `:44` |
| Audit điều kiện prose | `backend/app/modules/rag/evidence_indexed_audit.py:62`, `:98`; `evidence_verification.py:144` |
| Scope của ô và audit | `backend/app/modules/rag/row_answer.py:40`, `:106`, `:260`; `row_answer_contract.py:141`, `:330` |
| Nhánh trả ngay sau row answer | `backend/app/modules/rag/service.py:493` |
| Loại bảng khỏi fallback, ghi kết quả audit | `backend/app/modules/rag/prose_fallback.py:117`, `:125`, `:233` |

M05 đã xác định đúng guard dừng, nhưng không thể khôi phục cờ cụ thể mà log không lưu. P05 đã xác định đúng giai đoạn từ chối cuối, nhưng chưa biết ID điều kiện bị đánh dấu thiếu. P03 biết câu giới hạn có trong payload và bị bỏ khỏi đáp án được chấp nhận, không có raw per-clause verdict để khẳng định model đã đánh cờ nào. Các điểm này cần bổ sung trace có phạm vi khi sửa, không suy đoán thành sự thật.

## Bằng chứng kiểm chứng

- `diagnose.py`: **21 PASS, 1 FAIL, exit1**. FAIL là kiểm tra “không có ý định I/O”: import ứng dụng khởi tạo Qdrant client và thử kiểm phiên bản; socket guard đã chặn trước kết nối. Không xóa hoặc đổi kết quả FAIL này thành PASS.
- `followup.py`: **9 PASS, 0 FAIL, exit0**, chỉ dùng thư viện chuẩn; kiểm ô/hàng, guard enumeration và hash code, không import ứng dụng, không có thử kết nối.
- PASS ở đây nghĩa là phép đối soát hoặc tái hiện cơ chế đạt; **không có nghĩa 8 lỗi RAG đã được sửa**.
- Không chạy suite ứng dụng hay benchmark mới. Full suite gần nhất Context572 vẫn là kết quả lịch sử **2838 PASS / 18 FAIL / 17 SKIP**, không phải PASS toàn bộ.
- Chỉ tạo evidence tại `backend/storage/context574/` và báo cáo/memory. Không tạo dữ liệu kiểm thử trong DB/vector nên không có bản ghi mới cần dọn; không đụng Storage cũ đã bị policy chặn xóa.

Kết quả gốc vẫn **52/60**. Nên sửa luồng sử dụng và kiểm chứng bằng chứng trước; chỉ tạo lại revision nếu regression mới chứng minh parser thực sự làm mất nội dung hoặc quan hệ cấu trúc có căn cứ.
