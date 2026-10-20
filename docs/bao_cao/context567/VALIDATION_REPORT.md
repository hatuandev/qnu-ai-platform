# Context567 — Kiểm chứng và regression theo test ID

## Môi trường an toàn

DB/MinIO/Qdrant development đã xác minh loopback, source/config audit READ ONLY. Pytest dùng DB `qnu_test_context567_282bc5e59949`, ownership nonce, 49 ORM tables; Storage runtime riêng. Test MinIO/Qdrant/Redis trỏ loopback port1, không dùng production service. Không migration/auto-seed dùng chung. Encrypted ModelOps rows copy sang test DB để giữ policy, không ghi credential ra docs. PostgreSQL test-owned concurrency guard kiểm environment, loopback và strict test DB regex.

## Kết quả thực chạy

| Gate | Kết quả | Exit |
|---|---|---:|
| Red trên baseline-app snapshot bất biến | 10 FAIL /1 PASS | 1 |
| Focused stable trước sửa audit cuối | 349 PASS | 0 |
| Audit stable cuối | 118 PASS | 0 |
| Wire contract cuối | 49 PASS, có trùng focused | 0 |
| Full lần1 | 2764 PASS / 24 FAIL / 17 SKIP | 1 |
| Full lần2 | 2775 PASS / 23 FAIL / 17 SKIP | 1 |
| Full lần3 | 2783 PASS / 20 FAIL / 17 SKIP | 1 |
| **Full verified cuối** | **2785 PASS /18 FAIL /17 SKIP,23 subtests PASS** | **1** |
| Ruff 36 file cuối | PASS | 0 |
| Benchmark Run1/2/3 | Đủ 64 IDs/lượt; xem báo cáo chính | Runner0, scorer0 |

`red-corrected` bị chồng thời điểm sửa mã nên không dùng làm before-code baseline. `red-snapshot` ghim import full app copy trước sửa là chứng cứ đỏ đáng tin. Không rollback worktree để dựng baseline.

Các full giữa có lỗi thêm do orchestration doubles chưa khai báo ranh giới đọc canonical mới; sau đó đã ghim literal source doubles tại đúng unit tests. Lần3 còn2fixture wire507 gửi shape cũ; đã cập nhật payload theo schema mới, vẫn giữ assertion âm/dương, test ID và giá trị. Những doubles này không được dùng trong benchmark hay source proof tests. Fixture MagicMock khai báo binding/index tường minh. Không sửa câu hỏi/giá trị/assertion cũ để né thất bại. Các checks source/hash/revision thật và âm tính được kiểm riêng.

Lệnh từ repo root, interpreter venv sẵn có:

```powershell
backend/.venv/Scripts/python.exe backend/storage/context567/isolation.py run --state-file backend/storage/context567/isolation.json --audit-file backend/storage/context567/safety.json --evidence-dir backend/storage/context567/tests --label audit-stable tests/test_context567_rag_regressions.py tests/test_rag_batch_492.py tests/test_rag_entity_scoped_formatting.py tests/test_rag_generation_stage4.py tests/test_rag_rows_stage3.py tests/test_workflow_hitl_and_history.py tests/test_rag_prose_recovery_491.py
backend/.venv/Scripts/python.exe backend/storage/context567/isolation.py run --state-file backend/storage/context567/isolation.json --audit-file backend/storage/context567/safety.json --evidence-dir backend/storage/context567/tests --label full-final-gate
backend/.venv/Scripts/python.exe backend/storage/context567/benchmark-3/run.py
backend/.venv/Scripts/python.exe backend/storage/context567/benchmark-3/score.py
```

Exact commands/cwd/exit/basetemp trong `backend/storage/context567/tests/*-run.json`, Ruff trong `ruff-run.json`. Receipts/JUnit/logs và baseline import copy được giữ ignored; nguồn/docs không chứa connection credential.

## Lỗi nền theo đúng ID

Baseline full Context565 2747 PASS/18 FAIL/17 SKIP. Không có ID cũ mất/đổi status hoặc new FAIL. Các lỗi nền vẫn là FAIL; không seed corpus thật hoặc tắt auth/guard để đổi kết quả.

| Test ID | Nguyên nhân baseline | Nguyên nhân hiện tại |
|---|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Không kiểm tra được giới hạn server AI. |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | assert 403 == 200 | assert 403 == 200 |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | assert 403 == 200 | assert 403 == 200 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201 | assert 403 == 201 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400 | assert 403 == 400 |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200 | assert 403 == 200 |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | assert 403 == 200 | assert 403 == 200 |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | assert False is True | assert False is True |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin' | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | assert False is True | assert False is True |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. | app.core.exceptions.DomainException: Embedding provider 'vllm' không khả dụng: Không kiểm tra được giới hạn server AI. |

## Tests thêm và trạng thái cuối

