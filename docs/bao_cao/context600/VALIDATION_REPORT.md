# Context600 — Kiểm chứng Wiki 4–6

Ngày22/10/2026. Mã Wiki4–6 đã triển khai và kiểm chứng xuyên nguồn, revision và
consistency trong môi trường test riêng. **Chưa nghiệm thu toàn bộ yêu cầu**:
P07 mất điều kiện ở lượt chính; full backend vẫn FAIL18 lỗi nền. Không coi ngưỡng
85%, citation hợp lệ hoặc retry PASS là lý do bỏ qua loss này.

## Kết quả đã thực chạy

| Kiểm tra | Kết quả | Exit/cwd |
|---|---|---|
| Git/diff trước task | Sạch | 0, root |
| Preflight và freeze baseline | PASS; development, DB/MinIO/Qdrant loopback,64 ID,33 mapping không đổi | 0, root |
| Baseline64 trước sửa | 58/60 tri thức,48/50 positive,10/10 negative,4/4 social; FAIL P10/P15;135/135 citations | runner/scorer/postcheck0, root |
| Tái hiện thu hồi pointer | 1 FAIL đúng hành vi trước sửa | 1, backend |
| Tái hiện reuse revision | 1 FAIL đúng hành vi trước sửa | 1, backend |
| Network guard | 3 PASS; chặn model ngoài/MinIO/Qdrant thật | 0, backend |
| Focused chốt32 file | 829 PASS,1 warning version probe bị chặn | 0, backend |
| Boundary36 trước sửa literal | 36 PASS; sau đó thêm9 ca ranh giới chữ/mã | 0, backend |
| Ruff13 file Python | PASS | 0, root |
| Biome6 file | PASS, LF, không auto-fix toàn repo | 0, frontend |
| FE hành vi/render gồm reader | 22 PASS | 0, frontend |
| Build FE gồm TypeScript | PASS | 0, frontend |
| Browser sau đăng nhập | NOT RUN; IAB được đưa tới SSO, không có phiên đăng nhập để kiểm tra tính năng | Không bypass auth |
| Full backend trước sửa literal | 3330 PASS/18 FAIL/17 SKIP,+23subtests PASS; exact ID/cause khớp599,0mới/thiếu | 1, backend; toàn suite FAIL |
| Full backend mã chốt | **FAIL**:3339 PASS/18 FAIL nền/17 SKIP,+23subtests PASS;45 mới PASS | 1, backend |
| Benchmark64 cuối | 59/60 tri thức;49/50 positive,10/10 negative,4/4 social; FAIL P07;152/152 citations,0runtime | runner/scorer/postcheck0, root; ngưỡng85% đạt, gate không regression chưa đạt |
| Retry chẩn đoán P07 riêng | PASS,5/5 citations,0runtime; không sửa mã, không thay điểm chính | runner/postcheck0, root |

Lệnh/cwd/exitcode và JUnit từng ID: `backend/storage/context600/checks/`;
[bảng lệnh,45 test mới và17SKIP](TEST_EVIDENCE.md) ghi các process thực chạy.
baseline questions/raw responses/labels/usage/seals: `.../baseline/` được ignore.
Không sao chép source/prompt riêng/credential vào Git. Các lần kiểm trung gian
vẫn giữ artifact riêng; không thay bằng kết quả chốt.

## Baseline64

Trọn64 response, không missing/duplicate ID hoặc runtime exception. P10 và P15
từ chối khi chưa trả đủ nội dung, tính FAIL. Đây là baseline mới trên mã trước
Wiki4–6, không dùng58/60 của597 hoặc ghép6/6 của599 thành60/60.

167 usage records đều Luna thành công,0fallback;1136182 input/44458 output tokens.
Latency60 câu tri thức: p50=580,92ms, p95=61129,22ms, max=77866,67ms, toàn service.
Chi phí tiền không đo; không ước tính thành quan sát. Social4/4 ngoài mẫu số60.
Gold vẫn là draft source-rubric, không phải human holdout. Chấm actual response
và hash của response, kiểm citation canonical độc lập; không gọi judge LLM.

