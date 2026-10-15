# Phiên 468 — Giai đoạn 3: truy hồi hàng bảng và ngữ cảnh nguồn

Ngày 2026-10-15. Người dùng duyệt tiếp giai đoạn 3 sau phần nguồn/metadata phiên 467.

## Mục tiêu và phạm vi

Lấy đúng hàng thực thể, giữ đủ cột phương thức và phần điều kiện/chú giải trước khi
gửi cho model. Sửa nhánh legacy `fact_hybrid` đang chạy sau reset, không bật policy khác
để làm đẹp kiểm thử. Tận dụng BM25 hiện hữu, không thêm từ điển “điểm sàn”/tên ngành/model.
Theo Clean Code/Backend/RAG: thay đổi cục bộ, pin snapshot/tenant/revision, lỗi DB phải rõ,
trích dẫn dùng raw span; không suy năm dữ liệu từ ngày ban hành/tên tệp.

Không sửa ingestion/OCR, không reset/migrate/reparse/index/publish, không thay cấu hình
ModelOps/reranker/output budget. Không gọi model chat, OCR hay dịch vụ cloud trong phiên này.

## Thay đổi cốt lõi

### 1. Facts: lọc thực thể trước khi LIMIT

`facts.py` thêm điều kiện định danh theo phrase FTS của entity text hoặc mã chính xác
trước giới hạn SQL. Từ khóa thuộc tính không còn kéo hàng khác vào một lát dữ liệu rồi
mới lọc thực thể bằng Python. Năm áp dụng khớp được xếp trước scope chưa rõ; tie-break
bằng ID ổn định. Giữ scope tenant/workspace/index và giữ unknown-year, không tự gán năm.

PG regression tạo thực thể nhiễu đứng trước thực thể đích, thêm năm cũ/unknown/năm hỏi,
`limit=1` vẫn lấy đúng thực thể/năm. Dữ liệu test trong outer transaction hoàn tác;
không dùng fallback hoặc mock DB để pass. Đây là test predicate facts, không mô phỏng publish.

### 2. Nhánh bổ sung hàng bảng đã đánh chỉ mục

`source_rows.py` đọc chunk của index đã pin, chỉ nguồn ready/index active (hoặc ready cho
candidate-mode). Có joins/bộ lọc collection, tenant, workspace, binding, source và index;
không dùng giá trị ô khác để xác định thực thể. Entity cell được nhận diện từ cấu trúc bảng
hiện hữu, so khớp toàn cụm từ hoặc mã, không tìm tên ngành trong ô tổ hợp môn.

SQL dùng tên/mã đã phân giải nếu có, nếu chưa có dùng n-gram cấu trúc của câu hỏi làm
prefilter. Sau đó kiểm ô định danh trước khi đọc sâu manifest/graph của nguồn khớp.
Không cắt SQL top-K trước bước chọn thực thể. Các nguồn được gom theo index để không
kiểm lại cùng manifest cho từng hàng. Đây là bước thu hẹp ứng viên, không xác thực ngữ nghĩa.

Kiểm source hash/review/parity/unit-manifest pin/graph và raw row nằm trong chunk thật.
Artifact cũ chưa có graph được dựng liên kết đọc-only từ cùng manifest, không tính lại
giá trị facts đã hiệu đính và không viết ngược nguồn. Thiếu manifest trong chunk legacy
không tạo hàng giả; nhánh truy hồi cũ vẫn có thể dùng dữ liệu như trước.

### 3. BM25 và giữ đủ ngữ cảnh

Dùng lại `evidence_bm25.rank_blocks` trên hàng + intro/notes cùng nguồn. Năm đã verified
mới là hard filter; năm trong đoạn dẫn chỉ là hint xếp hạng. Không đổi năm, tên cột hoặc
giá trị để khớp câu hỏi. Chọn tối đa 6 anchors, giữ hai hàng đứng đầu khi trộn với kết quả
hybrid; số slot thông thường tôn trọng `reranker_policy.top_k`. Ghi chú được thêm nguyên
source-unit riêng, không cắt thành một phần câu hoặc đẩy mất do slot cạnh tranh.

