# Phiên 545 — Đợt 1: vòng đời annotation ngữ nghĩa đã duyệt

## Yêu cầu và phạm vi

Thực hiện prompt đợt 1 do người dùng cung cấp: lưu bền vững, xuất/đọc lại và khôi phục annotation theo đúng revision, giữ scope và cell state qua projection/facts/chunks. Không thêm semantic resolver, không đổi parser/Markdown Standard/retrieval/ModelOps hoặc chính sách unknown. Không nạp lại nguồn thật, duyệt nguồn thật, index, publish, deploy, restart, commit hoặc push.

Mã đầu phiên: `278a5e9590296e0660b79e2107cbf4c506721a50`. Git sạch trước sửa. Có fingerprint Python trước thay đổi tại `backend/storage/annotation545-before.json`. Tuân các skill backend, ingestion và clean code. AGENTS quy định một phạm vi dữ liệu ứng dụng chung: tenant/workspace cũ không phải phân vùng cấp quyền; kiểm quyền actor tại API và collection/binding/revision tại service.

## Khảo sát và lỗi tái hiện

| Điểm tích hợp | Trước sửa | Sau sửa |
|---|---|---|
| Tạo đề xuất | `propose_source_semantics` / `stage_semantic_annotations` lưu pending trong artifact | Tái sử dụng; đề xuất thay thế được tính trên projection cơ sở, không xóa bộ hiệu lực |
| Duyệt | `review_semantic_proposals` sửa artifact, commit parse_provenance | Ghi snapshot bất biến và đọc kiểm checksum trước, rồi commit con trỏ/lịch sử trong cùng giao dịch của revision |
| Nguồn chuẩn | `qnu_docx_artifacts` lưu cặp MD/JSON riêng | Giữ nguyên schema và cặp nguồn, bổ sung sidecar ngữ nghĩa |
| Rebuild | `prepare_standard_revision` gọi `project_document`, không nạp quyết định | `semantic_store.rebuild_projection` dựng base từ pair rồi áp bộ hiệu lực; không gọi model để khôi phục |
| Hiệu đính/reparse | Tạo revision mới từ nội dung/snapshot | Không kế thừa phê duyệt; giữ chỉ dấu cần đối soát từ revision trước |
| Facts/chunks | Manifest/graph/facts seals và metadata source unit | Thêm semantic hash khi có annotation; field refs giữ theo cột và đi vào metadata chunk |
| Nạp/index/publish | Guard pair/review và derived bundle | Kiểm snapshot hiệu lực và projection tương ứng trước khi tạo chunk hoặc dùng bundle dẫn xuất |
| Download | md/json là bản trích xuất nguồn | Giữ md/json; thêm `format=bundle` có manifest và sidecar hiệu lực |

Caller thực tế đã đối chiếu: import và `execute_reparse` gọi prepare; `qnu_revision.update_standard_revision` tạo revision hiệu đính; chunk set service tạo dữ liệu index; `derived_bundle.validate_index_bundle` kiểm trước publication; router download và review gọi service tương ứng.

Test tái hiện trước sửa (`annotation545-reproduction-actual.xml`): **1 FAIL**, state đã duyệt quay về mặc định khi prepare dựng projection từ document. Đây khác với serialize/deepcopy artifact vốn vẫn giữ state. Fixture cũ chỉ dùng cho projection; các test lưu pair mới đã bổ sung body/origin hợp lệ để đi qua validator thật, không bỏ validator.

## Thiết kế và nơi lưu có thẩm quyền

`KnowledgeSourceRevision.parse_provenance.semantic_store` là con trỏ có thẩm quyền của revision, gồm schema, `active` và `history`. Payload quyết định nằm trong StorageDriver:

`<snapshot_storage_path>.<sha256>.qnu-semantic-v1.json`

Snapshot gồm identity binding/revision/hash nguồn/pair/projection version; enrichment temporal trước hiệu đính đã ghim; payload đề xuất nguyên bản và proposal hash; review actor/thời điểm/lý do/decision riêng; semantic hash. Không sửa trạng thái trong payload đã băm để tái sử dụng hash cũ. Hash ngữ nghĩa loại phần audit thời gian chạy; snapshot checksum vẫn bao phủ toàn bộ quyết định.

