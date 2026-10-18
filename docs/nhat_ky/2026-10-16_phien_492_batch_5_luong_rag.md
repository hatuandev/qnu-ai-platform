# Phiên 492 — Batch năm luồng RAG

## Phạm vi đã được giao

Triển khai năm luồng đã thống nhất, đối chiếu các lỗi của bộ20 phiên490:
chọn chứng cứ; kiểm chứng dữ kiện; năm/phiên bản; bảng và hợp đồng model;
liệt kê/hội thoại/trình bày. Không upload lại, sửa nguồn/OCR, reindex, reset DB,
bật preset TopK, đổi model, migration, restart, commit/push hoặc deploy.
Chỉ dùng model nội bộ khi thử thật. Skill clean-code/backend/RAG pipeline/evaluation
được dùng để giữ thay đổi theo hành vi và chấm đúng nguồn, không lấy answered làm PASS.

## Thay đổi và giới hạn thiết kế

1. `facts.py`, `composer.py`, `service.py`: bỏ việc coi fact truy hồi là đã xác thực
   hoặc bảng luôn thắng văn xuôi. Bỏ fact chưa định kiểu khỏi câu hỏi chính sách;
   bộ lọc thuộc tính không được nới bằng OR từ khóa khác. Identity chỉ so trường
   định danh, không quét toàn raw JSON để lấy năm/giá trị làm bằng chứng thực thể.
2. `response_audit.py`: một audit độc lập cho câu trả lời fact/hybrid; từng mệnh đề
   phải có span trong đáp án, quote trong excerpt cùng snapshot và số trong quote
   riêng. Thiếu phủ, ID lạ, phần thêm không được hỗ trợ hoặc thiếu điều kiện không
   được xuất/cached như answered. Dùng lại source-bound prose recovery khi có thể;
   không cho model viết thay một đáp án mới để vượt gate. Citations của câu trả lời
   được chấp nhận lấy từ đúng excerpt auditor dùng, không chỉ word overlap.
3. `source_candidates.py`, `prose_fallback.py`: closure một bước trên lượng/số tham
   chiếu hiếm giúp đưa đoạn nhắc lại giá trị trước vào candidate set. Chuẩn hóa dấu
   phân cách bằng bộ numeric hiện có; không gán độ mới/thẩm quyền từ filename hoặc
   tự tuyên bố supersession. Giữ direct lexical hit + đối tác tham chiếu trước rerank.
   Planner nhỏ tách topic/facet/coverage từ câu hỏi gốc; so sánh phải giữ từng năm,
   liệt kê phải kiểm đủ danh sách, không chỉ một thành viên. Bước prose vẫn có budget
   riêng6000chars/1600output, tối đa3body focused; list/comparison dùng context_limit
   hiện hữu (legacy10), configured vẫn tôn trọng context_top_k; giữ
   dependencies nguyên nhóm. Không sửa max_tokens của trợ lý trong DB.
4. `enumeration_scope.py`: kiểm chứng độc lập căn cứ năm trong đoạn giới thiệu
   cùng nguồn; ngày ban hành, luật được dẫn hoặc tên file không đủ. Row/column year
   giữ ưu tiên, unknown không tự thành năm người hỏi. Catalog gốc không bị sửa.
5. `row_answer.py`: align chỉ khi hai ID chỉ đúng cùng tọa độ/hash/header/value;
   số bằng nhau ở ô khác không tương đương. Deduplicate ID audit lặp đúng cùng ô,
   nhưng ID lạ vẫn bị chặn. Ghi booleans/ID-diff để phân biệt lỗi metric/scope/coverage.
   Nếu audit đủ scope, không conflict và chỉ yêu cầu một tập con các ô selector đã
   đọc, có thể trả phần đồng thuận với trạng thái **partial**, nêu cột chưa thống nhất.
   Không bỏ qua auditor khi selector thiếu ô, không biến partial thành complete.
6. `evidence_model.py`, `evidence_indexed_audit.py`, `evidence_audit.py`: giữ hai
   attempt schema hiện hữu; repair không nhân đôi completion lỗi vào input; nhấn mạnh
   trả data instance thay schema. Diagnostic reason không còn giới hạn300 ký tự ở
   cả hợp đồng model và projection; verdict/claim/reference vẫn bắt buộc như cũ.
   Log loại lỗi/schema constraints, không dump prompt, câu trả lời hay secret.
7. `conversation_acts.py`, `combination_enumeration.py`: scope bất định trả phản hồi
   trung thực, không HTTP422; không lấy mọi nguồn đếm thay khi năm chưa xác minh.
   Gộp trùng khít cùng năm, viết tên nguồn một lần bằng nhãn; chưa có mã hoặc tên
   trùng mã được báo riêng và danh sách partial. Không tự sửa tên OCR hoặc gộp gần
   giống. Citations của giải thích chỉ lấy từ records/scopes thực tế, không chọn
   tùy ý một đoạn khác trong corpus cùng nhắc năm.

