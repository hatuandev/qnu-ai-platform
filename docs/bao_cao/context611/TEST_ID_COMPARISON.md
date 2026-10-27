# Context611 — Đối chiếu exact test ID

Baseline là full chốt Context608 (nguồn app bắt đầu611 giống608); final611 dùng DBtest mới, LocalStorage riêng/network guard. Defaults metadata typed inactive/no credential trong DBthử, không sửa runtime model. Có các lượt bị dừng/gián đoạn được giữ INCOMPLETE riêng; không dùng thay full cuối. OpenBLAS1thread chỉ theo tiến trình. So sánh exact IDs/cause, không suy từ tổng PASS.

| Run | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3564 | 18 | 17 | 1 |
| Final | 3586 | 18 | 17 | 1 |

Cả hai có23subtestPASS. Full vẫn FAIL khi còn lỗi nền.

- Failure mới:0; cause đổi:0; ID mất:0; lỗi nền sửa:0.
- Test mới:22; PASS:22.

## Lỗi nền

| ID | Cause baseline |
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
| `tests.test_compilation_checkpoint_611::test_checkpoint_resume_preserves_complete_bundle_without_repeating_completed_calls` | PASS |
| `tests.test_compilation_checkpoint_611::test_completed_schema_rejection_replays_feedback_without_resending_bad_call` | PASS |
| `tests.test_compilation_checkpoint_611::test_concurrent_resume_has_one_owner_and_no_duplicate_model_calls[False]` | PASS |
| `tests.test_compilation_checkpoint_611::test_concurrent_resume_has_one_owner_and_no_duplicate_model_calls[True]` | PASS |
| `tests.test_compilation_checkpoint_611::test_existing_assertion_factoring_is_lossless_and_retains_each_value_and_raw_proof` | PASS |
| `tests.test_compilation_checkpoint_611::test_failure_before_any_uncertain_call_can_resume_the_known_complete_prefix` | PASS |
| `tests.test_compilation_checkpoint_611::test_handler_pauses_then_resumes_completed_phases_and_keeps_idempotency` | PASS |
| `tests.test_compilation_checkpoint_611::test_medium_is_an_explicit_request_field_and_reaches_payload_without_numeric_guessing` | PASS |
| `tests.test_compilation_checkpoint_611::test_new_packet_cache_entries_do_not_change_the_resumed_stage_sequence` | PASS |
| `tests.test_compilation_checkpoint_611::test_partitioned_reviews_keep_all_raw_context_and_require_every_item[False]` | PASS |
| `tests.test_compilation_checkpoint_611::test_partitioned_reviews_keep_all_raw_context_and_require_every_item[True]` | PASS |
| `tests.test_compilation_checkpoint_611::test_persisted_resume_rejects_stale_or_untrusted_state_without_inference[checksum]` | PASS |
| `tests.test_compilation_checkpoint_611::test_persisted_resume_rejects_stale_or_untrusted_state_without_inference[config]` | PASS |
| `tests.test_compilation_checkpoint_611::test_persisted_resume_rejects_stale_or_untrusted_state_without_inference[permission]` | PASS |
| `tests.test_compilation_checkpoint_611::test_persisted_resume_rejects_stale_or_untrusted_state_without_inference[source]` | PASS |
| `tests.test_compilation_checkpoint_611::test_persisted_resume_rejects_stale_or_untrusted_state_without_inference[uncertain]` | PASS |
| `tests.test_compilation_checkpoint_611::test_resume_requires_version_and_rejects_legacy_unknown_client_policy` | PASS |
| `tests.test_compilation_checkpoint_611::test_separate_request_budgets_do_not_double_charge_quotes_to_extraction[400-True]` | PASS |
| `tests.test_compilation_checkpoint_611::test_separate_request_budgets_do_not_double_charge_quotes_to_extraction[600-False]` | PASS |
| `tests.test_compilation_checkpoint_611::test_total_budget_cannot_be_reset_by_replaying_checkpoints` | PASS |
| `tests.test_compilation_checkpoint_611::test_two_identical_coverage_inputs_still_make_two_independent_calls` | PASS |
| `tests.test_compilation_checkpoint_611::test_uncertain_stage_is_never_sent_again_on_resume` | PASS |

JUnit/log/run receipt baseline608/release-checks và final611/final-checks; focused/probes riêng không được ghép thành full PASS.