`structured_artifact`, manifest, graph, facts và chunks là dẫn xuất. `semantic_effective` chỉ là thông tin dẫn xuất để so seal, không phải một nơi phê duyệt độc lập. Tạo proposal mới giữ nguyên con trỏ hiệu lực; approve thay bộ hiệu lực, reject giữ bộ trước. Không cộng dồn lịch sử lên graph. Rebuild luôn xuất phát từ base, phục hồi enrichment đã ghim, đối chiếu input hash **trước** sửa cell state rồi áp đúng một bộ hiệu lực.

Ghi Storage trước và đọc lại bytes/hash/identity, sau đó mới cập nhật con trỏ DB. Lỗi commit rollback con trỏ cũ; file bất biến chưa được tham chiếu có thể còn như orphan. Không tự xóa orphan hoặc file đang theo dõi. `source_purge` biết các đường dẫn sidecar/history để bảo toàn ownership và tránh bỏ sót tham chiếu khi có yêu cầu xóa sau này.

Mất sidecar, checksum sai, revision/binding/pair đổi hoặc evidence không còn khớp đều là lỗi; không coi như chưa từng có annotation. API cập nhật dùng khóa nguồn/idle và nạp lại revision với `populate_existing` trước duyệt. Hash không thay cho quyền actor.

## Xuất, đọc lại và tương thích

API hiện có `/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/qnu-markdown?format=bundle` được bổ sung định dạng ZIP. Quyền `ai.knowledge.view` vẫn bắt buộc. Gói gồm:

- `source.qnu-rag-v1.md`, `source.qnu-doc-v1.json` là cặp nguồn chưa sửa.
- `source.qnu-semantic-v1.json` khi có bộ hiệu lực đã ghim.
- Raw evidence/resources nếu pair tham chiếu.
- `manifest.json` ghi identity, source reference, mapping file và checksum; phân biệt source-only với reviewed-sidecar.

`read_external_bundle` chỉ đọc bytes trong ZIP qua reader cô lập, không fetch đường dẫn do manifest cung cấp từ Storage server; kiểm budget/member/hash/pair. Kết quả luôn `trusted=False`, annotation là candidate cần quy trình duyệt. Không có UI nhập bundle mới hoặc API cho client tự đặt trusted.

`restore_internal_bundle` nhận revision đã được caller server xác minh, so manifest và active reference với bản ghi có thẩm quyền, rồi dùng đường rebuild chung. Bundle không mang toàn bộ history audit; history vẫn giữ ở revision/Storage. File MD riêng không bảo toàn toàn bộ quan hệ đã duyệt nếu thiếu sidecar/loader.

Revision chưa từng có annotation đi qua luồng tương thích. Với metadata verified cũ: khôi phục proposal nguyên bản trước khi kiểm hash; yêu cầu audit hợp lệ, đúng projection binding và exact base input. Nếu không chứng minh được (ví dụ enrichment cũ không khôi phục chính xác), trả `SEMANTIC_LEGACY_REVIEW_REQUIRED`; không tạo audit giả. Có `backfill_verified_semantics` xác định cho draft, được dùng trước tạo proposal thay thế; giữ nguyên người/thời điểm duyệt cũ. Không backfill hàng loạt hoặc sửa revision đang phục vụ. Legacy chưa có sidecar cần backfill trên draft trước khi xuất bundle reviewed; md/json cũ vẫn theo guard hiện hành.

## File và hàm thay đổi

