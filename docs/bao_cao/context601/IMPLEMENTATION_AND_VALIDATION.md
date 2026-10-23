# Context601 — Giữ tiền đề và kiểm tra nguồn nhiều năm

Ngày 22/10/2026. Tiếp đề xuất sau Wiki4–6: sửa P07 theo nguyên nhân chung, rồi
kiểm chứng trên tài liệu thật2024/2025/2026. Không triển khai thêm màn hình đồ thị,
semantic identity, overview hoặc packet-level reuse trong phiên này.

## Nguyên nhân và cách sửa

Trace600 cho thấy tiền đề thật có trong context. SourceDependencyReview đánh
required=true; Agreement lại trả not_required nhưng relation=scope cho cùng target.
Server nhận boolean này, nên nghĩa vụ không được ghi và đáp án thiếu tiền đề vẫn
được trả. Không có bằng chứng mất nội dung PDF, thiếu context window hoặc lỗi
publication gây ra ca này.

Sửa `source_dependency_agreement.py`: khi một dependency mới đã được source
review yêu cầu, phán đoán tiếp vẫn xác nhận quan hệ `scope`, `prerequisite` hoặc
`exception` thì không được dùng not_required để xóa nó. Giữ clause nguyên văn,
kiểm ID/source/revision như trường hợp required, ghi nghĩa vụ rồi phục hồi và kiểm
chứng lại bằng luồng sẵn có. Trace giữ verdict gốc cùng ID clause được bảo toàn.

`definition` và `unrelated` vẫn có thể là not_required; unresolved vẫn chặn.
Không ép mọi clause cùng đoạn thành tiền đề, không thêm từ khóa câu hỏi và không
tăng ngân sách call/round. Đây là bảo vệ tính nhất quán của hợp đồng, không chứng minh
mọi loại quan hệ do LLM phân loại đều đúng.

Bổ sung `evidence_rule_selection.py`, được gọi trong `propose_bound_claims` sau
khi bind: nếu đã chọn một mục danh sách native QNU, đưa cả nhóm liền mạch cùng
parent và cùng immutable source vào **bản nháp**. Giữ toàn bộ câu gốc, ID và span;
không vượt 12 claim/4.000 ký tự mỗi mục, không lấy nhóm một phần khi quá giới hạn.
Đây là gợi ý chọn evidence, không phải chứng minh quan hệ ngữ nghĩa. Bộ verifier
và audit vẫn chạy, vẫn loại mục không liên quan hoặc khác scope. Nhóm legacy,
container, khác parent/revision/hash/binding/index hoặc trùng canonical ID không
được tự mở rộng. Những mục chưa truy hồi không được coi là đã kiểm tra đầy đủ.

## Regression và an toàn

- Trước sửa:4 FAIL đúng hành vi (3 vai trò và integration bị mất tiền đề),2 PASS
  kiểm soát. Sau đó thêm3 ca khác revision: tổng9 regression mới.
- Lượt focused nhỏ đầu32PASS/1FAIL do adapter fixture gửi field rỗng ngoài schema
  sau khi phục hồi; sửa fixture mới, không đổi assertion hoặc ứng dụng để che lỗi.
- Focused trước mở rộng: 838 PASS; sau batch chốt 34 file: 852 PASS/1 warning, exit 0. Có các kiểm tra600 thật qua DB/ASGI.
- Fixture600 cho phép DB test601 kèm xác minh comment owner theo context; không
  thêm quyền truy cập DB ứng dụng. Không skip các kiểm tra600 chỉ vì tên phiên đổi.
- Full sau batch cuối: **3.361 PASS / 19 FAIL / 17 SKIP**, +23 subtest PASS,
  exit 1. Trong đó 18 lỗi nền khớp exact IDs/failure messages của600; thêm
  `test_real_backup_runner_starts_under_default_platform_loop` bị PermissionError
  khi đọc JSON fixture Windows. Chạy riêng nhóm backup:6 PASS, exit0; không
  thay kết quả full. Không mất ID; cả23 test mới PASS; code seal trong full giữ.
- Full trước thay selection:3.348 PASS/18 FAIL/17 SKIP là kết quả trung gian.
  Bảng ID/lệnh/nguyên nhân riêng ở [đối chiếu test](./TEST_ID_COMPARISON.md).
