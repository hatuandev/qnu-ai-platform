# Context562 — Đối chiếu regression theo test ID

Baseline: Context561 `full-after-layout.xml`. Sau sửa: Context562 `full-verified.xml`. Cùng 18 ID lỗi và cùng thông báo nguyên nhân đầu tiên; mọi ID chung giữ nguyên trạng thái. Không xóa test, không bỏ qua assertion.

| Test ID | Baseline | Sau sửa | Nguyên nhân cả hai lượt |
|---|---|---|---|
| `tests/test_configuration_seed_db.py::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL | FAIL | sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedTableError'>: relation "public.alembic_version" does not exist |
| `tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_admissions' |
| `tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_regulations' |
| `tests/test_ingestion_resilience.py::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL | FAIL | redis.exceptions.ConnectionError: Error 22 connecting to 127.0.0.1:1. The remote computer refused the network connection. |
| `tests/test_ingestion_resilience.py::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL | FAIL | app.core.exceptions.DomainException: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI. |
| `tests/test_ocr_modelops_safety.py::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL | FAIL | app.core.exceptions.DomainException: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI. |
| `tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled` | FAIL | FAIL | assert 403 == 201 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled` | FAIL | FAIL | assert 403 == 400 |
| `tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback` | FAIL | FAIL | assert 403 == 200 |
| `tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies` | FAIL | FAIL | AssertionError: assert 'legacy_payload_schema' in [] |
| `tests/test_tools.py::test_fact_layer_lookup_tool_found` | FAIL | FAIL | assert False is True |
| `tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims` | FAIL | FAIL | AssertionError: assert 'AI.Admin' == 'admin' |
| `tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts` | FAIL | FAIL | app.core.exceptions.EntityNotFoundError: KhÃ´ng tÃ¬m tháº¥y bá»™ sÆ°u táº­p 'col_admissions' |
| `tests/test_universal_tools.py::test_fact_layer_lookup_tool` | FAIL | FAIL | assert False is True |
| `tests/test_vllm_reranker.py::test_vllm_embedding_generation` | FAIL | FAIL | app.core.exceptions.DomainException: Embedding provider 'vllm' khÃ´ng kháº£ dá»¥ng: KhÃ´ng kiá»ƒm tra Ä‘Æ°á»£c giá»›i háº¡n server AI. |

## 172 test ID mới

Tất cả PASS trong full regression cuối, exit code suite vẫn 1 vì 18 lỗi nền ở trên.

- `tests/test_hybrid_chat_integration.py::test_chat_only_actor_cannot_bypass_ownership_through_admin_history_api[/conversations/private-conversation]` — PASS
- `tests/test_hybrid_chat_integration.py::test_chat_only_actor_cannot_bypass_ownership_through_admin_history_api[/conversations]` — PASS
- `tests/test_hybrid_chat_integration.py::test_conversation_capability_cannot_cross_assistant_or_session[False-True]` — PASS
- `tests/test_hybrid_chat_integration.py::test_conversation_capability_cannot_cross_assistant_or_session[True-False]` — PASS
- `tests/test_hybrid_chat_integration.py::test_conversation_capability_is_not_a_platform_access_token` — PASS
- `tests/test_hybrid_chat_integration.py::test_conversation_id_alone_does_not_authorize_another_browser_session` — PASS
- `tests/test_hybrid_chat_integration.py::test_deleted_thread_cannot_be_resurrected_by_an_old_capability` — PASS
- `tests/test_hybrid_chat_integration.py::test_handler_social_persists_and_authorized_debug_only[False-False]` — PASS
- `tests/test_hybrid_chat_integration.py::test_handler_social_persists_and_authorized_debug_only[False-True]` — PASS
- `tests/test_hybrid_chat_integration.py::test_handler_social_persists_and_authorized_debug_only[True-False]` — PASS
- `tests/test_hybrid_chat_integration.py::test_handler_social_persists_and_authorized_debug_only[True-True]` — PASS
- `tests/test_hybrid_chat_integration.py::test_history_database_failure_is_not_silently_treated_as_no_context` — PASS
- `tests/test_hybrid_chat_integration.py::test_history_is_scoped_to_thread_assistant_and_config_revision` — PASS
- `tests/test_hybrid_chat_integration.py::test_many_social_turns_cannot_push_out_knowledge_context` — PASS
- `tests/test_hybrid_chat_integration.py::test_new_anonymous_clients_do_not_share_a_client_chosen_conversation_id` — PASS
- `tests/test_hybrid_chat_integration.py::test_public_client_can_continue_its_own_signed_conversation` — PASS
- `tests/test_hybrid_chat_integration.py::test_viewer_cannot_enable_routing_debug_or_write_messages[False]` — PASS
- `tests/test_hybrid_chat_integration.py::test_viewer_cannot_enable_routing_debug_or_write_messages[True]` — PASS
- `tests/test_hybrid_conversation.py::test_invented_or_changed_scope_clarifies[H\u1ecdc ph\xed Alpha n\u0103m 2025?-refs2]` — PASS
- `tests/test_hybrid_conversation.py::test_invented_or_changed_scope_clarifies[H\u1ecdc ph\xed Alpha n\u0103m 2099?-refs0]` — PASS
- `tests/test_hybrid_conversation.py::test_invented_or_changed_scope_clarifies[H\u1ecdc ph\xed m\xe3 123 n\u0103m 2026?-refs1]` — PASS
- `tests/test_hybrid_conversation.py::test_model_cannot_select_old_program_after_explicit_switch` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[academic_not_calendar]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[assistant_prose_not_truth]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[condition_preserved]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[correction_then_social_then_followup]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[earlier_year_override]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[english_followup]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[explicit_current_program]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[institution]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[knowledge_greeting_followup]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[knowledge_thanks_followup]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[leading_zero_code]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[mixed_hello]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[mixed_thanks]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[negation_preserved]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[repeated_social]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[switch_program]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[switch_year]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[topic_change_same_subject]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[unknown_year_stays_unknown]` — PASS
- `tests/test_hybrid_conversation.py::test_multi_turn_gold_scope[user_correction]` — PASS
- `tests/test_hybrid_conversation.py::test_old_program_code_does_not_attach_to_new_explicit_program` — PASS
- `tests/test_hybrid_conversation.py::test_router_failure_is_explicit_clarification_never_social[error0]` — PASS
- `tests/test_hybrid_conversation.py::test_router_failure_is_explicit_clarification_never_social[error1]` — PASS
- `tests/test_hybrid_conversation.py::test_single_fact_year_change_cannot_be_lost_to_a_listing_only_filter` — PASS
- `tests/test_hybrid_conversation.py::test_twenty_concurrent_conversations_do_not_share_scope` — PASS
- `tests/test_hybrid_conversation.py::test_yes_examines_previous_clarification_without_treating_it_as_source_facts` — PASS
- `tests/test_hybrid_intent_routing.py::test_dataset_has_at_least_one_hundred_distinct_utterances` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[  Xin   Ch\xe0o  -SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n c\xf3 th\u1ec3 l\xe0m g\xec?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n c\xf3 th\u1ec3 t\u01b0 v\u1ea5n tuy\u1ec3n sinh kh\xf4ng?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n gi\xfap \u0111\u01b0\u1ee3c g\xec?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n h\u1ed7 tr\u1ee3 nh\u1eefng g\xec?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n l\xe0 ai?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n t\xean g\xec?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[B\u1ea1n t\xean l\xe0 g\xec-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Bye bye!-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n anh \u1ea1-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n anh, ng\xe0nh Alpha h\u1ecdc m\u1ea5y n\u0103m?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n b\u1ea1n nhi\u1ec1u nh\xe9-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n nh\xe9, gi\xfap t\xf4i so s\xe1nh hai ph\u01b0\u01a1ng th\u1ee9c.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n r\u1ea5t nhi\u1ec1u-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n, c\xf2n h\u1ecdc ph\xed?-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n, cho t\xf4i h\u1ecfi \u0111i\u1ec3m chu\u1ea9n n\u0103m 2026.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\u1ea3m \u01a1n-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\xe1c ph\u01b0\u01a1ng th\u1ee9c tuy\u1ec3n sinh \u0111\u01b0\u1ee3c c\xf4ng b\u1ed1?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\xf2n m\xf4n t\u1ef1 ch\u1ecdn?-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\xf2n n\u0103m 2025?-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\xf3 bao nhi\xeau ph\u01b0\u01a1ng th\u1ee9c tuy\u1ec3n sinh n\u0103m 2027?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[C\xf3-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Cam on, hoc phi CNTT 2026?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\u01b0\u01a1ng tr\xecnh Alpha h\u1ecdc m\u1ea5y n\u0103m?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\u01b0\u01a1ng tr\xecnh ch\u1ea5t l\u01b0\u1ee3ng cao y\xeau c\u1ea7u nh\u1eefng g\xec?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o anh-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o b\u1ea1n, b\u1ea1n l\xe0 ai?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o b\u1ea1n, cho t\xf4i danh s\xe1ch ng\xe0nh tuy\u1ec3n sinh.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o b\u1ea1n, ng\xe0nh X v\xe0 ng\xe0nh Y kh\xe1c nhau th\u1ebf n\xe0o?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o bu\u1ed5i s\xe1ng, c\xe1c m\xf4n b\u1eaft bu\u1ed9c l\xe0 g\xec?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o bu\u1ed5i t\u1ed1i-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o c\xf4, tr\u01b0\u1eddng c\xf3 h\u1ecdc b\u1ed5ng kh\xf4ng?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ch\xe0o ch\u1ecb, \u0111i\u1ec1u ki\u1ec7n mi\u1ec5n h\u1ecdc ph\xed l\xe0 g\xec?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Cho t\xf4i danh s\xe1ch m\xf4n h\u1ecdc g\xec \u0111\xf3-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Danh s\xe1ch ng\xe0nh tuy\u1ec3n sinh?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Danh s\xe1ch t\u1ed5 h\u1ee3p x\xe9t tuy\u1ec3n c\u1ee7a m\xe3 0123456?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Good evening-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Good morning!-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Goodbye-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[HELLO!-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1ea1n \u0111\u0103ng k\xfd k\xfd t\xfac x\xe1?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1eb9n g\u1eb7p l\u1ea1i-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1ecdc b\u1ed5ng d\xe0nh cho \u0111\u1ed1i t\u01b0\u1ee3ng n\xe0o?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1ecdc ph\u1ea7n b\u1eaft bu\u1ed9c c\u1ee7a ch\u01b0\u01a1ng tr\xecnh Gamma?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1ecdc ph\xed CNTT n\u0103m 2026?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[H\u1ecdc ph\xed c\xf3 bao g\u1ed3m l\u1ec7 ph\xed thi kh\xf4ng?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hello, ch\u01b0\u01a1ng tr\xecnh 00007 c\xf3 y\xeau c\u1ea7u g\xec?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hello, tr\u01b0\u1eddng c\xf3 bao nhi\xeau ng\xe0nh?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hello-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Help me-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hi b\u1ea1n-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hi, cho m\xecnh bi\u1ebft ph\u01b0\u01a1ng th\u1ee9c x\xe9t tuy\u1ec3n.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hi, n\u0103m h\u1ecdc 2026\u20132027 c\xf3 m\u1ea5y h\u1ecdc k\u1ef3?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Hi\u1ebfn ph\xe1p quy \u0111\u1ecbnh th\u1ebf n\xe0o v\u1ec1 gi\xe1o d\u1ee5c?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Kh\xf4ng, t\xf4i h\u1ecfi n\u0103m 2026-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Kh\xf4ng-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[M\u1ee9c ph\xed \xe1p d\u1ee5ng cho nh\xf3m B, kh\xf4ng \xe1p d\u1ee5ng cho nh\xf3m A?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[M\xe3 ch\u01b0\u01a1ng tr\xecnh 00127?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[M\xf4n h\u1ecdc mang t\xean Hello c\xf3 bao nhi\xeau t\xedn ch\u1ec9?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[N\u0103m h\u1ecdc 2026\u20132027 c\xf3 bao nhi\xeau t\xedn ch\u1ec9?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ng\xe0nh Beta c\xf3 nh\u1eefng m\xf4n h\u1ecdc n\xe0o?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ng\xe0nh \u0111\xf3 h\u1ecdc m\u1ea5y n\u0103m?-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ng\xe0nh n\xe0o t\u1ed1t?-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ok-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Ph\u1ea1m vi c\u1ee7a ph\u1ee5 l\u1ee5c IV?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[S\u1ed1 hi\u1ec7u quy\u1ebft \u0111\u1ecbnh m\u1edbi \u0111\u01b0\u1ee3c c\xf4ng b\u1ed1?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[See you-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[So s\xe1nh ch\u01b0\u01a1ng tr\xecnh Alpha v\xe0 Beta n\u0103m 2026.-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[T\u01b0 v\u1ea5n gi\xfap t\xf4i-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[T\u1ea1m bi\u1ec7t, nh\u01b0ng cho t\xf4i h\u1ecfi h\u1ea1n n\u1ed9p h\u1ed3 s\u01a1.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[T\u1ea1m bi\u1ec7t-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[T\u1eeb \u201cc\u1ea3m \u01a1n\u201d xu\u1ea5t hi\u1ec7n \u1edf trang n\xe0o?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Th\u1eddi gian nh\u1eadn h\u1ed3 s\u01a1 h\u1ec7 sau \u0111\u1ea1i h\u1ecdc?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Thank you, h\u1ecdc ph\xed ng\xe0nh Beta bao nhi\xeau?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Thank you-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Thanks a lot-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Thanks, what are the admission requirements?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Thanks-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Tr\u01b0\u1eddng \u0110\u1ea1i h\u1ecdc Delta c\xf3 ng\xe0nh ti\u1ebfng Nh\u1eadt kh\xf4ng?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Tr\u01b0\u1eddng nh\u1eadn h\u1ed3 s\u01a1 t\u1eeb ng\xe0y n\xe0o?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Tra c\u1ee9u h\u1ecdc ph\xed n\u0103m 2025.-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[What can you do?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Who are you?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin c\u1ea3m \u01a1n!-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o b\u1ea1n nh\xe9.-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o! T\xf4i mu\u1ed1n tra c\u1ee9u m\xe3 ng\xe0nh 00123.-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o, b\u1ea1n l\xe0 ai?-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o, h\u1ecdc ph\xed CNTT n\u0103m 2026 bao nhi\xeau?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o, kh\xf4ng t\xednh nh\xf3m A th\xec c\xf3 bao nhi\xeau?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o, th\xf4ng tin li\xean h\u1ec7 trong t\xe0i li\u1ec7u l\xe0 g\xec?-MIXED-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Xin ch\xe0o-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[Y\xeau c\u1ea7u \u0111\u1ea7u v\xe0o ngo\u1ea1i ng\u1eef?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110\u0103ng k\xfd thi \u1edf \u0111\u1ecba ch\u1ec9 n\xe0o?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110\u1ed1i chi\u1ebfu d\u1eef li\u1ec7u 2025 v\xe0 2026.-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110i\u1ec1u ki\u1ec7n chuy\u1ec3n ng\xe0nh \u0111\u01b0\u1ee3c quy \u0111\u1ecbnh \u1edf \u0111\xe2u?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110i\u1ec1u ki\u1ec7n mi\u1ec5n h\u1ecdc ph\xed?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110i\u1ec1u ki\u1ec7n x\xe9t tuy\u1ec3n h\u1ecdc b\u1ea1 l\xe0 g\xec?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[\u0110i\u1ec3m chu\u1ea9n S\u01b0 ph\u1ea1m To\xe1n?-KNOWLEDGE-True]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ban la ai-ASSISTANT_META-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[bye-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[cam on-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ch\xe0o b\u1ea1n-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ch\xe0o bu\u1ed5i s\xe1ng-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ch\xe0o c\xf4-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ch\xe0o ch\u1ecb \u1ea1-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[ch\xe0o th\u1ea7y-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[chao ban-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[gi\xfap t\xf4i-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[good afternoon-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[help-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[hey-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[hi-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[t\u01b0 v\u1ea5n gi\xfap m\xecnh-CLARIFICATION-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[tam biet nhe-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[xin ch\xe0o!-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_labeled_utterance_routes_without_a_model_for_certain_cases[xin cha\u0300o-SOCIAL-False]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[C\u1ea3m \u01a1n b\u1ea1n nhi\u1ec1u nh\xe9]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[Hello]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[Xin Ch\xe0o!]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[chao ban]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[t\u1ea1m bi\u1ec7t]` — PASS
- `tests/test_hybrid_intent_routing.py::test_pure_social_never_enters_knowledge_pipeline[xin ch\xe0o]` — PASS
- `tests/test_hybrid_intent_routing.py::test_social_stream_does_not_announce_document_retrieval` — PASS
