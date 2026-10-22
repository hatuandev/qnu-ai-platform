# Context591 — Sửa RAG/wiki và đo lại bộ 64 câu

Làm việc từ 21 sang 22/10/2026. **Benchmark cuối PASS: 59/60
câu tri thức (98.33%), trong đó 49/50 câu
có đáp án (98.0%).** Đối chứng 10/10;
xã giao 4/4. Hoàn tất đúng 64 request, không ghép lượt bổ sung.

Ca còn FAIL: **F03**. Đây là nghiệm thu bộ đo hiện tại, không phải bảo
đảm mọi tài liệu hoặc mọi câu hỏi đều đúng. Full backend vẫn **FAIL nền**, không
được gọi toàn suite PASS.

| Kiểm tra cuối | Kết quả thực tế | Exit code |
| --- | --- | --- |
| Regression tập trung, 12 file | 257 PASS | 0 |
| Scoped Ruff, 21 file app/test | PASS | 0 |
| Full backend | 3,123 PASS, 18 FAIL, 17 SKIP; 23 subtests PASS | 1 |
| Chấm bộ 64 | 59/60 tri thức; mục tiêu 85% PASS | 0 |
| Kiểm source/config/vector sau chạy | PASS | 0 |

Full có **37 test mới PASS**, không thiếu test baseline,
không có failure ID mới hoặc nguyên nhân lỗi nền thay đổi. Không hạ assertion để
biến lỗi nền thành xanh. JUnit baseline Context589 là 3.086 PASS/18 FAIL/17 SKIP.

Citation: **138/138**
khớp exact source/hash/revision/span/quote. Runtime errors: 0.
P95 tri thức 36.71 giây, tối đa
50.01 giây toàn luồng. Timeout provider vẫn 30 giây
mỗi lượt; một câu có nhiều lượt model nên thời gian toàn luồng có thể dài hơn.

ModelOps ghi 124 usage records, 1,037,796
input tokens và 30,482 output tokens ở lượt cuối;
0 fallback. Model thực tế xem receipt
`single-model-verified.json`; không đổi cấu hình DB để đạt kết quả này.

## Đối chiếu từng ca và các lượt đo

Baseline Context589 chính: 50/60, positive 40/50, P06 gián đoạn. Lượt bổ sung
P06 từng đạt chỉ cho tham khảo 51/60, positive 41/50; không coi là bộ 64 hoàn chỉnh.
So với bộ chính: gains P01, P03, P05, P06, P07, P09, P10, P11, P13, P14, losses
F03. P06 nằm trong gains cơ học nhưng baseline là
gián đoạn, không phải một lỗi sản phẩm đã tái hiện từ response.

| Batch Context591 | Tri thức | Positive | Ca FAIL | Cách đọc |
| --- | --- | --- | --- | --- |
| benchmark | 52/60 | 42/50 | N18, F04, P01, P03, P07, P08, P11, P13 | 63 kết quả; N18 gián đoạn, tính FAIL; không replay request cũ |
| release | 56/60 | 46/50 | P01, P06, P07, P13 | Đủ 64, batch packing/scope |
| final | 57/60 | 47/50 | P06, P07, P08 | Đủ 64, trước sửa cách đếm caption/header |
| acceptance | 59/60 | 49/50 | F03 | Đủ 64, bản code cuối được niêm phong |

Ba probe closure riêng không ghép vào điểm: probe1 chỉ P13 đạt; probe2 không
ca nào đạt; probe3 P01/P13 đạt, P06/P07 còn thiếu điều kiện. Đã giữ kết quả
FAIL dù service trả answered. Các artifact và independent-grading.json giữ riêng.

## Phạm vi và cách sửa

Yêu cầu là sửa theo thứ tự chẩn đoán Context590, mở rộng regression và đo lại
đúng 64 câu. Giữ toàn bộ thay đổi chưa commit Context587–590. Không sửa parser,
nguồn, facts, trang tri thức đã lưu, model, timeout, Quality Gate hoặc publication.
Không reindex, restart, migration, commit hay push. Chưa triển khai ưu tiên wiki 4–6.

Đây là sửa đường đọc và kiểm chứng bằng chứng, không phải bóc tách lại PDF.
Context590 đã đối chiếu được 24 gold spans/23 units của chín câu lỗi trong
canonical/wiki. Kết quả mới tiếp tục kiểm hash, tọa độ và trích đoạn nguồn.