- DB/MinIO/Qdrant môi trường development loopback đã xác minh. Pytest dùng DB
  `qnu_test_context601_3ef5959f23df` có nonce sở hữu và Storage local riêng; network
  guard chặn dịch vụ/model thật, tắt auto migration/seed. Một bản defaults metadata
  test không có credential phục vụ handler mock cũ; không thay config dùng chung.

## Thử nghiệm nguồn thật

Đọc nguyên bytes DOCX, dùng DoclingOfficeParser, QNU structured builder, native
layout fidelity, renderer/validator và canonical projector hiện hành. Lưu bản gốc
và dẫn xuất trong Storage local thuộc phiên, giữ hash/locator/unit/span. Không ghi
revision/index hoặc source vào kho đang chạy; tài liệu thử vẫn là local draft.

Bộ lõi gồm phương hướng2024, báo cáo tư vấn2025 có nhãn Dự thảo và văn bản thuyết
minh biên tập2026. Cả3 cặp Markdown/JSON qua validator cấu trúc. Bộ12 câu được
freeze trước khi chạy model, gồm scope năm, năm văn bản viện dẫn khác năm báo cáo,
metric khác nhau, draft, cập nhật cùng năm, so sánh2024/2026 và thiếu nguồn2027.

Cẩm nang biên tập2025 dài hơn được parse riêng:1301units/125594 ký tự; không lấy
nguồn khác thay thế rồi tuyên bố cẩm nang ấy đã được thử đủ. Bộ lõi dùng báo cáo
2025 có149units/12184ký tự. Lượt helper đầu chưa gọi native-layout fidelity;
đã giữ riêng và chạy bản đúng bước này, canonical hash không đổi ở3DOCX ban đầu.

Giới hạn: chưa render DOCX sang PDF/kiểm pagination hoặc visual; parser cảnh báo
DrawingML chưa có Office converter. QNU format validator không chứng minh toàn bộ
ảnh/ý nghĩa đã được bóc đủ hoặc tài liệu đủ điều kiện xuất bản. Không hạ Quality
Gate hoặc tự đặt draft thành ready để nghiệm thu.

## Lỗi nguồn thật phát hiện trước inference

- Tài liệu 2024 có 5 unit ngắn hơn 3 ký tự; báo cáo 2025 có 1 unit như vậy.
  Compiler giữ lỗi `KNOWLEDGE_WIKI_INVALID / source_unit_exceeds_reference_capacity`;
  không bỏ các unit ngắn, không giảm giới hạn quote để làm PASS. Đối chiếu OOXML
  xác nhận 5 cửa sổ ba fragment nằm trong một paragraph gốc. Một cửa sổ cuối câu
  chưa chứng minh được bằng cách đối chiếu này. Hiện tượng phân mảnh có bằng chứng;
  chưa kết luận mọi unit ngắn đều phải gộp hoặc toàn nội dung đã chính xác.
- Cẩm nang 2025 dài: probe dùng selector xác định, **0 LLM**, chạy thật compiler;
  sau 19 gói, validation từ chối `sections`: 1.301 vượt 512. Không đổi hợp đồng
  thành không giới hạn, không cắt mất nội dung hoặc gọi kết quả đó là Wiki ready.
- Ba nguồn lõi không đồng nghĩa ba Wiki đạt: chỉ nguồn 2026 qua preflight packet.
  Phép đo gọi thật sẽ giữ bundle unavailable đúng hợp đồng của luồng hiện tại
  cho 2024/2025, rồi thử canonical fallback. Không tự cấp chứng nhận chất lượng.

## Benchmark64 chốt và giới hạn nghiệm thu

| Lượt riêng | Tri thức | Positive | Negative | Hội thoại | Còn lỗi |
|---|---:|---:|---:|---:|---|
| Context600 final-release, lịch sử |59/60|49/50|10/10|4/4|P07|
| Context601, chỉ guard role, acceptance-final |56/60|46/50|10/10|4/4|P06,P07,P08,P13|
| Context601, code chốt, acceptance-release |**57/60 (95%)**|**47/50 (94%)**|10/10|4/4|**P07,P08,P16**|

Đạt ngưỡng85% ở cả tổng tri thức và positive, nhưng **giảm2 câu so với600**.
Không kết luận chất lượng tổng thể đã cải thiện hoặc P07 đã sửa xong. Hai lượt601
và lịch sử600 giữ riêng; không lấy câu tốt từ lượt khác thay FAIL. Model sampling
khác nhau, chưa có ablation lặp để quy mọi thay đổi đáp án cho một nhánh code.

