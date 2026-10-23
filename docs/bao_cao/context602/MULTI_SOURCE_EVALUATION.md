# Context602 — Đối soát bộ nhiều nguồn12 câu

## Kết luận và phạm vi

**6 PASS /6 FAIL**, tăng từ4/12 của601; chưa đạt nghiệm thu hỏi đáp nhiều nguồn.
Gains M01/M04/M11, loss M03 do timeout. M02 chuyển từ thiếu đáp án thành timeout.
M09–M12 không còn exception `EVIDENCE_PLAN_SCOPE_INVALID`, nhưng chỉ M11 đạt;
không nhầm sửa validation đầu vào với giải quyết đủ ngữ nghĩa.

Giữ nguyên12 question bytes/rubric, ba raw DOCX2024/2025/2026 và model Luna.
Canonical S1/S2 đổi ranh giới paragraph theo OOXML; không có causal ablation.
Dùng ModelOps thật, adapter source/snapshot local và BM25; không vector,
reviewed facts, upload/index/HTTP/browser E2E. Chưa phải compiler tổng hợp xuyên
nguồn mới. Không retry, không gọi judgeLLM, không chấm runtime error thành PASS.

## Đối chiếu đầy đủ theo ID

| ID |601|602| Kết quả và lớp lỗi |
|---|---|---|---|
| M01 | FAIL | PASS | Đủ hai chỉ tiêu và điều kiện nguồn2024; paragraph đã liền mạch. |
| M02 | FAIL | FAIL | EVIDENCE_TIMEOUT khoảng98,5s; nghị quyết/ngày vẫn có trong canonical2024. |
| M03 | PASS | FAIL | EVIDENCE_TIMEOUT khoảng98,5s; paragraph PT3 vẫn đủ hai đơn vị tổ chức thi. |
| M04 | FAIL | PASS có giới hạn hiển thị | Đủ ba lượng/qualifier và đúng nguồn2025; xem cách chấm trạng thái draft dưới đây. |
| M05 | PASS | PASS | Ngày nghị quyết2024 khác năm kế hoạch/báo cáo2025. |
| M06 | PASS | PASS | Xác định nguồn là Dự thảo, không gọi bản chính thức. |
| M07 | PASS | PASS | Giữ mức cập nhật, mức trước đó và đúng hai thông báo của2026. |
| M08 | FAIL | FAIL | Đủ nguồn, audit/verifier bất đồng về cover title là scope hay điều kiện phải công bố. |
| M09 | FAIL, scope exception | FAIL, incomplete | Chưa hoàn thành so sánh cách phân chia PT3 của2024 và PT3/PT4 của2026. |
| M10 | FAIL, scope exception | FAIL, incomplete | Chỉ trả phần2026, thiếu phía2024 trong câu trả lời so sánh. |
| M11 | FAIL, scope exception | PASS negative | Không mượn số liệu năm khác cho2027; mẫu từ chối còn chung chung. |
| M12 | FAIL, scope exception | FAIL, incomplete | Chưa hoàn thành suy luận vai trò năm văn bản viện dẫn với năm dữ liệu báo cáo. |

M04: rubric đóng băng đòi giữ tính dự thảo. Câu hỏi nêu rõ dự thảo, cả hai
citation title là đúng tên nguồn có “Du thao”, câu trả lời không tuyên bố chính
thức. Vì vậy chấm PASS theo toàn context/nguồn hiện ra, không bổ sung yêu cầu
keyword mới sau khi xem kết quả. Body chưa nhắc lại trạng thái dự thảo là giới
hạn hiển thị cần cải thiện; nếu rubric tương lai đòi nhãn ngay trong body, phải
version trước khi chạy. Không đổi rubric lịch sử hoặc che giới hạn này.

M11: không có số liệu2027 trong bộ nguồn thử, từ chối là đúng rubric. Wording
mẫu nói về “đề án chính thức” quá chung; không dùng nó làm bằng chứng toàn bộ
kho tài liệu chính thức không có dữ liệu. Không phát sinh giá trị chắc chắn sai.

## Nguyên nhân có chứng cứ

### M02/M03 — Deadline tổng, không phải chứng minh context32K thiếu

Hai request báo `EVIDENCE_TIMEOUT`, không phải lỗi parser hoặc exception
provider context-length. Canonical2024 có nghị quyết/ngày tại256:314 và PT3 tại
766:899. Trace cho thấy nhiều bước plan/wiki/select/verify/audit đã chạy trước
khi hết ngân sách evidence90s; thời gian98,5s gồm xử lý kết thúc. Usage các call
đã ghi đều success không biến request hết thời gian thành thành công.

