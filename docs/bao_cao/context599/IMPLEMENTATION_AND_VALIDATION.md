# Context599 — Sửa phục hồi P06 và đối chiếu điều kiện X09

Ngày 22/10/2026. Tiếp kết quả phân tích Context598. Phạm vi: RAG trên cùng PDF,
canonical, revision/index staging và cấu hình ModelOps. Không sửa parser, nguồn,
embeddings, publication hoặc các thay đổi ngoài phạm vi đang có của người dùng.

## Phương pháp

- Tách phần câu hỏi còn thiếu khỏi điều kiện nguồn còn thiếu. Vòng phục hồi vẫn
  tối đa hai lượt; sau bổ sung điều kiện, được chọn lại bằng chứng cho ý trả lời
  chưa đủ. Dùng feedback hiện hành, giữ claim đã qua kiểm chứng và kiểm lại toàn bộ.
  Dừng khi hoàn tất, mâu thuẫn, không tiến triển, hết ngân sách hoặc không còn gap
  có thể xử lý; không tự chấp nhận verdict chưa được kiểm chứng.
- Hướng dẫn whole-answer audit phân biệt cấu trúc hàng/ô/header do server gắn với
  kiểm tra ý nghĩa và phạm vi. Nội dung phủ định trong đúng ô có thể trực tiếp trả
  lời câu hỏi; nhãn cột không tạo thêm một yêu cầu ngoài câu hỏi. Vẫn kiểm đối tượng,
  điều kiện, năm, phủ định và ngoại lệ; không thêm từ điển từ khóa.
- Khi source-only review đề xuất một điều kiện mới mà indexed audit chưa xác nhận
  là bắt buộc, đối chiếu độc lập tính cần thiết cho đúng nhánh trước khi ghi nghĩa
  vụ. Không đưa bản nháp hoặc verdict trước vào bước này. Chưa giải được thì báo
  lỗi kiểm chứng, không giả thiếu nguồn. Nghĩa vụ đã xác nhận vẫn bất biến.
- Giữ nguyên numeric gate: số trong câu hỏi không thành fact nguồn. Nhánh thiếu
  đầu vào có thể trả lời bằng rule nguồn, không gán biến thiếu bằng 0 hoặc tính Q.

## Phạm vi mã

| File trong `backend/app/modules/rag/` | Thay đổi của599 |
|---|---|
| `prose_fallback.py` | Theo dõi facet/gap và lý do dừng; feedback hiện hành; giới hạn hai vòng giữ nguyên. |
| `evidence_indexed_audit.py` | Làm rõ kiểm nội dung ô so với vai trò nhãn cột; không tự duyệt. |
| `source_dependency_review.py` | Tái sử dụng payload source-only hiện có. |
| `source_dependency_agreement.py` | Đối chiếu điều kiện mới đang bất đồng, ID/phạm vi và cache/ngân sách. |
| `evidence_verification.py` | Đối chiếu trước khi ghi nghĩa vụ mới; giữ nghĩa vụ cũ. |

Regression ở `test_recovery_facets_599.py`, `test_dependency_agreement_599.py`;
adapter test597 được cập nhật cho hợp đồng mới, giữ assertion tiền đề cũ.
Đây không phải triển khai các ưu tiên wiki4–6.

## Môi trường kiểm thử

Kiểm tra DB, MinIO, Qdrant đều loopback trong môi trường development trước chạy.
Pytest dùng DB riêng có tên/nonce sở hữu và local Storage riêng. Endpoint ngoài
test trỏ `127.0.0.1:1`, tắt auto migration/seed; không migration DB dùng chung.
Chỉ sao chép một bản metadata defaults vào DB test cho handler cũ đã mock inference;
không sao chép credentials/provider rows hoặc cho test inference thật.

Live probe qua `rag_service.ask` với actor đã xác thực và candidate snapshot do
server xác minh. Giữ Luna chính, Qwen dự phòng trong DB; trong phép đo chỉ cho Luna
nhằm so sánh với597. Gọi tuần tự, không chạy synthetic ModelOps đồng thời. Chỉ lease
và usage audit của ModelOps được ghi; không tạo chat, gap, source/index hoặc publish.
Đây là candidate service integration, **không phải HTTP/browser E2E đã xuất bản**.

## Kết quả trung gian được bảo toàn