Code chốt:128/128 citations resolve chính xác về nguồn;0 runtime error/timeout;
149 usage Luna/0fallback,960.795 input và37.743 output tokens, max prompt22.514.
P95 tri thức58,31giây; worst77,76giây. Đây là latency cả chuỗi nhiều model calls,
không phải timeout một request provider. Provider vẫn30giây, chuỗi evidence90giây.
Không thay chính sách thời gian hoặc ngân sách để làm PASS.

| ID | Kết quả600 → chốt601 | Quan sát thực tế |
|---|---|---|
| P07 |FAIL → FAIL|Nguồn đủ trong context, nhưng quyết định cuối INVALID_OR_EMPTY_CLAIMS; không có BoundVerification/Agreement ở sample này. Trace chưa lưu raw proposal để chốt nguyên nhân chi tiết, nên không đoán lỗi ID hay binding cụ thể.|
| P08 |PASS → FAIL|Từ chối dù nguồn có quy tắc mã; các vòng kiểm chứng không chốt đủ coverage/điều kiện. Chưa được coi là parser mất mã.|
| P16 |PASS → FAIL|Audit có các lượt complete nhưng luồng vẫn từ chối vì chưa đối chiếu chắc số liệu/điều kiện. Không đổi nghĩa unknown hay bỏ gate để lấy câu trả lời.|

P06/P13 PASS ở lượt chốt; lượt trung gian FAIL của chúng vẫn giữ. Cùng raw PDF,
canonical hash, revision12, index, vector generation, câu hỏi/rubric/fact IDs và
model profile600; snapshot chỉ khác created_at, cache fingerprint giống nhau.

Đây là `rag_service.ask` thật với actor đã xác thực và snapshot candidate do server
kiểm tra. **Không phải published HTTP/browser E2E**. Nguồn vẫn chưa xuất bản,
active index rỗng,2.943 staging points/0retrievable không đổi. Không tạo index,
revision, embeddings, fact hoặc publication mới trong601.

Lượt freeze đầu dừng trước run-intent do2 test đổi trước seal; lượt prepare sau
thiếu bản sao receipt index đã dừng trước inference, sau đó xác minh lại receipt
với DB trước khi chạy. Hai sự cố chuẩn bị đều0model call, không phải resend một
request uncertain. Postcheck của cả hai lượt64 hoàn tất đềuPASS.

## Nguồn nhiều năm

Chi tiết phép thử riêng ở [báo cáo nhiều nguồn](./MULTI_SOURCE_EVALUATION.md).
Dùng compiler extractive thật và ModelOps hiện hành; 2026 tạo4 trang qua2 calls,
2024/2025 giữ unavailable trước inference. Sau đó thử evidence pipeline và
canonical fallback với các adapter đọc nguồn local, không sửa source đang chạy.

Giới hạn của phép thử này: BM25 anchors thay vector retrieval; source/index/snapshot
là đối tượng local draft, không phải serving snapshot đã xuất bản; không approved
fact records, không HTTP/browser hoặc full ingestion E2E. Các thiếu sót chưa được
chữa bằng cách bỏ fragment, viết lại corpus, đoán năm hay tự approve quan hệ.
Không gọi ModelOps phụ trong lúc64 đang chạy; không ghép điểm12 câu vào64.

## Bàn giao

Hai bảo vệ RAG đã có regression, nhưng **chưa APPROVED toàn RAG hoặc ingestion
nhiều năm**. Cần xử lý tiếp sai khác ở bước chọn/kiểm chứng evidence của P07/P08/P16,
đối soát paragraph native DOCX và chia trang inventory Wiki có giới hạn. Những phần
này phải có bằng chứng riêng, không hạ Quality Gate hoặc đổi dữ liệu đang phục vụ.

Không sửa FE trong601, không chạy lại FE/build cho thay đổi thuần backend.
Không commit/stage/push, reindex, publish, restart, deploy hoặc đổi config/model.
Các thay đổi600 của người dùng được giữ nguyên. DB test đã drop sau khi xác minh exact name/nonce. Storage/evidence giữ theo
chính sách bảo vệ có từ trước; không thử xóa hoặc bypass. Usage/audit giữ nguyên.
