# Đối chiếu regression Context556

Baseline toàn bộ là kết quả **lịch sử Context555**, không phải lần chạy baseline mới. Baseline trọng tâm 80 test đã chạy trước khi thêm công cụ.

Full mới: **18 FAIL, 2.429 PASS, 17 SKIP, 23 subtests PASS; exit 1**. Giữ đúng 18 failure ID và nguyên nhân đầu tiên; không ID bị bỏ, không đổi trạng thái, 13 ID thêm đều PASS.

| Test ID lỗi nền | Nguyên nhân đầu tiên, giữ nguyên |
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

Chi tiết mọi test ID và nguyên nhân trước/sau: [regression-comparison.json](regression-comparison.json).
