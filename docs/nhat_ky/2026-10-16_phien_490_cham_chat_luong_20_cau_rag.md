# Phiên 490 — Chấm chất lượng 20 câu RAG trên publication thật

## Kết luận

Chưa có bằng chứng preset Top K 30/30/30/5 làm chất lượng trả lời tốt lên ổn định.
Trên bộ 20 câu đại diện, cấu hình hiện tại có **5 đạt / 5 một phần / 9 không đạt /
1 lỗi thực thi**; preset có **6 đạt / 5 một phần / 8 không đạt / 1 lỗi thực thi**.
Không quy đổi câu một phần thành đúng, không loại câu lỗi khỏi mẫu, không suy mức
chất lượng toàn app từ 20 câu này. Hai câu đạt ở mỗi profile là từ chối đúng vì thiếu
dữ liệu năm được hỏi hoặc chưa có quy tắc tính điểm đã kích hoạt, không phải tính được điểm.

Ưu tiên sửa đường đi và kiểm chứng claim trước khi thêm thuật toán hoặc chạy 82 câu.
Không sửa mã ứng dụng, cấu hình lưu DB, nguồn, vector hay publication trong phiên này.

## Phạm vi, phương pháp và giới hạn

- Người dùng yêu cầu chấm 20 câu trước đợt tiếp theo. Dùng skill `qnu-rag-evaluation`
  để tách trạng thái `answered`, hit/trích dẫn và tính đúng thực sự; đọc thêm
  `qnu-rag-pipeline` để truy vết đường xử lý, không thay đổi nó.
- Bộ 20 câu đại diện gồm nhận diện, hotline, chỉ tiêu, số ngành, phương thức,
  ngoại lệ giáo viên, hệ số môn, quy đổi, ưu tiên, phí, lịch, bảng tổ hợp, liệt kê,
  điểm lịch sử, so sánh năm, năm thiếu và tính điểm. Có hai cặp hỏi tiếp nối.
  **Không phải 20 câu đầu của bộ 82, không phải mẫu ngẫu nhiên hay holdout mới.**
- Chạy `RagService.ask` với runtime policy của trợ lý `admissions`/`col_admissions`,
  cùng cách dựng request của luồng trợ lý. Không gọi toàn bộ wrapper HTTP/SSE/UI;
  history hai lượt được truyền trong bộ nhớ, không ghi cuộc hội thoại vào DB.
- 20 câu × 2 profile, một lần mỗi cặp, đảo thứ tự profile theo câu. Không chạy lại
  lỗi để làm đẹp kết quả. `legacy` là baseline đang lưu; `configured` ghi đè policy
  trong request, không lưu preset. Dense/lexical/fusion/context preset là 30/30/30/5.
  Baseline quan sát ở 12 lượt hybrid dùng dense/lexical 12; reranker policy có top_k=5.
- Cache đọc/ghi bị bỏ qua có chủ đích; không dùng lại đáp án cache. Model
  `qwen3.5-9b`, provider nội bộ `prov_rtx5090_vllm`, temperature 0.2, max_tokens 5000.
  Evidence branch đang tắt, nên không tuyên bố đã đo chất lượng branch đó.
- 22 nguồn đang active; chốt cấu hình, metadata, binding/index/source và canonical
  hash trước chạy, kiểm tra lại trước từng case và cuối chạy. Fingerprint cuối
  **config/metadata/snapshot/sources đều unchanged**.
- Giới hạn provider/HTTP trong runner: chỉ model server nội bộ đã được phép và
  localhost; không gửi tài liệu sang model ngoài. Quan sát 50 lần generate thành
  công đều cùng primary nội bộ, không fallback; danh sách chặn external rỗng.
- Ranh giới chạy có thể ghi usage/lease/capability của ModelOps bình thường; không
  gọi đây là thí nghiệm hoàn toàn không ghi DB. Không đổi cấu hình hay tài liệu.
