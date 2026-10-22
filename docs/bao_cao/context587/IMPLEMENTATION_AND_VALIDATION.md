# Context587 — Trang tri thức, phạm vi năm và đọc thêm nguồn

## Kết quả sản phẩm

Đã triển khai ba ưu tiên được người dùng đồng ý từ hướng tiếp cận của llm_wiki:

1. Biên soạn trang Markdown về **nguồn, đối tượng và chủ đề** bằng LLM qua ModelOps,
   dựa trên canonical Markdown/Structured JSON đã được kiểm tra của QNU.
2. Giữ năm dữ liệu, năm ban hành, năm hiệu lực, năm sự kiện, điều kiện, ngoại lệ
   và liên kết về từng đơn vị nguồn. Một tài liệu có thể nói về nhiều năm.
3. Cho chatbot chọn mở trang và đọc thêm nguồn gốc trong cùng snapshot, với ngân
   sách lượt gọi, thời gian và độ dài ngữ cảnh có giới hạn.

Giao diện: **Kho tri thức → Nguồn → Nội dung → Trang tri thức → Xem trang**.
Mỗi trang có nút **Xem nguồn** để mở trích đoạn. Nguồn cũ chưa biên soạn trang sẽ
hiển thị đúng trạng thái; việc chỉ mở giao diện không gọi LLM hoặc thay dữ liệu.

Tính năng áp dụng cho revision DOCX/PDF mới qua luồng chuẩn. Trang được tạo khi
materialize chunk set, trước embedding, rồi dùng lại cho các vector generation.
Phiên này không tạo revision mới trong kho thật, không reindex hoặc xuất bản.

## Thiết kế và ranh giới

- `wiki_compiler.py`: phân tích dàn trang rồi sinh nội dung theo gói, kiểm tra
  JSON, ID, trích đoạn nguyên văn, số/mã và bằng chứng năm. Kết quả sai bị từ chối.
- `wiki_build.py`: giải quyết model chính/fallback từ ModelOps hiện hành. Usage
  dùng giao dịch riêng để không vô tình commit giao dịch nguồn/chunk set.
- Chính sách có version `qnu-knowledge-wiki/v1`; hash chính sách tham gia
  fingerprint nguồn. Bundle trang được ghim cùng chunk set và index revision.
- Ngân sách mặc định: 24.000 ký tự nguồn/gói, 180.000 ký tự nguồn cộng dồn qua các
  lượt, 16 lượt logic, 6.000 output tokens/lượt, 180 giây toàn tác vụ. Retry hợp
  đồng tối đa một lần, vẫn trừ ngân sách. Fallback/transport giữ chính sách ModelOps.
- Chi phí thêm: thông thường hai lượt biên soạn cho mỗi gói, rồi tối đa hai lượt
  điều hướng trong một câu hỏi có wiki. Bundle đã lưu được dùng lại. Snapshot
  không có wiki không phát sinh lượt đọc trang. Latency có thể tăng; chưa có
  phép đo throughput hoặc so sánh chi phí trên corpus thật.
- Heading cha nguyên văn được mang theo gói và dàn trang. Không suy năm từ tên
  file, không thêm từ điển phương thức, năm hoặc từ khóa của một câu benchmark.
- Biên soạn thất bại trả `unavailable` và không lưu trang có thể dùng. Chất lượng
  nguồn gốc vẫn được đánh giá riêng; không hạ Quality Gate để có trang.
- `wiki_views.py` và API GET kiểm quyền `ai.knowledge.view` cùng collection,
  binding và source revision; có thể xem trang trước xuất bản trong giao diện quản trị.
- `wiki_context.py` chỉ đọc trang của index/source/hash đúng snapshot. Chatbot
  thường chỉ dùng index active; candidate giữ ranh giới kiểm thử có quyền hiện có.
- Chatbot được chọn `read_pages`, `read_source`, `search`, `done`, với IDs do
  server cấp; không được chọn file, URL, SQL hoặc công cụ ghi. Mặc định hai lượt,
  14.000 ký tự trang, 30 giây; chia sẻ ngân sách với context bằng chứng gốc.
- Trang dẫn xuất chỉ hỗ trợ điều hướng. Trích dẫn cuối phải là block canonical,
  qua claim binding và kiểm tra điều kiện/ngoại lệ hiện có. Nhãn năm do LLM đề
  xuất không trở thành semantic approval hay fact đã xác minh.
