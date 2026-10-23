# Context600 — Lệnh và test evidence

Cwd root=`D:/DuAnPhanMem/qnu-ai-platform`; backend=`root/backend`; frontend=`root/frontend`. Lệnh dưới chạy qua harness đã xác minh DB nonce riêng, local Storage riêng và network guard; không chạy pytest trực tiếp bằng cấu hình vận hành. DB test đã dọn sau kiểm chứng. Receipt/JUnit/log local giữ trong `backend/storage/context600/checks/`.

## Lệnh chốt

| Receipt | Cwd | Exit | Lệnh process thật |
|---|---|---|---|
| focused-literal-final | D:\DuAnPhanMem\qnu-ai-platform\backend | 0 | `'D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe' -m pytest -q tests/test_source_provenance_boundaries_597.py tests/test_source_dependency_repair_597.py tests/test_evidence_stability_597.py tests/test_rag_chat_441.py tests/test_source_answer_scope_575.py tests/test_rag_reliability_591.py tests/test_context_reference_repair_592.py tests/test_context_scope_integrity_594.py tests/test_context_extension_595.py tests/test_wiki_packing_591.py tests/test_rag_prose_recovery_491.py tests/test_prose_selection_502.py tests/test_hybrid_conversation.py tests/test_hybrid_intent_routing.py tests/test_conversation_acts.py tests/test_wiki_navigation.py tests/test_context567_rag_regressions.py tests/test_answer_obligations_576.py tests/test_benchmark_review_505.py tests/test_evidence_claims.py tests/test_evidence_completeness_437.py tests/test_evidence_contracts_500.py tests/test_evidence_priorities_443.py tests/test_evidence_quality_444.py tests/test_evidence_scope_452.py tests/test_historical_reference_449.py tests/test_recovery_facets_599.py tests/test_dependency_agreement_599.py tests/test_wiki_links_600.py tests/test_wiki_snapshot_integration_600.py tests/test_wiki_revision_reuse_600.py tests/test_wiki_revocation_600.py '--basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600-runtime-a0f0c693aabe\focused-literal-final' '--junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600\checks\focused-literal-final.xml'` |
| full-release | D:\DuAnPhanMem\qnu-ai-platform\backend | 1 | `'D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe' -m pytest -q '--basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600-runtime-a0f0c693aabe\full-release' '--junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600\checks\full-release.xml'` |
| network-guard | D:\DuAnPhanMem\qnu-ai-platform\backend | 0 | `'D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe' -m pytest -q D:/DuAnPhanMem/qnu-ai-platform/.antigravity-bridge/validation/test_context600_network_guard.py '--basetemp=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600-runtime-a0f0c693aabe\network-guard' '--junitxml=D:\DuAnPhanMem\qnu-ai-platform\backend\storage\context600\checks\network-guard.xml'` |
| ruff-release | D:\DuAnPhanMem\qnu-ai-platform | 0 | `'D:\DuAnPhanMem\qnu-ai-platform\backend\.venv\Scripts\python.exe' -m ruff check backend/app/modules/knowledge/services/chunk_set_service.py backend/app/modules/knowledge/services/wiki_views.py backend/app/modules/knowledge/wiki_router.py backend/app/modules/knowledge/wiki_schemas.py backend/app/modules/rag/wiki_context.py backend/app/modules/knowledge/services/wiki_consistency.py backend/app/modules/knowledge/services/wiki_links.py backend/app/modules/knowledge/services/wiki_reuse.py backend/app/modules/knowledge/services/wiki_snapshot.py backend/tests/test_wiki_links_600.py backend/tests/test_wiki_revision_reuse_600.py backend/tests/test_wiki_revocation_600.py backend/tests/test_wiki_snapshot_integration_600.py` |
| frontend-tests | D:\DuAnPhanMem\qnu-ai-platform\frontend | 0 | `'C:\Program Files\nodejs\node.EXE' --test src/features/knowledge/components/knowledge-wiki.test.mjs src/features/knowledge/components/knowledge-wiki-navigation.test.mjs src/features/knowledge/components/qnu-document-reader.test.mjs` |
| biome-final | D:\DuAnPhanMem\qnu-ai-platform\frontend | 0 | `'C:\Program Files\nodejs\npm.cmd' exec -- biome check --line-ending=lf src/features/knowledge/components/knowledge-wiki-navigation.tsx src/features/knowledge/components/knowledge-wiki-navigation.test.mjs src/features/knowledge/components/knowledge-wiki-panel.tsx src/features/knowledge/components/knowledge-wiki.test.mjs src/types/knowledge-wiki.ts src/services/knowledge-api.ts` |
| frontend-build | D:\DuAnPhanMem\qnu-ai-platform\frontend | 0 | `'C:\Program Files\nodejs\npm.cmd' run build` |

