# Context564 — Exact regression IDs

Baseline Context562 và full-final Context564: 0 changed, 0 removed; 27 added PASS. 18 failure IDs và nguyên nhân đầu tiên khớp hoàn toàn. Full gate vẫn FAIL, exit 1.

## 18 lỗi nền giữ nguyên

| Test ID | Nguyên nhân trước = sau |
|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | assert False is True |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## 27 test ID mới

| Test ID | Kết quả |
|---|---|
| `tests/test_evidence_closure_564.py::test_canonical_only_pack_preserves_transitive_required_context` | PASS |
| `tests/test_evidence_closure_564.py::test_canonical_text_without_reviewed_facts_keeps_existing_behavior` | PASS |
| `tests/test_evidence_closure_564.py::test_duplicate_canonical_unit_is_rejected` | PASS |
| `tests/test_evidence_closure_564.py::test_fact_group_keeps_exact_source_row_and_its_own_dependencies` | PASS |
| `tests/test_evidence_closure_564.py::test_fact_selection_pack_and_claim_projection_retains_source_proof` | PASS |
| `tests/test_evidence_closure_564.py::test_insufficient_budget_rejects_whole_fact_group[10-100-character_budget]` | PASS |
| `tests/test_evidence_closure_564.py::test_insufficient_budget_rejects_whole_fact_group[2-36000-block_limit]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_canonical_chain_remains_an_evidence_error[b]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_canonical_chain_remains_an_evidence_error[refs0]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_canonical_chain_remains_an_evidence_error[refs1]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_dependency_metadata_is_not_accepted[None]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_dependency_metadata_is_not_accepted[note]` | PASS |
| `tests/test_evidence_closure_564.py::test_invalid_dependency_metadata_is_not_accepted[refs2]` | PASS |
| `tests/test_evidence_closure_564.py::test_missing_required_source_unit_stays_blocked[header]` | PASS |
| `tests/test_evidence_closure_564.py::test_missing_required_source_unit_stays_blocked[note]` | PASS |
| `tests/test_evidence_closure_564.py::test_missing_required_source_unit_stays_blocked[row]` | PASS |
| `tests/test_evidence_closure_564.py::test_numbered_group_member_keeps_its_own_footnote` | PASS |
| `tests/test_evidence_closure_564.py::test_published_fact_selection_through_projection_does_not_mutate_snapshot` | PASS |
| `tests/test_evidence_closure_564.py::test_referenced_note_does_not_pull_its_unrequested_list_siblings` | PASS |
| `tests/test_evidence_closure_564.py::test_shared_source_and_note_deduplicate_with_stable_order_and_serialization` | PASS |
| `tests/test_evidence_closure_564.py::test_source_row_can_be_shared_but_note_does_not_expand_other_fact_rows` | PASS |
| `tests/test_evidence_closure_564.py::test_source_row_transitive_dependencies_and_cycles_are_closed_once` | PASS |
| `tests/test_evidence_closure_564.py::test_structural_ancestor_keeps_its_required_note_within_budget` | PASS |
| `tests/test_evidence_closure_564.py::test_wrong_source_identity_is_not_replaced_by_similar_text[binding_id-other-binding]` | PASS |
| `tests/test_evidence_closure_564.py::test_wrong_source_identity_is_not_replaced_by_similar_text[canonical_hash-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb]` | PASS |
| `tests/test_evidence_closure_564.py::test_wrong_source_identity_is_not_replaced_by_similar_text[index_revision_id-stale-index]` | PASS |
| `tests/test_evidence_closure_564.py::test_wrong_source_identity_is_not_replaced_by_similar_text[source_revision_id-other]` | PASS |

Exact receipts và JUnit nằm trong `backend/storage/context564/tests/`; comparison private `regression-comparison.json` giữ trạng thái tất cả test ID thay vì chỉ tổng số.
