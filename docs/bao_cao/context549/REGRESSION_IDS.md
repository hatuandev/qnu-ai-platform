# Exact regression IDs — context549

Baseline configured:18FAIL/2289PASS/17SKIP; after:18FAIL/2336PASS/17SKIP. Both exit1.
Full suite remains FAIL.0removed,0changed statuses,0new failing IDs;47added IDs all PASS.

## Residual failures, identical first causes

- tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import — sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist
- tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export — app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_admissions'
- tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export — app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_regulations'
- tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item — redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection.
- tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests — app.core.exceptions.DomainException: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI.
- tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page — app.core.exceptions.DomainException: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI.
- tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api — assert 403 == 200
- tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint — assert 403 == 200
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled — assert 403 == 201
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled — assert 403 == 400
- tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit — assert 403 == 200
- tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback — assert 403 == 200
- tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies — AssertionError: assert 'legacy_payload_schema' in []
- tests/test_tools.py::test_fact_layer_lookup_tool_found — assert False is True
- tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims — AssertionError: assert 'AI.Admin' == 'admin'
- tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts — app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_admissions'
- tests/test_universal_tools.py::test_fact_layer_lookup_tool — assert False is True
- tests/test_vllm_reranker.py::test_vllm_embedding_generation — app.core.exceptions.DomainException: Embedding provider 'vllm' khÃ´ng kháº£ dá»¥ng: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI.

## Added IDs, all PASS

- tests/test_json_output_contract.py::test_bad_request_is_not_key_failure_or_context_cropping[error0-MODEL_OUTPUT_REQUEST_INVALID]
- tests/test_json_output_contract.py::test_bad_request_is_not_key_failure_or_context_cropping[error1-MODEL_OUTPUT_CONTRACT_UNSUPPORTED]
- tests/test_json_output_contract.py::test_bad_request_is_not_key_failure_or_context_cropping[error2-MODEL_CONTEXT_EXCEEDED]
- tests/test_json_output_contract.py::test_compiled_schema_matches_every_business_field_and_nested_selector
- tests/test_json_output_contract.py::test_expansion_does_not_reset_format_retry_limit
- tests/test_json_output_contract.py::test_fallback_rechecks_capability_and_strict_never_silently_downgrades
- tests/test_json_output_contract.py::test_finish_and_refusal_precede_syntax[metadata0-response_incomplete]
- tests/test_json_output_contract.py::test_finish_and_refusal_precede_syntax[metadata1-refusal]
- tests/test_json_output_contract.py::test_finish_and_refusal_precede_syntax[metadata2-refusal]
- tests/test_json_output_contract.py::test_http_through_modelops_and_real_binder_stages_only_valid_retry
- tests/test_json_output_contract.py::test_old_adapter_signature_without_thinking_budget_preserves_contract
- tests/test_json_output_contract.py::test_packet_two_fails_after_retry_never_stages_first_packet
- tests/test_json_output_contract.py::test_parameter_negotiation_cannot_remove_output_format
- tests/test_json_output_contract.py::test_request_service_adapter_http_preserves_contract[None-capabilities0-None]
- tests/test_json_output_contract.py::test_request_service_adapter_http_preserves_contract[contract1-capabilities1-json_schema]
- tests/test_json_output_contract.py::test_request_service_adapter_http_preserves_contract[contract2-capabilities2-json_object]
- tests/test_json_output_contract.py::test_request_service_adapter_http_preserves_contract[contract3-capabilities3-None]
- tests/test_json_output_contract.py::test_retry_keeps_deadline_and_cancellation_without_mutation[False]
- tests/test_json_output_contract.py::test_retry_keeps_deadline_and_cancellation_without_mutation[True]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[evidence-1]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[fail-2]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[length-1]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[refusal-1]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[schema-1]
- tests/test_json_output_contract.py::test_retry_same_packet_real_binding_atomic_stage[success-2]
- tests/test_json_output_contract.py::test_selector_shape_is_never_filled_coerced_or_dropped[coerce]
- tests/test_json_output_contract.py::test_selector_shape_is_never_filled_coerced_or_dropped[enum]
- tests/test_json_output_contract.py::test_selector_shape_is_never_filled_coerced_or_dropped[extra]
- tests/test_json_output_contract.py::test_selector_shape_is_never_filled_coerced_or_dropped[missing_nested]
- tests/test_json_output_contract.py::test_selector_shape_is_never_filled_coerced_or_dropped[null]
- tests/test_json_output_contract.py::test_semantic_contract_rejects_stream_and_ambiguous_choices
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[[]-prompt_only-selector_schema]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[```json\n{}-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[```json\n{}\n``` extra-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[```json\n{}\n```-json_schema-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{"context_id":"a","context_id":"b"}-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{"value":Infinity}-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{"value":NaN}-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{} trailing-prompt_only-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{} {}-json_object-json_syntax]
- tests/test_json_output_contract.py::test_strict_parser_rejects_without_repair[{}-prompt_only-selector_schema]
- tests/test_json_output_contract.py::test_transport_retry_shares_byte_budget_and_preserves_schema
- tests/test_json_output_contract.py::test_valid_unicode_escaped_text_and_brackets[False]
- tests/test_json_output_contract.py::test_valid_unicode_escaped_text_and_brackets[True]
- tests/test_json_output_contract.py::test_whole_response_rejects_missing_duplicate_and_extra_data[duplicate]
- tests/test_json_output_contract.py::test_whole_response_rejects_missing_duplicate_and_extra_data[extra_data]
- tests/test_json_output_contract.py::test_whole_response_rejects_missing_duplicate_and_extra_data[missing]

Red probe separately: missing/duplicate transitioned FAIL→PASS; extra_data PASS→PASS.
These three IDs were not in the original full baseline; do not claim full-suite FAIL→PASS.