| Thứ tự | Nguyên nhân chung | Thay đổi |
| --- | --- | --- |
| 1 | Lỗi nội bộ có thể bị hiểu nhầm thành mã HTTP upstream | Trace allowlist theo stage/attempt/contract, actual upstream status nếu quan sát được, app error code, finish reason và token thật. Không lưu prompt hoặc completion vào trace mới. Không tự retry lỗi provider. |
| 2 | Reader mở trang rồi gọi thêm lượt xác nhận sai schema | Model chọn trang; server mở ngay original canonical refs. Action được kiểm theo đúng loại. Repair hình dạng dùng chung ngân sách hai lượt/thời gian, không reset budget hoặc che lỗi quyền/provider. |
| 3 | Ô ambiguous/unreadable bị nhầm với lỗi integrity | Consumer số liệu mặc định vẫn strict. Catalog mô tả chỉ định vị chú giải/nguồn; ô hạn chế không trở thành giá trị đã xác minh. Raw/header/span giả vẫn bị chặn. |
| 4 | Câu hỏi chỉ đọc nguồn bị ép năm hiện tại hoặc cơ quan từ persona | Thêm question_scope tương thích ngược. Câu hỏi hiệu lực vẫn giữ kiểm phạm vi; đọc nội dung không tự nhận năm/cơ quan từ cấu hình. Năm/cơ quan người dùng nêu rõ vẫn được kiểm chứng. |
| 5 | Wiki giành hết context; điều kiện bị rơi hoặc tách sai | Ưu tiên record/địa chỉ nguồn rõ ràng; wiki hỗ trợ điều hướng. Đóng cả danh sách và dependency có hướng, giữ scope nguồn. Caption hình mở đối tượng mới; caption/header bảng giữ nguyên và tính byte budget nhưng không chiếm thêm suất body Top-K. |
| 6 | Audit vòng sau phát hiện điều kiện mới nhưng không bổ sung được | Không tách danh sách năm thành clause mồ côi. Chỉ thêm nguyên văn điều kiện đã có trong context, rồi audit lại; tối đa hai vòng, dừng khi không tiến triển. Không bỏ scope, conflict, topic coverage hoặc giới hạn claim. |

Nhánh đọc nguồn không tạo được claim chỉ được thử lại qua bộ đối soát canonical
hiện có khi không có binding rejection/conflict, không có evidence policy bật
rõ và còn thời gian của request gốc. Không dùng để biến lỗi provider thành câu
trả lời giả hoặc lấy partial làm PASS. Tuyên bố nguồn trình bày như heading
chỉ được làm claim chính khi thực sự được chọn cho câu hỏi đọc nội dung.

17 file app được sửa trong lượt này, so với snapshot đầu Context591:

- Knowledge: `wiki_schemas.py`.
- ModelOps: `services/key_rotation.py`.
- RAG: `evidence_model.py`, `wiki_context.py`, `evidence_schemas.py`,
  `evidence_pipeline.py`, `row_answer_contract.py`, `row_answer.py`,
  `source_scope_audit.py`, `prose_fallback.py`, `service.py`,
  `evidence_dependencies.py`, `evidence_passages.py`, `evidence_claims.py`,
  `evidence_indexed_audit.py`, `evidence_verification.py`, `evidence_blocks.py`.

Regression mới nằm trong `test_rag_reliability_591.py`,
`test_wiki_packing_591.py`, `test_wiki_route_compatibility.py`; cập nhật hành vi
reader trong `test_wiki_navigation.py`. Giữ test ID cũ để đối chiếu baseline.
Tài liệu luồng đọc nguồn được cập nhật tại
[quy trình trang tri thức](../../quy_trinh/16_trang_tri_thuc_va_doc_nguon.md).
Không chỉnh frontend trong Context591; các thay đổi frontend đã có thuộc phiên trước.

## Cách đo và giới hạn

- Cùng source revision `ks_rev_993a7ad91b32`, index `idx_rev_6bf0d6f86b1b`,
  generation `vg_a6e3190d11af`; 327 chunks, 415 facts, wiki 11 trang.
- Cùng 64 câu, rubric, gold spans và phiên follow-up; 60 câu tri thức gồm
  50 câu có thể trả lời và 10 câu đối chứng, cộng 4 câu xã giao. 33 ánh xạ
  fact được kiểm, **0 fact ID thay đổi**. Không thêm câu dễ hoặc đổi nhãn để tăng điểm.
- 29 ca ô/hàng chấm tọa độ, header, giá trị, năm, số lượng và citation bằng
  thuật toán. Các ca còn lại được đọc đáp án và đối chiếu rubric nguồn,
  lưu SHA-256 của chính response được chấm. Không gọi judge LLM.
