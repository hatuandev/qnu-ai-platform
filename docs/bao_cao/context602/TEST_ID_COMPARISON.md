# Context602 — Đối chiếu regression theo test ID

Baseline và final dùng cùng DB test602, Storage riêng và network guard; full
baseline chạy trên snapshot app đầu602, giữ cả thay đổi600/601 có sẵn.

| Lượt | PASS | FAIL | SKIP | Exit |
|---|---:|---:|---:|---:|
| Baseline trước sửa app | 3362 | 18 | 17 | 1 |
| Trung gian trước sửa reselection | 3407 | 18 | 17 | 1 |
| Final sau sửa reselection | 3413 | 18 | 17 | 1 |

Các lượt có thêm23 subtest PASS. Exact ID/cause của18 failure baseline và final
không đổi:0 lỗi mới,0 mất ID cũ,0 đổi failure message.51 ID mới đều PASS. **Tổng
full suite vẫn FAIL.** Focused cuối889 PASS/exit0, Ruff21 file PASS/exit0.

## 18 failure ID giữ nguyên

Failure messages đầy đủ nằm trong JUnit/log private; phép so sánh exact cause
ghi trong `backend/storage/context602/checks/test-id-comparison-final.json`.
Không dùng tổng số lỗi giống nhau để suy rằng nguyên nhân giống nhau.

| ID | Nguyên nhân baseline/final cùng giữ |
|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | DB test tạo schema, thiếu bảng alembic_version; không chạy migration DB ứng dụng. |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | DB cô lập không có các collection seed cũ mà test đòi hỏi. |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | DB cô lập không có các collection seed cũ mà test đòi hỏi. |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | Endpoint dịch vụ test đóng hoặc capacity check không khả dụng trong network guard. |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | Endpoint dịch vụ test đóng hoặc capacity check không khả dụng trong network guard. |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | Capacity server AI không khả dụng trong network guard. |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | Contract endpoint trả403, test cũ đòi200/201/400. |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | Assertion legacy_payload_schema không tìm thấy trong kết quả. |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | Test lookup fact cũ thiếu dữ liệu mong đợi trong DB cô lập. |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | Actor role trảAI.Admin, test cũ đòiadmin. |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | Thiếu collection/fact seed cũ trong DB cô lập. |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | Thiếu collection/fact seed cũ trong DB cô lập. |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | Embedding vLLM/capacity không khả dụng trong network guard. |

## 51 test mới và bằng chứng tái hiện

Baseline full chưa có51 test mới; cột tái hiện ghi các lần chạy riêng trên app
trước sửa. NOT RUN là chưa chạy trước sửa, không phải PASS.21 ca có baseline
riêng gồm14 FAIL/7 control PASS.30 ca bổ sung còn lại, gồm contract mới, chỉ được
chạy sau sửa. Không tuyên bố tất cả51 đều từng đỏ.