Không tạo CE score giả, không đổi cấu hình reranker. Anchor riêng có RRF 0 vì không
phải kết quả fusion/CE. Không có anchor thì giữ nguyên danh sách reranker, không cắt lại.
Dedup theo binding/index/source-unit, không xóa trùng nội dung giữa hai revision/năm khác nhau.

Metric chưa được phân giải thì không đưa toàn bộ học phí/chỉ tiêu cùng thực thể lên
“TẦNG 1 ĐÃ XÁC THỰC” khi đã có hàng gốc. Model nhận tên cột và đoạn dẫn để xác định loại
số liệu; không tự map một từ “điểm” sang một loại điểm. Prompt nhắc đọc đủ cột/dấu/chú giải,
không áp điều kiện cho mọi hàng khi nguồn chưa xác nhận phạm vi.

### 4. Citation và quan sát luồng

`citation_guard.py` dùng `citation_quote` raw source-unit cho anchors mới, không quote
projection embedding như thể nguyên văn. Ghi chú giữ source-unit riêng và trang riêng,
không sao chép temporal scope/trang của hàng sang ghi chú. Row source_pages có trang
hàng/header thật trong manifest. Context-only không tự là mệnh đề đã kiểm chứng.

`service.py` ghi `rag_execution_branch` (`fact_hybrid` hoặc `evidence`) và snapshot;
cache legacy có version `entity-rows-v1` để không dùng đáp án theo thuật toán cũ. Không
xóa cache hoặc thay policy trong DB. `temporal_answer.py` mở prefetch cho câu hỏi năm +
thực thể/số liệu dù chưa biết mã metric; deterministic answer vẫn yêu cầu context tương thích.
Hai strict-xfail routing phiên 466 đã được gỡ; lỗi refusal có citations vẫn strict-xfail.

## File thay đổi

- Runtime: `backend/app/modules/rag/source_rows.py`, `facts.py`, `service.py`,
  `temporal_answer.py`, `citation_guard.py`.
- Regression mới: `backend/tests/test_rag_rows_stage3.py` (10 ca, có PG rollback và lỗi DB).
- Cập nhật regression mở: `backend/tests/test_rag_floor_stage1_466.py` (chỉ routing đã sửa).
- Mở rộng fixture của 4 suite unit cũ: `test_rag.py`, `test_rag_entity_scoped_formatting.py`,
  `test_revision_safe_qdrant_and_retrieval.py`, `test_workflow_hitl_and_history.py` để khai báo
  dependency row-anchors rỗng trong các ca chỉ kiểm prompt/fallback/history. Không thay assertions;
  chức năng anchors có suite PG/negative/prompt riêng, không thêm fake fallback vào runtime.
- Diagnostic: `backend/scripts/audit_rag_rows_stage3.py` (READ ONLY, không model/OCR).
- Runbook 03, WORK_LOG, memory, snapshot 468 và mục lục nhật ký.

## Kết quả kiểm chứng

- Đầu tiên 7 ca thiếu chức năng fail vì chưa có module; không coi đây là bằng chứng
  tái hiện mọi bug. Baseline truy hồi sai đã có trace thật ở phiên 466.
- Regression chống thăng hạng metric sai chạy RED: **1 failed/9 passed** do học phí giả định
  trong test vẫn nằm trong prompt “điểm sàn”; sau sửa không còn ô đó, có đủ 15/18/600/15.
- Focus cuối trước full: **116 passed, 1 skipped, 1 xfailed/7,31s**.
  `storage/pytest468_handoff_focus.xml`; 1 xfail là refusal/status còn mở, không phải đã sửa.
- Ruff toàn Backend đạt, có cảnh báo quyền đọc các artifact cũ. Dùng Python venv sẵn có,
  không cài/cập nhật dependency. Không FE build vì không thay Frontend.