Chưa có đo đạc đủ để quy toàn bộ chậm cho upstream hoặc một bước cụ thể. Chỉ
tăng timeout sẽ che vòng kiểm tra lặp. Hướng sửa: đo deadline theo stage, giảm
kiểm scope lặp sau khi có bằng chứng xác định, giữ cả timeout và lỗi hạ tầng
trung thực. Không tăng timeout trong602.

### M08 — Metadata chứng minh scope khác điều kiện nghiệp vụ

Đúng mã PT3/402A, PT4/402B, đơn vị thi và năm2026 cùng nằm trong paragraph
`qnu:p014`, canonical5530:5917. Prose selection chọn đúng paragraph, hai claim
được chấp nhận và topic coverage đạt. Audit tiếp tục đòi cover title tại0:48 như
điều kiện; verifier loại title vì không trả lời mã/đơn vị thi. Ledger giữ gap,
trả thiếu căn cứ. Không sửa parser hoặc nạp lại vector để giải quyết bất đồng này.

Cover là paragraph thường trong nguồn, không có chứng cứ native đủ để tùy ý
đổi thành heading. Không dùng heuristic chữ hoa hoặc từ điển riêng để ép role.
Hướng sửa theo [thiết kế](./COMPILATION_DESIGN.md): scope/temporal metadata có
bằng chứng riêng, tách khỏi condition/exception chi phối assertion; verifier
kiểm role độc lập. Không xoá mọi qualifier hoặc gắn nhãn metadata để bỏ ngoại
lệ thật. Binding thuần của đợt2 chưa giải quyết entailment này.

### M09/M10 — Coverage chưa khép đủ hai nguồn

Dữ kiện cho cả hai năm vẫn có trong canonical. Kết quả chỉ giữ phía2026; fallback
cũng không tạo được câu trả lời so sánh đủ hai phía. Năm sát chữ đã qua validator,
nhưng selection/topic/condition ledger chưa thống nhất. Hướng sửa: phân rã câu
so sánh thành từng yêu cầu có source/year riêng, kiểm coverage từng phía rồi
mới tổng hợp, giữ mã và điều kiện tại đúng năm. Không mở scope sang năm khác
vì thiếu kết quả, không tự cộng chỉ tiêu.

### M12 — Vai trò thời gian chưa thành kết luận được kiểm chứng

Nguồn có tiêu đề và số liệu báo cáo2025, đồng thời viện dẫn văn bản ký2024.
Trả lại các số liệu chưa trả lời câu hỏi về vai trò năm. Fallback từ chối coi
ngày văn bản viện dẫn là bằng chứng năm dữ liệu; đây là chặn đúng suy luận sai
nhưng chưa hoàn thành câu trả lời có căn cứ. Hướng sửa: biểu diễn assertion với
data_year, document_date và cited_document_date riêng, kiểm từng role trước khi
tạo kết luận. Không suy năm dữ liệu từ tên file hoặc ngày ký văn bản viện dẫn.

## Chỉ số và giới hạn

Ba source wiki ready,14 trang;7 compiler calls,32.682 input/3.832 output tokens.
QA127 usage success,758.829 input/32.069 output, prompt lớn nhất17.625 tokens,
0 fallback.23/23 citation exact source/revision/hash/span/index khớp. Tọa độ
đúng chưa chứng minh mọi câu hỏi đã trả lời đầy đủ.

p50 request72.750,17ms; p95124.983,31ms; max130.642,07ms. Một request có thể qua
nhánh evidence rồi prose fallback; không đồng nhất số này với timeout30s mỗi
provider call. Runner exit0 và offline integrity exit0, **quality vẫn FAIL**.

Các đối chiếu bảng/native body xác minh parser602 không làm mất nội dung giải
thích các lỗi trên. Chưa render Office/hình ảnh hoặc chứng nhận đầy đủ mọi nội
dung tài liệu. Rubric là draft do Codex đối chiếu nguồn, chưa human holdout.

Lưu private: `backend/storage/context602/multi-source-final/{adjudications,
labels-final,comparison-601,summary}.json`, ghim response hash, không thay checkpoint
cũ. Không đưa source corpus hoặc prompt riêng vào báo cáo/Git.

Các việc tiếp theo thuộc phần role/coverage/runtime của compiler và RAG, cần
được giữ làm điều kiện nghiệm thu đợt sau; chưa tự triển khai đợt3, reindex hay
publish để làm điểm thử nghiệm tăng.