- Chấm bởi Codex đối chiếu canonical nguồn, không nhờ chính model sinh đáp án tự
  chấm. Đây là **nhãn AI source-review**, chưa được cán bộ tuyển sinh duyệt làm gold.
  Chưa đối chiếu hình ảnh từng PDF gốc; khác biệt OCR phải giữ là bất định.
- Mỗi profile chỉ một lượt, temperature khác 0: không quy mọi khác biệt văn phong
  cho Top K, không có cơ sở kiểm định ý nghĩa thống kê hay khẳng định thắng/thua.

Snapshot fingerprint: `b7456674dcc9b51ce736`.
Config SHA-256: `2d4ade9b85406c1c2b374d73ef07cadb6990a972c81e107c5eb41ff0ed0fe8fe`.
Source inventory SHA-256: `af5abb04968268135eac78554d0a654529672a55ffb6d54f8492631947df2084`.
Thời gian chạy: 2026-10-16 03:29:47–03:34:18 UTC, tương ứng 10:29–10:34 UTC+7.

## Tiêu chí chấm

- **Đạt**: đáp ứng phần cốt lõi, không thêm kết luận sai đáng kể, đúng phạm vi năm/
  loại chỉ số và có căn cứ. Từ chối đúng phạm vi thiếu cũng có thể đạt.
- **Một phần**: hữu ích nhưng thiếu điều kiện, thêm kết luận nhỏ chưa có căn cứ,
  còn mâu thuẫn nguồn thật, hoặc không đáp ứng yêu cầu trình bày ngắn gọn.
- **Không đạt**: sai loại số/năm/điều kiện quan trọng hoặc không trả lời được dù
  nguồn xuất bản có căn cứ rõ.
- **Lỗi**: exception thực thi, không gọi là thiếu dữ liệu và không bỏ khỏi mẫu.

Đọc riêng tính đúng, độ đủ, năm/phạm vi, hỗ trợ trích dẫn và tính tự nhiên trong ghi
chú từng câu; không tạo điểm tổng hợp giả hoặc dùng faithfulness tự báo làm correctness.

## Kết quả từng câu

