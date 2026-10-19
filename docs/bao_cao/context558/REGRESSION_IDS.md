# Context558 — Đối chiếu từng test ID

Baseline lịch sử: Context557 `full-final.xml`; hiện tại: Context558 `ingestion-full-final.xml`. Không coi baseline lịch sử là một lượt chạy mới.

- Baseline: 2.429 PASS / 18 FAIL / 17 SKIP.
- Hiện tại: 2.466 PASS / 18 FAIL / 17 SKIP; exit 1.
- Không mất test ID, không đổi trạng thái ID chung, không thêm lỗi.
- 18 failure message đầu tiên khớp chính xác; nguyên nhân đối chiếu dưới đây.

## 18 lỗi giữ nguyên

| Test ID | Trước → sau | Nguyên nhân trước/sau |
|---|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL → FAIL | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | FAIL → FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | FAIL → FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL → FAIL | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL → FAIL | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL → FAIL | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | FAIL → FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | FAIL → FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | FAIL → FAIL | assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | FAIL → FAIL | assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL → FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | FAIL → FAIL | assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | FAIL → FAIL | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | FAIL → FAIL | assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | FAIL → FAIL | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | FAIL → FAIL | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | FAIL → FAIL | assert False is True |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | FAIL → FAIL | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## 37 test ID mới

| Test ID | Kết quả |
|---|---|
| `tests/test_automatic_ingestion.py::test_automatic_unknown_builds_staging_vectors_without_publishing` | PASS |
| `tests/test_automatic_ingestion.py::test_clean_docx_is_auto_ready_without_human_semantic_approval` | PASS |
| `tests/test_automatic_ingestion.py::test_content_certificate_invalidates_on_material_changes[canonical]` | PASS |
| `tests/test_automatic_ingestion.py::test_content_certificate_invalidates_on_material_changes[quality]` | PASS |
| `tests/test_automatic_ingestion.py::test_content_certificate_invalidates_on_material_changes[table]` | PASS |
| `tests/test_automatic_ingestion.py::test_native_digital_pdf_is_ready_without_semantic_model_or_ocr` | PASS |
| `tests/test_automatic_ingestion.py::test_optional_pending_assertion_does_not_block_verified_content` | PASS |
| `tests/test_automatic_ingestion.py::test_raw_uninterpreted_symbol_is_a_limitation_not_a_numeric_fact` | PASS |
| `tests/test_automatic_ingestion.py::test_source_blank_and_actual_zero_remain_distinct[-READY_WITH_LIMITATIONS-source_blank]` | PASS |
| `tests/test_automatic_ingestion.py::test_source_blank_and_actual_zero_remain_distinct[0-AUTO_READY-None]` | PASS |
| `tests/test_automatic_ingestion.py::test_source_bytes_tamper_blocks_index_even_when_cached_marker_is_unchanged` | PASS |
| `tests/test_automatic_ingestion.py::test_unreadable_or_missing_table_remains_blocking` | PASS |
| `tests/test_smart_approval.py::test_allowlist_requires_exact_revision_provenance_not_test_filename` | PASS |
| `tests/test_smart_approval.py::test_changed_semantic_payload_cannot_inherit_fixture_acceptance` | PASS |
| `tests/test_smart_approval.py::test_exact_source_binding_does_not_prove_semantic_scope` | PASS |
| `tests/test_smart_approval.py::test_legacy_approval_error_preserves_context_blocker` | PASS |
| `tests/test_smart_approval.py::test_machine_validation_cannot_reopen_a_previous_decision[changes_requested]` | PASS |
| `tests/test_smart_approval.py::test_machine_validation_cannot_reopen_a_previous_decision[rejected]` | PASS |
| `tests/test_smart_approval.py::test_machine_validation_cannot_reopen_a_previous_decision[unavailable]` | PASS |
| `tests/test_smart_approval.py::test_only_exact_native_footnote_anchor_can_make_unknown_page_a_warning` | PASS |
| `tests/test_smart_approval_api.py::test_authenticated_endpoint_one_request_and_viewer_denied` | PASS |
| `tests/test_smart_approval_api.py::test_dry_run_and_unproven_scope_make_no_writes` | PASS |
| `tests/test_smart_approval_api.py::test_failure_rolls_back_source_and_semantic_pointer[commit]` | PASS |
| `tests/test_smart_approval_api.py::test_failure_rolls_back_source_and_semantic_pointer[storage]` | PASS |
| `tests/test_smart_approval_api.py::test_fixture_bulk_certificate_rebuild_has_no_fabricated_human_issue_decisions` | PASS |
| `tests/test_smart_approval_api.py::test_important_content_failures_are_never_downgraded[cached-cell]` | PASS |
| `tests/test_smart_approval_api.py::test_important_content_failures_are_never_downgraded[integrity]` | PASS |
| `tests/test_smart_approval_api.py::test_important_content_failures_are_never_downgraded[missing-table]` | PASS |
| `tests/test_smart_approval_api.py::test_important_content_failures_are_never_downgraded[pair-checksum]` | PASS |
| `tests/test_smart_approval_api.py::test_one_click_approves_atomically_and_duplicate_is_idempotent` | PASS |
| `tests/test_smart_approval_api.py::test_real_two_connection_concurrent_duplicate_has_one_committed_decision` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[actor]` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[binding]` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[canonical]` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[collection]` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[proposal]` | PASS |
| `tests/test_smart_approval_api.py::test_stale_wrong_identity_and_permission_do_not_approve[revision]` | PASS |