Scorer đầu có category runtime cũ của P13 bị kế thừa trong metadata review dù
response hiện tại đạt và không exception. Đã sửa category sau khi đối chiếu
current response, chạy lại scorer offline; không gọi lại benchmark hoặc đổi
criteria/gold. Postcheck template có nhãn focused_probe_ids6 kế thừa, nhưng
run-intent/completed/ids và dữ liệu thật đều64; không dùng nhãn đó để đếm mẫu.

## Phân biệt thật và mock

- Baseline64: source/index/vector/model thật, candidate snapshot do server xác
  minh, actor xác thực; gọi tuần tự `rag_service.ask`. Không HTTP/browser E2E
  đã xuất bản, không publish để đo, không concurrent synthetic ModelOps.
- Fixture nhiều nguồn: PostgreSQL thật trong DB nonce riêng; ASGI router và
  auth dependency/exception handler thật. ModelOps bị chặn/mock; kiểm GET0write/
  0model bằng SQL statement và mock assertion. Không có vector hoặc upload thật.
- Reader xuyên nguồn: DB/canonical thật trong fixture; chỉ mock lựa chọn page ID.
  Ba nguồn2024/2025/2026 trả các span100/200/300 riêng và đúng binding/revision;
  query2025 không mở nguồn2024/2026. Kiểm `bind_quote` trên canonical thật.
  Đây không phải phép đo chất lượng answer LLM xuyên nguồn độc lập.
- Lifecycle: create/update/staging/activate/remove/rollback chỉ trong DB test;
  kiểm snapshot/epoch, retry/concurrent sessions và job cũ không đổi pointer mới.
- Reuse: fixture selector mock; số gọi quan sát được từ mock, không phải chi phí
  provider đo thật. Bundle mới calls0, metrics rỗng và trace reuse có seal.
- Projection trên nguồn thật hiện tại:11 trang,10 cạnh nguồn,327 reference;
  read-only transaction và actor/candidate snapshot thật. JSON graph1039121 ký
  tự; load/build/validate/review1237,4ms,0 usage model thêm,0blocker,
  52source limitations/10warnings. Đây là một phép đo source staging một nguồn,
  không dùng nó thay fixture xuyên nguồn hoặc benchmark answer.

## Bản đồ regression

| Ranh giới | Test IDs/file hiện tại |
|---|---|
| Nhiều nguồn/năm, publication≠data | `test_three_sources_years_and_publication_never_merge_values_or_identity`; reader integration parametrized |
| Nhiều cột năm gồm2027 | `test_multi_year_columns_including_2027_keep_literal_values_and_unknown` |
| Cùng tên khác mã/số0/Unicode | `test_same_name_different_codes_are_distinct_nodes_with_only_co_mention`; `test_leading_zero_and_unicode_identifiers_remain_exact_and_alias_is_only_candidate` |
| Alias evidence/nhập nhằng | Alias chỉ candidate, không BFS; same-name không merge; warning/candidate trong review |
| NhómA/B,AM-0007/AM-0070, điều kiện/ngoại lệ | Bộ `test_source_answer_scope_575`, `test_context_scope_integrity_594`, `test_dependency_agreement_599`, nguyên văn/group trong fixture |
| Chú thích cùng chữ, khác bảng | `test_identical_footnotes_keep_distinct_table_locators_and_conditions`, regression595 trong focused |
| Unknown/thiếu input/không gán0 | `test_source_injection_and_unknown_symbol_stay_literal_navigation_data`; recovery/dependency599 |
| Conflict cùng/khác năm, unit, conditions | `test_value_difference_requires_same_data_year_metric_unit_and_conditions` |
| Update/remove/rollback/cache/concurrency/late job | Sáu test integration tương ứng và hai tái hiện PostgreSQL trước sửa |
| Unpublished/revoked/foreign collection | Handler403, draft không vào published map, strict snapshot và cache revoke409 |
| Vòng/fanout/budget | BFS visited/depth/node/edge; reference cap trả422, không partial ready |
| Injection | Source vẫn navigation data, không có mutation/model permission |
| Legacy/v1 | Các test wiki/navigation/persistence và các ca historical snapshot không wiki |
| P06/X09/P07/P10/P12/P16 | Focused599/597; kết quả live64 được báo từng lượt, không ghép điểm |
| Đổi publication trong GET | `test_publication_change_during_map_read_returns_stale_instead_of_partial_graph` |
| Text/span giả | `test_canonical_text_and_span_must_match_before_a_page_can_be_ranked` |
| Provider/DB error | Mã timeout/infrastructure riêng; DB503 không thành map rỗng |

