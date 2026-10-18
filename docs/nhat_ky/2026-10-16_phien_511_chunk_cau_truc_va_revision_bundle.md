# Phiên 511 — Bước 4–5: chunks theo cấu trúc và bản dẫn xuất có phiên bản

## Yêu cầu và phạm vi

Tiếp bước 1–3 của phiên 510: chia đoạn giữ cấu trúc đã duyệt, ghim bản sạch,
facts và vector vào đúng revision, xuất bản/rollback tường minh. Backend-only;
không migration, OCR, model, reindex nguồn thật, restart, deploy hoặc Git push.

## Nguyên nhân và thay đổi

- Regression trước sửa tái hiện: công thức bị ngắt ở dòng trống; nguồn còn
  yêu cầu review vẫn tạo chunks nếu lifecycle cũ ghi `ready`. Hai ca đều FAIL
  đúng nguyên nhân trước sửa. Ca kiểm tra lại sau remote I/O cũng FAIL trước sửa.
- `normalization/structure_chunks.py`: embedding view `structure-chunks-v1`.
  Giữ khối fenced code/công thức, đoạn trước công thức và chú giải kế tiếp cùng
  scope, nhóm danh sách cha–con, header/đơn vị/chú thích đã có context graph và
  footnote Markdown tham chiếu định danh. Không dùng từ điển tuyển sinh hay gọi LLM.
- Ghi source unit IDs, exact source span và context-only IDs; không ghi đè unit
  manifest, canonical, raw extraction hoặc OCR. Không đưa heading giả bên trong
  code fence vào heading context cho đoạn sau. Bộ lọc năm xem cả các unit trong
  nhóm, không chỉ unit đầu. Không suy năm từ filename hay xác nhận OCR đúng.
- Đoạn văn thông thường dùng strategy đã cấu hình nhưng kiểm tra text/subspan
  và khoảng hở; không chấp nhận strategy làm đổi hoặc bỏ nội dung. Nhóm cấu trúc
  ưu tiên tính nguyên vẹn hơn preferred chunk size; vượt hard `max_chars` báo
  `SOURCE_UNIT_TOO_LARGE`, không cắt ngầm. Chú thích thiếu/trùng báo cần đối soát.
- `derived_bundle.py`: `derived-bundle-v1` ghim source/binding, hash binary gốc
  đã lưu, canonical, metadata/page manifest, parser/normalizer, units, context
  graph, facts, toàn manifest chunks (kể cả provenance metadata) và config.
  Đây là kiểm tra toàn vẹn, không phải chữ ký chống sửa DB hoặc chứng nhận nội dung.
- `chunk_set_service.py`: chặn review còn mở, key mới có phiên bản và hash facts;
  cùng text nhưng khác annotation không dùng chung tập dẫn xuất. Tái dùng cùng
  binding phải deep-copy và tạo seal mới cho revision mới. Xử lý chia đoạn qua
  ranh giới thread, không thêm worker/framework.
- Build mới lưu bundle hash vào parity report. Candidate/publish/rollback đối
  soát lại nguồn, chunks DB, facts và revision. Facts dùng so sánh đa tập để
  không mất số lượng bản ghi trùng. Không cho bỏ marker report để vượt seal.
- Publish toàn thế hệ và theo lựa chọn kiểm tra lại sau remote I/O, trước đổi
  pointer; CAS giữ cả source/index/epoch. Xuất bản toàn thế hệ có activation audit.
- Rollback thế hệ chọn revision từng xuất bản từ activation audit, không chọn
  staging mới hơn. `revision_publish_service.py` giữ endpoint từng nguồn cho
  bản sealed cùng thế hệ: khóa theo thứ tự collection/binding, kiểm tra lịch sử
  rollback, target vector space, bundle và audit actor. Đổi thế hệ dùng endpoint
  thế hệ. Không tắt points cũ của bản sealed: snapshot đang chạy và rollback còn dùng.
- Nguồn biên tập và nguồn đang phục vụ là hai pointer khác nhau. Rollback index
  không tự ghi đè bản sạch mới đang biên tập/chờ nạp.

## Kiểm chứng thực chạy

Từ `backend`:

- Regression trọng tâm: **114 PASS**, exit 0; XML local
  `storage/structure511-focused.xml`. Gồm units/context links, chunk sets,
  candidate, selected publication, generation rollback, legacy publication.
- Test PostgreSQL thật dùng dữ liệu fixture riêng trong outer transaction và
  savepoint, hoàn tác toàn bộ: seal hợp lệ; sai provenance chunk bị chặn; xóa
  marker report không vượt seal; sai hash facts bị chặn; rollback qua service
  hiện có đúng index/epoch/actor. Chỉ vector adapter được mock, không gọi model.
