# Context569 — Nguồn → Facts → retrieval/context → answer/audit

Đọc cùng [báo cáo chính](ROOT_CAUSE_REPORT.md). Q/L là Qwen Context567 benchmark-3 và Luna Context568. Dữ liệu dưới đây thuộc snapshot đã đóng băng, không phải lượt chạy mới.

Quy ước: **xác nhận** = thấy trực tiếp trong source/response/trace hoặc tái hiện hàm thuần; **chưa xác định** = thiếu payload/call result để gán nguyên nhân sâu hơn. `prose_fallback.context_ids` chỉ mô tả fallback, không chứng minh context ban đầu vắng các block đó. Không dùng số Facts hoặc số citation thay cho chất lượng trả lời.

## N19 — Giá trị và ý nghĩa một hàng trạng thái

- Kết quả: Q PASS, L FAIL.
- Nguồn: `qnu:t005:row:0`, header `qnu:t005:header`; ô số 0 và phần diễn giải đều còn nguyên, trạng thái ô `present`. Không có Fact riêng cho hàng gold; điều đó không cản Q trả đúng bằng tọa độ ô.
- Chọn hàng: Q trả `VERIFIED_ROW_COORDINATES` với hai ô và hai citations. L trả `ROW_SELECTION_MISSING` cùng lý do không có bảng phù hợp.
- Fallback L: `allow_tables=false`; hàng cần thiết không vào supplemental/context. Rerank trả rỗng, fallback giữ các ứng viên lexical rồi kết thúc ở proposal với `NO_UNAMBIGUOUS_BOUND_PROSE`.
- Xác nhận: không mất số 0 khi parse; lời từ chối của L không chứng minh bảng nguồn không tồn tại. Cho phép bảng trong probe chỉ cho thấy hàng trở lại candidate bổ sung, chưa chứng minh câu sẽ PASS.
- Chưa xác định: metric selector/row selector ban đầu đã nhận và chọn những IDs nào; không đủ log để kết luận một model call cụ thể sai.
- Bước sửa phù hợp: căn cứ caption/header và phục hồi hàng có scope được xác minh. Hybrid Extraction không phải yêu cầu đã được chứng minh.

## M05 — Liệt kê toàn bộ mã/tên

- Kết quả: Q PASS, L FAIL.
- Nguồn: `qnu:r001`–`qnu:r012` của `qnu:t001`; có đủ 12 cặp, mã đầu 0/dấu nối còn nguyên. Hàng tổng không là chương trình. Có 118 Facts gắn 12 hàng gold; không dùng con số này làm thước đo đầy đủ.
- Probe gọi `identity_entries` đọc đúng 12 hàng bằng code, không LLM. Q đi `source_identity_enumeration`, trả đủ 12 citations và `EXHAUSTIVE_SOURCE_IDENTITIES`.
- L không có kết quả ở nhánh chuyên biệt, rơi xuống `fact_hybrid`; visible audit ghi thiếu 12 cặp, fallback không có proposal được bind chắc chắn.
- Gap payload xác nhận từ code và artifact: schema-choice có headers/source revision nhưng `source_context=[]` cho Bảng 1; caption/number của bảng không được đưa theo đường context này, trong khi instruction yêu cầu đúng số bảng.
- Chưa xác định: selector 1/2 hoặc guard nào trả `None`. Không có trace để khẳng định riêng Luna không biết liệt kê hoặc nguyên nhân duy nhất là caption.
- Bước sửa: căn cứ chọn schema có nguồn và trace từng quyết định, rồi giữ đọc toàn bộ bằng code. Không dùng TopK để chứng minh đã liệt kê hết.

## P03 — Thứ tự chứng cứ và điều kiện giới hạn

- Kết quả: Q FAIL, L PASS.
- Nguồn: `qnu:l004`, chứa thứ tự và giới hạn đối với bản tổng hợp. Không có Fact prose riêng.
- Q: fallback rerank đúng gold hạng 1, gold có trong context; câu cuối chỉ chọn phần thứ tự trước giới hạn. `verified=true`, `audit_complete=true`, `missing_constraints=[]` nhưng thiếu mệnh đề thiết yếu theo rubric.
- L: trả đủ hai ý qua đường sinh thông thường và visible audit chấp nhận.
- Xác nhận: lỗi chọn/giữ đủ source sentences và kiểm completeness, không phải gold không tới fallback Q.
- Bước sửa: điều kiện ràng buộc quy tắc phải theo cùng câu trả lời; cần regression bằng văn bản khác, không gắn cứng tên Điều 3.

