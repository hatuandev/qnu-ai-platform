# Context602 — Kiểm chứng đợt 1 và 2

Ngày 22/10/2026. Đã triển khai sửa nền và hợp đồng proposal cho lớp biên soạn
tri thức. **Chưa nghiệm thu khả năng tổng hợp nhiều nguồn**: bộ 64 câu đạt mục
tiêu 85%, nhưng bộ nhiều năm chỉ đạt 6/12 và full Pytest còn 18 lỗi nền.

## 1. Phạm vi thay đổi và môi trường

Phạm vi ứng dụng gồm 16 file so với snapshot đầu602, không dùng Git HEAD để
ghi đè các thay đổi600/601 đang có. Bốn file test mới gồm 51 ca; fixture
integration600 chỉ bổ sung DB test602 có kiểm sở hữu. Không sửa frontend.
Chi tiết phương pháp: [IMPLEMENTATION_REPORT.md](./IMPLEMENTATION_REPORT.md).

Trước regression đã xác minh DB phát triển, MinIO và Qdrant ở loopback; tạo DB
riêng `qnu_test_context602_b842423bcce8` có ownership nonce và Storage riêng
`backend/storage/context602-runtime-b842423bcce8`. Pytest dùng network guard,
chỉ mở kết nối DB sở hữu, thay endpoint dịch vụ bằng `127.0.0.1:1`, không auto
migrate/seed. Một row defaults không hoạt động được sao chép vào DB test phục vụ
contract cũ: 0 credential và 0 provider row. Không migration DB ứng dụng.

Inference thật được chạy riêng sau pytest, qua ModelOps hiện hữu và actor đã
kiểm quyền. Hai bộ live chạy tuần tự, không chạy đồng thời với inference giả.
Giữ primary Luna, model fallback cấu hình sẵn, timeout provider30s và ngân sách
evidence90s; phạm vi thí nghiệm chỉ cho Luna, không ép đổi cấu hình fallback.
Số lần fallback thực tế bằng0.

## 2. Regression và lệnh đã thực chạy

Các lệnh dưới đây chạy từ root bằng Python `.venv` đã cài; helper đặt cwd pytest
thành `backend`, DB/Storage/network guard và ghi đầy đủ argv/exit code. Không cài
thêm dependency. `<focused tests>` là danh sách 37 module ghi trong receipt
`focused-obligation-final-run.json`, không phải full suite.

```powershell
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py setup
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py run --baseline --label baseline-full
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py run --label focused-obligation-final <focused tests>
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py run --label full-closure
```

Ruff thực chạy bằng `backend/.venv/Scripts/python.exe -m ruff check` trên đúng
16 file ứng dụng và 5 file test sửa; argv scope nằm trong `ruff-final-run.json`.

| Kiểm tra | Kết quả | Exit | Kết luận |
|---|---|---:|---|
| Baseline full trước sửa app | 3362 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 | FAIL |
| Focused cuối | 889 PASS, 1 warning | 0 | PASS |
| Full cuối | 3413 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 | FAIL |
| 51 regression mới | 51 PASS trong full cuối | 0 theo focused | PASS |
| Ruff 21 file | Không finding | 0 | PASS |
| Frontend lint/typecheck/build/browser | Không chạy; không sửa FE trong602 | — | NOT RUN |

Đối chiếu exact test IDs: 0 lỗi mới, 0 ID cũ mất, 0 đổi failure message của18 lỗi
nền. Lỗi nền gồm fixture schema thiếu `alembic_version`, dữ liệu seed cũ thiếu,
dịch vụ bị network guard chặn, contract auth cũ và assertion payload legacy.
Không sửa các lỗi này ngoài phạm vi và không gọi full suite là PASS. Lỗi backup
Windows từng thấy ở601 không tái hiện trong baseline602; không tuyên bố đã sửa.

Đã chạy tái hiện trước sửa trên snapshot app: foundation9 FAIL/6 PASS,
recovery3 FAIL/1 PASS; bug reselection cuối có2 FAIL tại đúng assertion mất
điều kiện. Các fixture sai ban đầu được giữ riêng, không dùng làm bằng chứng lỗi
ứng dụng. Chi tiết từng ID: [TEST_ID_COMPARISON.md](./TEST_ID_COMPARISON.md).

Có lượt full trung gian3407/18/17 trước khi sửa reselection cuối. Chạy lại full
vì app có thay đổi mới; không lặp full chỉ để tìm kết quả xanh. Sau full cuối,
không sửa app/test khi chạy live64 và nhiều nguồn.

