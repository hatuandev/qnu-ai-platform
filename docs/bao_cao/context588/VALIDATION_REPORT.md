# Context588 — PDF revision mới, vector staging và benchmark 64 câu

## Kết quả luồng nạp

Theo yêu cầu người dùng, tạo một revision mới từ đúng PDF phức tạp đã kiểm thử,
nạp vector staging, kiểm trang tri thức và chạy lại bộ 64 câu. Không sửa mã ứng
dụng, không đổi model, không xuất bản, không commit/push/restart/deploy.

| Bước | Kết quả quan sát |
|---|---|
| Đúng PDF | `tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).pdf`, 648.851 byte, SHA-256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02` |
| Nguồn | `col_admissions` / `bnd_12190866d5ec` |
| Revision mới | `ks_rev_697bfdc3de8e`, revision 5; job `job_41be9eb5a86c` |
| Chất lượng | `READY_WITH_LIMITATIONS`, 0 blocker; cặp QNU Markdown/JSON và đối soát nguồn PASS |
| Markdown | 51.531 ký tự, cùng hash và trùng hoàn toàn với PDF Context583 |
| JSON | 327 block, 12 block bảng; không đổi cấu trúc do thêm wiki policy |
| Index mới | `idx_rev_bb4c3f1a91d0`, trạng thái `ready` |
| Vector | 327 chunks / 415 facts cho index mới, staging |
| Namespace | Tổng 654 points: 327 cũ giữ lại + 327 mới; 0 retrievable |
| Trang tri thức | **FAIL — unavailable**, 0 trang; `ALL_PROVIDERS_UNAVAILABLE` |
| API trang | GET local thật trả HTTP 200, đúng collection/binding/revision/index và `unavailable/pages=[]` |
| Xuất bản | Không thực hiện; active index pointer vẫn null |

Snapshot nguồn đã lưu qua StorageDriver khớp bytes file trên đĩa. Tạo revision
qua `queue_reparse(dispatch=False)` và task worker chính thức chạy inline, không
đổi dispatcher/config hoặc restart dịch vụ. Chứng nhận chép hình đã được người
dùng xác nhận trước đó được kế thừa vì source/image hash không đổi; không tạo
phê duyệt quan hệ ngữ nghĩa mới hoặc cấp quyền xuất bản.

## Môi trường, quyền và phạm vi

- Development; DB/MinIO/Qdrant đều loopback. Đã xác minh trước thao tác; không
  migration hoặc thay cấu trúc DB dùng chung.
- Actor do luồng auth hiện có của môi trường local giải quyết; kiểm quyền view,
  update, sync/upload và quyền admin cho candidate benchmark. Không tạo actor giả,
  override dependency hoặc bỏ guard.
- Giữ Luna `cx/gpt-6-luna` chính, Qwen `qwen3.5-9b` dự phòng. Giữ cấu hình
  embedding, provider, timeout và policy đang có.
- Không xóa nguồn, revision, chỉ mục hoặc vector cũ. Source pointer chuyển sang
  revision mới theo luồng ingestion; publication pointer không chuyển.
- Giữ toàn bộ thay đổi chưa commit của Context587; các helper và artifact của
  lượt này nằm trong vùng validation/storage được ignore của repo.

## Vì sao chưa tạo được trang tri thức

Không phải lỗi thiếu nội dung PDF: canonical Markdown của revision 5 trùng
revision 4, cùng SHA-256 `ad0dc2900b502fbe84ed5549263be49f4d55d4df5c17001414ea2f748d2c9152`.

Lượt phân tích đầu qua Luna đã thành công, ghi nhận **35.591 prompt tokens** và
1.700 completion tokens. Bước gọi tiếp theo timeout; fallback Qwen trả HTTP 400
vì context vượt giới hạn. Compiler trả unavailable, không nhận đầu ra chưa hoàn
chỉnh. Indexing nội dung canonical vẫn hoàn thành theo cơ chế tách wiki khỏi
Quality Gate của nguồn đã triển khai, không hạ gate để vượt lỗi này.

Đo offline chính payload biên soạn, không gọi lại LLM:

| Gói | Source units | Ký tự văn bản được budget | Ký tự JSON thực | Phần JSON/metadata thêm |
|---|---:|---:|---:|---:|
| 1 | 161 | 23.891 | 107.136 | 83.245 |
| 2 | 141 | 23.971 | 102.694 | 78.723 |
| 3 | 32 | 3.439 | 22.085 | 18.646 |

Riêng gói đầu: JSON `heading_path` chiếm 15.707 ký tự, `temporal` 55.540 ký tự.
Chính sách hiện chỉ tính `unit.text`, bỏ qua overhead metadata, schema, analysis
outlines và output budget. Vì thế `packet_chars=24000` không đảm bảo request
vừa context provider. Số token của request generation thất bại không được quan
sát chính xác; không dùng phép đếm ký tự để bịa ra số token đó.

Đây là khoảng hở của phần compiler wiki ở Context587, chưa lộ trên fixture tổng
hợp ngắn. **Không thể dùng benchmark dưới đây để kết luận wiki đã nâng chất
lượng RAG**, vì snapshot thực tế có `knowledge_wiki_enabled=false`.

Hướng sửa cần một lượt triển khai riêng: budget toàn request theo token/capability
provider, tính cả output/schema/feedback; chia nhỏ gói và dùng metadata chia sẻ
theo ID thay vì lặp nguyên bản. Giữ provenance, điều kiện/ngoại lệ và validation;
không cần tăng context hoặc đổi model để che lỗi đóng gói. Chưa áp dụng thay đổi
này trong lượt chỉ kiểm thử hiện tại.

## Benchmark và đối chiếu

| Nhóm | Context583 trước | Context588 mới |
|---|---:|---:|
| Tri thức | 54/60 = 90,00% | **55/60 = 91,67%** |
| Có đáp án trong nguồn | 44/50 = 88,00% | 45/50 = 90,00% |
| Negative | 10/10 | 10/10 |
| Social, ngoài mẫu số tri thức | 4/4 | 4/4 |
| Mục tiêu 85% | Đạt | **Đạt** |

Không thiếu hoặc trùng ID; đủ 64 kết quả. Hai câu chuyển FAIL→PASS: **P01, P16**.
Một câu chuyển PASS→FAIL: **F04**. Bốn câu vẫn FAIL: **P05, P07, P09, P10**.
Không gộp kết quả retry ở Context586 vào baseline 64 câu để làm đẹp phép so sánh.

| ID còn lỗi | Kết quả và nguyên nhân quan sát |
|---|---|
| F04 | Câu nối tiếp đổi sang AM-0070; router trả CLARIFICATION/CONTEXT_SCOPE_UNPROVEN, không gọi RAG dù lịch sử đã có năm 2026. Không phải mất ô nguồn. |
| P05 | Từ chối quá mức, chưa trả đủ cột Ước tính 2027 chưa nghiệm thu và không áp sang Ghi nhận 2026. |
| P07 | Có biên bản trực tuyến/30 ngày/không miễn an toàn/không áp A, nhưng thiếu điều kiện cơ sở tạm đóng gây chậm chữ ký, nhật ký và xác nhận giảng viên cùng kỳ. |
| P09 | Lỗi runtime ROW_ANSWER_SOURCE_INVALID khi hỏi dấu / ở CT-06; không được tính là từ chối đúng. |
| P10 | Lỗi runtime ROW_ANSWER_SOURCE_INVALID khi phân biệt dấu – ở CT-05 với số 0 CT-01. |

Có 62/64 kết quả service thành công, 2 lỗi runtime trên; không có timeout trong
64 câu. Tổng 124/124 citation giải được đúng source/index revision/hash và span.
Điều đó không làm P07 thành PASS: citation hợp lệ vẫn có thể thiếu điều kiện.

Usage riêng benchmark: **105 lượt Luna success, 0 fallback**, 516.787 prompt +
22.899 completion tokens, prompt lớn nhất 8.909 tokens. Khác với gói wiki 35.591
prompt tokens; không lẫn lỗi context của biên soạn vào các request RAG này.
Latency toàn service: p50 515,48 ms, p95 33.714,02 ms, max 40.100,48 ms.
Một câu gồm nhiều lần inference nên tổng lâu hơn timeout từng provider là hợp lệ.
Không ước tính chi phí tiền khi chưa có đơn giá đủ căn cứ.

Runner exit 0; scorer exit 0 theo ngưỡng 85%; **wiki test vẫn FAIL**. Không kết
luận luồng wiki đã sẵn sàng chỉ vì benchmark canonical đạt ngưỡng.


Giữ đúng 64 câu của Context583, gồm 60 câu tri thức và 4 social ngoài mẫu số.
Giữ câu hỏi, session, rubric, nhãn answerable và toàn bộ gold spans. Ánh xạ 33
fact IDs mới bằng source unit/column/header/raw value/row code khớp chính xác.
Canonical trùng nên không nới chuẩn hoặc thay nội dung gold để thích nghi kết quả.

Đo qua `rag_service.ask` thật với candidate snapshot được server kiểm quyền và
đối soát, gọi ModelOps/Qdrant thật. **Không phải HTTP E2E chatbot đã xuất bản**.
Benchmark giữ cùng phạm vi Luna-only như Context583; không đổi cấu hình fallback
trong DB. Lỗi provider được tính FAIL, không coi là từ chối đúng.

Scorer dùng kiểm chứng tọa độ/giá trị/citation cho ô dữ liệu và rà thủ công từng
câu văn bản theo rubric nguồn, không gọi judge LLM. Nhãn vẫn là draft source-rubric,
chưa phải human holdout. HTTP 200 hoặc citation resolve không tự đồng nghĩa đáp
án đúng.

Giới hạn so sánh: timeout Luna hiện là 30 giây, Context583 dùng 15 giây; chỉ mục
mới và cache identity mới. Không quy mọi chênh lệch cho mã wiki, đặc biệt khi wiki
không được tạo. Không chạy lại baseline cũ trong lượt này.

## Kiểm chứng cuối và tài nguyên

Postcheck PASS/exit 0: source bytes và các revision/index cũ giữ nguyên; nguồn,
repository/kho khác, model/provider/assistant config và mã ứng dụng khớp seal
trước/sau. Luna vẫn timeout 30 giây, không đổi primary/fallback. Không có busy job.

New source revision/index đều ready; active publication pointer null và Qdrant
không có point retrievable trong namespace kiểm thử. Candidate chỉ dùng index
mới, không đọc lẫn 327 points của index cũ.

Không tạo conversation thread/message hoặc gap kiểm thử còn tồn tại (đều 0),
không cần thao tác xóa. Không tạo DB test trong lượt này; giữ usage audit, báo
cáo và nguồn/vector staging có chủ ý. Không dùng cleanup để đụng dữ liệu cũ.


Không chạy lại full Pytest vì không đổi mã ứng dụng. Full Context587 là kết quả
lịch sử: 3.026 PASS / 18 FAIL nền / 17 SKIP; không ghi là full hiện tại PASS.
Revision/vector staging mới là đầu ra người dùng yêu cầu, giữ lại để kiểm tra.
Không tạo DB test hoặc tài liệu người dùng giả để rồi xóa dữ liệu thật.

## Bằng chứng và lệnh thực

Từ root repo, dùng Python venv hiện có; không cài thư viện hoặc đổi runtime:

```powershell
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_preflight.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_revision.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_vector.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_prepare.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_run.py
backend/.venv/Scripts/python.exe -X utf8 .antigravity-bridge/validation/context588_score.py
```

- [Preflight](../../../backend/storage/context588/preflight.json)
- [Revision receipt](../../../backend/storage/context588/revision-receipt.json)
- [Chất lượng revision](../../../backend/storage/context588/revision-validation.json)
- [Staging và API wiki](../../../backend/storage/context588/staging-validation.json)
- [Chẩn đoán payload wiki](../../../backend/storage/context588/wiki-payload-diagnosis.json)
- [Manifest bộ câu hỏi](../../../backend/storage/context588/manifest-frozen.json)
- [Ánh xạ gold](../../../backend/storage/context588/gold-mapping.json)
- [Benchmark summary](../../../backend/storage/context588/summary.json)
- [Đối chiếu từng câu](../../../backend/storage/context588/comparison.json)
- [Postcheck](../../../backend/storage/context588/postcheck.json)