## P06 — Ngoại lệ E-A và đóng gói bằng chứng

- Kết quả: Q FAIL, L FAIL.
- Nguồn: `qnu:l014` là quy định đầy đủ; `qnu:t010:row:0` là hàng tóm tắt. Có 3 Facts ở hàng tóm tắt; điều kiện chi tiết nằm ở canonical prose.
- Q fallback: hai gold blocks hạng 3 và 2. L fallback: đoạn đầy đủ hạng 2; hàng tóm tắt chưa vào danh sách rerank sau khi kênh bảng bị loại bởi `ROW_SELECTION_MISSING`.
- Cả hai context lưu đều là 11 blocks về Điều 5/Bảng 1: `qnu:l006` và nhóm đóng theo cấu trúc, gồm caption/header và sáu hàng nhóm A, cùng headings. Không có hai gold blocks.
- `pack_context` cho phép nhóm đầu tiên vượt K để giữ nguyên nhóm; khi đã nhận nhóm lớn thì `break`, nên gold phía sau không được thử. `dropped=[]` ở đây không có nghĩa mọi ứng viên đã được xét hoặc không mất bằng chứng cần trả lời.
- Probe dùng đúng thứ tự rerank đã lưu tái hiện đúng 11 IDs ở cả hai model. Probe oracle đặt hai gold blocks trước đưa được cả hai vào với K=5 và 36.000 ký tự, không thay mã hoặc source. Đây không phải ranking production hoặc chạy lại RAG.
- Xác nhận: evidence selection/packing là nút thắt trực tiếp. Chưa thể gán toàn bộ lỗi nhánh sinh ban đầu cho cùng nguyên nhân vì payload ban đầu không được lưu đầy đủ.
- Bước sửa: độ liên quan và bao phủ proof trước nhận nhóm rộng; kiểm giới hạn nhóm đóng theo cấu trúc. Không tháo điều kiện hoặc chèn gold IDs vào logic ứng dụng.

## P07 — Ngoại lệ E-B mất điều kiện

- Kết quả: Q FAIL, L FAIL.
- Nguồn: `qnu:l015`, hàng tóm tắt `qnu:t010:row:1`; 3 Facts ở hàng tóm tắt.
- Cả hai trả đúng hình thức thay chữ ký, thời hạn và không miễn an toàn, nhưng bỏ điều kiện cơ sở tạm đóng/nhật ký/xác nhận giảng viên cùng kỳ và giới hạn không áp nhóm A.
- Cả hai citation phủ toàn `qnu:l015`, offsets 45163–45796; vì vậy toàn điều kiện nguồn có ở citation. Không có log đủ để dựng toàn initial prompt, nhưng không có cơ sở nói parser đã mất đoạn điều kiện.
- Visible audit cả hai: `essential_conditions_retained=true`, `accepted=true`, không có missing constraint. Benchmark vẫn FAIL theo rubric đã chốt.
- Xác nhận: câu trả lời thiếu điều kiện và audit bỏ lọt. Fact mới rời rạc không tự khắc phục khả năng bỏ điều kiện khi sinh.
- Bước sửa: chuẩn đầy đủ của một quy tắc có điều kiện; nếu nghiên cứu Hybrid thì biểu diễn điều kiện/ngoại lệ cùng rule và evidence từng phần.

## P08 — Quy tắc giữ mã trong các ô bảng

- Kết quả: Q FAIL, L FAIL.
- Nguồn: `qnu:t009:row:0`, `qnu:t009:row:1`, `qnu:p089`; hai hàng có state `present`, không có Fact riêng cho các gold units.
- Đường hàng trả `ROW_METRIC_SCOPE_UNRESOLVED`. Fallback có chú thích và footnote về mã dạng chuỗi nhưng thiếu hai hàng nói rõ quy tắc ở Bảng 9. L có 2 accepted claims nhưng topic/complete còn thiếu yêu cầu về dấu nối; Q dừng ở proposal.
- Probe bác bỏ giả thuyết cờ: cả hai đã có `allow_tables=true`; supplemental vẫn bỏ hai hàng. Hàm đang tìm đối chiếu nhãn ô đầu `ma_chuong_trinh`, trong khi câu hỏi dùng các mã ví dụ ở cột sau và hỏi quan hệ/quy tắc.
- Chú thích nói ví dụ không phải bản ghi cập nhật không thay thế được hai quy tắc giữ mã. Không ép verifier chấp nhận phần proof còn thiếu.
- Xác nhận: lỗ hổng tìm/chọn canonical table evidence cho câu hỏi về quy tắc; không thấy lỗi làm rơi số 0/dấu nối trong nguồn.
- Bước sửa: candidate search theo nội dung ô và cấu trúc bảng, phân biệt quy tắc với phép tra số. Không thêm từ khóa của riêng câu này.