- Không tự diễn giải ký hiệu chưa định nghĩa thành 0. Không tự sửa facts,
  proposal, source Markdown/JSON hoặc active publication pointer.
- Chưa hợp nhất trang thực thể xuyên nguồn và chưa tạo đồ thị wiki. Không sao
  chép mã triển khai GPL của llm_wiki vào QNU; chỉ áp dụng ý tưởng tổ chức/đọc nguồn.

## File thay đổi chính

| Phần | File/hành vi |
|---|---|
| Hợp đồng và compiler | `backend/app/modules/knowledge/wiki_schemas.py`, `services/wiki_compiler.py`, `services/wiki_build.py` |
| Lưu và ghim revision | `services/qnu_serving.py`, `chunk_set_service.py`, `derived_bundle.py`, `vector_generation_service.py`, `generation_candidate.py` |
| API chỉ đọc | `knowledge/wiki_router.py`, `knowledge/router.py`, `services/wiki_views.py` |
| RAG | `rag/wiki_context.py`, `schemas.py`, `retriever.py`, `service.py`, `evidence_pipeline.py`, `evidence_model.py` |
| Giao diện | `knowledge-wiki-panel.tsx`, `knowledge-api.ts`, `knowledge-wiki.ts`, source detail và cache invalidation |
| Regression | `test_knowledge_wiki.py`, `test_wiki_navigation.py`, `test_wiki_persistence.py`, `test_automatic_ingestion.py`, `knowledge-wiki.test.mjs` |

## Môi trường kiểm thử

Baseline thực chạy trước sửa app trên bản sao code sạch tại HEAD `83415add`.
Đã xác minh DB, MinIO và Qdrant cấu hình local trước chạy. DDL chỉ tạo schema
trong DB `qnu_test_*` do phiên này sở hữu; không chạy migration vào DB dùng chung.

Pytest dùng DB riêng, LocalStorage riêng và chặn endpoint ngoài về `127.0.0.1:1`;
tắt auto migrate/seed. Full regression dùng bản sao typed defaults metadata,
không có provider credentials. Không dùng bộ đầy đủ làm phép thử với khóa thật.

Lượt gọi ModelOps thật dùng một DB test riêng, dữ liệu tổng hợp tạo trong RAM và
bản sao cấu hình/credential có bảo vệ; không ghi secret ra file/log. DB đó đã dọn.
Không gửi corpus nội bộ hoặc DOCX/PDF đang lưu trong kho cho phép thử này.

## Kết quả kiểm chứng

| Kiểm tra | Kết quả thực chạy | Exit |
|---|---|---|
| Full baseline, code trước sửa | 2.985 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS | 1 — FAIL |
| Focused release, 10 file | 162 PASS | 0 |
| Full release | 3.026 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS | 1 — FAIL |
| So exact IDs/nguyên nhân | 18 lỗi cũ cùng message; 0 lỗi mới, 0 test cũ mất; 41 ca thêm PASS | 0 |
| Scoped Ruff | 21 file Python PASS | 0 |
| Scoped Biome | 6 file PASS, override LF theo AGENTS | 0 |
| Frontend behavior/render | 15 PASS (7 wiki + 8 reader) | 0 |
| Frontend build + TypeScript | `npm run build` PASS | 0 |
| ModelOps thật, synthetic fixture | Compiler và reader PASS | 0 |
| Visual/browser và HTTP E2E toàn luồng | NOT RUN; preview bị client chặn | — |
| Benchmark 64 / vector thật / publication thật | NOT RUN; ngoài phạm vi phiên | — |

Full suite **vẫn FAIL**, không được gọi 18 lỗi baseline là PASS hoặc đã sửa.
Nguyên nhân các lỗi này gồm fixture/config/quyền và endpoint hạ tầng bị chặn;
không suy từ đó rằng tất cả là lỗi production hay tất cả đều vô hại.

Lệnh backend cuối chạy từ root repo qua helper test-owned; subprocess Pytest có
cwd `backend`, dùng Python `.venv`, `-m pytest -q --basetemp=... --junitxml=...`.
Lệnh đầy đủ và test IDs/status lưu trong receipts/XML/JSON dưới đây. Baseline
dùng runner ghim code trước sửa, bỏ ba file test mới chưa tồn tại ở baseline.