- `tests.test_context567_rag_regressions::test_contradictory_audit_summary_requires_repair_not_a_positive_override[False-True]` — PASS
- `tests.test_context567_rag_regressions::test_contradictory_audit_summary_requires_repair_not_a_positive_override[True-False]` — PASS
- `tests.test_context567_rag_regressions::test_exhaustive_identity_list_preserves_zero_and_never_drops_unresolved_rows[tail0-True]` — PASS
- `tests.test_context567_rag_regressions::test_exhaustive_identity_list_preserves_zero_and_never_drops_unresolved_rows[tail1-False]` — PASS
- `tests.test_context567_rag_regressions::test_exhaustive_identity_list_preserves_zero_and_never_drops_unresolved_rows[tail2-False]` — PASS
- `tests.test_context567_rag_regressions::test_final_retained_claim_audit_is_authoritative_and_never_promotes_rejected_claims[False]` — PASS
- `tests.test_context567_rag_regressions::test_final_retained_claim_audit_is_authoritative_and_never_promotes_rejected_claims[True]` — PASS
- `tests.test_context567_rag_regressions::test_indexed_reader_cannot_invent_proof_drop_span_or_override_atomic_summary` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_correction_preserves_full_user_scope[C\xf2n n\u0103m 2031 th\xec sao?]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_correction_preserves_full_user_scope[N\u0103m 2031?]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_correction_preserves_full_user_scope[Th\u1ebf n\u0103m 2031?]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_resolver_declines_ambiguous_or_new_predicates[Th\u1ebf n\u0103m 2031 cho nh\xf3m kh\xe1c?-previous0]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_resolver_declines_ambiguous_or_new_predicates[Th\u1ebf n\u0103m 2031?-previous1]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_resolver_declines_ambiguous_or_new_predicates[Th\u1ebf n\u0103m 2031?-previous2]` — PASS
- `tests.test_context567_rag_regressions::test_literal_year_resolver_declines_ambiguous_or_new_predicates[Th\u1ebf n\u0103m 2031?-previous3]` — PASS
- `tests.test_context567_rag_regressions::test_measure_label_precedes_unrelated_condition_in_literal_row_query` — PASS
- `tests.test_context567_rag_regressions::test_multiple_requested_metrics_are_complete` — PASS
- `tests.test_context567_rag_regressions::test_natural_requested_unit_is_not_replaced_by_source_unit[l\u1edbp]` — PASS
- `tests.test_context567_rag_regressions::test_natural_requested_unit_is_not_replaced_by_source_unit[nh\xf3m]` — PASS
- `tests.test_context567_rag_regressions::test_quote_address_repair_never_changes_scope_or_invents_a_value` — PASS
- `tests.test_context567_rag_regressions::test_ranked_full_conditions_are_not_crowded_out_by_table_summary` — PASS
- `tests.test_context567_rag_regressions::test_recorded_quantity_paraphrases_preserve_metric[B\u1ea3ng ghi nh\u1eadn bao nhi\xeau SV c\u1ee7a UX-0405 n\u0103m 2030?]` — PASS
- `tests.test_context567_rag_regressions::test_recorded_quantity_paraphrases_preserve_metric[M\xe3 UX-0405 \u0111\xe3 ghi nh\u1eadn \u0111\u01b0\u1ee3c m\u1ea5y SV n\u0103m 2030?]` — PASS
- `tests.test_context567_rag_regressions::test_recorded_quantity_paraphrases_preserve_metric[S\u1ed1 SV ghi nh\u1eadn n\u0103m 2030 c\u1ee7a m\xe3 UX-0405?]` — PASS
- `tests.test_context567_rag_regressions::test_reusing_one_proof_is_valid_but_foreign_ids_stay_rejected[ids0-True]` — PASS
- `tests.test_context567_rag_regressions::test_reusing_one_proof_is_valid_but_foreign_ids_stay_rejected[ids1-False]` — PASS
- `tests.test_context567_rag_regressions::test_scalar_zero_is_not_an_unlabeled_identity` — PASS
- `tests.test_context567_rag_regressions::test_schema_identifier_is_not_a_spaced_natural_language_entity` — PASS
- `tests.test_context567_rag_regressions::test_search_prefix_is_not_a_canonical_quote_and_foreign_or_altered_body_is_rejected[False-False]` — PASS
- `tests.test_context567_rag_regressions::test_search_prefix_is_not_a_canonical_quote_and_foreign_or_altered_body_is_rejected[False-True]` — PASS
- `tests.test_context567_rag_regressions::test_search_prefix_is_not_a_canonical_quote_and_foreign_or_altered_body_is_rejected[True-False]` — PASS
- `tests.test_context567_rag_regressions::test_server_owned_source_proof_keeps_every_atomic_negative[False-True-False]` — PASS
- `tests.test_context567_rag_regressions::test_server_owned_source_proof_keeps_every_atomic_negative[True-False-False]` — PASS
- `tests.test_context567_rag_regressions::test_server_owned_source_proof_keeps_every_atomic_negative[True-True-True]` — PASS
- `tests.test_context567_rag_regressions::test_source_locators_and_given_scenario_inputs_are_not_answer_fact_demands` — PASS
- `tests.test_context567_rag_regressions::test_source_name_selects_verified_coordinates_without_static_code` — PASS
- `tests.test_context567_rag_regressions::test_source_query_does_not_invent_a_major_code_for_a_name` — PASS
- `tests.test_context567_rag_regressions::test_unknown_table_cell_cannot_be_promoted_through_semantic_supplement` — PASS

Mock/source fixture PASS không thay bằng chứng runtime. Benchmark dùng backend TCP và model/reranker thật, với source/config/vector seals. Không suy E2E production từ local run. Cleanup database/runtime và hội thoại có bằng chứng riêng; [báo cáo chính](BENCHMARK_REPORT.md) ghi phần đã dọn hoặc còn bị chặn.