- Full đầu: **1406 passed, 20 failed, 16 skipped, 1 xfailed/186,75s**. Ngoài 11 lỗi nền,
  9 ca unit lắp ghép dùng AsyncMock DB chưa khai báo dependency mới, `.all()` trả coroutine
  thay vì SQLAlchemy rows. Đã mở rộng fixture có sẵn của đúng 4 suite, không nuốt lỗi ở runtime.
- Regression sau cập nhật fixture: **163 passed, 1 skipped, 1 xfailed/9,02s**,
  `storage/pytest468_final_regression.xml`; Ruff toàn Backend vẫn đạt.
- **Full handoff: 1.415 passed, 11 failed, 16 skipped, 1 xfailed/182,78s**,
  `storage/pytest468_handoff.xml`. Đối chiếu exact ID với phiên 467: cùng 11 lỗi nền,
  không còn lỗi mới. Gồm consulting export2, publishing/canary/GC/direct upload6,
  reconciliation1, auth-cookie role1, universal tools1. Không tuyên bố toàn suite xanh.

## Diagnostic trên kho thật

`backend/storage/rag_stage3_468/handoff_report.json`, chỉ đọc PostgreSQL/snapshot, model_calls=0.
Giữ mode RAG và evidence policy tắt như hiện trạng. Cả hai câu điểm sàn QLGD/SP Toán năm 2026
đều đưa nguồn **TB điểm sàn 26** lên hạng 1. Hàng giữ đúng 15/18/600/15 và 20/–/–/20;
phần điều kiện/chú giải trang 7–8 vẫn được đưa vào nhóm ngữ cảnh cùng revision.
Không tự xác nhận năm áp dụng của mọi hàng từ intro 2026.

Vòng prefilter n-gram rộng ban đầu mất 6.423,83/9.146,43ms; thu hẹp entity + kiểm ô trước
manifest còn 1.249,88/1.727,55ms, lượt handoff 843,98/1.245,31ms. Đây chỉ là phép đo
retrieval hai câu trên một corpus/máy, không phải tốc độ chat hay benchmark tổng quát.

Test khác tenant trả rỗng. Config/snapshot/inventory/metadata/source+facts+chunks fingerprint
trước/sau bằng nhau. Không claim toàn DB read-only vì suite test có fixture riêng/normal logs;
diagnostic bản thân đặt transaction READ ONLY. Không chạm vector/Qdrant hoặc nguồn thật.

## Giới hạn và bước kế tiếp

- Chưa chạy sinh câu trả lời thật, chưa 20/82 hoặc Ragas, không tuyên bố accuracy tăng bao nhiêu.
- Shared evidence path vẫn giữ nguyên; nhánh đang sửa là fact-hybrid sau reset. Không tự bật policy.
- Chưa sửa context window8192 so với output5000; chưa sửa refusal có evidence thành answered,
  hoặc coverage ngữ nghĩa của câu hỏi nhiều ý. Các vấn đề đó không được che bằng đổi model.
- Anchor là retrieval hint: hàng cùng tên ở nhiều cấp đào tạo/metric vẫn cần scope verification;
  BM25 không tự hiểu mọi đồng nghĩa hoặc đảm bảo mọi câu liệt kê đã đủ ý.
- Prefilter dựa trên FTS nguyên bản: không cam kết bảo vệ anchor cho mọi cách viết không dấu/
  viết tắt mới; hybrid cũ vẫn hoạt động khi không có anchor. Corpus lớn cần benchmark riêng.
- BE/worker cần nhận code mới trước thử hỏi. Nguồn cũ còn thiếu số/ngày cần quy trình
  targeted reparse→duyệt→staging→probe→publish phiên 467; giai đoạn 3 không tự làm bước đó.

Giữ docs/tai_lieu, Git index và mọi thay đổi đang có; không commit/push/deploy/restart.