Frontend từ `frontend`: `node --test src/features/knowledge/components/knowledge-wiki.test.mjs src/features/knowledge/components/qnu-document-reader.test.mjs`;
`biome check --line-ending=lf` trên sáu file sửa; `npm run build`.
Không đổi `biome.json` đang dùng CRLF và không format toàn repo.

- [Baseline XML](../../../backend/storage/context587/checks-final/full-baseline.xml)
- [Baseline receipt](../../../backend/storage/context587/checks-final/full-baseline-run.json)
- [Focused release XML](../../../backend/storage/context587gate/checks-final/focused-release.xml)
- [Focused receipt](../../../backend/storage/context587gate/checks-final/focused-release-run.json)
- [Full release XML](../../../backend/storage/context587gate/checks-final/full-release.xml)
- [Full release receipt](../../../backend/storage/context587gate/checks-final/full-release-run.json)
- [Exact comparison, tất cả test IDs/status trước/sau](../../../backend/storage/context587gate/checks-final/full-release-comparison.json)
- [Ruff receipt](../../../backend/storage/context587gate/checks-final/ruff-run.json)
- [Biome receipt](../../../backend/storage/context587gate/checks-final/biome-run.json)
- [Frontend behavior receipt](../../../backend/storage/context587final/checks-final/frontend-behavior-run.json)
- [Gọi ModelOps thật](../../../backend/storage/context587/checks-final/live-report.json)
- [Seal dữ liệu sau task](../../../backend/storage/context587/checks-final/after-seal-verification.json)

### Đối chiếu đủ 18 lỗi baseline

Mỗi ID dưới đây FAIL ở cả baseline và full release, message trùng chính xác.
JSON đối chiếu giữ nguyên message đầy đủ; bảng rút gọn để dễ đọc.

