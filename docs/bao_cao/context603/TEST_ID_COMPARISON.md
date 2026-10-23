# Context603 — Đối chiếu exact test ID

Baseline và final đều dùng DB test603, Storage riêng, network guard. Baseline chạy snapshot app đầu603.

| Lượt | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3413 | 18 | 17 | 1 |
| Final | 3468 | 18 | 17 | 1 |

Cả hai còn23 subtest PASS. Full suite vẫn FAIL nếu còn lỗi nền.

- Failure ID mới: 0; đổi cause: 0; mất ID cũ: 0; lỗi nền được sửa: 0.
- Test mới: 55, PASS: 55.
- Baseline metadata/API riêng4 FAIL trước guard mới, gồm PUT handler thật. Các contract/compiler mới chưa tồn tại trước603; không gọi thiếu module là lỗi nghiệp vụ cũ.

## Failure baseline/final

| ID | Cause giống baseline |
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

## Test mới

| ID | Final |
|---|---|
| `tests.test_compilation_engine_603::test_two_sources_same_entity_label_stay_separate_unknown_and_conditions_preserved` | PASS |
| `tests.test_compilation_engine_603::test_incremental_rebuild_calls_only_changed_source_packets_and_preserves_prior_bundle` | PASS |
| `tests.test_compilation_engine_603::test_invalid_generation_or_incomplete_independent_review_fails_closed[omit_review]` | PASS |
| `tests.test_compilation_engine_603::test_invalid_generation_or_incomplete_independent_review_fails_closed[bad_time]` | PASS |
| `tests.test_compilation_engine_603::test_invalid_generation_or_incomplete_independent_review_fails_closed[dropped_section]` | PASS |
| `tests.test_compilation_engine_603::test_unresolved_check_is_visible_and_never_auto_approved` | PASS |
| `tests.test_compilation_engine_603::test_corrupted_cache_and_wrong_revision_do_not_reuse_semantic_checks` | PASS |
| `tests.test_compilation_engine_603::test_oversized_unit_and_model_call_budget_fail_before_excess_inference` | PASS |
| `tests.test_compilation_engine_603::test_metadata_and_context_are_not_copied_as_business_conditions_by_server` | PASS |
| `tests.test_compilation_engine_603::test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed[evidence_ids]` | PASS |
| `tests.test_compilation_engine_603::test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed[condition_ids]` | PASS |
| `tests.test_compilation_engine_603::test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed[exception_ids]` | PASS |
| `tests.test_compilation_engine_603::test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed[scope]` | PASS |
| `tests.test_compilation_engine_603::test_valid_global_proof_not_offered_to_packet_cannot_be_borrowed[temporal]` | PASS |
| `tests.test_compilation_engine_603::test_synthesis_batches_fit_without_dropping_assertions_or_removing_conditions` | PASS |
| `tests.test_compilation_engine_603::test_cache_invalidates_when_semantic_manifest_changes_without_text_change` | PASS |
| `tests.test_compilation_engine_603::test_independent_topic_review_retains_relevant_evidence_excluded_by_first_pass` | PASS |
| `tests.test_compilation_engine_603::test_topic_selection_cannot_drop_unclassified_evidence` | PASS |
| `tests.test_compilation_engine_603::test_all_independently_unrelated_is_explicit_no_topic_evidence_not_fake_content` | PASS |
| `tests.test_compilation_engine_603::test_explicit_scope_proof_closure_preserves_metadata_role_without_inventing_condition` | PASS |
| `tests.test_compilation_engine_603::test_max_units_stops_before_any_topic_inference` | PASS |
| `tests.test_compilation_engine_603::test_only_known_json_rejection_has_one_bounded_correction_counted_in_budget` | PASS |
| `tests.test_compilation_engine_603::test_repeated_bad_json_stops_after_one_correction_and_provider_error_has_none` | PASS |
| `tests.test_compilation_engine_603::test_inventory_accounting_never_creates_a_fact_or_marks_unassigned_as_verified` | PASS |
| `tests.test_compilation_engine_603::test_unassigned_relevant_proof_reported_by_independent_review_blocks_approval_readiness` | PASS |
| `tests.test_compilation_lifecycle_603::test_handler_persists_readback_idempotent_human_review_without_publication_or_fact_writes` | PASS |
| `tests.test_compilation_lifecycle_603::test_concurrent_creation_has_one_inference_owner_and_both_keys_are_idempotent` | PASS |
| `tests.test_compilation_lifecycle_603::test_concurrent_review_uses_occ_and_does_not_duplicate_or_overwrite_audit` | PASS |
| `tests.test_compilation_lifecycle_603::test_source_change_or_removal_blocks_review_and_returns_no_stale_derived_text[canonical]` | PASS |
| `tests.test_compilation_lifecycle_603::test_source_change_or_removal_blocks_review_and_returns_no_stale_derived_text[raw]` | PASS |
| `tests.test_compilation_lifecycle_603::test_source_change_or_removal_blocks_review_and_returns_no_stale_derived_text[binding]` | PASS |
| `tests.test_compilation_lifecycle_603::test_source_change_or_removal_blocks_review_and_returns_no_stale_derived_text[epoch]` | PASS |
| `tests.test_compilation_lifecycle_603::test_revocation_propagates_to_reused_derivative_and_never_reactivates_on_read` | PASS |
| `tests.test_compilation_lifecycle_603::test_unresolved_semantics_cannot_be_approved_even_by_admin` | PASS |
| `tests.test_compilation_lifecycle_603::test_provider_failure_has_durable_uncertain_receipt_and_does_not_resend_same_intent` | PASS |
| `tests.test_compilation_lifecycle_603::test_handler_permissions_hash_foreign_source_and_generic_metadata_cannot_bypass_compiler` | PASS |
| `tests.test_compilation_lifecycle_603::test_storage_corruption_never_becomes_approved_or_model_fallback` | PASS |
| `tests.test_compilation_lifecycle_603::test_cancellation_keeps_a_durable_receipt_and_cannot_auto_resend` | PASS |
| `tests.test_compilation_lifecycle_603::test_source_change_while_inference_runs_does_not_commit_ready_artifact` | PASS |
| `tests.test_compilation_lifecycle_603::test_changed_idempotency_payload_and_wrong_proposal_hash_cannot_override_review` | PASS |
| `tests.test_compilation_lifecycle_603::test_failed_storage_write_is_visible_and_no_unconfirmed_artifact_pointer_is_saved` | PASS |
| `tests.test_compilation_metadata_603::test_generic_collection_metadata_cannot_import_compilation_registry[payload0]` | PASS |
| `tests.test_compilation_metadata_603::test_generic_collection_metadata_cannot_import_compilation_registry[payload1]` | PASS |
| `tests.test_compilation_metadata_603::test_generic_collection_metadata_cannot_import_compilation_registry[None]` | PASS |
| `tests.test_compilation_metadata_603::test_existing_put_handler_rejects_registry_injection_before_any_metadata_write` | PASS |
| `tests.test_compilation_modelops_603::test_route_comes_from_modelops_and_rotation_changes_only_opaque_configuration_seal` | PASS |
| `tests.test_compilation_modelops_603::test_missing_modelops_defaults_fails_without_constructing_an_inference_request` | PASS |
| `tests.test_compilation_modelops_603::test_client_cannot_choose_model_or_claim_approval_authority[preferred_provider_id]` | PASS |
| `tests.test_compilation_modelops_603::test_client_cannot_choose_model_or_claim_approval_authority[preferred_model_name]` | PASS |
| `tests.test_compilation_modelops_603::test_client_cannot_choose_model_or_claim_approval_authority[actor_id]` | PASS |
| `tests.test_compilation_modelops_603::test_client_cannot_choose_model_or_claim_approval_authority[publication]` | PASS |
| `tests.test_compilation_modelops_603::test_existing_adapter_measures_full_request_and_propagates_provider_failure` | PASS |
| `tests.test_compilation_modelops_603::test_json_adapter_keeps_observed_usage_and_does_not_leak_bad_output_in_errors` | PASS |
| `tests.test_compilation_modelops_603::test_truncated_structured_output_is_not_treated_as_complete_generation` | PASS |
| `tests.test_compilation_modelops_603::test_short_handle_transport_preserves_raw_literals_and_restores_nested_proofs` | PASS |

JUnit/log và receipts riêng trong `backend/storage/context603/checks/`. Không gộp test chạy lại riêng thành full PASS.
