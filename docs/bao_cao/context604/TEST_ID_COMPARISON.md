# Context604 — Đối chiếu exact test ID

Baseline và final đều dùng DB test604, Storage riêng, network guard. Baseline chạy snapshot app đầu604, giữ thay đổi600–603.

| Lượt | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3468 | 18 | 17 | 1 |
| Final | 3520 | 18 | 17 | 1 |

Cả hai còn23 subtest PASS. Full suite vẫn FAIL nếu còn lỗi nền.

- Failure ID mới: 0; đổi cause: 0; mất ID cũ: 0; lỗi nền được sửa: 0.
- Test mới: 52, PASS: 52.
- Bốn regression tái hiện phạm vi/năm FAIL trước sửa và PASS sau sửa. Baseline full không gồm test mới604; test ID cũ giữ nguyên. Các thay đổi fixture model chỉ thích ứng hợp đồng mới và số nhóm synthesis theo ngân sách, vẫn kiểm đúng một inference owner và không resend.

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
| `tests.test_compilation_semantics_604::test_unproved_compound_scope_cannot_be_supported_by_title_and_reviewer_boolean` | PASS |
| `tests.test_compilation_semantics_604::test_supported_section_cannot_mix_source_or_data_year_scope[True]` | PASS |
| `tests.test_compilation_semantics_604::test_supported_section_cannot_mix_source_or_data_year_scope[False]` | PASS |
| `tests.test_compilation_semantics_604::test_heading_cannot_invent_a_year_absent_from_its_assertion_scopes` | PASS |
| `tests.test_compilation_semantics_604::test_atomic_literal_scope_preserves_source_spelling[D\u1ef1 th\u1ea3o]` | PASS |
| `tests.test_compilation_semantics_604::test_atomic_literal_scope_preserves_source_spelling[nh\xf3m A]` | PASS |
| `tests.test_compilation_semantics_604::test_atomic_literal_scope_preserves_source_spelling[2024]` | PASS |
| `tests.test_compilation_semantics_604::test_publication_and_data_time_roles_can_coexist_without_merging_years` | PASS |
| `tests.test_compilation_semantics_604::test_supersedes_direction_must_agree_with_blind_source_witness[True]` | PASS |
| `tests.test_compilation_semantics_604::test_supersedes_direction_must_agree_with_blind_source_witness[False]` | PASS |
| `tests.test_compilation_semantics_604::test_blind_endpoint_membership_survives_transport_without_encoding_proposed_direction` | PASS |
| `tests.test_compilation_semantics_604::test_later_date_does_not_prove_supersession[unresolved]` | PASS |
| `tests.test_compilation_semantics_604::test_later_date_does_not_prove_supersession[contradicted]` | PASS |
| `tests.test_compilation_semantics_604::test_direction_review_cannot_omit_duplicate_or_invent_proofs[duplicate]` | PASS |
| `tests.test_compilation_semantics_604::test_direction_review_cannot_omit_duplicate_or_invent_proofs[missing]` | PASS |
| `tests.test_compilation_semantics_604::test_direction_review_cannot_omit_duplicate_or_invent_proofs[foreign_proof]` | PASS |
| `tests.test_compilation_semantics_604::test_direction_review_cannot_omit_duplicate_or_invent_proofs[self]` | PASS |
| `tests.test_compilation_semantics_604::test_scope_cannot_assemble_a_literal_from_different_proofs` | PASS |
| `tests.test_compilation_semantics_604::test_short_handle_roundtrip_maps_singular_coverage_id_but_never_literal_values` | PASS |
| `tests.test_compilation_semantics_604::test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact[supporting_context]` | PASS |
| `tests.test_compilation_semantics_604::test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact[unrelated]` | PASS |
| `tests.test_compilation_semantics_604::test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact[required_assertion]` | PASS |
| `tests.test_compilation_semantics_604::test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact[unresolved]` | PASS |
| `tests.test_compilation_semantics_604::test_missed_evidence_reconciles_without_changing_original_review_or_fabricating_fact[disagreement]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[foreign_source]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[missing]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[duplicate]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[unknown_assertion]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[unsupported_context]` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_requires_exact_ledger_and_same_source_association[unrelated_with_assertion]` | PASS |
| `tests.test_compilation_semantics_604::test_handler_blocks_admin_approval_when_scope_is_literal_unproved_despite_positive_model` | PASS |
| `tests.test_compilation_semantics_604::test_rehashing_machine_ready_flag_cannot_bypass_persisted_review_ledger` | PASS |
| `tests.test_compilation_semantics_604::test_coverage_transport_limits_claim_ids_and_restores_them_without_touching_literals` | PASS |
| `tests.test_compilation_semantics_604::test_empty_assertion_catalog_cannot_invent_a_supporting_claim` | PASS |
| `tests.test_compilation_semantics_604::test_extraction_does_not_remap_new_local_ids_to_prior_assertions` | PASS |
| `tests.test_compilation_semantics_604::test_navigation_hint_status_never_becomes_source_authored_or_publication_status` | PASS |
| `tests.test_compilation_semantics_604::test_optional_context_association_disagreement_is_only_candidate_never_effective_fact[True]` | PASS |
| `tests.test_compilation_semantics_604::test_optional_context_association_disagreement_is_only_candidate_never_effective_fact[False]` | PASS |
| `tests.test_compilation_semantics_604::test_unresolved_actual_fact_still_blocks_despite_any_optional_context_policy` | PASS |
| `tests.test_compilation_semantics_604::test_offered_context_deferred_is_audited_separately_without_dropping_primary_or_guessing_relevance` | PASS |
| `tests.test_compilation_semantics_604::test_deferring_an_unoffered_proof_still_fails_in_context_aware_inventory` | PASS |
| `tests.test_compilation_semantics_604::test_legacy_policy_remains_readable_but_cannot_gain_new_v3_approval[v1]` | PASS |
| `tests.test_compilation_semantics_604::test_legacy_policy_remains_readable_but_cannot_gain_new_v3_approval[v2]` | PASS |
| `tests.test_compilation_semantics_604::test_synthesis_reference_contract_rejects_unknown_or_missing_ids_before_semantic_binding[foreign_section]` | PASS |
| `tests.test_compilation_semantics_604::test_synthesis_reference_contract_rejects_unknown_or_missing_ids_before_semantic_binding[foreign_endpoint]` | PASS |
| `tests.test_compilation_semantics_604::test_synthesis_reference_contract_rejects_unknown_or_missing_ids_before_semantic_binding[foreign_proof]` | PASS |
| `tests.test_compilation_semantics_604::test_synthesis_reference_contract_rejects_unknown_or_missing_ids_before_semantic_binding[missing_proof]` | PASS |
| `tests.test_compilation_semantics_604::test_complete_budget_matches_exact_prepared_reference_contract_and_transport_instruction` | PASS |
| `tests.test_compilation_semantics_604::test_qualifier_view_is_exact_existing_binding_not_an_invented_exception_or_condition` | PASS |
| `tests.test_compilation_semantics_604::test_empty_dependencies_cannot_gain_qualifier_bindings_from_nearby_raw_text` | PASS |
| `tests.test_compilation_semantics_604::test_revision_date_uses_existing_event_role_without_changing_v1_binding_schema` | PASS |
| `tests.test_compilation_semantics_604::test_synthesis_keeps_fitting_source_data_and_issue_date_in_one_context_group` | PASS |

JUnit/log và receipts riêng trong `backend/storage/context604/checks/`. Không gộp test chạy lại riêng thành full PASS.