| Test ID | Nguyên nhân trước và sau |
|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist [SQL: SELECT version_num FROM public.ale |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | assert 403 == 200  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | assert 403 == 200  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | assert 403 == 200  +  where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | assert False is True |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin'      - admin   + AI.Admin |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | assert False is True |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## Gọi ModelOps thật và giới hạn phép đo

Lượt cuối trên dữ liệu tổng hợp 2024/2025/2026 tạo ba trang (source/entity/concept),
hai lượt biên soạn qua model đang cấu hình `gpt-6-luna`, không dùng fallback trong
hai lượt này. Tổng token biên soạn ghi nhận: 6.476 prompt và 2.042 completion.
Không đổi model hoặc timeout của cấu hình đang chạy.

Hai lượt điều hướng ModelOps thật thực hiện mở trang rồi đọc nguồn, chọn được năm
block canonical; context trang 1.720 ký tự. Registry trang được đưa từ RAM, còn
bộ nạp/persistence/quyền được kiểm riêng bằng test DB và handler. Đây **không phải
HTTP E2E, benchmark đáp án hoặc bằng chứng điểm bộ 64 câu tăng**.

Các lần thăm dò trước lượt cuối vẫn giữ trong bằng chứng:

- Có lượt đầu ra không đạt hợp đồng hoặc quote binding, trả `unavailable`.
- Một lượt thành công trước khi hardening; không lấy nó thay bằng kết quả cuối.
- Lỗi quote binding tái hiện do planner chỉ chọn đoạn thân, thiếu heading năm;
  compiler nay bổ sung đúng ancestor IDs có sẵn. Hai output đã ghi lại đều qua
  kiểm tra sau bổ sung heading, không sửa quote hoặc hạ validator.
- Một lỗi contract cũ không lưu raw output: chưa đủ căn cứ quy chính xác cho
  Markdown code fence. Adapter hiện chỉ nhận JSON hoặc một code fence JSON trọn
  vẹn, cùng feedback field/type đã bỏ nội dung nhạy cảm. Không nhận văn bản thừa.

LLM vẫn có thể sinh sai hoặc bỏ sót ý; validator số/quote không chứng minh mọi
diễn giải ngữ nghĩa đều đúng. Trang vì vậy giữ vai trò điều hướng, không thay
thế nguồn, Evidence Binding hoặc chính sách phục vụ đang có.
Bundle lỗi cũng được lưu để tránh gọi model lặp ngoài ý muốn. Hiện chưa có nút
biên soạn lại wiki riêng; mở lại trang hoặc thử lại GET chỉ đọc trạng thái đã
lưu. Cần revision mới cho lần biên soạn mới trong quy trình hiện tại.

## Phát hiện và sửa trong full regression

Full đầu trên batch gần cuối có 27 FAIL, gồm 18 lỗi baseline và 9 lỗi mới; giữ
nguyên log/XML, không ghi nhận là PASS:

- Bảy ca automatic ingestion: chính sách wiki được gắn sau khi seal readiness,
  làm fingerprint thay đổi ngay. Đã chuyển gắn chính sách trước seal; regression
  mới kiểm cả readiness hợp lệ lẫn chặn thay đổi chính sách âm thầm.
- Một ca concurrency cũ: tên DB test có hậu tố `final` không khớp quy tắc bảo vệ
  đã có của test. Gate cuối dùng đúng mẫu tên số phiên; không nới guard của test.
- Test persistence mới dùng pool của app qua nhiều event loop của Pytest.
  Đã chuyển fixture sang engine riêng/NullPool và dispose sau dọn đúng fixture.
- Khi mở rộng focused suite, còn một ca automatic vector đụng pool inference
  khác event loop. Các test native ingestion nay mô phỏng provider wiki không
  khả dụng, kiểm thêm `unavailable/pages=[]` và vẫn giữ staging index đúng.
  Compiler/adapter/persistence và gọi thật được đo riêng, không gọi test mock là E2E.

Full tiếp theo đạt 3.020 PASS / 18 FAIL / 17 SKIP; đối chiếu exact IDs và nguyên
nhân với baseline đều khớp, không có lỗi mới. Rà soát sau đó phát hiện nhánh
candidate chưa nhận `knowledge_wiki: null` của metadata tùy chọn. Sáu biến thể
missing/null/ready qua hai luồng candidate tái hiện hai lỗi null trước sửa và
đều đạt sau sửa. Không nới quyền hoặc thay source scope. Gate release được chạy
lại vì có thay đổi mã này; không lấy full trước sửa thay cho gate release.

Một full run trung gian bị dừng trước khi hoàn tất vì adapter/compiler còn đổi;
run đó không được dùng làm gate và không được ghi nhận PASS.

## Dữ liệu vận hành và bàn giao

Đối chiếu read-only trước/sau cho collection, binding, source revision, index
revision, assistant và provider config: hash từng row khớp; số row lần lượt
5, 24, 4, 29, 5, 13. Không migration, restart, deploy, commit, push, reindex hoặc
publication trong kho thật. Thay đổi con trỏ publication chỉ nằm trong fixture
test riêng và được dọn; không phải xuất bản tài liệu người dùng.

Kiểm tra hình ảnh giao diện bằng trình duyệt chưa hoàn tất: preview cục bộ bị
`ERR_BLOCKED_BY_CLIENT`. Đã đóng tab thử nghiệm; không bypass hoặc đụng tab đăng
nhập của người dùng. Test render/hành vi và build không thay thế visual QA.

Nguồn cũ không tự có trang. Bước kiểm thực tế tiếp theo cần một revision mới,
nạp vector staging, xem trang và chạy đối chứng câu hỏi trên cùng dữ liệu; đây
chưa phải thao tác đã thực hiện trong phiên này.

Storage tạm đang giữ vì kiểm duyệt tự động từ chối thao tác xóa đệ quy
(`blocked by policy`). Không tắt chính sách và không đổi công cụ để vượt chặn.
Cả ba DB test đã DROP và xác minh không còn tồn tại. Các thư mục runtime
chưa xóa; thư mục đầu bị policy chặn, các thư mục tiếp theo giữ lại theo cùng
giới hạn bảo vệ (NOT RUN), không đổi công cụ/đường dẫn để thử vượt chặn:

- DB đã dọn: `qnu_test_context587_51bd260fb550`; Storage giữ: `D:/DuAnPhanMem/qnu-ai-platform/backend/storage/context587-runtime-51bd260fb550`.
- DB đã dọn: `qnu_test_context587final_8a02d02f7a8a`; Storage giữ: `D:/DuAnPhanMem/qnu-ai-platform/backend/storage/context587final-runtime-8a02d02f7a8a`.
- DB đã dọn: `qnu_test_context587_be756ec22a85`; Storage giữ: `D:/DuAnPhanMem/qnu-ai-platform/backend/storage/context587gate-runtime-be756ec22a85`.

Log, XML và báo cáo nằm trong thư mục `checks-final` riêng, tiếp tục giữ làm bằng chứng.