- Mới `services/semantic_store.py`: authority, snapshot I/O, replay, enrichment recipe, legacy backfill, verification.
- Mới `services/semantic_bundle.py`: export, external loader, internal restore, download service.
- `services/semantic_annotations.py`: giữ nguyên resolver, stage trên base; review ghi snapshot, rollback khi thất bại; tạo đề xuất giữ bộ hiệu lực; facts mang semantic hash.
- `services/qnu_serving.py`: loader hỗ trợ reader bytes; prepare dùng replay, bảo toàn pending, không rebuild revision ready; approval kiểm bộ hiệu lực.
- `services/qnu_revision.py`, `services/source_reparse.py`, `services/source_ingestion_service.py`: ranh giới revision mới, stale review refresh và transaction review.
- `normalization/retrieval_models.py`, `retrieval_units.py`, `structure_chunks.py`, `services/source_links.py`, `derived_bundle.py`, `chunk_set_service.py`: semantic seal và scope qua dữ liệu dẫn xuất. Trường mới rỗng không đổi hash manifest cũ.
- `router.py`: thêm `format=bundle` vào download hiện có; không thêm màn hình.
- `source_purge.py`: nhận diện sidecar hiệu lực/lịch sử thuộc nguồn; không chạy xóa.
- `tests/test_semantic_lifecycle.py`: bộ vòng đời mới; hai test cũ cập nhật fixture/assertion để có source pair thật và nhận trường neutral mới.

## Kết quả và cách chạy lại

Python/Ruff của `backend/.venv`, không cài dependency. Cwd root repo với focused; cwd `backend` với full. Các test asyncio trên Windows cần socket nội bộ: lượt sandbox bị treo ở `socketpair` trước test, đã dừng và chạy ngoài sandbox. Thư mục temp mặc định không có quyền; các lượt cuối dùng `--basetemp` riêng dưới Storage workspace, không đổi config ứng dụng.

- Reproduction trước sửa: **FAIL 1**, exit 1, 3.86s.
- Baseline thực đo trước sửa: **FAIL 13 / PASS 2134 / SKIP 17 / ERROR 60 / 23 subtests**, exit 1, 192.61s. 60 ERROR là quyền thư mục temp mặc định; cần đối chiếu từng ID với full cuối, không mặc định baseline chỉ có 13 lỗi.
- Focused gần cuối: **211 PASS**, exit 0, 45.74s. Phạm vi: semantic lifecycle/proposals, serving, review536/541, derived bundle, structure chunks, source purge, studio revision safety, PDF markdown. Lệnh cuối có trong machine report; full cuối bao gồm code/test mới nhất.
- Ruff trên Python sửa và file mới: **PASS**, exit 0. Diff/UTF-8/LF và links được kiểm cuối phiên.
- Full cuối: **FAIL 13 / PASS 2223 / SKIP 17 / ERROR 0 / 23 subtests**, exit 1, 257.50s. Exact 13 FAIL IDs trùng baseline đo trước sửa, không lỗi mới. 60 ERROR baseline trở thành PASS khi dùng basetemp trong workspace; đây là sửa điều kiện chạy test, không phải sửa lỗi chức năng bằng annotation. **29/29 test vòng đời mới PASS** trong full cuối. Tổng suite vẫn FAIL.
- JUnit cuối: `backend/storage/annotation545-full-final.xml`; machine report gồm command/cwd/exit, code/fixture fingerprints, mọi test IDs và đối chiếu: `backend/storage/annotation545-validation-report.json`.

Lệnh chạy lại:

```powershell
# Cwd repo root; chọn thư mục basetemp mới, không dùng thư mục chứa dữ liệu cần giữ.
backend/.venv/Scripts/python.exe -m pytest -q backend/tests/test_semantic_lifecycle.py --basetemp=backend/storage/pytest545-rerun --junitxml=backend/storage/annotation545-rerun.xml
# Cwd backend
.venv/Scripts/python.exe -m pytest -q --basetemp=storage/pytest545-full-rerun --junitxml=storage/annotation545-full-rerun.xml
```

Test mới dùng service ứng dụng thật; mock chỉ ở biên lỗi I/O/commit, ModelOps và lịch khóa. Các ca persistence thực dùng PostgreSQL hiện có với **chỉ fixture mới**, savepoint cho commit service trong một outer transaction luôn rollback, không DDL hoặc thay nguồn thật. Đóng session rồi mở session khác đọc JSON từ DB và bytes từ LocalStorage. Đây là persistence DB/Storage thực trong giao dịch cô lập; không phải thử durability sau crash hoặc S3 thật.

Hai request review cạnh tranh được kiểm ở service với lịch khóa giả lập tại biên DB và truy vấn PostgreSQL thật trên connection fixture dùng chung. Chỉ một quyết định được ghi, bên còn lại stale. **Chưa stress hai connection PostgreSQL độc lập**; không gộp mức này thành chứng minh concurrency production.