| ID | Tái hiện trước sửa app | Final full |
|---|---|---|
| `tests.test_compilation_contracts_602::test_bound_unknown_keeps_evidence_and_cannot_be_used_for_serving` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[duplicate_id]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[foreign_collection]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[invented_year]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[missing_condition]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[missing_proof]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[scope_missing_proof]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[unknown_endpoint]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[wrong_canonical]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[wrong_entity]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[wrong_hash]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_invalid_source_scope_and_dependencies_are_rejected[wrong_revision]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_missing_permission_is_rejected_before_reading_sources` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_model_cannot_self_approve_or_choose_actor[actor_id-admin]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_model_cannot_self_approve_or_choose_actor[publication-published]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_model_cannot_self_approve_or_choose_actor[status-approved]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_one_assertion_cannot_borrow_condition_from_another_revision` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_relation_remains_candidate_even_when_evidence_exists` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_unknown_cannot_be_replaced_with_a_scalar[0]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_unknown_cannot_be_replaced_with_a_scalar[12]` | NOT RUN | PASS |
| `tests.test_compilation_contracts_602::test_unknown_cannot_be_replaced_with_a_scalar[?]` | NOT RUN | PASS |
| `tests.test_evidence_recovery_602::test_condition_fragment_matches_one_sentence_or_remains_unresolved` | FAIL | PASS |
| `tests.test_evidence_recovery_602::test_different_revision_derived_row_is_not_treated_as_a_duplicate` | NOT RUN | PASS |
| `tests.test_evidence_recovery_602::test_repair_does_not_borrow_a_same_text_clause_from_another_source` | PASS | PASS |
| `tests.test_evidence_recovery_602::test_repair_uses_complete_owning_sentence_for_a_semicolon_clause` | FAIL | PASS |
| `tests.test_evidence_recovery_602::test_second_missing_clause_in_same_block_can_be_restored_then_reverified` | NOT RUN | PASS |
| `tests.test_evidence_recovery_602::test_selector_uses_canonical_owner_instead_of_duplicate_derived_row` | FAIL | PASS |
| `tests.test_foundation_602::test_attached_year_scope[C\xf3 d\u1eef li\u1ec7u n\u0103m2027 kh\xf4ng?-years2]` | FAIL | PASS |
| `tests.test_foundation_602::test_attached_year_scope[Ng\xe0y 22/12/2023-years4]` | NOT RUN | PASS |
| `tests.test_foundation_602::test_attached_year_scope[So s\xe1nh ph\u01b0\u01a1ng h\u01b0\u1edbng2024 v\xe0 k\u1ebf ho\u1ea1ch2026-years0]` | FAIL | PASS |
| `tests.test_foundation_602::test_attached_year_scope[b\xe1o c\xe1o2025 vi\u1ec7n d\u1eabn v\u0103n b\u1ea3n2024-years1]` | FAIL | PASS |
| `tests.test_foundation_602::test_attached_year_scope[n\u0103m2024\u20132026-years3]` | FAIL | PASS |
| `tests.test_foundation_602::test_fragments_rejoin_only_a_unique_complete_native_paragraph_and_keep_raw_proof` | FAIL | PASS |
| `tests.test_foundation_602::test_identifier_is_not_permission_to_invent_a_year[1.2024]` | FAIL | PASS |
| `tests.test_foundation_602::test_identifier_is_not_permission_to_invent_a_year[2024A]` | PASS | PASS |
| `tests.test_foundation_602::test_identifier_is_not_permission_to_invent_a_year[AM-2024]` | FAIL | PASS |
| `tests.test_foundation_602::test_identifier_is_not_permission_to_invent_a_year[M\xe320241234]` | PASS | PASS |
| `tests.test_foundation_602::test_identifier_is_not_permission_to_invent_a_year[X_2024_Y]` | PASS | PASS |
| `tests.test_foundation_602::test_legitimate_short_literal_is_retained_without_turning_into_a_fact` | FAIL | PASS |
| `tests.test_foundation_602::test_long_inventory_is_paged_without_dropped_units_and_tamper_is_rejected` | FAIL | PASS |
| `tests.test_foundation_602::test_no_merging_across_native_paragraphs_duplicates_or_missing_text[native0]` | PASS | PASS |
| `tests.test_foundation_602::test_no_merging_across_native_paragraphs_duplicates_or_missing_text[native1]` | PASS | PASS |
| `tests.test_foundation_602::test_no_merging_across_native_paragraphs_duplicates_or_missing_text[native2]` | PASS | PASS |
| `tests.test_foundation_602::test_no_merging_across_native_paragraphs_duplicates_or_missing_text[native3]` | NOT RUN | PASS |
| `tests.test_foundation_602::test_search_variant_cannot_add_an_attached_year_and_history_is_only_used_when_requested` | NOT RUN | PASS |
| `tests.test_scope_reselection_602::test_prose_recovery_uses_the_same_literal_years_as_plan_validation[m\xe3 AM-2024-years2]` | NOT RUN | PASS |
| `tests.test_scope_reselection_602::test_prose_recovery_uses_the_same_literal_years_as_plan_validation[n\u0103m2024/2025-years1]` | NOT RUN | PASS |
| `tests.test_scope_reselection_602::test_prose_recovery_uses_the_same_literal_years_as_plan_validation[n\u0103m2024\u20132026-years0]` | NOT RUN | PASS |
| `tests.test_scope_reselection_602::test_reselection_cannot_drop_new_source_obligation[False]` | FAIL | PASS |
| `tests.test_scope_reselection_602::test_reselection_cannot_drop_new_source_obligation[True]` | FAIL | PASS |
| `tests.test_scope_reselection_602::test_same_words_in_a_different_block_do_not_satisfy_a_recovered_obligation` | NOT RUN | PASS |

Các lần tái hiện hợp lệ:

- `baseline-foundation-correct-fixture`:9 FAIL/6 PASS, exit1; year literal,
  identifier, native paragraph, inventory dài và literal ngắn.
- `baseline-recovery`:3 FAIL/1 PASS, exit1; canonical owner và full sentence.
- `baseline-reselection-valid-context`:2 FAIL, exit1 tại đúng assertion mất
  qualifier. Hai ID ban đầu ở scratch module, được chuyển sang
  `tests.test_scope_reselection_602` khi triển khai.

Các lần fixture sai ban đầu (fake parent.resolve/manifest và câu English không
chọn owner) được giữ riêng, không dùng làm chứng cứ lỗi sản phẩm. Chúng không
thay thế các baseline hợp lệ nêu trên. Contract đợt2 mới chưa tồn tại ở app đầu
phiên, không gọi việc module thiếu là một lỗi nghiệp vụ cũ.

Ứng dụng/test không đổi sau full cuối và trong lúc live64/multi-source. Chấm
live theo ID, source, question và rubric riêng trong
[VALIDATION_REPORT.md](./VALIDATION_REPORT.md) và
[MULTI_SOURCE_EVALUATION.md](./MULTI_SOURCE_EVALUATION.md); unit PASS không thay
nghiệm thu model thật.