## Lượt trung gian và giới hạn

Focused-first:115PASS/3FAIL; chỉnh tương thích import/budget và giả định fixture
Unicode. Parser legacy có thể chưa nhận mã dùng combining mark; wiki giữ raw
canonical, không tạo alias bằng Unicode normalization. Không đổi parser task này.
Integration tiếp:118PASS/4FAIL do fixture thiếu vector_generation_id; sửa fixture.
Lượt fixture riêng:3PASS/1FAIL do app test chưa đăng ký exception handler; sửa
harness ASGI theo main thật. Focused814 lượt đầu:810PASS/4FAIL do lẫn thu hồi quyền
với context budget thiếu block; sửa phân loại, giữ assertion595. Lượt814 sau PASS;
bổ sung36 boundary và chốt820PASS. Các log/receipts giữ nguyên.

Review bổ sung sau full đầu tái hiện một lỗi co-mention do prefix của tên dài
hơn: `literal-boundary-before`1FAIL, exit1, compiler fixture/0LLM. Đã sửa và thêm
9 regression, focused chốt829PASS, Ruff13PASS. Full thứ hai cần thiết vì app có
thay đổi mới; full đầu giữ nguyên artifact. Preflight cũ ở `final/` không gửi
benchmark request; lượt chốt dùng preflight/freeze mới dưới `final-release/`.

Chưa có browser desktop/mobile/light/dark sau đăng nhập; không claim visual PASS.
Không semantic judge toàn tài liệu mỗi GET, không approved semantic identity,
không packet-level reuse khi canonical đổi. Không có ablation để quy mọi gain/
loss stochastic của bộ64 cho liên kết wiki.

## So sánh64, usage và latency cuối

[Bảng đủ64 ID](BENCHMARK_BY_ID.md) ghi PASS/FAIL, citation, latency và lý do.
Baseline58/60→cuối59/60; gains P10/P15, loss P07. Cả hai đủ64 ID đúng thứ tự,
không missing/duplicate/interruption. P06/P10/P12/P16/X09 đạt ở lượt cuối;
P07 chưa đạt. Negative10/10 và social4/4 giữ; social không retrieval/model.

| Quan sát | Baseline | Cuối |
|---|---|---|
| Tri thức / positive | 58/60;48/50 | 59/60;49/50 |
| Citation canonical | 135/135 | 152/152 |
| Runtime / fallback | 0/0 | 0/0 |
| Usage Luna thành công | 167 | 150 |
| Input / output tokens | 1136182/44458 | 929770/38091 |
| Service60 p50/p95/max, ms | 580,92/61129,22/77866,67 | 596,86/50672,60/68563,84 |

Đây là hai lượt thực tế, không có ablation để quy giảm token/latency hoặc gain
cho graph. Cùng máy và service boundary, concurrency1, không warmup riêng hoặc
synthetic model đồng thời. Chưa đo chi phí tiền, cache hit rate toàn hệ thống,
Hit@K/Recall@K/MRR hay dense/hybrid/rerank ablation.

Wiki reader xuất hiện ở cùng6 câu mỗi lượt, mỗi câu1 call chọn trang; lượt cuối
linked_pages=0 ở nguồn đơn này. P07 cùng10 evidence blocks/4347 navigation chars.
Không coi0 link expansion là bằng chứng xuyên nguồn; fixture nhiều nguồn và
reader canonical integration được báo riêng ở trên. Request-local cache/reuse
đã kiểm bằng regression; không có upload/update kho thật để đo reuse provider
live. Compiler reuse0call là số đo mock fixture, không phải token savings thật.

## Loss P07 và quyết định nghiệm thu

P07 cuối giữ cách thay chữ ký, tối đa30 ngày và ngoại lệ nhómA/an toàn, nhưng
thiếu tiền đề cơ sở tiếp nhận tạm đóng, nhật ký cá nhân và xác nhận giảng viên
cùng kỳ. Đáp án vì thế có thể mở rộng sai đối tượng được áp dụng, tính FAIL.

