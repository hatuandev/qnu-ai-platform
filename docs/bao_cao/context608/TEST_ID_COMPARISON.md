# Context608 — Đối chiếu exact test ID

Baseline và final chạy hai DB test608 riêng, schema và typed defaults metadata giống nhau, Storage riêng/network guard. Final giới hạn OpenBLAS1thread theo tiến trình để giảm áp lực RAM; không đổi config app/model. Full đầu không có receipt/JUnit giữ INCOMPLETE, không dùng thay final.

| Run | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline | 3551 | 18 | 17 | 1 |
| Final | 3564 | 18 | 17 | 1 |

Cả hai có23subtestPASS. Full vẫn FAIL khi còn lỗi nền.

- Failure mới:0; cause đổi:0; ID mất:0; lỗi nền sửa:0.
- Test mới:13; PASS:13.

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
| `tests.test_compilation_context_608::test_empty_draft_coverage_disagreement_or_ambiguity_remains_incomplete[roles0]` | PASS |
| `tests.test_compilation_context_608::test_empty_draft_coverage_disagreement_or_ambiguity_remains_incomplete[roles1]` | PASS |
| `tests.test_compilation_context_608::test_empty_draft_reaches_two_coverage_audits_and_one_targeted_repair` | PASS |
| `tests.test_compilation_context_608::test_empty_packet_is_excluded_only_after_both_coverage_audits_agree_unrelated` | PASS |
| `tests.test_compilation_context_608::test_repeated_empty_repair_keeps_required_omissions_without_recursive_model_calls` | PASS |
| `tests.test_compilation_context_608::test_review_protocol_change_invalidates_cached_packets_without_changing_model` | PASS |
| `tests.test_compilation_context_608::test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role[None]` | PASS |
| `tests.test_compilation_context_608::test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role[data]` | PASS |
| `tests.test_compilation_context_608::test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role[effective]` | PASS |
| `tests.test_compilation_context_608::test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role[event]` | PASS |
| `tests.test_compilation_context_608::test_review_targets_preserve_literal_year_without_filling_missing_date_or_assigning_role[publication]` | PASS |
| `tests.test_compilation_context_608::test_separated_time_review_does_not_override_a_negative_temporal_verdict` | PASS |
| `tests.test_compilation_context_608::test_time_literal_hints_do_not_cross_to_other_offered_proofs_or_infer_a_role` | PASS |

JUnit/log/run receipt trong checks/ và release-checks/; focused/probes riêng không được ghép thành full PASS.
