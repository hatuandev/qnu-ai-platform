# Context614 — Đối chiếu test ID

Baseline là full cuối Context613; trạng thái ứng dụng đầu Context614 khớp hash baseline. Final dùng database riêng có nonce ownership, LocalStorage riêng và guard chặn egress ngoài loopback. Không ghép lượt chạy dở hoặc focused vào full.

| Run | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Context613 | 3601 | 18 | 17 | 1 |
| Context614 final | 3622 | 18 | 17 | 1 |

Lỗi mới: 0; cause đổi: 0; ID mất: 0; lỗi nền đổi trạng thái: 0.

## Test mới

| Exact ID | Final |
|---|---|
| `tests.test_compilation_structure_614::test_blank_header_keeps_raw_candidate_and_first_data_row_instead_of_promoting_role` | PASS |
| `tests.test_compilation_structure_614::test_cell_coordinates_preserve_column_year_unknown_zero_and_metric_distinction` | PASS |
| `tests.test_compilation_structure_614::test_compact_structure_preserves_column_overrides_and_temporal_authority_once` | PASS |
| `tests.test_compilation_structure_614::test_corrupt_field_metadata_cannot_replace_literal_cell_value` | PASS |
| `tests.test_compilation_structure_614::test_engine_persists_revalidates_structure_and_invalidates_changed_field_link_cache` | PASS |
| `tests.test_compilation_structure_614::test_field_note_is_not_attached_to_other_row_or_other_revision` | PASS |
| `tests.test_compilation_structure_614::test_header_candidate_does_not_consume_alpha_north_data_or_infer_numeric_role` | PASS |
| `tests.test_compilation_structure_614::test_header_role_needs_unique_literal_layout_evidence[duplicate_header]` | PASS |
| `tests.test_compilation_structure_614::test_header_role_needs_unique_literal_layout_evidence[header_text_disagrees]` | PASS |
| `tests.test_compilation_structure_614::test_large_structural_context_is_blocked_without_dropping_qualifier_evidence` | PASS |
| `tests.test_compilation_structure_614::test_long_review_explanation_does_not_change_scope_or_completeness_verdict` | PASS |
| `tests.test_compilation_structure_614::test_missing_or_foreign_structural_reference_fails_closed` | PASS |
| `tests.test_compilation_structure_614::test_multilevel_header_paths_and_escaped_pipes_keep_positional_cells` | PASS |
| `tests.test_compilation_structure_614::test_numbered_section_candidates_and_table_header_reach_row_without_crossing_branch` | PASS |
| `tests.test_compilation_structure_614::test_operational_packet_count_can_scale_without_changing_default_or_evidence` | PASS |
| `tests.test_compilation_structure_614::test_oversized_coverage_audit_keeps_all_debt_without_dispatch_or_fake_classification` | PASS |
| `tests.test_compilation_structure_614::test_oversized_optional_repair_remains_visible_unresolved_without_source_trimming` | PASS |
| `tests.test_compilation_structure_614::test_planned_request_reserves_exact_minimal_correction_without_reserving_a_third_call` | PASS |
| `tests.test_compilation_structure_614::test_planner_measures_complete_source_and_temporal_metadata_without_fixed_correction_reserve` | PASS |
| `tests.test_compilation_structure_614::test_request_handles_map_all_structural_proofs_without_rewriting_raw_text` | PASS |
| `tests.test_compilation_structure_614::test_topic_planner_budgets_independent_selection_with_full_prior_result` | PASS |

## Lỗi nền

| Exact ID | Cause baseline, rút gọn để đọc |
|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist [SQL: SELECT version_num FROM public.alembic_version] (Background on this error at: https://sqlalche.me/e/20/f405) |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | assert 403 == 200 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | assert 403 == 200 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | assert 403 == 200 + where 403 = <Response [403 Forbidden]>.status_code |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | assert False is True |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin' - admin + AI.Admin |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | assert False is True |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

So sánh cause dùng toàn bộ message trong JUnit, không dùng phần rút gọn của bảng. Full còn lỗi nền vẫn là FAIL. Xem receipt, log và JUnit trong `backend/storage/context614/final-validation/`.
