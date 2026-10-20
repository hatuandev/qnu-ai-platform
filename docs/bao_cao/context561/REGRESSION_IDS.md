# Đối chiếu test ID Context561

Baseline lịch sử Context558, không chạy lại trên database ứng dụng. Lượt đầu đầy đủ: 2490 PASS / 21 FAIL / 17 SKIP, exit 1; phát hiện ba regression mới.

Lượt cuối: {'SKIP': 17, 'PASS': 2494, 'FAIL': 18}, exit 1. Các test mới: 28; regression mới còn lại: 0; thay đổi nguyên nhân lỗi nền: 0. Full suite vẫn là **FAIL**.

## Ba ca được xử lý

- `tests/test_qnu_header_and_cell_states.py::test_headerless_docx_preserves_every_row_without_trusting_docling_flags[values0]`: baseline PASS → lượt đầu FAIL → lượt cuối PASS
- `tests/test_qnu_header_and_cell_states.py::test_headerless_docx_preserves_every_row_without_trusting_docling_flags[values1]`: baseline PASS → lượt đầu FAIL → lượt cuối PASS
- `tests/test_qnu_header_and_cell_states.py::test_duplicate_table_content_with_different_roles_does_not_guess_source_association`: baseline PASS → lượt đầu FAIL → lượt cuối PASS

## Các lỗi còn lại

| Test ID | Baseline | Hiện tại | Nguyên nhân đầu tiên |
|---|---|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL | FAIL | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL | FAIL | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL | FAIL | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL | FAIL | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | FAIL | FAIL | assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | FAIL | FAIL | assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | FAIL | FAIL | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | FAIL | FAIL | assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | FAIL | FAIL | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | FAIL | FAIL | assert False is True |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | FAIL | FAIL | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## Test mới

- `tests/test_docx_layout_fidelity.py::test_explicit_header_keeps_data_values_present` — PASS
- `tests/test_docx_layout_fidelity.py::test_header_role_does_not_disambiguate_identical_native_table_content` — PASS
- `tests/test_docx_layout_fidelity.py::test_missing_raw_row_is_not_certified` — PASS
- `tests/test_docx_layout_fidelity.py::test_prose_prefix_is_not_a_standalone_list_item` — PASS
- `tests/test_docx_layout_fidelity.py::test_quoted_list_content_maps_after_number_and_opening_quote` — PASS
- `tests/test_docx_layout_fidelity.py::test_source_merge_stays_one_literal_without_assigning_group_scope` — PASS
- `tests/test_docx_layout_fidelity.py::test_tampered_field_fails_revalidation` — PASS
- `tests/test_docx_layout_fidelity.py::test_untyped_source_grid_is_literal_only_never_promotes_alpha_to_header` — PASS
- `tests/test_docx_layout_fidelity.py::test_wrong_source_does_not_resolve_any_flag` — PASS
- `tests/test_qnu_fact_identity.py::test_final_identity_is_not_constant_across_distinct_source_pages` — PASS
- `tests/test_qnu_fact_identity.py::test_final_provenance_identity_survives_orm_materialization_without_changes` — PASS
- `tests/test_qnu_fact_identity.py::test_legacy_projection_is_not_silently_rewritten` — PASS
- `tests/test_qnu_fact_identity.py::test_new_identity_is_deterministic_and_preserves_zero_and_code` — PASS
- `tests/test_qnu_fact_identity.py::test_unknown_identity_policy_fails_closed` — PASS
- `tests/test_source_figure_review.py::test_body_change_after_review_is_detected` — PASS
- `tests/test_source_figure_review.py::test_cross_collection_cannot_record_confirmation` — PASS
- `tests/test_source_figure_review.py::test_explicit_transcription_keeps_audit_and_does_not_create_relations` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[binding]` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[body]` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[image]` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[no_actor]` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[no_confirmation]` — PASS
- `tests/test_source_figure_review.py::test_invalid_review_fails_closed[source]` — PASS
- `tests/test_source_figure_review.py::test_real_db_record_is_authenticated_idempotent_and_queued_only` — PASS
- `tests/test_source_figure_review.py::test_receipt_in_markdown_is_not_a_server_record` — PASS
- `tests/test_source_figure_review.py::test_unapproved_image_stays_blocking` — PASS
- `tests/test_source_figure_review.py::test_unauthenticated_actor_cannot_record` — PASS
- `tests/test_worker_cold_start.py::test_worker_settings_imports_in_a_fresh_process_without_importing_api_first` — PASS

Không đổi assertion của 18 lỗi nền, không tắt kiểm tra quyền, không migration để che lỗi môi trường. Các lỗi fixture/seed, quyền, Redis và provider là FAIL thực tế trong test harness này. Chúng không được đổi thành PASS dựa trên kết quả live riêng. JUnit, exit code và log đầy đủ giữ tại `backend/storage/context561/tests/`.