Không có thuật toán nào bảo đảm model nhỏ không đánh giá sai entailment. Kiểm tra
span/số không thay kiểm tra ý nghĩa; code và unit test không chứng minh chất lượng
trên mọi chatbot. Các giới hạn còn lại phải đọc cùng bảng chấm thực tế bên dưới.

## Kiểm chứng

- Regression cuối ở13 file: **181 PASS**, exit0; chạy Python venv với `-X utf8`
  từ backend. `tests/test_rag_batch_492.py` thêm positive/negative cho proof riêng,
  scope, contract reason, closure, year và cell agreement.
- Một số fixture routing/presentation cũ mock rõ audit boundary mới để tiếp tục
  kiểm đúng prompt/cache/history; không hạ assertion số hoặc scope. Test mới kiểm
  chính audit boundary, gồm provider failure và snapshot khác.
- Full đầu `full.xml/log`:1692pass/13fail/17skip/54error.54setup errors là quyền
  thư mục tạm Windows; hai failure mới ở fixture API chưa mock audit boundary.
- Sau sửa fixture và dùng basetemp mới trong workspace: `verified-full.xml/log`
  **1748pass/11fail/17skip**, exit1, tổngFAIL; đối chiếu exactIDs khớp491.
  Sau lượt này còn tinh chỉnh packing/reference priority, metadata source_kind và
  loại table/heading khỏi prose. **Chưa chạy full trên chính mã cuối**; không dùng
  kết quả trước đó như full gate cho các tinh chỉnh cuối.
- Regression13file ở bước gần cuối183pass; sau thay đổi cuối test table-kind,
  hai file batch492/prose491 **45pass**, exit0. Bộ API/batch/prose/row78pass trước
  tinh chỉnh packing cuối. Ruff có phạm vi và git diff --check đạt ở các lần ghi nhận.
- Live: hai lượt đầu cùng10câu đã giữ trong storage, không xóa lỗi hay chọn đáp án
  đẹp. Chúng phát hiện reason projection, incomplete enumeration, update retrieval,
  quote coverage và audit IDs lặp. Chưa là nghiệm thu mã cuối sau các sửa đó.

Artifacts riêng tư: `backend/storage/quality_492/`. Không đưa snapshot corpus/log
runtime vào tài liệu Git. Không gửi corpus ra provider bên ngoài; guard chặn dựng
adapter ngoài và HTTP ngoài AI server/loopback. ModelOps có thể ghi usage như luồng
thường; không gọi đây là zero-write DB. Không sửa config/source/vector.

## Kết quả cuối

Phiên bị ngắt có chủ đích. Lượt model cuối đã kết thúc trước khi nhận lệnh dừng;
không còn tiếp tục test sau khi kiểm tra trạng thái tiến trình.

- `acceptance/results.json`:10câu Q03/Q05/Q08/Q10/Q11/Q15/Q16/Q17/Q18/Q19,
  **4completed/6error**. Các error đều `ALL_PROVIDERS_UNAVAILABLE`; log có primary
  HTTP502 ở các lượt, hoặc không lấy được route khả dụng, fallback ngoài bị guard
  chặn403. Chưa đủ bằng chứng kết luận toàn bộ là lỗi mạng hay lỗi RAG.
- Q10 có trả nguyên tắc quy đổi từ nguồn nhưng cần chấm tính trực diện/đủ ý;
  Q15 trả39cách ghi, có cảnh báo20mục thiếu mã và1tên trùng mã, trạng tháipartial;
  Q17 vẫn `ROW_AUDIT_INVALID_CELLS` dù có bảng trong nguồn; Q19 từ chối đúng scope2027.
- **Nghiệm thu chất lượng chưa đạt**. Không lấy các câu tốt ở lượt trước để bù các
  lỗi của lượt cuối. Giữ đủ3lượt×10attempts, không gọi đây là chỉ10request.
- Config/metadata/22sources/snapshot/rag_code fingerprint đều unchanged trong lượt
  acceptance. Không source/vector/config mutation, không reset circuit/đổi model.

Việc còn lại khi tiếp tục: review chi tiết lỗi upstream/route trong phạm vi cho phép;
truy vết ID không hợp lệ ở Q17; chấm lại độ đủ ý Q03/Q05/Q10/Q11/Q18 khi model khả
dụng; full gate trên mã chốt với basetemp riêng. Không chạy82 hoặc reindex để né lỗi.
