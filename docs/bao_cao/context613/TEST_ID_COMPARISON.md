# Context613 — Đối chiếu exact test ID

Baseline là full chốt Context611; final613 dùng DBtest mới, LocalStorage riêng và network guard. Defaults metadata typed inactive/no credential trong DBthử, không sửa runtime model. Có các lượt bị dừng/gián đoạn được giữ INCOMPLETE riêng; không dùng thay full cuối. So sánh exact IDs/cause, không suy từ tổng PASS.

| Run | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3586 | 18 | 17 | 1 |
| Final | 3601 | 18 | 17 | 1 |

Cả hai có23subtestPASS. Full vẫn FAIL khi còn lỗi nền.

- Failure mới:0; cause đổi:0; ID mất:0; lỗi nền sửa:0.
- Test mới:15; PASS:15.

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
| `tests.test_compilation_groups_613::test_capacity_failure_through_handler_has_explicit_stage_and_no_retry_or_publication` | PASS |
| `tests.test_compilation_groups_613::test_cross_group_shared_names_require_raw_evidence_and_independent_verdict` | PASS |
| `tests.test_compilation_groups_613::test_cross_relation_budget_deferral_keeps_candidate_without_effective_relation[direction]` | PASS |
| `tests.test_compilation_groups_613::test_cross_relation_budget_deferral_keeps_candidate_without_effective_relation[review]` | PASS |
| `tests.test_compilation_groups_613::test_fallback_is_sized_for_its_own_profile_and_unknown_capacity_is_explicit` | PASS |
| `tests.test_compilation_groups_613::test_label_overlap_is_only_a_candidate_and_search_exhaustion_remains_unknown` | PASS |
| `tests.test_compilation_groups_613::test_large_compilation_keeps_all_objects_sections_checks_and_resume_checkpoints[1]` | PASS |
| `tests.test_compilation_groups_613::test_large_compilation_keeps_all_objects_sections_checks_and_resume_checkpoints[2]` | PASS |
| `tests.test_compilation_groups_613::test_large_output_request_and_capacity_profile_roundtrip_are_endpoint_bound` | PASS |
| `tests.test_compilation_groups_613::test_model_budget_uses_resolved_limits_instead_of_global_24k_8192_caps` | PASS |
| `tests.test_compilation_groups_613::test_partitioned_synthesis_review_keeps_raw_context_and_exact_global_coverage[supported]` | PASS |
| `tests.test_compilation_groups_613::test_partitioned_synthesis_review_keeps_raw_context_and_exact_global_coverage[unresolved]` | PASS |
| `tests.test_compilation_groups_613::test_provider_update_persists_capacity_and_old_forms_cannot_silently_clear_it` | PASS |
| `tests.test_compilation_groups_613::test_synthesis_can_pack_a_single_complete_request_without_fixed_5000_reserve` | PASS |
| `tests.test_compilation_groups_613::test_thinking_separate_from_output_requires_a_confirmed_budget_not_a_numeric_guess` | PASS |

JUnit/log/run receipt baseline611/release-checks và final613/acceptance-checks; focused/probes riêng không được ghép thành full PASS.