Trace baseline/final đều chứa đoạn tiền đề; source-only review đều đánh dấu
required cho e5.c0. Bước agreement baseline trả required, ghi2 obligations và
repair bổ sung; cuối trả not_required cho cùng đoạn, chỉ ghi1 obligation nên
không repair phần thiếu. Context stage metadata giống nhau:349 corpus,13 shortlist,
11 packed,16621 chars, cùng dropped IDs. Audit/review/agreement code không sửa
trong batch này. Selected page IDs/draft/target có khác; không có causal ablation
để kết luận chắc chắn nguyên nhân là graph hoặc hoàn toàn là biến động model.

Sau khi đủ64 kết quả, chạy đúng1 retry P07 riêng trên cùng mã/source/config:
PASS,5/5 citations,82944,82ms,12 Luna success,156174 input/4771 output tokens,
0fallback/runtime. Không thay response, label hoặc điểm59/60 của lượt chính.
Retry chứng minh kết quả biến động, không chứng minh guard đã đáng tin cậy.

Không thêm từ khóa benchmark, ép mọi điều kiện thành required, xóa nghĩa vụ đã
ghi hoặc gọi model lặp đến khi đạt. Chưa có sửa tổng quát được chứng minh cho
false-negative agreement này; đây là **việc chưa hoàn thành ở gate bảo toàn điều
kiện**, cần tái hiện cả nhánh được phép/không đủ input/ngoại lệ và kiểm lại nguyên
bộ sau sửa. Không công bố toàn RAG hay toàn nhiệm vụ Wiki4–6 đã được nghiệm thu.

## Seals và cleanup

Comparability-before và postcheck PASS: questions/gold bytes, source/canonical,
binding/index/vector generation, collection epoch, assistant profile và các row
knowledge/ModelOps giữ nguyên. Chỉ19 path code trong phạm vi thay đổi; mã giữ
nguyên trong full và benchmark. Nguồn12 revisions,2943 points/0retrievable,
active index NULL; không publication/reindex/restart/deploy/commit/push.

DB test49 bảng có owner nonce/comment; metadata defaults chỉ sao chép1 row bất
hoạt,0credentials/0provider. Đã xác minh owner rồi DROP đúng database test phiên600,
kiểm lại không còn. Không migrate/drop DB dùng chung. Storage runtime đã xác minh
đúng absolute path riêng,1234 files/19234687 bytes,0reparse points. Thao tác xóa
đệ quy bị policy tự động chặn; giữ lại, không đổi tool hoặc bypass. Bằng chứng
baseline/final/tests/retry và usage audit được giữ dưới `backend/storage/context600`
được ignore; không xóa artifact hoặc dữ liệu nguồn.

Postcheck sau lượt chính và retry:0 test threads/messages/gaps, code/source/model/
vector seals khớp. Chưa có browser xác thực desktop/mobile/light/dark và published
assistant HTTP E2E; chưa có approved identity/semantic replacement checker hay
packet-level reuse. Kiểm structural closure không thay thế semantic completeness
trong answer, như P07 đã cho thấy.

<!-- EXACT_BASELINE_FAILURES -->

## Exact lỗi nền so với Context599

Full mã chốt1427,74s, exit1; code trước/sau full giữ nguyên. Không FAIL mới,
không đổi cause, không missing/rename ID. Toàn suite vẫn FAIL. Bảng dưới ghi
message đầu; toàn message và từng status nằm trong `full-release-comparison.json`.

| Exact test ID | Message đầu | Khớp599 |
|---|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | `sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist` | Có |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | `app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions'` | Có |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | `app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations'` | Có |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | `app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI.` | Có |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | `redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection.` | Có |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | `app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI.` | Có |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | `assert 403 == 200` | Có |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | `assert 403 == 200` | Có |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | `assert 403 == 400` | Có |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | `assert 403 == 201` | Có |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | `assert 403 == 200` | Có |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | `assert 403 == 200` | Có |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | `AssertionError: assert 'legacy_payload_schema' in []` | Có |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | `assert False is True` | Có |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | `AssertionError: assert 'AI.Admin' == 'admin'` | Có |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | `assert False is True` | Có |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | `app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions'` | Có |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | `app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI.` | Có |

Không sửa assertion/guard của18 ca để đạt màu xanh; không migrate DB ứng dụng
hoặc mở endpoint thật cho pytest để chữa lỗi fixture/môi trường.