- Baseline mã trước599: 8 FAIL ở bộ ban đầu, gồm2 assertion tái hiện mất facet,
  1 lỗi fixture lexical và5 ImportError do API đối chiếu mới chưa có. Không coi5
  lỗi import là5 lỗi hành vi X09; đã sửa fixture cho đúng điều kiện cần kiểm.
- Lượt đầu: 44 PASS/1 FAIL fixture; sau sửa fixture: 48 PASS.
- Bộ mở rộng đầu: 776 PASS/2 FAIL ở negative tests575. Không sửa assertion575;
  bổ sung dừng khi verdict chưa đạt nhưng không còn gap có thể xử lý.
- Bộ mở rộng tiếp: **778 PASS**, exit0. Ruff 8 file exit0.
- Live `probe-fixed` phát hiện P06 `SOURCE_DEPENDENCY_AGREEMENT_INVALID`;
  đây là lỗi thật, không tính PASS hoặc từ chối đúng. Trace đầu chưa lưu quyết định
  bị từ chối nên chưa chốt được trường cụ thể gây lỗi. Giữ nguyên artifact lượt này.
- Full trước chỉnh hợp đồng: **3288 PASS/18 FAIL/17 SKIP, 23 subtest PASS**, exit1;
  exact IDs/nguyên nhân của18 FAIL khớp597, không thiếu test hoặc FAIL mới.
  Sau khi live phát hiện lỗi, có thay đổi mới nên chạy lại full ở mã chốt.
- Hợp đồng đối chiếu được đơn giản hóa: `clause_id` liên kết trực tiếp một lần với
  `evidence_ids` hợp lệ, thay cho khai báo lặp qua cả `governs` và `basis_ids`.
  ID clause/target ngoài catalog, target rỗng/trùng, revision sai, quan hệ không
  nhất quán và unresolved vẫn bị chặn. Quyết định và mã lỗi chỉ gồm ID được lưu
  trong trace trước khi kiểm tính nhất quán; ngân sách một lượt được tính cả khi lỗi.
- Bộ chốt **780 PASS**, exit0; bộ contract riêng119 PASS; Ruff8 file PASS.
  Tổng **15 test case mới** so597, gồm giữ/mất facet, vòng không tiến triển,
  điều kiện bắt buộc/không bắt buộc/chưa rõ, cache/budget, sai revision/ID/proof,
  không xóa nghĩa vụ cũ và kiểm integration tại `verify_bound_answer`.

Test119/780 chạy trước thay đổi chỉ xuống dòng import để đạt Ruff; full mã chốt
và live chốt chạy sau formatting. Freeze live có amendment trước gửi, chỉ đổi hash
file test ấy; không đổi app, question, rubric, nguồn hoặc cấu hình. Không phát lại
run-intent của lượt cũ.

## Giới hạn và ngân sách

- Tối đa hai source-only review hiện có **cộng thêm tối đa một** đối chiếu điều kiện
  mới đang bất đồng; cache nội dung/phạm vi. Đây có thể tăng chi phí/latency ở ca
  cần đối chiếu; không tuyên bố tốc độ nhanh hơn. Hai vòng phục hồi không tăng.
- Liên kết ID và same-source là kiểm cấu trúc; tính cần thiết của quan hệ vẫn do
  LLM đánh giá. Không có bảo đảm mọi false positive/negative đều bị loại bỏ.
- Không sửa whitelist số hoặc triển khai đầy đủ typed user-assumption arithmetic.
  Ca thiếu input trả lời bằng rule nguồn; không tạo một Q chính xác.
- Không chạy lại64 trong phiên này. Nhóm6 không được ghép vào lượt597 để tuyên bố
  60/60. Điểm58/60 của597 giữ nhãn lịch sử; chưa đo điểm64 của mã599.
- Không thay đổi frontend, không chạy lại FE build. Không HTTP/browser E2E qua
  chatbot đã xuất bản, không chứng minh production readiness bằng candidate probe.

## Finding từ lượt kiểm soát và sửa bổ sung

Lượt `probe-final` ở mã hợp đồng đơn giản: **4/6**, P06/P07/P10/X09 đạt;
P12/P16 FAIL. Cả22 citation được trả đều đúng tọa độ,57 Luna usage/0fallback.
Không đổi nhãn hoặc lấy P12/P16 từ lượt trước để ghép thành6/6.

