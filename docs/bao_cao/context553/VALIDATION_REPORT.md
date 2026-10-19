# Context553 — kiểm chứng

## Môi trường và giới hạn

Python 3.12.13, phù hợp pyproject và lock. Pydantic 2.13.5 đúng lockfile. Audit cấu hình PostgreSQL/MinIO/Qdrant trước chạy; database ứng dụng chỉ đọc trong transaction READ ONLY. Suite chạy trên database test có ownership nonce `qnu_test_context548_eba155eff9ff`, Storage trong thư mục runtime riêng. MinIO/Qdrant/Redis test trỏ `127.0.0.1:1`; migration/seed tắt trong tiến trình test. Metadata schema chỉ tạo trong DB test trống, không migration database ứng dụng.

ModelOps cấu hình chat đã mã hóa được copy READ ONLY sang database test để baseline có cùng điều kiện; không đổi cấu hình nguồn. Task này **0 lượt gọi lại LLM**, không dùng response giả nhận là model thật. Bốn annotation gốc là kết quả live Context552; 12 assertion sửa là agent đối soát, chưa human-approved.

## Reproduce và xử lý trong lượt

- Red ban đầu: exit1, **5 FAIL/4 PASS**, đúng các khoảng hở biểu diễn assertion/mixed-scope/duplicate span/persistence.
- Nhóm focused đầu: 3 FAIL/223 PASS; v1 regression do tự chuyển span con thành kiểu mới. Sửa để selector v1 giữ hành vi cũ; v2 mới dùng assertion scoped.
- Test phủ định reference ban đầu kỳ vọng sai loại exception: ứng dụng đã chặn đúng bằng lỗi miền `SEMANTIC_PROPOSAL_INVALID`. Chỉnh test kiểm đúng code, giữ nguyên yêu cầu từ chối, không nới assertion an toàn.
- Full đầu sau batch: exit1, **19 FAIL/2395 PASS/17 SKIP/23 subtests**, gồm lỗi mới `tests/test_qnu_serving.py::test_old_unit_manifest_seal_remains_compatible`. Sửa bỏ metadata assertion rỗng khi serialize, giữ seal v1; test compatibility riêng **2 PASS**, exit0.
- Cell span probe: **1 FAIL/1 PASS**, exit1; assertion đúng span bị từ chối bởi đường liên kết ID cũ. Sửa chỉ chấp nhận EvidenceBinding trùng chính xác trong phụ thuộc đã scope của ô; span khác cùng source vẫn bị chặn.
- Lượt full `after-final` bị chủ động ngắt khi còn chạy để sửa cell span, **INTERRUPTED**, không dùng làm kết quả nghiệm thu.
- Focused cuối `focused-last`: exit0, **261 PASS** (chín module semantic/binding/lifecycle/context/contract/serving). Bổ sung fixture tham chiếu không liên quan thực sự (giờ thư viện khác đối tượng đánh giá), chạy lại hai case liên quan/không liên quan: **2 PASS**, exit0.
- Scoped Ruff: 13 file PASS, exit0. Frontend **18 tests PASS**, Biome ba file PASS, build Vite + TypeScript PASS, exit0. UI render/intent được kiểm bằng test; chưa kiểm thao tác browser thật.

## Ma trận nghiệm thu hành vi

