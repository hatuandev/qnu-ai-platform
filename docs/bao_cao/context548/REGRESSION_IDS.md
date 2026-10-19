# Regression IDs — context548

Baseline:24FAIL/2266PASS/17SKIP; final:18FAIL/2289PASS/17SKIP; both exit1.
No removed IDs, no newly failing IDs;18residual first causes are identical.

## Six reproduced failures fixed

- tests/test_context548_patch.py::test_expand_table_counts_full_rows_not_only_private_ids — FAIL → PASS
- tests/test_context548_patch.py::test_issue_only_cannot_become_clean_empty — FAIL → PASS
- tests/test_context548_patch.py::test_mixed_generic_review_cannot_clear_missing_context — FAIL → PASS
- tests/test_context548_patch.py::test_multiyear_binding_requires_specific_canonical_scope_review — FAIL → PASS
- tests/test_context548_patch.py::test_publication_guard_catches_legacy_empty_unresolved — FAIL → PASS
- tests/test_context548_patch.py::test_reject_and_changes_requested_preserve_context_blockers — FAIL → PASS

## Eighteen residual failures (full suite remains FAIL)

- tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import — sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist
- tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export — app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions'
- tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export — app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations'
- tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item — redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection.
- tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests — app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI.
- tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page — app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI.
- tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api — assert 403 == 200
- tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint — assert 403 == 200
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled — assert 403 == 201
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled — assert 403 == 400
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit — assert 403 == 200
- tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback — assert 403 == 200
- tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies — AssertionError: assert 'legacy_payload_schema' in []
- tests/test_tools.py::test_fact_layer_lookup_tool_found — assert False is True
- tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims — AssertionError: assert 'AI.Admin' == 'admin'
- tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts — app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions'
- tests/test_universal_tools.py::test_fact_layer_lookup_tool — assert False is True
- tests/test_vllm_reranker.py::test_vllm_embedding_generation — app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI.

## Seventeen added IDs, all PASS

- tests/test_context548_patch.py::test_api_deadline_retains_exact_code_and_draft — PASS
- tests/test_context548_patch.py::test_api_whole_actual_document_uses_same_deadline_and_preserves_pending_scope — PASS
- tests/test_context548_patch.py::test_cancellation_on_packet_two_is_not_output_error_or_partial_stage — PASS
- tests/test_context548_patch.py::test_context_resolution_cannot_be_forged_or_close_missing_source[actor] — PASS
- tests/test_context548_patch.py::test_context_resolution_cannot_be_forged_or_close_missing_source[issue] — PASS
- tests/test_context548_patch.py::test_context_resolution_cannot_be_forged_or_close_missing_source[missing] — PASS
- tests/test_context548_patch.py::test_context_resolution_cannot_be_forged_or_close_missing_source[span] — PASS
- tests/test_context548_patch.py::test_context_resolution_cannot_be_forged_or_close_missing_source[target] — PASS
- tests/test_context548_patch.py::test_deadline_during_stage_thread_never_mutates_caller — PASS
- tests/test_context548_patch.py::test_omission_retains_issue_and_reprocessing_requires_new_bound_source — PASS
- tests/test_context548_patch.py::test_reject_issue_over_active_keeps_effective_set_but_blocks_source[changes_requested] — PASS
- tests/test_context548_patch.py::test_reject_issue_over_active_keeps_effective_set_but_blocks_source[rejected] — PASS
- tests/test_context548_patch.py::test_reprocess_model_proof_becomes_new_human_issue_not_auto_resolution — PASS
- tests/test_context548_patch.py::test_runner_context_missing_differs_from_specific_scope_review — PASS
- tests/test_context548_patch.py::test_scope_decisions_snapshot_reload_session_and_tamper — PASS
- tests/test_context548_patch.py::test_scope_simple_conflict_unchanged_and_issue_identity_ignores_reason — PASS
- tests/test_context548_patch.py::test_v1_hash_recipe_remains_unchanged_but_unresolved_needs_review — PASS