- P12 đã giữ ba chú giải nhưng audit vẫn đòi chúng. Round tiếp chỉ chép qualifier,
  rồi vẫn thiếu. Đổi hướng xử lý chung: sau bổ sung điều kiện một lần, nếu chỉ còn
  qualifier chưa đạt thì chọn lại nguồn với feedback mới, giữ claim an toàn và
  kiểm lại. Không loại một missing constraint để tự cho PASS.
- P16 first review đề xuất điều kiện mới, đối chiếu và bổ sung được; lượt sau lại
  đề xuất một clause khác cho cùng target cũ. Cache toàn payload trước đó không
  dùng lại được vì có thêm claim; một lượt đối chiếu đã hết nên báo CONFLICT.
  Sửa proof theo từng clause/câu hỏi/plan/nguồn và target nguyên văn. Một lượt xem
  các clause ứng viên hiện có, nhưng chỉ áp dụng verdict cho các đề xuất đang bất
  đồng. Proof đã xét chỉ được dùng lại cho target cũ trùng text/span/source; không
  dùng cho target/revision mới. Vẫn một lượt đối chiếu, không xóa nghĩa vụ cũ.

Sau sửa bổ sung: bộ contract123 PASS, focused **784 PASS**, Ruff8file PASS;
tổng **19 test case mới** so597. Thêm ca target không đổi sau bổ sung claim được
dùng lại proof, target đổi bị chặn và qualifier còn thiếu cần chọn lại nguồn.

Full trước bổ sung:3290 PASS/18 FAIL/17 SKIP,23subtest PASS,exit1;18ID/cause khớp597.
Full và probe mã bàn giao được ghi riêng bên dưới. Chưa công bố nghiệm thu toànRAG.

## Probe mã bàn giao

`probe-handoff`: **6/6 PASS**, không lỗi service; **39/39 citation** đúng nguồn,
revision/index/hash và nguyên văn span. 40 usage records đều Luna, thành công,
0fallback. Không gọi judge LLM. Chấm từng actual response theo criteria đã freeze,
lưu hash response và đối chiếu canonical; không dùng câu trả lời mong đợi để tạo
câu trả lời thật. Kết quả giữa các lượt không được ghép.

| ID | Kết quả theo nguồn | Thời gian service |
|---|---|---:|
| P06 | Đủ đối tượng/năm, thời hạn, điều kiện và ngoại lệ; không đổi chỉ tiêu/nhóm. | 72,26s |
| P07 | Giữ đủ tiền đề của phương thức thay chữ ký, thời hạn và kiểm tra an toàn. | 62,80s |
| P10 | Phân biệt ký hiệu chưa đo, số0 có chứng cứ và ký hiệu chưa định nghĩa. | 26,23s |
| P12 | Đủ công thức, chú giải biến và điều kiện được tính. | 33,46s |
| P16 | Thiếu input/chứng cứ thì chưa đủ điều kiện; không gán0 hoặc kết luận mức. | 54,30s |
| X09 | ThiếuA thì không xác địnhQ; rule nguồn giữ đủ mọi biến, không gán thiếu=0. | 32,24s |

Đây là latency toàn service với nhiều lượt model, không phải timeout mỗi lượt
inference; cấu hình provider vẫn30s. Không suy ra chất lượng100% từ6 câu.
Các trường hợp này đã được dùng để sửa lỗi, không phải tập holdout độc lập.

Postcheck exit0: bytes/hash PDF, canonical, revision/index, config, code và vector
payload seals giữ nguyên;2943points,0retrievable, không active index/publication.
Không tạo thread/message/gap kiểm thử. Giữ usage audit và toàn bộ evidence riêng.