## Ma trận nghiệm thu T01–T14

| Ca | Bằng chứng |
|---|---|
| T01 | Pending không thay graph/fields/facts hoặc pointer hiệu lực |
| T02 | Review service thật, đóng session, tải DB JSON và file snapshot qua Storage lại |
| T03/T04/T05 | c4 không lan c3; not_stated giữ raw, facts không hồi sinh; `/` vẫn ambiguous và guard xuất bản vẫn chặn |
| T06/T07 | Export ZIP, lưu file, đọc bằng driver mới, internal restore và rebuild ba lần không nhân bản |
| T08/T09 | Mismatch nguồn/revision/binding/path/hash/file/derived projection; external approved không có quyền; API viewer không được review, không quyền view không được download |
| T10 | Thay c4 bằng c3 loại liên kết cũ; reject giữ pointer và history trước |
| T11 | Storage fail, read-back corrupt, commit fail, stale review và hai call cạnh tranh theo mức mô phỏng nêu trên |
| T12 | Không có annotation, verified legacy đủ chứng cứ, legacy thiếu chứng cứ, referenced file mất được xử lý khác nhau |
| T13 | Chunk giữ `field_context_refs`; consumer `unit_context_ids` đúng cột; semantic/unit/graph/fact seals đổi khi scope đổi dù raw text không đổi |
| T14 | DOCX thực, checksum cố định, C-2027 theo ba cột 2027 và D-AM-0007 đúng một dòng sau export/restore. Ca hai note giống chữ ở hai bảng dùng fixture tổng quát riêng, không sửa DOCX gốc |

DOCX SHA256: `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`. Đối chiếu OOXML độc lập: 10 bảng; Bảng 2 có 50 hàng Word = 1 header + 49 hàng thân; đủ 45 mã NV-01…NV-45. Kết quả tại `backend/storage/annotation545-docx-inventory.json`.

Ví dụ round-trip máy đọc được do test T06 tạo trong Storage test tại `evidence/roundtrip-report.json`; JUnit ghi đường dẫn. Bản sao thuận tiện: `backend/storage/annotation545-roundtrip.json`. Báo cáo có identity, original proposal, review, sidecar reference/checksum, before/after semantic fingerprint, trạng thái ô, c3/c4 contexts, facts equality và chunk metadata. Proposal là dữ liệu TEST xác định, không phải kết quả ModelOps thật. Gói ZIP và bytes MD/JSON/sidecar còn trong cùng thư mục test.

## Giới hạn và đợt 2

- Không kiểm provider ModelOps thật, trình duyệt, production S3, durability sau crash hoặc stress hai connection độc lập; không cần các bước đó để chạy unit/service test đợt này.
- Không duyệt các PDF/DOCX thật hoặc chuyển trạng thái nguồn trong kho. Duyệt trong test không phải phê duyệt nghiệp vụ.
- Chưa thêm UI nhập bundle; chỉ loader/service, API download và test round-trip. Markdown độc lập vẫn là bản nguồn, không được quảng cáo mang đủ annotation sidecar.
- Legacy không đủ fingerprint/enrichment phải đối soát lại. Không suy quan hệ từ graph để tự tạo trạng thái approved.
- Unknown và guard QNU_UNRESOLVED_CELLS giữ nguyên. Không đổi BM25/embedding/reranker; benchmark và provider thật để đợt sau.

## Kết luận đợt 1

Đạt các contract đợt 1 trong mức unit/service/API với dependency test và PostgreSQL/LocalStorage thực trong giao dịch cô lập. Không mất annotation sau source-pair rebuild; mismatch không được bỏ qua; scope/state/facts/chunk seal đúng bộ hiệu lực. Không gộp thành end-to-end production PASS. Full suite vẫn FAIL do các ID dưới đây:

```text
tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export
tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export
tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint
tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit
tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback
tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies
tests/test_tools.py::test_fact_layer_lookup_tool_found
tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims
tests/test_universal_tools.py::test_fact_layer_lookup_tool
tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts
```