| ID / chủ đề | Hiện tại | Preset | Ghi nhận chính |
| --- | --- | --- | --- |
| Q01 Mã trường | Đạt | Đạt | DQN; phân biệt QNU. |
| Q02 Hotline | Đạt | Đạt | Đúng hotline; số điện thoại cố định bổ sung có nguồn. |
| Q03 Tổng chỉ tiêu 2026 | Không đạt | Không đạt | Từ chối dù văn bản thuyết minh nêu 5.173 và phân biệt bản đầu 4.500. |
| Q04 Số ngành/chương trình | Một phần | Một phần | Phân biệt 53/56 nhưng gán số hiệu thông báo cho số ngành chưa được đoạn nguồn chứng minh; kéo thêm số liệu ngoài câu hỏi. |
| Q05 Phương thức 2026 | Đạt | Một phần | Baseline đủ phương thức và ngoại lệ; preset bỏ hạn chế giáo viên, diễn đạt “kết hợp” dễ hiểu sai. |
| Q06 Giải thích ngắn lại Q05 | Một phần | Một phần | Giữ chủ đề, không lặp bảng; còn dài, thêm điều không hỏi; preset bỏ ngoại lệ. |
| Q07 Ngành không xét học bạ | Một phần | Đạt | Baseline thêm khẳng định không rõ căn cứ về “ngành khác”; preset trả đúng nhóm giáo viên. |
| Q08 Giáo viên và ĐGNL ĐHSP HN | Không đạt | Không đạt | Mở đầu đúng một số ngành dùng PT4 nhưng bảng biến điểm sàn 20 thành 20 chỉ tiêu. |
| Q09 Tiếng Anh nhân hai? | Không đạt | Không đạt | Chỉ kiểm tra bảng điểm sàn rồi từ chối, bỏ văn xuôi có đáp án không nhân hai. |
| Q10 Nguyên tắc quy đổi ĐGNL | Không đạt | Không đạt | Baseline trộn điều kiện ngưỡng đầu vào/thang điểm và điều kiện ưu tiên; preset bị numeric guard chặn. |
| Q11 Ưu tiên KV1 | Không đạt | Không đạt | Đã retrieve đoạn liên quan nhưng numeric guard chặn; trả mẫu “chưa có thông tin” không đúng tình trạng dữ liệu. |
| Q12 Phí thi năng khiếu | Không đạt | Một phần | Cả hai đúng số tiền; baseline gán hạn phí xét tuyển cho phí thi năng khiếu; preset phân biệt loại nhưng thêm lịch không được hỏi. |
| Q13 Lịch đăng ký năng khiếu | Một phần | Đạt | Đúng ngày; baseline thêm yêu cầu nộp cùng phí xét tuyển chưa có căn cứ. Preset vẫn dài. |
| Q14 Tổ hợp Sư phạm Toán | Một phần | Một phần | Có bốn tổ hợp nhưng nguồn có Tin/Tín; giữ cảnh báo hợp lý, chưa tách gọn phần chắc chắn/bất định, lặp nhiều ghi chú. |
| Q15 Liệt kê Toán–Lý–Hóa 2026 | Không đạt | Không đạt | Từ chối do xác minh scope; năm đã nêu vẫn yêu cầu chỉ rõ năm. Có bảng trong nguồn. |
| Q16 “Sao nhiều thế?” sau Q15 | Lỗi | Lỗi | `CONVERSATION_SCOPE_INVALID`; Q15 trước đó không sinh danh sách nên chưa đo happy path giải thích danh sách thành công. |
| Q17 Điểm chuẩn Toán/CNTT gần nhất | Không đạt | Không đạt | Audit hàng bác kết quả; TSĐH cập nhật có bảng năm 2024/2025, không phải thiếu dữ liệu. |
| Q18 So sánh 2025/2026 | Không đạt | Không đạt | Gán học bạ ba năm cho 2025 trong khi thông báo năm đó ghi lớp 12; thêm sai số phương thức/nhóm ngành hoặc tự mâu thuẫn PT4. |
| Q19 Chỉ tiêu 2027 | Đạt | Đạt | Chưa có chỉ tiêu tuyển sinh 2027 được xác nhận trong snapshot; không mượn số năm học 2026–2027. |
| Q20 Tính điểm từ ĐGNL | Đạt | Đạt | Từ chối an toàn vì chưa có rule active; không khẳng định tính được kết quả. |

## Bằng chứng và nguyên nhân đã phân biệt

1. **Typed route trả về trước khi tìm đoạn văn**: Q03 có decision
   `NO_COMPATIBLE_FACT_EVIDENCE`, không chạy hybrid. Q09 đi qua chọn ô của bảng
   và `ROW_SELECTION_MISSING`; bảng sàn không chứa hệ số môn không đồng nghĩa cả
   kho không có câu trả lời. Đoạn văn nguồn `ks_rev_8f3c2063c14e` có nội dung cần.
   Điểm can thiệp: `rag/service.py`, `temporal_answer.py`, `row_answer.py`; cần
   fallback theo đúng scope và đúng loại câu hỏi, không bỏ guard sai năm.
2. **Chặn số rồi thay bằng mẫu thiếu dữ liệu**: log ghi Q10 preset
   `ungrounded=['402']`, Q11 hai profile `ungrounded=['000']`.
   `service.py` thay đáp án và xóa citations sau numeric gate; vì không lưu nội dung
   trước gate nên chưa kết luận hai chuỗi này là số đúng bị parse sai hay số LLM
   tự thêm. Đã đủ căn cứ nói đây là gate failure, không phải kho thiếu dữ liệu.
   Cần trace nguyên nhân và chuẩn hóa số theo ngữ nghĩa; không nới allowlist để qua test.
3. **Đúng con số nhưng sai nghĩa**: Q08 fact có attr “Phương thức xét điểm thi
   ĐGNL ĐHSP HN” =20 từ bảng ngưỡng đầu vào; LLM biến thành chỉ tiêu. Q12 baseline
   biến lịch phí xét tuyển thành hạn phí thi năng khiếu. Các gate kiểm tra số xuất
   hiện trong nguồn vẫn không bảo vệ được loại chỉ số/đối tượng/đợt.
