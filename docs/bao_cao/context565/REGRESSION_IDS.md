# Context565 — Exact test IDs

Baseline: Context564 full-final. Gate focused: focused-current + orchestration-compat. Full gate: full-verified.

## Tests mới

| Test ID | Focused | Full |
|---|---|---|
| `tests/test_context565_entity_metric.py::test_numbers_are_not_source_verified_codes[N\u0103m 2026 c\xf3 100 SV]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_numbers_are_not_source_verified_codes[H\u1ecdc ph\xed 1000000 \u0111\u1ed3ng]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_numbers_are_not_source_verified_codes[\u0110i\u1ec3m 6.8]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_label_words_are_never_candidates[m\xe3]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_label_words_are_never_candidates[m\xe3 ch\u01b0\u01a1ng tr\xecnh]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_label_words_are_never_candidates[m\xe3 ng\xe0nh]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_label_words_are_never_candidates[m\xe3 nhi\u1ec7m v\u1ee5]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_label_words_are_never_candidates[m\xe3 CT]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_candidates_keep_identity_and_leading_zeroes[ZX-0007]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_candidates_keep_identity_and_leading_zeroes[zx-0007]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_candidates_keep_identity_and_leading_zeroes[0012]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_candidates_keep_identity_and_leading_zeroes[AB_0120]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_candidates_keep_identity_and_leading_zeroes[7480107]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_column_is_not_a_name_or_metric[headers0-row0-Ch\u01b0\u01a1ng tr\xecnh A-ZX-0007]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_column_is_not_a_name_or_metric[headers1-row1-Ch\u01b0\u01a1ng tr\xecnh A-ZX-0007]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_column_is_not_a_name_or_metric[headers2-row2-0012-0012]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_column_is_not_a_name_or_metric[headers3-row3-ZX-0007-ZX-0007]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2026 / Quy m\xf4 / Ch\u1ec9 ti\xeau (SV)-quota-expected_quota]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2026 / Ghi nh\u1eadn / S\u1ed1 l\u01b0\u1ee3ng (SV)-reported_count-reported_count]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2025 / Ghi nh\u1eadn / S\u1ed1 l\u01b0\u1ee3ng (SV)-reported_count-reported_count]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2027 / D\u1ef1 b\xe1o / S\u1ed1 l\u01b0\u1ee3ng \u01b0\u1edbc t\xednh-estimate-estimated_count]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2026 / T\u1ef7 l\u1ec7 (%)-rate-rate]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2026 / S\u1ed1 l\u01b0\u1ee3ng (SV)-None-None]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_header_path_disambiguates_quantities[2026 / Ghi nh\u1eadn / Ch\u1ec9 ti\xeau (SV)-None-None]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[Ch\u1ec9 ti\xeau m\xe3 ZX-0007 n\u0103m 2026?-expected0]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[S\u1ed1 l\u01b0\u1ee3ng ghi nh\u1eadn m\xe3 ZX-0007 n\u0103m 2026?-expected1]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[S\u1ed1 l\u01b0\u1ee3ng ghi nh\u1eadn m\xe3 ZX-0007 n\u0103m 2025?-expected2]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[Ch\u1ec9 ti\xeau m\xe3 ZX-0070 n\u0103m 2026?-expected3]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[Ch\u1ec9 ti\xeau m\xe3 ZX-0007 n\u0103m 2025?-expected4]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[Ch\u1ec9 ti\xeau m\xe3 ZX-0007 n\u0103m 2098?-expected5]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_derivation_through_temporal_selection_preserves_requested_tuple[Ch\u1ec9 ti\xeau m\xe3 ZX-0099 n\u0103m 2026?-expected6]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_code_does_not_inject_static_major_alias` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_alphanumeric_code_cross_page_continuation_is_source_bound` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_resolution_keeps_source_and_review_status` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[source_revision_id-other]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[content_hash-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[source_unit_id-missing]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[column_id-c3]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[field_state-ambiguous]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[unit_manifest_hash-wrong]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_coordinates_stay_blocked[raw_value-999]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_legacy_wrong_binding_or_index_cannot_borrow_a_row` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_explicit_human_metric_override_is_preserved` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_wrong_unit_or_missing_year_never_selects_an_adjacent_quantity[Ch\u1ec9 ti\xeau (l\u1edbp) m\xe3 ZX-0007 n\u0103m 2026?]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_wrong_unit_or_missing_year_never_selects_an_adjacent_quantity[Ch\u1ec9 ti\xeau m\xe3 ZX-0007?]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_current_metric_and_unit_override_stale_rewritten_constraints` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_code_and_year_do_not_turn_a_narrative_condition_into_a_quantity` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_cutoff_method_is_not_a_quantity_unit` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_row_anchor_exact_codes_are_case_insensitive_and_do_not_match_metric_values` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_multi_entity_partial_coverage_is_not_supported` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_two_source_units_require_explicit_unit` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_fact_resolution_debug_is_not_in_public_telemetry` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_exact_identity_and_legacy_metric_are_filtered_before_sql_limit[reported_count]` | PASS | PASS |
| `tests/test_context565_entity_metric.py::test_exact_identity_and_legacy_metric_are_filtered_before_sql_limit[expected_quota]` | PASS | PASS |

## Lỗi nền theo ID và nguyên nhân

| Test ID | Context564 | Context565 |
|---|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | assert 403 == 200 | assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | assert 403 == 200 | assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201 | assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400 | assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200 | assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | assert 403 == 200 | assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | assert False is True | assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin' | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | assert False is True | assert False is True |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## Contract được đổi công khai

`tests/test_facts.py::test_extract_admissions_table_row_facts`: bare quantity giữ raw header và unknown, thêm assertion không có quota sai. ID/fixture/value giữ nguyên; xem IMPLEMENTATION_REPORT.
