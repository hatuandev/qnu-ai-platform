# Phiên507 — Audit theo ID, đóng gói nguyên nhóm và tách nội dung công khai

Ngày 2026-10-16. Người dùng yêu cầu tập trung ba việc sau review506: sửa liên kết
kiểm chứng–đáp án, chọn/đóng gói chứng cứ và trình bày gọn. Không đổi nguồn, model,
Top K, cấu hình DB, vector, publication; không restart/deploy/migration/Git.

## 1. Nguyên nhân đã đối chiếu

- Q34: visible audit trả semantic supported nhưng copy lại answer_quote khác câu
  hiển thị; gate nguyên văn bác đúng hợp đồng, nhưng nhiệm vụ copy của model gây
  false rejection. Không sửa bằng fuzzy matching hoặc cho mọi quote nguồn là đúng.
- Q2: model có lúc bác địa chỉ trích nguyên văn bằng kiến thức ghi nhớ. Đồng thời
  câu hỏi địa điểm kéo cả thông tin hội trường/sự kiện; proof phụ trở thành đáp án.
- Q62: nguồn đang xuất bản có mục công thức quy đổi. Dependency group chứa9blocks
  công thức/chú giải bị loại do K=5. Nhãn CORRECT_ABSTENTION506 chưa có căn cứ.
  Nguồn công thức có layout/glyph nhiều dòng; phiên này không sửa nguồn hoặc tự tính.
- Q40/Q55: tất cả focused queries vẫn packing atomic_lists, dẫn tới kéo cả danh
  sách không được hỏi. Sau rerank, topic_order ưu tiên từ khóa tổng quát trở lại;
  bản thân reranker client trộn RRF với CE một lần nữa, có thể ưu tiên ứng viên
  lexical gốc dù CE thực xếp đoạn trực tiếp cao hơn. Repack sau overflow giữ anchor
  đó nên có thể giữ đoạn bonus vận động viên hoặc sự kiện bổ sung thay đoạn cần hỏi.
- Q25: source_grounded_claims phát sinh public claims từ mọi reference và dependency
  parent. Một reference phụ/đoạn tiếp nối không phải tự động là câu cần công khai.

## 2. Thay đổi

### Liên kết kiểm chứng

`response_audit.py`: server chia answer_spans phủ toàn câu trả lời, model chỉ trả
answer_span_id và proof. Dynamic contract yêu cầu mỗi span đúng một lần, IDs thuộc
catalog; quote hỗ trợ entailed=true phải khớp source. Mapping ngược không sửa text.
Kiểm tra số, nghĩa, relevance, missing/conflict và phủ toàn answer vẫn bắt buộc.
Không tự biến negative thành positive, không nhận ID lạ hoặc bỏ span bất lợi.
Giữ hai attempt structured_call có sẵn, không thêm vòng gọi model để repair span.

### Chọn và đóng gói

`prose_fallback.py`: RecoveryIntent yêu cầu entity/intent/event/round (nullable khi
thật sự không nêu), scalar_update_lookup explicit; không cho bỏ scope rồi dùng
default âm thầm. Rerank thấy cả topic và ORIGINAL question. Focused prose giữ CE
score thật nếu đầy đủ, không dùng RRF thứ hai/từ khóa để đảo ngược thứ hạng. Nếu
không có scores, giữ thứ hạng quan sát, không giả score. Enumeration vẫn giữ
topic-aware closure; trace candidates chỉ ID/score, không ghi nội dung nguồn.

Reference-priority theo số chỉ dành scalar update đã phân loại, không dành ngày,
sự kiện/eligibility/existence. Reference-linked candidates vẫn giữ trong pool.
Repack chỉ sau provider window rejection, giữ whole priority seeds + anchor, không
cắt danh sách/công thức và không tăng số lần retry của502.

`evidence_blocks.py`: thêm opt-in allow_first_whole_group cho recovery. Chỉ một
nhóm chứng cứ đầu tiên có thể nhiều physical blocks hơn K; phải vừa hard character
budget, giữ toàn nhóm rồi dừng không thêm body khác. Ghi whole_group_exceeds_block_k.
Không thay policy Top K, không cắt5/9đoạn hoặc mở ngân sách vô hạn. Các caller
khác giữ mặc định cũ; không coi số blocks là số logical proof units.

Focused packing không còn ép toàn bộ sibling list. Structural dependencies và
year/header provenance vẫn giữ; enumeration phải giữ cả danh sách cần thiết.
`prose_selection.py`: ưu tiên coverage tổng hợp mọi facet thay max của một facet.

### Trình bày

`evidence_passages.py`, `evidence_claims.py`: trong compact recovery, evidence_ids
chọn câu CÔNG KHAI, context_ids chỉ proof phụ (tối đa3). Tách từng public passage,
bind cùng-source, giữ primary reference; source_grounded_claims(primary_only=True)
không tự xuất heading/parent/context thành public fact. Essential conditions phải
ở public text và còn qua coverage audit; context không được mượn năm từ nguồn khác.
Luồng mặc định ngoài compact-mode giữ tương thích. Không LLM paraphrase thêm, không
tự sửa OCR/số/công thức để tạo vẻ trôi chảy. Chưa bảo đảm hội thoại tự nhiên hoàn toàn.