## 3. DOCX thật và bảo toàn nguồn

Ba nguồn2024/2025/2026 được đọc từ file thật, lưu bản raw trong LocalStorage
thử nghiệm, chạy Docling → structured model → native layout → canonical
Markdown theo chuẩn hiện có → format validator và manifest. Không tạo revision
hoặc index trong kho vận hành.

| Nguồn | Trước: units/chars | Sau: units/chars | Native paragraph được khôi phục | Table/table-row giữ nguyên |
|---|---:|---:|---:|---:|
| S1: phương hướng2024 | 208 /11287 | 196 /11279 | 3, giữ15 raw fragments | 126 |
| S2: báo cáo2025, dự thảo | 149 /12184 | 142 /12178 | 2, giữ9 raw fragments | 85 |
| S3: thuyết minh2026 | 56 /18370 | 56 /18370 | 0 | 0 |

Ba format validator PASS; hash raw trước/sau không đổi. Đối chiếu độc lập xác
minh text/hash của5 paragraph khớp OOXML,189/133/56 body không merge giữ nguyên;
0 body đổi không giải thích được. Full table body/attributes/source_data khớp.
Giảm số unit là nối lại paragraph nguồn, không bỏ fragment ngắn.

Giới hạn: chưa render Office/PDF preview; cảnh báo DrawingML converter chưa có.
Format validator và phép so sánh này không chứng minh toàn bộ hình/layout hay
full Quality Gate đạt. S2 vẫn là dự thảo, S3 là bản thuyết minh biên tập; không
tự chứng nhận cả hai là chính sách chính thức.

Cẩm nang dài: compiler thật xử lý canonical hiện có với selector xác định,
1301/1301 inventory sections trên3 trang, tối đa512/trang;19 packet calls,
0 LLM thật. PASS về coverage/phân trang, không phải ingestion E2E hoặc chất
lượng generation của model thật.

## 4. Frozen64 với nguồn PDF và model giữ nguyên

Lượt cuối riêng `acceptance-closure`, hoàn thành64/64; không retry P10 hoặc ghép
điểm giữa các lượt. Binding `bnd_12190866d5ec`, source revision12
`ks_rev_993a7ad91b32`, index `idx_rev_6bf0d6f86b1b` vẫn staging. Nguồn PDF/raw,
canonical, gold/fact IDs, profile, snapshot và vector payload đều ghim hash.
Đây là `rag_service.ask` candidate đã xác thực, có vector/ModelOps thật;
**không phải HTTP/browser E2E của assistant đã xuất bản**.

| Chỉ tiêu | Context601 lịch sử | Context602 cuối |
|---|---:|---:|
| Tri thức | 57/60,95% | **59/60,98,33%** |
| Câu có đáp án | 47/50 | 49/50 |
| Câu âm tính | 10/10 | 10/10 |
| Giao tiếp | 4/4 | 4/4 |
| FAIL | P07,P08,P16 | P10 |
| Citation resolve chính xác | 128/128 | 140/140 |
| Lỗi runtime | 0 | 0 |

P06/P07/P08/P16 hiện PASS. Gains so601: P07/P08/P16; loss mới: P10. So sánh cùng
question/rubric/source/model, nhưng không phải causal ablation và model vẫn có
dao động. Lượt trung gian602 `acceptance-release` đạt58/60, FAIL P06/P08, được
lưu riêng để truy nguyên sửa reselection; không trộn vào điểm cuối.

P10: source có đủ dữ liệu. Audit bắt một chú thích làm điều kiện cho phép so
sánh; verifier loại chú thích đó vì không liên quan câu hỏi, obligation ledger
tiếp tục chặn. Đây là bất đồng về applicability, chưa có bằng chứng mất dữ liệu
hoặc thiếu context model. Không bỏ guard hoặc xoá obligation để ép PASS.

Lượt cuối ghi147 usage success của `gpt-6-luna`,0 fallback;1.111.748 input và
38.534 output tokens. p95 tri thức55.121,24ms; tối đa82.595,36ms. Giá tiền chưa
tổng hợp vì không dùng đơn giá giả định. Chấm rubric offline, không gọi judgeLLM.