## P10 — So sánh ký hiệu chưa đo với số 0

- Kết quả: Q PASS, L FAIL.
- Nguồn: chú giải `qnu:p072` và hàng số 0 `qnu:t005:row:0`; chú giải gắn native footnote riêng.
- Q đi fallback sau `ROW_METRIC_SCOPE_UNRESOLVED`, giữ được cả hai vế và trả đúng. L đi sau `ROW_SELECTION_MISSING`, nên `allow_tables=false` và mất hàng số 0.
- Context L vẫn có chú giải đúng. L verifier công nhận ý nghĩa dấu gạch nhưng không công nhận đủ ý nghĩa số 0; whole-answer audit hoàn thành nhưng kết quả chung không đầy đủ.
- Thông báo cuối giữ lý do của row answer trước đó, nói thiếu chú giải; thông báo này không phản ánh chính xác bằng chứng fallback thực sự có.
- Xác nhận: context coverage một vế so sánh bị mất theo loại trigger; lý do cuối lỗi thời. Chưa có proof cho phép bỏ scope guard của bảng.
- Bước sửa: phục hồi có kiểm chứng từng vế và trả lý do kết thúc phản ánh đúng kết quả đối soát.

## P11 — Ngưỡng khác toán tử, chủ thể và đơn vị

- Kết quả: Q FAIL, L PASS.
- Nguồn: `qnu:t006:row:0`, `qnu:t006:row:1`, đoạn giải thích toán tử `qnu:p073`. Không có Fact riêng ở các gold units; hai hàng tự chứa các phân biệt cần trả lời.
- Fallback cả hai có hai hàng cần thiết. Q nhận 3 claims nhưng `verifier_complete=false`; missing constraints yêu cầu thêm khoảng 12–18 và các chỉ tiêu số hóa khác không được hỏi. L giữ hai hàng và PASS.
- Audit nhánh sinh ban đầu của Q còn báo conflict/không đủ proof; không lưu raw câu trước audit nên không thể kết luận toàn bộ các rejection ban đầu là sai.
- Xác nhận: fallback mở rộng yêu cầu gây từ chối quá mức. Không kết luận cứ thiếu đoạn giải thích toán tử là retrieval FAIL vì hai hàng tương đương đủ cho L.
- Bước sửa: completeness theo yêu cầu và điều kiện thiết yếu, giữ `> / >=`, giờ/người khác giờ/khoa.

## P15 — Ngày đúng, quan hệ thứ tự sai

- Kết quả: Q FAIL, L PASS.
- Nguồn: `qnu:p045`, `qnu:l003`. Hai model đều trích đúng các spans ngày/hiệu lực.
- Q thêm phần mô tả các ngày đã được xếp tăng dần, nhưng đặt mốc đầu năm học trước đó về sau danh sách. Các ngày riêng lẻ đúng vẫn không chứng minh tuyên bố về thứ tự.
- Visible audit Q báo mọi assertion được hỗ trợ, `accepted=true`; L trả đúng hai mốc theo câu hỏi, không thêm quan hệ sai.
- Xác nhận: lỗi sinh thêm quan hệ và bỏ lọt khi audit; nguồn không thiếu ngày.
- Bước sửa: kiểm quan hệ sinh thêm hoặc giữ câu trả lời trong phạm vi hỏi. Hybrid Extraction ngày không phải giải pháp trực tiếp đã được chứng minh.

## P16 — Thiếu đầu vào và chọn sai đoạn chứng minh

- Kết quả: Q PASS, L FAIL.
- Nguồn: `qnu:p077` có quy tắc trực tiếp ở 14.1; `qnu:l012` ở Điều 15. `qnu:c001` là chứng cứ tương đương về nhánh thiếu A/B/C và có trong cả hai fallback contexts.
- Cả hai fallback chưa có `qnu:p077`; đây là gap liên kết dẫn chiếu cần ghi nhận. Không suy từ gap đó rằng hoàn toàn không có bằng chứng trả lời, vì khối mã còn nguyên.
- Q chọn câu quy định và khối mã, kiểm chứng PASS. L có 1 accepted claim nhưng claim liên quan thiếu biến bị bác vì primary quote nói về thiếu tỷ lệ chứng cứ 80%; `verification_errors` ghi rõ, kết quả chung FAIL dù các cờ verifier/audit khác hoàn thành.
- Xác nhận: chọn/ghép proof sai cho tình huống, kèm thiếu đoạn trực tiếp. Không được ghi PASS chỉ dựa vào `verifier_complete=true` hoặc `audit_complete=true`.
- Bước sửa: đưa đúng quy tắc tham chiếu và gắn assertion với nhánh thiếu biến, không dùng nhánh thiếu tỷ lệ làm chứng cứ thay thế.

