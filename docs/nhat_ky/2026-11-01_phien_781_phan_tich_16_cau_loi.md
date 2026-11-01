# Phiên 781 — Phân tích 16 kết quả lỗi, không sửa hoặc hỏi lại

## Phạm vi và kết luận

Chỉ đọc mã, report, checkpoint, PostgreSQL và blob của đúng phiên 93faa11f0caf. Không đổi app, ModelOps, prompt, benchmark, nguồn/OCR/compiler/index; không gọi model, reindex hoặc sửa kết quả chấm. Kết quả 780 giữ **37 PASS / 16 FAIL**, trong đó MX-01 bị gián đoạn, chưa có kết quả model.

Lỗi nằm ở nhiều khâu: chuẩn hóa bảng, bảo toàn nghĩa khi compiler, truy xuất câu nhiều ý, hợp đồng đầu ra model, bộ chấm và gián đoạn tiến trình. Không có căn cứ tăng token để giải quyết toàn bộ.

## Bằng chứng

- Đọc report cuối 780, 179 chunk cùng cấu trúc/citation và các trace truy xuất. Dựng lại catalog bằng chính hàm cells.catalog từ primary/support IDs của 7 câu lỗi có response; không chạy retrieval/model lại.
- Đọc 3 canonical JSON qua S3, xác minh SHA256 khớp artifact. Tệp phục vụ phân tích chỉ nằm trong ignored tmp; không đưa nguồn, prompt hoặc credential vào memory.
- Probe bản sao bộ nhớ của bảng IELTS: baseline 0 ô/header_unresolved; chỉ xác nhận header hàng đầu thì hết lỗi header nhưng vẫn 0 ô. Không ghi lại nguồn hoặc DB.
- Đọc 52 provider.execution event trong thời gian cohort: attempt=1; hai event chat_output_truncated đều upstream HTTP 200. Các lỗi parse/projection xảy ra sau provider nên event upstream vẫn ok.
- Raw answer/đường dẫn ValidationError của các câu response_invalid không được lưu; không xác định được chính xác field sai. Offline probe chỉ chứng minh hành vi cấu trúc, không nghiệm thu chất lượng model.

## Nguyên nhân từng nhóm

### F13 — Bộ chấm quá hẹp: độ chắc chắn cao

Model trả hai statement cùng dẫn E1 có nguồn trang 7–8: một statement nêu ngưỡng, một statement nêu ngoại lệ. Bộ lọc candidates ở admissions-evaluation.ts đòi số, chủ thể và từ chỉ ngoại lệ đồng thời trong một statement. Vì vậy không statement nào vượt bộ lọc dù toàn answer và citation có đủ hai phần; kiểm tra expected_patterns toàn answer đã qua.

Đây là false negative theo hình thức câu đối với output quan sát. Giữ FAIL gốc, chưa rescore. Cần kiểm nhóm claim có quan hệ và nguồn chung, vẫn giữ kiểm đúng giá trị, điều kiện, năm và citation; không chỉ dò số trên toàn answer.

### F18, I25-04 — Hết ngân sách output, không phải input

Chat yêu cầu tối đa 4096 output. Adapter chỉ phát chat_output_truncated khi provider báo finish_reason=length. Hai upstream đều HTTP 200/attempt 1. Không thấy lỗi input/context/rerank/quota cho hai lượt này.

Config/trace các câu có response ghi answer chưa cấu hình reasoning (task_not_configured); thinking off trước đó chỉ áp compiler. Reasoning có thể góp phần tiêu hao output, nhưng thiếu raw nên chưa chứng minh số reasoning token thực tế của hai câu. Không khẳng định toàn bộ 4096 dùng để suy luận. Context 128K không tự đổi output 4096.

### F14, I25-07, MX-04 — Không đạt ModelAnswer schema

drafting.parse_answer dùng Pydantic ModelAnswer.model_validate_json; JSON, extra key, status, statement, cell ID hoặc text đều có thể làm validation thất bại. Có nhánh cùng mã khi materialize vượt 20 statement, nhưng parse đã giới hạn cả statements/lookups ≤20 và materialize chọn một trong hai, nên nhánh đó không giải thích lượt qua đường hiện tại. Chưa biết field cụ thể vì không lưu raw/error path.

RAG gọi prepare_chat_request không truyền output_schema; ChatRequest.json_mode=True khiến adapter gửi json_object, không gửi JSON Schema của ModelAnswer. JSON object không bảo đảm hợp đồng Pydantic. Cần structured schema khi đúng provider hỗ trợ đã xác minh, giữ validation và thêm diagnostic an toàn về field/type/finish/size/hash; không log nguyên prompt/nguồn/key.

### BC24-02, BC24-05, BC24-10 — Không chọn ô bảng