- So sánh offline cùng file MD mẫu phiên 509, không sửa file: 240 source units,
  cũ/mới cùng 235 chunks, max chars 926 → 970; 157 chunks có context refs;
  nguồn giữ hash, span bounds hợp lệ. Mẫu này không có nhóm công thức/list cần
  gộp. Đây là đối soát cấu trúc, **không phải đo chất lượng trả lời hoặc retrieval**.
- Ruff có phạm vi: **PASS**, exit 0.
- Lần full đầu: 1922 PASS / 15 FAIL / 17 SKIP, exit 1 (212,64 giây).
  So baseline510, 4 lỗi thêm đều là fixture `SimpleNamespace` thiếu trường nguồn
  cho gate review ở `test_vector_load_workflow.py`. Đổi fixture sang model nguồn
  thật, không sửa assertion hoặc nới gate; thêm negative case ready nhưng review required.
- Rà cuối phát hiện thêm ranh giới index đổi generation trong remote I/O:
  regression FAIL trước sửa; bổ sung kiểm tra binding/generation/source sau refresh
  cho cả selected và whole-generation publication.
- Final regression mở rộng: **128 PASS**, exit 0, 11,40 giây;
  `storage/structure511-final-focused.xml`.
- Full cuối: **1928 PASS / 11 FAIL / 17 SKIP**, exit 1, 206,83 giây;
  `storage/structure511-final-full.xml` và `.txt`. So sánh exact test IDs với
  `clean510-full.xml`: đúng 11 lỗi nền cũ, không thêm ID; **tổng suite vẫn FAIL**.
- UTF-8 không BOM/LF và liên kết local các tài liệu mới, `git diff --check`
  phạm vi sửa: PASS. Không thay cấu hình Git line ending dù Git có cảnh báo autocrlf.

Lệnh thực chạy (cwd `D:/DuAnPhanMem/qnu-ai-platform/backend`):

```text
.venv/Scripts/python.exe -m ruff check <14 file Python trong phạm vi>
.venv/Scripts/python.exe -m pytest tests/test_structure_chunks_511.py tests/test_derived_bundle_511.py tests/test_vector_load_workflow.py tests/test_knowledge_chunk_set_and_vector_generation.py tests/test_knowledge_v3_backfill_and_cutover.py tests/test_selected_vector_publish.py tests/test_candidate_artifact_integration.py tests/test_knowledge_units.py tests/test_source_context_stage2.py tests/test_knowledge_publishing_v2.py tests/test_publishing_v2_hardening.py -q --tb=short --junitxml=storage/structure511-final-focused.xml
.venv/Scripts/python.exe -m pytest -q --tb=short --junitxml=storage/structure511-final-full.xml
```

11 ID lỗi nền (đã đối chiếu, không xử lý trong batch):

```text
tests.test_consulting_dispatcher::test_dispatch_admissions_with_export
tests.test_consulting_dispatcher::test_dispatch_regulations_with_export
tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint
tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled
tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit
tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback
tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies
tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims
tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts
```

## Giới hạn và vận hành

- Không tự đưa phiên bản mới vào index đang phục vụ. Duyệt bản sạch → nạp vector
  vào bản staging → xem candidate → xuất bản là các thao tác riêng. Không cần
  upload lại file chỉ để đổi chunker; reindex là thao tác cần người vận hành chọn.
  BE/worker phải nạp mã mới theo quy trình triển khai được cho phép; phiên này
  không tự restart và chưa chứng minh runtime đã dùng contract mới.
- Bản cũ không có seal vẫn có cầu tương thích, không được giả nhận là đã kiểm
  chứng theo contract mới. Rollback hiện đại cần lịch sử xuất bản; thiếu lịch sử
  thì chặn, không suy một staging là bản từng phục vụ. Legacy archived bridge
  chỉ áp dụng index cũ không có source revision V2.
- Đọc binary gốc từ StorageDriver, live Qdrant/embedding, UI tương tác và chấm
  chatbot 10/20/82: **NOT RUN**. Không đổi collection thực hoặc policy provider.
- Chọn chú giải/cấu trúc là heuristic; công thức quá lớn hoặc chú giải mơ hồ
  cần người duyệt. `token_count` vẫn là ước lượng ký tự, không có bảo đảm tokenizer.
- Chưa chứng minh tăng độ chính xác RAG, không gán điểm chất lượng từ test kỹ thuật.