## 3. Kiểm chứng

- Regression mới `tests/test_rag_focus_507.py`: positive/negative span verdict,
  missing/duplicate/foreign IDs, invented quote, whole group>K opt-in + hard budget,
  public/context separation, cross-source scope rejection và original-event ranking.
- Scoped đầu103pass/2fail do test cũ đòi reranker chỉ topic; cập nhật đúng hợp đồng
  mới topic+original question. Scoped tiếp148pass; test mới sau đó phát hiện fixture
  không có lexical match và fixture planner chưa cung cấp required scope; sửa fixture,
  giữ mọi assertion grounding. Gate nhỏ cuối55pass/4,88s, có overlap, không cộng số.
- Ruff đúng9file PASS, exit0. Full `storage/focus507-full.xml`:1877PASS/11FAIL/
  17SKIP,220,59s,exit1; exact11 IDs trùng `review505-verified.xml`,0new failures.
  Tổng suite vẫn FAIL, không sửa baseline hoặc gọi toàn backend PASS.
- Chỉ probe model nội bộ qua `scripts.probe_review_505.py`, cache bypass trong process,
  không cloud hoặc semantic-cache flush. Chưa kiểm tra WebUI/API chat sau507; probe
  gọi RagService thực với DB/snapshot/retrieval/inference thật, không coi là HTTP E2E.

## 4. Các lượt thật, giữ cả kết quả chưa đạt

Artifact `backend/storage/review507-*.json`, không đưa raw corpus vào Git:

- initial6: Q2/Q34 bắt đầu trả có nguồn; Q62 lấy được công thức+chú giải; Q25 bớt
  đoạn cụt; Q40 còn chọn đoạn bonus vận động viên, Q55 refusal sau repack.
- focused-rank3: Q25 chỉ giữ ý hệ số; Q40/Q55 vẫn lệch. Không coi answered là đạt.
- no-numeric-priority3: có một Q5 trả số dự kiến cũ, không phải cải thiện. Phát hiện
  planner optional bỏ intent/coverage sai; bắt buộc scope và dùng CE score thực.
- ce-scope3: Q40 lấy đoạn thi năng khiếu trực tiếp (còn thêm thời gian/URL), Q5 trả
  số cập nhật kèm số cũ đúng quan hệ; Q55 provider error, không chuyển cloud.
- final6 (`review507-final.json`):6/6answered có citations,0error. Đây không tự
  đồng nghĩa6/6PASS chất lượng: Q40 còn thêm ngày/URL; Q62 công thức nhiều dòng
  chưa hiển thị chuẩn toán học. Q2 chỉ địa chỉ trụ sở; Q34 quy tắc đúngscope;
  Q55 đúng lịch chính không kéo bổ sung; Q25 chỉ giữ câu hệ số, không đoạn cụt.
  Q62 nhóm>K được giữ nguyên,9citations. Visible span mismatch bằng0 ở Q2/Q34/Q55;
  draft vẫn có thể bị audit bác về nghĩa; fallback verifier không bị bỏ qua.
  Mọi fingerprint config/snapshot trước=sau. Cùng snapshot `b7456674dcc9b51ce736`
  với506, không đổi nguồn/TopK/model. Không xóa lượt probe trước có failure.

Lệnh tại `backend`: `.venv/Scripts/python.exe -m pytest` các test507/502/505/491/
claims/492/500 (scoped148PASS trước lần bổ sung fixture), gate nhỏ cuối55PASS,
full `-q --junitxml=storage/focus507-full.xml --basetemp=storage/focus507-full-temp`;
`-m ruff check` đúng6file RAG và3file test. Probe `-m scripts.probe_review_505 --live
--ids 2 34 40 55 62 25 --output storage/review507-final.json`. Không runner retries.
Một test sandbox bị treo đã ngắt; kết quả gates ở đây là các lệnh có quyền chạy
đã hoàn tất, không coi lệnh bị ngắt là PASS.

Không suy accuracy80% hoặc toàn82 từ tập nhỏ. Không có groundedness score được đo
độc lập. Metadata/counts không thay bằng chứng nội dung và năm áp dụng.

## 5. Rủi ro/bước tiếp theo

- Q62 chứng minh cần sửa nhãn506, không chứng minh công thức nguồn đã được render
  chuẩn toán học hoặc rule tính đã được kích hoạt. Không thực hiện phép tính thật.
- Atomic group có thể vượt serving window dù vừa character budget: provider phải
  báo lỗi, không tự cắt formula/list. Chưa có tokenizer/window tin cậy cho mọi model.
- Audit theo span không bỏ entailment; một span chứa nhiều quan hệ vẫn có thể bị
  bác nếu không có proof chung. Phải giữ negative cases khi tối ưu về sau.
- Trình bày vẫn extractive: có thể dài, xuống dòng theo nguồn hoặc dư chi tiết.
  Không công bố toàn bộ ba mục đã giải quyết triệt để chỉ vì unit tests xanh.
- Không sửa11baseline, không full82, không restart/reindex/push.