cells.materialize chỉ phát answer_cell_selection_required khi lookups rỗng và có statement chứa chữ số dẫn evidence loại table. Ba lượt qua JSON/schema nhưng vi phạm giao thức chọn ô. HTTP 502 ở đây là chặn grounding, không chứng minh mất kết nối hay hết token. Không bỏ guard để nhận prose số liệu chưa chứng minh.

### Sáu câu model_abstained — Cần tách nguyên nhân

| Câu | Quan sát | Khâu cần xử lý |
|---|---|---|
| I25-05 | Bảng đúng trang 9 rerank hạng 1; context 0 ô/16 header_unresolved | Header native và mô hình chủ thể dòng; không phải không tìm ra tài liệu |
| BC24-04 | Bảng đúng hạng 8; catalog có đủ hai ô số lượng/header của hai trường | Model vẫn abstain dù đủ ô; chưa có raw reasoning để biết quyết định bên trong |
| BC24-08 | Canonical có mô tả tham quan tại Trường, nhưng không chunk nào trong index còn mô tả này; context hạng 2 chỉ giữ tổng số và diễn giải hướng nghiệp | Compiler làm mất qualifier trước retrieval; có số chưa đồng nghĩa có đủ nghĩa để trả lời |
| MX-02 | Bảng chỉ tiêu 2025 đúng có trong index, ngoài dense 50; lexical hạng 33 bị loại trước fusion 50. Context có ngưỡng 2026 nhưng thiếu chỉ tiêu 2025 | Một query cho hai ý không bảo đảm coverage từng ý/tài liệu |
| MX-05 | Bảng IELTS hạng 3 nhưng không có ô hợp lệ; ô kênh/tỷ lệ báo cáo 2024 có trong catalog | Nửa IELTS vướng cấu trúc như I25-05 |
| MX-10 | Ô ngưỡng 2026 đúng hạng 1 có trong catalog; bảng số lượng của 2024 ngoài cả dense/lexical candidate. Đoạn hạng 2 chỉ có tỷ lệ | Thiếu bằng chứng nửa 2024; không phải toàn bộ truy xuất thất bại |

**Bảng IELTS vướng hai lỗi độc lập.** native_tables tạo Cell với header mặc định false. Canonical giữ tên cột ở hàng đầu nhưng header false; table_layout.header_rows chỉ nhận header tường minh. Ngoài ra cells.catalog yêu cầu chủ thể dòng có chữ, nên bảng tra số→số bị loại mọi dòng dù xác nhận header trong probe. Cần numeric-axis/column-role tổng quát, không vá bằng từ khóa IELTS.

**Compiler có thêm sai nghĩa đáng chú ý:** một paragraph dẫn xuất floor2026 gán nhãn học phí/chỉ tiêu cho số thuộc bảng ngưỡng thi. Bảng nguồn vẫn còn nhưng paragraph này đang retrievable, có thể gây nhiễu. Hash/citation khớp không chứng minh diễn giải đúng metric. Chưa kết luận paragraph này là nguyên nhân duy nhất của bất kỳ câu cụ thể nào trong 16 FAIL.

### MX-01 — Gián đoạn, không đánh giá lỗi trả lời

Request đã dispatch khi user ngắt; API/runner cùng dừng. Server giữ running với lease đến 12:31 ngày 01/11. Phiên 780 chỉ GET, không gửi lại, ghi interrupted rồi hỏi 9 câu mới. Đọc DB phiên 781 vẫn running; conversations.service.expire chỉ chuyển uncertain sau lease khi qua API read/reserve. Không update DB thủ công; không gọi đây là model trả sai hoặc lỗi token.

## Thứ tự xử lý đề xuất

1. Bảo toàn bằng chứng: header có proof/confidence, bảng numeric-axis, nối bảng; compiler giữ qualifier/metric, chặn prose sai nghĩa từ bảng. Nguồn bất biến; tạo dẫn xuất/index mới khi được phép.
2. Retrieval câu nhiều ý: phân tích nhu cầu, tìm từng ý đúng scope, gộp/dedup/rerank cùng snapshot và budget. Đo coverage từng fact, không tăng K vô hạn.
3. Hợp đồng model: schema thật khi hỗ trợ, lookup cho bảng, diagnostic an toàn; đo riêng reasoning/output của answer trước đổi budget.
4. Bộ chấm/vận hành: claim-group có nguồn cho F13; interrupted/unknown tách riêng. Sau sửa chạy cohort mới đủ 53 câu, mỗi câu một lần, không cộng PASS nhiều đợt.

Không chạy full suite cho lượt phân tích/tài liệu thuần. Diff/UTF-8/LF và liên kết tài liệu được kiểm tra. Report gốc ở tmp/v1-e2e/93faa11f0caf/runs/admissions-chat-remaining-1793510384663788200/admissions-answers.json; bằng chứng phân tích trong tmp/diagnose781-*, tmp/ocr781-*, tmp/events781.json. Nhãn benchmark vẫn draft, chưa thay đánh giá ngữ nghĩa độc lập.