## X05 — Sai đơn vị, lý do từ chối chưa đủ

- Kết quả: Q FAIL, L FAIL; không phát ra giá trị số sai.
- Nguồn: header `qnu:t001:header`; hàng `qnu:r003` có Facts quota/count/rate gắn đơn vị SV hoặc %. Không có nguồn quy đổi SV thành lớp trong phần bằng chứng liên quan.
- Cả hai: resolve đúng mã, trace có 3 candidate Facts, selected IDs rỗng, kết thúc ở `structured_or_dialogue`, không hybrid retrieval/prose fallback.
- Hàm `decide_table_answer` lọc unit không khớp, sau đó gộp vào `NO_COMPATIBLE_FACT_EVIDENCE`. Probe dùng 9 Facts của đúng hàng được bind nguồn tái hiện cùng reason và public refusal, không tái hiện SQL historical candidate filtering.
- Xác nhận: guard đơn vị đúng nhưng nguyên nhân bị mất khi tạo response. Benchmark đòi giải thích nguồn là SV và không có quy đổi.
- Bước sửa: lý do có cấu trúc theo unit mismatch, quote header thật. Không mở rộng phép quy đổi hoặc gọi LLM để đoán sĩ số lớp.

## X08 — Dự kiến khác đã nghiệm thu

- Kết quả: Q FAIL, L FAIL; không biến ước tính thành giá trị đã nghiệm thu.
- Nguồn: `qnu:p051` xác định vai trò 2027 và các header/Facts của `qnu:r003` có `estimated_count`, khác `reported_count`.
- Cả hai: 2 candidate Facts trong trace, selected IDs rỗng, trả `NO_COMPATIBLE_FACT_EVIDENCE` qua nhánh cấu trúc; không có fallback.
- Probe với toàn bộ 9 Facts của đúng hàng tái hiện cùng refusal, vẫn giữ các vai trò khác nhau.
- Xác nhận: thiếu lý do cụ thể ở đầu ra, không phải cần thêm một giá trị thật mới cho 2027.
- Bước sửa: giữ lý do role mismatch cùng chú thích có nguồn, không nói chung rằng thiếu mọi dữ liệu.

## X09 — Tình huống thiếu A

- Kết quả: Q FAIL, L PASS.
- Nguồn: `qnu:p077` nêu điều kiện đủ đầu vào và không thay giá trị thiếu bằng 0; không cần Fact số Q.
- Q nhánh đầu bị `NUMERIC_GROUNDING_FAILED`, unsupported number `90`. Đây cũng là số người dùng đã đưa trong tình huống, nhưng raw câu bị gate chặn không được lưu, nên chưa thể kết luận gate sai chỉ từ sự trùng số.
- Fallback cả hai có `qnu:p077` hạng rerank 2 và trong context. Q nhận 3 claims, không có verification error cụ thể nhưng completeness/audit không đạt; L chọn đúng rule và trả trạng thái không tính được, giữ source citation.
- Xác nhận: đủ source/context ở fallback; vấn đề còn ở chọn kết luận và kiểm completeness. Không có bằng chứng rằng model window không chứa được đoạn cần thiết.
- Bước sửa: phân biệt dữ kiện người dùng giả định với sự kiện từ nguồn và kiểm kết luận tính được/không tính được. Không tự tính Q hoặc biến A thiếu thành 0.

## Những thông tin chưa thể khôi phục từ log cũ

Không lưu đầy đủ raw câu sinh trước các gate, raw phản hồi cả hai schema/row selectors, thứ tự mọi candidate ban đầu hoặc mọi model payload. Không thể tái hiện cùng đầu ra model một cách độc lập chỉ từ final JSON. Bước này không gọi model lại để lấp khoảng trống đó.

Đối với bước sửa sau, chỉ thêm trace có phạm vi (IDs, quyết định, loại mismatch, hash/counter), tránh ghi nguyên corpus, prompt, credential hoặc dữ liệu cá nhân. Các probes đã chạy trong bước này là chẩn đoán offline, không phải nghiệm thu retrieval/LLM hiện tại.