| Yêu cầu | Test ID / bằng chứng | Kết quả đã đo |
|---|---|---|
| T01 mixed scope | `test_T01_mixed_source_unit_never_spreads_other_assertions`, `test_T01_selector_v2_blocks_whole_numbered_unit_but_keeps_full_item_negation`, `test_T01_cell_interpretation_requires_the_exact_scoped_assertion_span[True/False]` | Ba quan hệ tách riêng, không lan sang row khác; nguồn multi-item table scope bị chặn; ô chỉ nhận exact scoped span. PASS |
| T02 AM codes | `test_T02_T08_T11_persist_reload_rebuild_exact_span_and_string_codes`; checkpoint probe cuối | r003 AM-0007 nhận p050, r004 AM-0070 không nhận; raw fields giữ nguyên. PASS |
| T03 2027 | `test_T03_T04_year_groups_and_estimate_are_independent_in_facts_and_chunks`; probe trên 12 assertion | c11 có p051, c10/c12/c05/c08 không có; quan hệ cả năm là assertion riêng. PASS |
| T04 mốc từng năm | Cùng T03/T04 và probe real checkpoint | p049 tách c04–06/c07–09/c10–12, tỷ lệ chung cùng năm; không đổi issued/data-year. PASS |
| T05 reference liên quan | `test_T05_T06_reference_analysis_is_not_approval_and_accepts_only_specific_intent[related-related_context_reviewed]`, bốn negative cases `test_T05_T07_cannot_clear_related_reference_with_unrelated_or_missing_evidence` | Không tự duyệt; thiếu body/binding hoặc đổi thành không liên quan đều bị chặn. PASS |
| T06 reference không liên quan | `test_T05_T06_reference_analysis_is_not_approval_and_accepts_only_specific_intent[unrelated-not_applicable_to_target]`, rerun `unrelated-reference` | Nguồn về lịch thư viện được đối chiếu với assertion đánh giá khác đối tượng; chỉ quyết định TEST cụ thể mới cho qua. PASS, không suy diễn semantics bằng từ điển |
| T07 heading | `test_T07_heading_expansion_keeps_nested_body_and_respects_budget`; FE heading test | Mở cả mục con/body; heading trống báo thiếu, quá ngân sách báo lỗi, không hiện nút quyết định khi chỉ có heading. PASS |
| T08 footnote | Probe source checkpoint + T02/T08/T11 | Binding nguyên văn, mã chuỗi không bị ép int, c02/r001–003. PASS |
| T09 integrity | `test_T09_checkpoint_file_envelope_and_source_hash_tampering_are_rejected[file/proposal/source]`, `test_T09_same_source_same_target_different_spans_are_not_duplicates`, checkpoint probe | Hash file/envelope/source lệch đều chặn; original 14 file giữ nguyên; revised hash mới. PASS |
| T10 no approval | `test_T10_new_assertion_always_requires_specific_human_scope_review`, reference tests, eight original issue IDs preserved | Đồng ý chung bị chặn; **18 issue vẫn mở** trong checkpoint thật. PASS về guard, human decision thật NOT RUN |
| T11 lưu/rebuild | `test_T11_test_actor_handler_db_reload_keeps_assertion_and_reference` | Qua handler, DB session đóng/mở, LocalStorage và rebuild giữ reference/scope/seal. PASS với actor TEST; không phải approval thật |
| T12 regression | baseline/after XML và regression-comparison.json | Exact 18 ID/cause nền giữ nguyên, 23 ID mới PASS, không mất ID/đổi trạng thái/lỗi mới. Full vẫn FAIL |

## Đối soát checkpoint

Original hash `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3`; revised cuối `33d9cdae6fc80547aa6243ea7ac11d94b9fa5e9b765398ba569a9905870f3fc2`.

Pure validation trên bản sao RAM: 12 assertion, sáu reference assessments có full-source binding; tám issue gốc và mười issue bổ sung giữ mở. Giao nhóm A và cột 2027 được kiểm từng dòng/cột; B không nhận ngoại lệ A; p050 không lan AM-0070; p051 không lan c10/c12/2025/2026. Manifest/canonical spans PASS; 392 facts, 278 chunks, raw tables giữ nguyên. Đây là **validation của proposal**, không apply/persist trên nguồn thật.

Selector v1/v2 business/wire hash so Context552 giữ nguyên. Chỉ 10 file ứng dụng hiện có và một module assertion mới khác frozen baseline backend, đúng phạm vi; không sửa parser, retrieval ranking hoặc cấu hình provider đang chạy.

## Full suite cuối và cleanup

Baseline mới trên frozen app trước sửa: exit1, **18 FAIL/2375 PASS/17 SKIP/23 subtests**, 463,87 giây. Full cuối `after-verified`: exit1, **18 FAIL/2398 PASS/17 SKIP/23 subtests**, 427,42 giây. Đối chiếu từng ID và nguyên nhân dòng đầu: exact18 giữ nguyên, 23 case thêm đều PASS, không ID mất, không đổi trạng thái, không lỗi mới. Test T06 được tăng độ thực chất bằng reference lịch thư viện, hai biến thể đã chạy lại riêng sau khi full collect; mã ứng dụng không đổi. File XML xuất đã bỏ captured output/tracebody, giữ ID/status/first cause; log gốc ở Storage private.

Database test đã xóa sau khi kiểm ownership nonce và xác nhận vắng trong pg_database. Public audit cấu hình DB/MinIO/Qdrant trước/sau không đổi; kết nối database ứng dụng dùng READ ONLY. **Storage runtime chưa dọn:** kiểm duyệt tự động từ chối xóa `backend/storage/context548-runtime-eba155eff9ff` với “blocked by policy”, cả dạng có guard và exact literal path. Không dùng cơ chế xóa khác để vượt chặn. Thư mục còn tồn tại, ghi `BLOCKED_BY_POLICY` trong cleanup.json; cần người dùng xử lý thư mục test này. Checkpoint gốc, revised và bằng chứng được giữ để đối chiếu.

NOT RUN: human approval/apply/persist/rebuild/retrieval trên nguồn thật, nhập pending revision UI thật, whole-document ModelOps API, native provider schema enforcement, browser tương tác thực. Dừng đúng WAITING_FOR_REVIEW theo prompt; không E2E PASS.