4. **Năm/loại bảng phải theo từng claim**: Q18 dùng học bạ ba năm cho 2025.
   `ks_rev_61ed5ddbe2bd` ghi lớp 12, còn thuyết minh 2026 ghi ba năm. Nghị quyết
   phương hướng có cách đánh số PT khác thông báo sau; phải nêu phiên bản/nguồn,
   không trộn số hiệu từ nhiều văn bản thành một bảng chắc chắn.
5. **Liệt kê và hỏi tiếp bị chặn scope**: Q15 `ENUMERATION_SCOPE_UNVERIFIED`;
   Q16 exception từ `conversation_acts.resolve_act_scopes` khi
   `validated_scopes` bác plan. Không có bằng chứng lỗi do conversation_id giả hay
   thiếu bản ghi history trong DB: đường exception này kiểm chứng source/year proof.
   Tuy nhiên runner chưa ghi plan bị bác/inner ValueError nên chưa xác định chính
   xác điều kiện bác nào. Không bỏ kiểm chứng scope để ép sinh danh sách.
6. **Có bảng lịch sử nhưng audit không nhận**: Q17 `ROW_AUDIT_REJECTED`.
   `ks_rev_ee85a12d415e`, mục 11, có header 2024/2025 với cột chỉ tiêu, nhập học và
   điểm trúng tuyển riêng; hai hàng 7140209 và 7480201 đủ làm căn cứ tra cứu lịch sử.
   Không lấy năm 2026 của văn bản gán cho mọi cột, không nhầm chỉ tiêu với điểm.
7. **Bất định nguồn thật không được xóa**: Q14 “Tin” so với “Tín” ở hai nguồn.
   Báo mâu thuẫn là hành vi an toàn; cần trình bày phần cùng được chứng minh trước,
   phần cần duyệt riêng, không sửa OCR âm thầm hoặc gán mọi trường hợp là RAG sai.
8. **Công cụ tính điểm chưa được kích hoạt**: kiểm tra readonly DB hiện tại cho
   `registry_present=false`, `active_count=0`; Q20 trả
   `NO_VERIFIED_CONVERSION_RULE` đúng. Không coi thiếu rule là thiếu PDF,
   không tự import/duyệt/kích hoạt trong đợt chấm.

Các đoạn chứng minh độc lập có source revision/hash và offset trong sidecar
`review.json`; không chép toàn bộ corpus hoặc prompt nội bộ vào nhật ký/Git.

## Quan sát Top K, trích dẫn và thời gian

| Chỉ số | Hiện tại | Preset |
| --- | ---: | ---: |
| Đủ record, không trùng cặp ID/profile | 20/20 | 20/20 |
| Trạng thái runtime answered | 11 | 10 |
| insufficient_context | 8 | 9 |
| Exception | 1 | 1 |
| Lượt có chạy hybrid retrieval | 12 | 12 |
| Trích dẫn trả về, đếm theo occurrence | 59 | 54 |
| Resolve đúng binding/index/source đang active | 59/59 | 54/54 |
| Quote khớp liên tiếp sau chuẩn hóa whitespace | 33/59 | 32/54 |
| p50 toàn attempt | 5,949 giây | 6,112 giây |
| p95 nearest-rank toàn attempt | 15,564 giây | 15,534 giây |

Những quote không khớp liên tiếp có thể do prefix heading/marker trang; không tự
gán là bịa trích dẫn. Resolve ID đúng cũng **không chứng minh claim đúng hoặc đầy đủ**.
Chưa làm nhãn relevance exhaustive/claim-level precision hay nDCG/Recall vàng.