| Artifact | Mục đích |
|---|---|
| [Baseline/first run](../../../backend/storage/context599/checks/baseline-run.json) | Mã trước sửa và exitcode của bộ tái hiện ban đầu. |
| [Focused chốt](../../../backend/storage/context599/checks/focused-proof-final-run.json) | 784 PASS, đúng DB/Storage riêng và lệnh thật. |
| [Ruff](../../../backend/storage/context599/checks/ruff-proof-final.json) | 8 file, exit0. |
| [Probe5/6](../../../backend/storage/context599/probe-fixed/summary.json) | Lỗi hợp đồng ban đầu được giữ. |
| [Probe4/6](../../../backend/storage/context599/probe-final/summary.json) | P12/P16 FAIL trung gian, không ghép điểm. |
| [Probe6/6](../../../backend/storage/context599/probe-handoff/summary.json) | Kết quả mã bàn giao và chấm từng ID. |
| [Postcheck](../../../backend/storage/context599/probe-handoff/postcheck.json) | Bảo toàn nguồn/config/index/publication và không ghi dữ liệu chatbot. |

Các artifact kiểm thử nằm trong Storage local được ignore, không đưa corpus,
profile riêng, prompt hoặc credentials vào Git.

## Full gate và dọn dữ liệu kiểm thử

Kiểm bổ sung hồi cứu trên app trước599 đã seal/import đúng đường dẫn: test
`test_verification_latches_only_reconciled_new_conditions[False]` FAIL đúng vì
điều kiện thừa vẫn bị ghi và chặn câu trả lời; ca `[True]` PASS giữ tiền đề thật.
Mã mới cả hai PASS trong focused/full. Đây là replay baseline thực hiện sau sửa
trên bản code trước sửa, không giả thời điểm chạy trước implementation.
[Receipt baseline hành vi](../../../backend/storage/context599/checks/baseline-branch-behavior-run.json).
0 model/DB/external network; một version probe bị guard chặn, hai self-pipe của
Windows asyncio được phép tạo. Hai thử nghiệm helper trước đó không dùng nghiệm
thu baseline: một chặn nhầm self-pipe, một chưa seal app import trước Pytest.

Full mã bàn giao: **3294 PASS/18 FAIL/17 SKIP,23 subtest PASS**, exit1,508,41s.
Toàn suite vẫn **FAIL**. So với full597 theo exact ID và failure message:
0 FAIL mới,0 lỗi được giải quyết ngoài phạm vi,0 thay đổi nguyên nhân,0 test mất;
19 case thêm đều PASS. Không đổi assertion cũ để che lỗi nền.

- [Lệnh/cwd/exitcode full](../../../backend/storage/context599/checks/full-handoff-run.json).
- [JUnit từng test](../../../backend/storage/context599/checks/full-handoff.xml),
  [log full](../../../backend/storage/context599/checks/full-handoff.log).
- [Đối chiếu toàn bộ ID/nguyên nhân với597](../../../backend/storage/context599/checks/full-handoff-comparison.json).
- [Seal code không đổi trong full](../../../backend/storage/context599/checks/full-handoff-code-after.json).

Lệnh thực thi do harness ghi trong receipt: Python venv của repo, `-m pytest -q`
tại `backend`, thêm basetemp và JUnit thuộc runtime599; focused dùng28 file trong
receipt tương ứng. Ruff dùng `-m ruff check` trên8 file được liệt kê. Các runner
preflight/prepare/run/postcheck và scorer đều nằm `.antigravity-bridge/validation/`
với tiền tố `context599_probe_handoff_`; preflight/prepare/run/postcheck/score exit0.
Không phát lại runner có run-intent; score chỉ đọc artifact, không gọi model.

Đã dọn đúng DB `qnu_test_context599_6e8406555a61`, exit0, sau xác minh tên/nonce
sở hữu và kiểm lại DB không tồn tại. Không xóa DB ứng dụng. Không tạo chat/message/
gap để phải xóa; usage audit giữ nguyên. Storage runtime và evidence vẫn giữ dưới
`backend/storage/context599-runtime-6e8406555a61` và `backend/storage/context599/`.
Chính sách bảo vệ đã chặn thao tác xóa Storage đệ quy ở phiên trước; không thử lại
bằng công cụ khác, không tắt policy hoặc coi Storage đã được dọn.
[Trạng thái isolation/cleanup](../../../backend/storage/context599/checks/isolation.json).

Phần sửa được kiểm chứng cho P06/X09 và nhóm kiểm soát6 câu. Giữ nguyên nguồn,
model, Quality Gate và mọi dữ liệu staging/publication; không parser/reindex/
restart/publish/commit/push. Full64 và published HTTP/browser E2E **NOT RUN**;
58/60 của597 vẫn là lịch sử, không đổi thành60/60 của599.