Full `exit1` vẫn là FAIL. Hai runner baseline/final: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context600_baseline_run.py` và `.../context600_final_release_run.py`, cwd root, exit0; scorer và postcheck tương ứng exit0. Mỗi run có run-intent chống resend; không chạy lại các script này trên artifact đã tồn tại. Retry riêng `context600_retry_p07.py` và postcheck exit0. Chấm64 offline bằng scorer, không gọi model judge.

## 45 test mới ở full chốt

| Exact ID (JUnit classname::name) | Kết quả |
|---|---|
| `tests.test_wiki_links_600::test_three_sources_years_and_publication_never_merge_values_or_identity` | PASS |
| `tests.test_wiki_links_600::test_leading_zero_and_unicode_identifiers_remain_exact_and_alias_is_only_candidate` | PASS |
| `tests.test_wiki_links_600::test_same_name_different_codes_are_distinct_nodes_with_only_co_mention` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[hash]` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[snapshot]` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[target]` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[backlink]` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[duplicate]` | PASS |
| `tests.test_wiki_links_600::test_resealed_or_stale_graph_cannot_change_trust_or_evidence[status]` | PASS |
| `tests.test_wiki_links_600::test_bfs_loop_fanout_and_depth_budgets_never_add_model_calls` | PASS |
| `tests.test_wiki_links_600::test_unknown_year_cannot_drive_auto_expansion_and_issue_role_stays_separate` | PASS |
| `tests.test_wiki_links_600::test_source_injection_and_unknown_symbol_stay_literal_navigation_data` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[code]` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[hash]` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[revision]` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[span]` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[condition]` | PASS |
| `tests.test_wiki_links_600::test_integrity_failure_is_explained_and_never_downgraded_to_limitation[footnote]` | PASS |
| `tests.test_wiki_links_600::test_reuse_rebinds_all_ids_and_rejects_changed_metadata_policy_and_foreign_binding` | PASS |
| `tests.test_wiki_links_600::test_multi_year_columns_including_2027_keep_literal_values_and_unknown` | PASS |
| `tests.test_wiki_links_600::test_identical_footnotes_keep_distinct_table_locators_and_conditions` | PASS |
| `tests.test_wiki_links_600::test_value_difference_requires_same_data_year_metric_unit_and_conditions` | PASS |
| `tests.test_wiki_links_600::test_provider_failure_and_not_compiled_are_not_reported_as_missing_source_data` | PASS |
| `tests.test_wiki_links_600::test_cross_collection_projection_is_rejected_before_link_ranking` | PASS |
| `tests.test_wiki_links_600::test_graph_reference_budget_has_an_explicit_error_instead_of_partial_ready_graph` | PASS |
| `tests.test_wiki_links_600::test_database_failure_remains_infrastructure_error_not_empty_navigation` | PASS |
| `tests.test_wiki_links_600::test_similar_name_prefix_does_not_prove_a_shared_literal_mention` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[0007-00070-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[AM-0007-AM-0007-A-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[AM-0007-AM-0007.1-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[A-A\u0301-007-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[\xc1-007-A\u0301-007-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[Vi\u1ec7n A-Vi\u1ec7n AB-False]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[Vi\u1ec7n A-(Vi\u1ec7n A).-True]` | PASS |
| `tests.test_wiki_links_600::test_literal_boundary_preserves_whole_unicode_words_and_identifiers[AM-0007-| AM-0007 |-True]` | PASS |
| `tests.test_wiki_revision_reuse_600::test_unchanged_revision_reuses_wiki_without_inference` | PASS |
| `tests.test_wiki_revocation_600::test_revoked_publication_pointer_rejects_old_wiki` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_handler_auth_backlinks_source_scope_and_get_never_writes_or_calls_model` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_update_remove_rollback_and_foreign_or_draft_never_mix_snapshots` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_cached_navigation_rechecks_revocation_even_with_stale_blocks` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_concurrent_retry_and_late_old_revision_job_preserve_new_pointer` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_publication_change_during_map_read_returns_stale_instead_of_partial_graph` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_canonical_text_and_span_must_match_before_a_page_can_be_ranked` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_cross_source_reader_uses_original_spans_and_filters_year_before_expansion[years0-numbers0]` | PASS |
| `tests.test_wiki_snapshot_integration_600::test_cross_source_reader_uses_original_spans_and_filters_year_before_expansion[years1-numbers1]` | PASS |

## 17 SKIP trong full

Không đổi các skip thành PASS. Chi tiết reason đầy đủ trong JUnit.

| Exact ID | Lý do đầu |
|---|---|
| `tests.test_admissions_agentic_flow::test_admissions_consulting_chat_flow_returns_artifacts` | Yêu cầu PostgreSQL, ModelOps provider và dữ liệu tuyển sinh V2 đang hoạt động. |
| `tests.test_backups_integration::test_internal_target_has_no_default_route` | Opt-in disposable Docker data stores; no live data changed |
| `tests.test_backups_integration::test_real_encrypted_backup_and_isolated_restore` | Opt-in disposable Docker data stores; no live data changed |
| `tests.test_dev_auth_redis_460::test_real_redis_shared_window_expiry_and_global_limit` | Set QNU_TEST_DEV_AUTH_REDIS=1 for a disposable real Redis container |
| `tests.test_evidence_postgres::test_pinned_hash_review_scope_and_corrected_row_use_real_database` | Opt-in real PostgreSQL evidence fixture |
| `tests.test_glossary_terms::test_glossary_persistence_roundtrip_on_test_database` | NOT RUN: TEST_DATABASE_URL chưa được cấu hình. |
| `tests.test_knowledge_group_sources::test_real_postgresql_persistence_not_null_invariant` | Bỏ qua test persistence vì TEST_DATABASE_URL chưa được cấu hình. |
| `tests.test_knowledge_units_integration::test_staging_units_match_dense_lexical_bm25_and_exact_source_without_publishing` | Opt-in real scoped PostgreSQL/Qdrant/embedding fixture |
| `tests.test_knowledge_units_integration::test_actual_model_distinguishes_historical_data_from_citation_and_event_years` | Opt-in actual configured semantic model |
| `tests.test_model_probe_postgres::test_model_role_roundtrip_primary_removal_and_merge` | Opt-in PostgreSQL rollback fixture |
| `tests.test_phase1_postgres::test_serving_sources_and_durable_failure_use_real_db` | Opt-in PostgreSQL fixture |
| `tests.test_runtime_key_queue_postgres::test_twenty_jobs_share_one_key_without_overlap` | Opt-in PostgreSQL concurrency test |
| `tests.test_selected_publish_postgres::test_publish_incrementally_preserves_snapshot_and_round_trips_pointers` | Opt-in PostgreSQL fixture |
| `tests.test_unlimited_usage_postgres::test_new_month_unlimited_records_usage_above_old_limit` | Opt-in PostgreSQL rollback fixture |
| `tests.test_workflow_expired_identity::test_workflow_finalizes_real_expired_identity_after_node_rollback[completed]` | Opt-in PostgreSQL expiration regression |
| `tests.test_workflow_expired_identity::test_workflow_finalizes_real_expired_identity_after_node_rollback[failed]` | Opt-in PostgreSQL expiration regression |
| `tests.test_workflow_expired_identity::test_workflow_finalizes_real_expired_identity_after_node_rollback[paused_for_approval]` | Opt-in PostgreSQL expiration regression |

18 FAIL nền có bảng exact IDs/message và đối chiếu599 trong [VALIDATION_REPORT](VALIDATION_REPORT.md). So sánh đủ64 RAG ID trong [BENCHMARK_BY_ID](BENCHMARK_BY_ID.md). Không sửa assertion hoặc nới guard của18 ca nền.