**Giới hạn context cần xử lý sau:** P13 có audit prompt76.323 tokens quan sát
trong usage, vượt32K. Điều này không chứng minh cấu hình Qwen32K sẽ chạy được
luồng tương tự và cũng không phải nguyên nhân đã chứng minh của P10. Cần budget
toàn payload serialized cùng trace trước khi hỗ trợ model cửa sổ nhỏ hơn; chưa
đổi model, budget hoặc timeout trong602.

Rubric là draft do Codex đối chiếu nguồn, chưa phải human holdout. Chưa đo
Hit@K/Recall@K/MRR hay làm dense/hybrid/rerank ablation. Đạt85% trên bộ này không
đồng nghĩa toàn bộ RAG hoặc tác vụ nhiều nguồn đã được nghiệm thu.

## 5. Thử nhiều nguồn và hợp đồng đợt 2

Bộ12 dùng nguyên question/rubric/raw source/model của601, canonical S1/S2 đã
đổi ranh giới theo native paragraph. ModelOps thật, nhưng source/snapshot đọc
qua adapter local, BM25 anchor, không reviewed facts và không vector retrieval.
Không gọi đây là upload/index/HTTP E2E.

Kết quả **6/12 PASS,6 FAIL** so4/12 trước;23/23 citation resolve chính xác.
Ba source wiki đều ready:14 trang,7 compiler calls. QA127 usage success,
758.829 input/32.069 output; compiler32.682 input/3.832 output;0 fallback.
Hai request vẫn `EVIDENCE_TIMEOUT` dù usage đã ghi thành công các call trước
đó. Lệnh runner exit0 chỉ chứng minh hoàn tất12 request, quality vẫn FAIL.

Chi tiết từng ID và hướng xử lý: [MULTI_SOURCE_EVALUATION.md](./MULTI_SOURCE_EVALUATION.md).

Đợt2 có schema/hàm binding thuần,21 test contract PASS, [JSON Schema](./COMPILATION_SCHEMA.json)
khớp schema sinh từ mã. Binding kiểm revision/hash/proof và trả `review_only`,
không xác nhận entailment hoặc quyền phục vụ. Chưa triển khai compiler tổng hợp,
endpoint/persistence/concurrency/revocation mới; các phần đó chỉ là
[thiết kế đợt sau](./COMPILATION_DESIGN.md), không được ghi là E2E PASS.

## 6. Kiểm tra cuối và dọn dữ liệu thử

Sau cả hai bộ live: raw source, các revision/index cũ, cấu hình assistant/model,
code và inventory ngoài ca thử khớp trước chạy. Scroll lại toàn namespace:
2943 point giữ nguyên hash payload,0 retrievable; không publication.0 thread,
0 message và0 knowledge gap test còn lại. Usage/audit được giữ nguyên.

```powershell
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py seals --label after
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context602_checks.py cleanup
```

Cả hai exit0. Đã xác minh đúng tên DB và comment ownership nonce trước khi drop;
đọc lại xác nhận DB test đã không còn. Chỉ DB test602 bị xóa. Storage tạm và bằng
chứng kiểm thử **còn giữ**, trạng thái `database_removed_storage_pending`, theo
chính sách bảo vệ đang áp dụng; không tắt policy hoặc thử đường xóa thay thế.

Bằng chứng local ở `backend/storage/context602/`: `checks/*-run.json`, JUnit,
`test-id-comparison-final.json`, `after-seal-verification.json`, `isolation.json`,
`acceptance-closure/{summary,adjudications,postcheck-after-multi-vector}.json`,
`multi-source-final/{summary,comparison-601,fidelity-comparison,native-body-integrity}.json`.
Không đưa corpus, credential hoặc raw prompt vào Git/docs.

Không commit/stage/push/reset, reindex, xuất bản, restart hoặc deploy. Đợt3 chưa
bắt đầu. Phần nền và contract đã có kiểm chứng, nhưng còn P10,6 ca nhiều nguồn,
payload context và18 lỗi nền cần được theo dõi tách biệt.

Kiểm bàn giao offline cuối exit0:1269 code seals còn khớp, schema sinh từ mã
khớp JSON Schema,21 file source/test và9 tài liệu UTF-8 không BOM/LF,26 liên kết
local hợp lệ,0 secret pattern flag, `git diff --check` exit0 và0 file staged.
Receipt: `backend/storage/context602/closing-checks.json`. Đây là kiểm toàn vẹn
bàn giao, không đổi kết quả FAIL của full suite hoặc bộ nhiều nguồn.