Hai profile đều rerank về 5 context chính; hàng/neighbor/fact còn có ngữ cảnh bổ
sung nên context_top_k không phải giới hạn cứng mọi nguồn hay mọi hàng. Nhiều
nhánh trả lời trước hybrid nên tăng K không tác động. Các context_characters quan
sát ở hybrid tối đa 3.761/4.217, thấp hơn ngân sách 36.000 ký tự của preset;
completion lớn nhất ghi nhận 924/859 token. Không có bằng chứng các lỗi đã xác
định ở trên do max_tokens=5000, và max_tokens cũng không phải context window model.
Không suy ra mọi trường hợp dài đều đã được kiểm chứng không truncate.

## Artifacts, lệnh thật và kiểm chứng

Runtime artifacts ở `backend/storage/quality_490/`:

- `run_quality.py`: runner gọi thật, chặn external, freeze state và đổi profile trong RAM.
- `results.json`: 40 records thô, model calls, trace, final unchanged và timestamp.
- `source_snapshot.json`: canonical inventory nội bộ, **không đưa vào commit**.
- `run.log`: tiến độ + numeric gate warnings, không lưu prompt/bí mật.
- `review_quality.py` / `review.json`: nhãn review, source anchors, rubric và thống kê tái tính được.

Lệnh sinh đáp án (cwd `backend`, môi trường được phép kết nối nội bộ):
`./.venv/Scripts/python.exe -X utf8 -m storage.quality_490.run_quality` → exit0,
**40/40 attempts**, nhưng **2 exception runtime**, không gọi 40 câu đều PASS.
Không chạy lại các câu lỗi. Model trace: 50 generate thành công, internal-only.

Lệnh đọc registry qua SQLAlchemy trong transaction readonly → exit0, không registry,
0 active. Lệnh chấm offline (cwd repo):
`backend/.venv/Scripts/python.exe -X utf8 backend/storage/quality_490/review_quality.py`
→ exit0, đủ 40 nhãn và các source span kiểm tra tồn tại.
Lần đầu reviewer helper dừng vì marker khác hoa/thường; đã sửa marker theo byte nguồn,
không sửa dữ liệu nguồn, không chạy lại model.

Kiểm tra cuối: `py_compile` hai runner/reviewer exit0; validator offline xác nhận
40raw=40nhãn, không thiếu/trùng cặp, SHA-256 khớp, 17source anchors tồn tại;
UTF-8 không BOM và link490 hợp lệ; hai tài liệu mới dùng LF.
`git diff --check -- docs/nhat_ky/README.md docs/WORK_LOG.md docs/memory/PROJECT_CONTEXT.md`
exit0 (Git cảnh báo autocrlf khi chạm file sau này, không có lỗi whitespace).

- **PASS**: completeness/dedup records, nguồn/config unchanged, internal-only observed calls,
  recompute thống kê và anchors, kiểm tra tài liệu ở cuối phiên.
- **FAIL**: acceptance chất lượng; có câu sai/từ chối sai và exception như bảng.
- **NOT RUN**: HTTP/SSE/UI, happy path Q16 sau một danh sách thành công, 82 câu,
  full Pytest/FE build (không sửa ứng dụng), kiểm chứng ảnh PDF toàn corpus.
- Lỗi nền 11 test phiên489 là **lịch sử**, chưa chạy lại; không dùng nó để giải thích
  hoặc bỏ qua 2 lỗi runtime của lượt đánh giá này.

## Bước tiếp theo đề nghị

1. Sửa routing bảng/fact so với prose và thông báo numeric gate; giữ phân biệt
   không truy hồi được, evidence chưa đủ và hạ tầng lỗi. Tái hiện Q03/Q09/Q11/Q17.
2. Ràng buộc claim với metric/unit/year/source thực, đặc biệt Q08/Q12/Q18; không
   đẩy toàn bộ fact cùng thực thể lên LLM như các số đã xác minh đúng câu hỏi.
3. Ghi rõ scope rejection rồi sửa Q15/Q16; rút gọn câu trả lời và tách OCR conflict
   khỏi phần chắc chắn. Sau batch mới test trọng tâm và chấm lại cùng 20 câu;
   chưa cần chạy full82 hoặc thêm một thuật toán mới trước các lỗi gốc này.

Không tự kích hoạt preset/rule, không sửa nguồn/reindex/restart/commit/push/deploy.