- Có thể tìm đúng trích đoạn nhưng trả thiếu điều kiện vẫn FAIL; partial hoặc
  lỗi runtime không được tính là từ chối đúng. Unknown không đổi thành 0.
- Ngưỡng 85% cần đồng thời ít nhất 51/60 tổng tri thức và 43/50 câu có đáp án;
  nhóm đối chứng và xã giao báo riêng.
- Luna primary và Qwen fallback trong DB giữ nguyên; phép đo giới hạn thực thi
  Luna-only như baseline để không âm thầm lấy fallback làm cải thiện. Token
  thực, model và fallback được đối chiếu từ usage audit, không ước lượng chi phí.
- Gọi `rag_service.ask` thật với actor có quyền và candidate snapshot do server
  xác minh. Đây là kiểm thử RAG staging, **không phải HTTP/browser E2E của chatbot
  đã xuất bản**. Không thay active pointer để làm E2E.
- Sampling khác giữa các lượt; không có A/B đồng thời hay holdout độc lập.
  Không suy từng gain/loss là tác động nhân quả riêng của một dòng sửa.
- Một số đáp án trích nguyên văn còn xuống dòng hoặc lặp đoạn nối của nguồn.
  Bộ đo này chấm độ đúng nội dung và citation, chưa chấm chất lượng trình bày.

## An toàn môi trường và dọn kiểm thử

Đã kiểm môi trường development, DB/MinIO/Qdrant ở localhost trước các phép đo.
Full/focused tests dùng DB test riêng có tên và nonce sở hữu, Local Storage
tạm; các endpoint S3/Qdrant/Redis/embedding của test trỏ cổng không phục vụ.
Không chạy migration hoặc fixture ghi vào DB phát triển. Metadata mặc định
cho test không mang credential LLM.

Benchmark được phép đọc snapshot staging cũ và gọi ModelOps hiện có; ModelOps
vẫn ghi lease/usage audit trong giao dịch riêng. Không tuyên bố toàn bộ DB là
read-only vì các bản ghi audit này là side effect có chủ đích. Source/index,
model config, các revision cũ và payload vector được so seal trước/sau.

Hai DB test do Context591 tạo được kiểm owner nonce trước dọn. Bằng chứng test,
benchmark và Storage tạm được giữ trong `backend/storage/context591*` bị ignore.
**Kiểm duyệt tự động đã từ chối xóa Storage đệ quy ở lượt trước. Không đổi công
cụ, tắt chính sách hoặc xóa vòng qua để vượt chặn.** Không có dữ liệu kiểm thử
nào được publish hay đánh dấu retrievable.

## Lịch sử kiểm chứng trong lượt sửa

Không chọn riêng điểm cao nhất để thay cho phép đo cuối. Các batch code khác nhau
và probe được lưu tách biệt; bảng kết quả ở đầu báo cáo ghi từng lượt.

- Lượt tái hiện trước sửa có 13 FAIL, gồm contract mới và hai vấn đề fixture;
  fixture được điều chỉnh trong helper/test, không dùng để hạ assertion sản phẩm.
- Full giai đoạn đầu có hai lỗi mới do catalog mô tả làm rộng consumer strict;
  đã khôi phục strict mặc định và kiểm lại các test source limitation/integrity.
- Lượt full-release bị gián đoạn và full-closure-final dừng khi có batch sửa
  tiếp: **không hoàn tất, không PASS**. Bằng chứng gián đoạn được giữ.
- Lệnh focused có đường dẫn không tồn tại từng exit 4: NOT RUN, không cộng PASS.
- Regression caption đã FAIL trước sửa; chỉ bỏ caption khỏi body count vẫn
  chưa đủ vì header bảng còn chiếm suất. Bản cuối giữ cả hai trong byte budget
  nhưng không đếm thêm như một body. Không đổi giới hạn kích thước để lấy điểm.
- Full cuối đối chiếu exact test ID và nguyên nhân với JUnit Context589;
  tổng suite vẫn FAIL nếu còn lỗi nền. FE lint/build/typecheck và published
  HTTP E2E của lượt này NOT RUN vì không sửa FE và không được xuất bản.

