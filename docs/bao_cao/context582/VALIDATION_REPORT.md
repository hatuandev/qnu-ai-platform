# Context582 — Test IDs và kiểm chứng cuối

Full Pytest: **FAIL**, exit1; 2.985 PASS, 18 FAIL, 17 SKIP và 23 subtests PASS. 18 lỗi trùng baseline Context580 theo đúng ID/nguyên nhân; không có test cũ đổi trạng thái, thêm 27 test PASS. Mã ứng dụng giữ nguyên trong full cuối.

## 18 lỗi nền — vẫn là FAIL

| Test ID | Baseline | Hiện tại | Nguyên nhân đầu tiên, giữ nguyên |
| --- | --- | --- | --- |
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL | FAIL | asyncpg.exceptions.UndefinedTableError: relation "public.alembic_version" does not exist |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL | FAIL | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL | FAIL | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL | FAIL | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | FAIL | FAIL | assert 403 == 200 |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | FAIL | FAIL | assert 403 == 200 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | FAIL | FAIL | assert 403 == 400 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | FAIL | FAIL | assert 403 == 201 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL | FAIL | assert 403 == 200 |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | FAIL | FAIL | assert 403 == 200 |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | FAIL | FAIL | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | FAIL | FAIL | assert False is True |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | FAIL | FAIL | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | FAIL | FAIL | assert False is True |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | FAIL | FAIL | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection |

## Regression mới

27 ca đều PASS trong full cuối. Canary ban đầu có 11 ca: 10 FAIL/1 PASS. Các biến thể còn lại được thêm trong quá trình triển khai; không giả rằng tất cả đã chạy trước sửa.

| Test ID | Trước sửa trong canary | Cuối |
| --- | --- | --- |
| `tests.test_pdf_content_fidelity::test_table_engine_lost_glyph_is_blocking_instead_of_a_source_unknown` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_full_width_group_after_header_is_not_a_second_header` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_verified_headerless_grid_is_literal_only_and_never_becomes_facts` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_only_visible_native_glyphs_override_conflicting_ocr[True]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_only_visible_native_glyphs_override_conflicting_ocr[False]` | PASS | PASS |
| `tests.test_pdf_content_fidelity::test_code_background_is_not_a_figure_but_unrelated_artwork_remains` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_value_label_inside_a_solid_bar_does_not_make_it_decorative_code_background` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_glyph_baselines_restore_reordered_identifier_without_rewriting_raw_matrix[source_key]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_glyph_baselines_restore_reordered_identifier_without_rewriting_raw_matrix[001_02]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_glyph_baselines_restore_reordered_identifier_without_rewriting_raw_matrix[2027_02]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_glyph_baselines_restore_reordered_identifier_without_rewriting_raw_matrix[am_k2]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence[text]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence[missing]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence[extra]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence[geometry]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_source_verifier_rejects_changed_or_missing_canonical_evidence[source]` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_replayed_raw_native_proposal_cannot_forge_a_header_role` | FAIL | PASS |
| `tests.test_pdf_content_fidelity::test_continuations_need_matching_headers_and_no_new_caption[False]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_continuations_need_matching_headers_and_no_new_caption[True]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_small_bottom_note_is_preserved_without_assigning_a_table_scope` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_page_break_fragment_preserves_two_cells_and_dependency_without_filling_identity` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_numbered_bottom_paragraph_requires_separator_to_be_a_native_footnote[True]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_numbered_bottom_paragraph_requires_separator_to_be_a_native_footnote[False]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_pdf_image_needs_its_own_authenticated_transcription_not_an_ocr_label` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_indexing_verifier_rejects_broken_pdf_source_evidence[sidecar_hash]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_indexing_verifier_rejects_broken_pdf_source_evidence[sidecar_missing]` | NOT RUN | PASS |
| `tests.test_pdf_content_fidelity::test_indexing_verifier_rejects_broken_pdf_source_evidence[forged_native]` | NOT RUN | PASS |

## Lệnh và môi trường

- Cwd Pytest: `D:/DuAnPhanMem/qnu-ai-platform/backend`.
- Full: `.venv/Scripts/python.exe -m pytest -q --basetemp=<owned-runtime>/full-verified --junitxml=<context582>/checks-final/full-verified.xml`; 473,27 giây, exit1.
- Focused: cùng Python, 9 file PDF/source/serving/studio/automatic/DOCX, 159 PASS, exit0; chi tiết command nằm trong `checks/final-guards-run.json`.
- Ruff: 11 file app/test đã sửa trong lượt582, exit0. Không lint hoặc build frontend vì không sửa frontend.
- Hai database có nonce sở hữu riêng đã xóa/kiểm không còn; Storage local tạm còn do auto-review chặn xóa, không bypass.
- Đã xác minh DB/MinIO/Qdrant local; regression dùng DB/Storage riêng và endpoint dịch vụ127.0.0.1:1, không migration ứng dụng.
- Live PDF reparse/embedding dùng service hiện có, nguồn thật trong kho được giao; 695 ô/cặp source/MD/JSON/projection/API tải/parity327/327/prepublication đều PASS.
- Publication và benchmark64: NOT RUN. Không dùng kết quả parser thay cho chất lượng trả lời RAG.

[Báo cáo tổng thể](PDF_BLOCKERS_AND_VALIDATION.md).
