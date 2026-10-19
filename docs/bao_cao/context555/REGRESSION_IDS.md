# Đối chiếu ID regression Context555

| Test ID | Trước | Sau | Nguyên nhân đầu tiên |
|---|---|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL | FAIL | Giữ nguyên: sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL | FAIL | Giữ nguyên: redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | FAIL | FAIL | Giữ nguyên: assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | FAIL | FAIL | Giữ nguyên: assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | FAIL | FAIL | Giữ nguyên: assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | FAIL | FAIL | Giữ nguyên: assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL | FAIL | Giữ nguyên: assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | FAIL | FAIL | Giữ nguyên: assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | FAIL | FAIL | Giữ nguyên: AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | FAIL | FAIL | Giữ nguyên: assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | FAIL | FAIL | Giữ nguyên: AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | FAIL | FAIL | Giữ nguyên: assert False is True |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | FAIL | FAIL | Giữ nguyên: app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

Đối chiếu đầy đủ mọi ID/PASS/FAIL/SKIP và added/removed/change trong regression-comparison.json.