Các helper chạy từ repo root bằng Python của backend. Test runner thực chạy
`python -m pytest -q ... --junitxml=...` trong `backend`, lưu toàn bộ argv, cwd,
exit code, log và JUnit. Ruff dùng `python -m ruff check` trên đúng 21 file
app/test thay đổi. Full là toàn bộ Pytest trong DB cô lập, không thay bằng mock-only.
Benchmark vẫn cần LLM thật; regression nội bộ không chứng minh upstream E2E.

Private profile, prompt, corpus và response đầy đủ không sao chép vào tài liệu
theo dõi Git. Báo cáo chỉ ghi ID ca, số đo, nguyên nhân và đường dẫn bằng chứng.

## F03 còn lại: hỏi lại ngữ cảnh, không phải mất dữ liệu

F03 dừng ở `CONTEXT_SCOPE_UNPROVEN` trước retrieval. Trace cho thấy model tạo
một topic referent có giá trị không nằm nguyên văn trong trích đoạn mà nó dùng
làm căn cứ; referent mã và năm đúng literal. Guard từ chối là đúng chính sách,
nhưng việc hỏi lại làm ca có thể trả lời bị FAIL. Đây không phải timeout, lỗi
context window hoặc bằng chứng parser làm mất ô nguồn; gold fact vẫn còn đủ.

Probe offline trích đúng hàm validate_referents, cấp giả định thuận lợi rằng
standalone query chứa mọi giá trị, vẫn tái hiện việc từ chối do quote/value lệch.
Mã `intent_contracts.py` và `conversation_resolution.py` khớp SHA từ đầu lượt.
Không có exact standalone query bị từ chối trong log, nên không khẳng định đã
tái hiện toàn bộ router hoặc chứng minh sampling là nguyên nhân duy nhất.

Không retry riêng F03 để thay điểm của bộ 64, không bỏ guard. Hướng tiếp theo
là sửa hợp đồng literal referents và cân nhắc một lượt sửa định dạng trong
deadline hiện có, sau đó validate toàn bộ phạm vi lại. Regression cần giữ các
ca thay mã/năm nhiều lượt, sửa giá trị gần nhất, hai đối tượng mơ hồ, phủ định
và quote sai; không dùng từ khóa riêng của F03. Chưa triển khai hướng này trong
bản code đã niêm phong để đo ở đây.

[Probe chẩn đoán F03](../../../backend/storage/context591/acceptance/f03-offline-diagnosis.json)
không gọi LLM hoặc DB. Không ghép nó thành PASS sản phẩm.

## Lỗi nền theo exact test ID

- `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import`
- `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export`
- `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export`
- `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests`
- `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item`
- `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page`
- `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint`
- `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api`
- `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled`
- `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled`
- `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit`
- `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback`
- `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies`
- `tests.test_tools::test_fact_layer_lookup_tool_found`
- `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims`
- `tests.test_universal_tools::test_fact_layer_lookup_tool`
- `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts`
- `tests.test_vllm_reranker::test_vllm_embedding_generation`

Nguyên nhân từng ID so với baseline không đổi, lưu tại full-acceptance-comparison.json.
Không đưa thông báo lỗi thô có thể chứa dữ liệu nội bộ vào báo cáo Git.

## Bảng đối chiếu đủ 64 ID

P06 baseline ghi GIÁN ĐOẠN; không tráo thành response cũ. PASS/FAIL hiện tại
đến từ nhãn offline và response hash đã được kiểm.

