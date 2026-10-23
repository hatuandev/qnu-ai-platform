# Context606 — Đối chiếu exact test ID

Baseline và final dùng cùng DB test606, Storage riêng, network guard. Baseline chạy snapshot app đầu606, giữ thay đổi600–605; bỏ file test606 mới. Final chạy code cuối, gồm31 test mới606.

| Lượt | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3520 | 18 | 17 | 1 |
| Final | 3551 | 18 | 17 | 1 |

Cả hai còn23 subtest PASS. Full suite vẫn FAIL nếu còn lỗi nền.

- Failure ID mới: 0; đổi cause: 0; mất ID cũ: 0; lỗi nền được sửa: 0.
- Test mới: 31, PASS: 31.
- Regression entity graph5FAIL, output packing1FAIL, scalar error code4FAIL trước sửa. Wire feature baseline10FAIL vì chưa có mapping/restore và alias. Cùng31 test mới PASS trong focused cuối; bảng dưới đối chiếu final full. Fixture lifecycle đếm proof coverage và packet thực, giữ idempotency/reuse/revocation; không bỏ assertion để làm xanh.

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
| `tests.test_compilation_context_606::test_default_packet_plan_leaves_output_headroom_without_discarding_selected_proofs` | PASS |
| `tests.test_compilation_context_606::test_packet_output_policy_splits_primary_work_and_keeps_dependency_proofs[1]` | PASS |
| `tests.test_compilation_context_606::test_packet_output_policy_splits_primary_work_and_keeps_dependency_proofs[2]` | PASS |
| `tests.test_compilation_context_606::test_packet_output_policy_splits_primary_work_and_keeps_dependency_proofs[4]` | PASS |
| `tests.test_compilation_context_606::test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review[missing_entities]` | PASS |
| `tests.test_compilation_context_606::test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review[foreign_entity]` | PASS |
| `tests.test_compilation_context_606::test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review[duplicate_entity]` | PASS |
| `tests.test_compilation_context_606::test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review[duplicate_assertion]` | PASS |
| `tests.test_compilation_context_606::test_packet_contract_rejects_invalid_local_entity_graph_before_semantic_review[orphan_entity]` | PASS |
| `tests.test_compilation_context_606::test_scalar_state_rejection_has_actionable_code_without_source_text[present-None-compilation_present_requires_scalar]` | PASS |
| `tests.test_compilation_context_606::test_scalar_state_rejection_has_actionable_code_without_source_text[present-  -compilation_present_requires_scalar]` | PASS |
| `tests.test_compilation_context_606::test_scalar_state_rejection_has_actionable_code_without_source_text[unknown-0-compilation_unresolved_cannot_hold_scalar]` | PASS |
| `tests.test_compilation_context_606::test_scalar_state_rejection_has_actionable_code_without_source_text[conflict-unclear-compilation_unresolved_cannot_hold_scalar]` | PASS |
| `tests.test_compilation_context_606::test_invalid_local_graph_is_known_adapter_contract_error_without_retry_or_raw_output_leak` | PASS |
| `tests.test_compilation_context_606::test_explicit_source_limitation_survives_compilation_and_reload_without_scalar_or_invented_time[Ng\xe0y ban h\xe0nh: ng\xe0y     th\xe1ng      n\u0103m 2032.]` | PASS |
| `tests.test_compilation_context_606::test_explicit_source_limitation_survives_compilation_and_reload_without_scalar_or_invented_time[M\u1ee9c t\u1ed1i \u0111a: \u2014 (ch\u01b0a \u0111\u01b0\u1ee3c ngu\u1ed3n x\xe1c \u0111\u1ecbnh).]` | PASS |
| `tests.test_compilation_context_606::test_explicit_source_limitation_survives_compilation_and_reload_without_scalar_or_invented_time[K\xfd hi\u1ec7u \u25c7 ch\u01b0a c\xf3 ph\u1ea7n \u0111\u1ecbnh ngh\u0129a trong ngu\u1ed3n.]` | PASS |
| `tests.test_compilation_context_606::test_explicit_source_limitation_survives_compilation_and_reload_without_scalar_or_invented_time[Kho\u1ea3ng \xe1p d\u1ee5ng: t\u1eeb ng\xe0y ... \u0111\u1ebfn ng\xe0y ...; ch\u1ec9 c\xf3 n\u0103m tham kh\u1ea3o 2034.]` | PASS |
| `tests.test_compilation_context_606::test_unknown_value_does_not_override_unresolved_evidence_review` | PASS |
| `tests.test_compilation_context_606::test_source_limitation_policy_change_invalidates_cached_extractions_and_keeps_previous_bundle[source_limitations]` | PASS |
| `tests.test_compilation_context_606::test_source_limitation_policy_change_invalidates_cached_extractions_and_keeps_previous_bundle[extraction_instruction]` | PASS |
| `tests.test_compilation_context_606::test_model_value_state_alias_is_round_tripped_without_changing_raw_text_or_temporal_unknown` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[source_unspecified-None-True]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[source_unspecified-0-False]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[present-0-True]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[present-None-False]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[unknown-None-False]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[unresolved-None-False]` | PASS |
| `tests.test_compilation_context_606::test_model_assertion_schema_separates_source_unspecified_from_review_verdict[conflict-None-True]` | PASS |
| `tests.test_compilation_context_606::test_model_adapter_restores_legacy_state_before_durable_contract_validation` | PASS |
| `tests.test_compilation_context_606::test_empty_draft_review_rejects_invented_items_and_keeps_missed_evidence` | PASS |

JUnit/log và receipts riêng trong `backend/storage/context606/checks/`. Không gộp test chạy lại riêng thành full PASS.