| ID | Baseline589 chính | Context591 cuối | Citations đúng/tổng |
| --- | --- | --- | --- |
| N01 | PASS | PASS | 1/1 |
| N02 | PASS | PASS | 1/1 |
| N03 | PASS | PASS | 1/1 |
| N04 | PASS | PASS | 1/1 |
| N05 | PASS | PASS | 1/1 |
| N06 | PASS | PASS | 1/1 |
| N07 | PASS | PASS | 1/1 |
| N08 | PASS | PASS | 1/1 |
| N09 | PASS | PASS | 1/1 |
| N10 | PASS | PASS | 1/1 |
| N11 | PASS | PASS | 1/1 |
| N12 | PASS | PASS | 1/1 |
| N13 | PASS | PASS | 1/1 |
| N14 | PASS | PASS | 1/1 |
| N15 | PASS | PASS | 1/1 |
| N16 | PASS | PASS | 1/1 |
| N17 | PASS | PASS | 3/3 |
| N18 | PASS | PASS | 4/4 |
| N19 | PASS | PASS | 3/3 |
| N20 | PASS | PASS | 3/3 |
| M01 | PASS | PASS | 2/2 |
| M02 | PASS | PASS | 2/2 |
| M03 | PASS | PASS | 2/2 |
| M04 | PASS | PASS | 2/2 |
| M05 | PASS | PASS | 12/12 |
| M06 | PASS | PASS | 1/1 |
| F01 | PASS | PASS | 1/1 |
| F02 | PASS | PASS | 1/1 |
| F03 | PASS | FAIL | 0/0 |
| F04 | PASS | PASS | 1/1 |
| F05 | PASS | PASS | 1/1 |
| F06 | PASS | PASS | 1/1 |
| F07 | PASS | PASS | 1/1 |
| F08 | PASS | PASS | 1/1 |
| P01 | FAIL | PASS | 3/3 |
| P02 | PASS | PASS | 3/3 |
| P03 | FAIL | PASS | 4/4 |
| P04 | PASS | PASS | 4/4 |
| P05 | FAIL | PASS | 6/6 |
| P06 | GIÁN ĐOẠN | PASS | 6/6 |
| P07 | FAIL | PASS | 5/5 |
| P08 | PASS | PASS | 5/5 |
| P09 | FAIL | PASS | 6/6 |
| P10 | FAIL | PASS | 4/4 |
| P11 | FAIL | PASS | 4/4 |
| P12 | PASS | PASS | 4/4 |
| P13 | FAIL | PASS | 5/5 |
| P14 | FAIL | PASS | 3/3 |
| P15 | PASS | PASS | 6/6 |
| P16 | PASS | PASS | 6/6 |
| X01 | PASS | PASS | 0/0 |
| X02 | PASS | PASS | 0/0 |
| X03 | PASS | PASS | 0/0 |
| X04 | PASS | PASS | 0/0 |
| X05 | PASS | PASS | 0/0 |
| X06 | PASS | PASS | 0/0 |
| X07 | PASS | PASS | 4/4 |
| X08 | PASS | PASS | 0/0 |
| X09 | PASS | PASS | 3/3 |
| X10 | PASS | PASS | 0/0 |
| S01 | PASS | PASS | 0/0 |
| S02 | PASS | PASS | 0/0 |
| S03 | PASS | PASS | 0/0 |
| S04 | PASS | PASS | 0/0 |

### Chi tiết ca chưa đạt

- **F03**: Router tạo topic referent có value không nằm nguyên văn trong quote; guard CONTEXT_SCOPE_UNPROVEN chặn trước retrieval. Mã resolver/validator giữ nguyên từ đầu lượt; số liệu nguồn còn đủ. Không retry hoặc nới guard.

## Bằng chứng và bàn giao

- [Summary phép đo cuối](../../../backend/storage/context591/acceptance/summary.json).
- [Nhãn từng ID và nguyên nhân](../../../backend/storage/context591/acceptance/labels-final.json).
- [Postcheck nguồn/cấu hình/vector](../../../backend/storage/context591/acceptance/postcheck.json).
- [Focused receipt](../../../backend/storage/context591/checks-final/acceptance-ready-run.json).
- [Ruff receipt](../../../backend/storage/context591/checks-final/ruff-acceptance.json).
- [Full receipt](../../../backend/storage/context591/checks-final/full-acceptance-run.json).
- [JUnit cuối](../../../backend/storage/context591/checks-final/full-acceptance.xml).
- [Đối chiếu exact IDs/nguyên nhân](../../../backend/storage/context591/checks-final/full-acceptance-comparison.json).
- [Bộ so câu hỏi/gold](../../../backend/storage/context591/acceptance/gold-mapping.json).

Source/config/old revisions/vector payload giữ nguyên; 2.943 staging/history
points và 0 retrievable; không publish. Không còn benchmark threads/messages/gaps.
Hai DB test đã dọn, Storage tạm giữ theo chính sách bảo vệ. Code có seal trước/sau
full test và benchmark; tài liệu bàn giao được ghi sau khi hoàn tất phép đo.

Không tự chuyển sang ưu tiên 4–6 hoặc xuất bản nguồn. Bộ 64 là tập đã dùng để
phát triển, chưa có holdout/đa nguồn/đa tài liệu mới hoặc đo tải đồng thời.

Kiểm tra bàn giao: 17 local links của tài liệu/mục lục mới đều tồn tại; UTF-8
không BOM, LF, kiểm tra mẫu secret và seal app/test/FE đạt. Quét toàn các mục
lục cũ phát hiện 241 liên kết lịch sử không tồn tại, nên phép quét toàn mục lục
là FAIL; giữ receipt riêng, không sửa lịch sử ngoài phạm vi để làm xanh.
