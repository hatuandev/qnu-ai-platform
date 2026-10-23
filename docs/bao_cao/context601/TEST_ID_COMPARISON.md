# Context601 — Đối chiếu test theo ID

Full chốt: **3.361 PASS / 19 FAIL / 17 SKIP**, thêm 23 subtest PASS, exit 1.
So với full Context600: giữ đủ ID, 18 lỗi nền giữ nguyên failure message; thêm một lỗi backup Windows.
Không thay kết quả full bằng kết quả retry.

| Test ID | Kết quả trước → sau | Nguyên nhân quan sát |
|---|---|---|
| `tests.test_backup_launcher::test_real_backup_runner_starts_under_default_platform_loop` | PASS → FAIL | PermissionError khi đọc catalogue JSON fixture Windows; chưa kết luận nguyên nhân gốc. |
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | FAIL → FAIL | Thiếu bảng version Alembic trong DB test không chạy migration. |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | FAIL → FAIL | Thiếu fixture collection tuyển sinh. |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | FAIL → FAIL | Thiếu fixture collection quy chế. |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | FAIL → FAIL | Không xác minh được capacity server AI trong môi trường cô lập. |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | FAIL → FAIL | Redis test không có listener. |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | FAIL → FAIL | Không xác minh được capacity OCR server AI. |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | FAIL → FAIL | Quyền API:403 thay vì200. |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | FAIL → FAIL | Quyền API:403 thay vì200. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | FAIL → FAIL | Quyền API:403 thay vì400. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | FAIL → FAIL | Quyền API:403 thay vì201. |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | FAIL → FAIL | Quyền API:403 thay vì200. |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | FAIL → FAIL | Quyền API:403 thay vì200. |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | FAIL → FAIL | Không nhận discrepancy legacy_payload_schema. |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | FAIL → FAIL | Tool fact lookup trả false. |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | FAIL → FAIL | Role legacy AI.Admin khác admin. |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | FAIL → FAIL | Tool fact lookup trả false. |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | FAIL → FAIL | Thiếu fixture collection tuyển sinh. |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | FAIL → FAIL | Embedding provider không khả dụng trong isolation. |

Chẩn đoán riêng `tests/test_backup_launcher.py`: **6 PASS, exit 0**, cùng code và DB test; không tái hiện lỗi đọc tệp. Điều này không biến full 19 FAIL thành 18 FAIL.

## Regression mới

23 test mới đều PASS. Trước sửa role: 4 FAIL đúng hành vi, 2 PASS control; sau đó thêm 3 ca khác revision. Trước sửa selection: 1 probe FAIL vì thiếu các sibling nguồn.

| Test ID mới | Kết quả |
|---|---|
| `tests.test_dependency_roles_601::test_conflicting_governing_verdict_cannot_borrow_another_revision[exception]` | PASS |
| `tests.test_dependency_roles_601::test_conflicting_governing_verdict_cannot_borrow_another_revision[prerequisite]` | PASS |
| `tests.test_dependency_roles_601::test_conflicting_governing_verdict_cannot_borrow_another_revision[scope]` | PASS |
| `tests.test_dependency_roles_601::test_negative_decision_cannot_erase_affirmed_governing_relation[exception]` | PASS |
| `tests.test_dependency_roles_601::test_negative_decision_cannot_erase_affirmed_governing_relation[prerequisite]` | PASS |
| `tests.test_dependency_roles_601::test_negative_decision_cannot_erase_affirmed_governing_relation[scope]` | PASS |
| `tests.test_dependency_roles_601::test_non_governing_background_can_still_be_rejected[definition]` | PASS |
| `tests.test_dependency_roles_601::test_non_governing_background_can_still_be_rejected[unrelated]` | PASS |
| `tests.test_dependency_roles_601::test_verification_preserves_eligibility_then_accepts_exact_source_repair` | PASS |
| `tests.test_native_rule_selection_601::test_all_or_none_selection_preserves_the_existing_twelve_claim_budget` | PASS |
| `tests.test_native_rule_selection_601::test_full_native_members_have_unique_ids_and_exact_bound_source_spans` | PASS |
| `tests.test_native_rule_selection_601::test_independent_verifier_can_reject_an_unrelated_offered_list_member` | PASS |
| `tests.test_native_rule_selection_601::test_invalid_or_unbounded_group_is_not_partially_offered[absent_parent]` | PASS |
| `tests.test_native_rule_selection_601::test_invalid_or_unbounded_group_is_not_partially_offered[duplicate_native]` | PASS |
| `tests.test_native_rule_selection_601::test_invalid_or_unbounded_group_is_not_partially_offered[oversized]` | PASS |
| `tests.test_native_rule_selection_601::test_native_rule_selection_offers_whole_source_group_before_independent_verification` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[binding]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[container]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[hash]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[index]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[legacy]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[parent]` | PASS |
| `tests.test_native_rule_selection_601::test_selection_does_not_cross_native_owner_or_source_boundary[revision]` | PASS |

Focused chốt 34 file: **852 PASS, 1 warning, exit 0**. Ruff 6 file: **PASS, exit 0**.
Full trước thay selection:3.348 PASS/18 FAIL/17 SKIP; lịch sử trung gian, không phải kết quả full chốt.

Các lệnh được chạy bằng Python trong `backend/.venv`, từ repo hoặc helper đặt cwd `backend`:

- `context601_checks.py run --label baseline-role --baseline ...`: exit 1, 4 FAIL/2 PASS.
- `context601_checks.py run --label baseline-rule-group ...`: exit 1, probe tái hiện thiếu sibling.
- `context601_checks.py run --label focused-rule-selection ...`: exit 0, 852 PASS.
- `context601_gate.py full-handoff`: exit 1, kết quả full ở trên; code seal không đổi.
- `context601_compare.py full-handoff`: exit 0 cho thao tác đối chiếu, **không phải exit của Pytest**.
- `context601_checks.py run --label backup-diagnostic tests/test_backup_launcher.py`: exit 0, 6 PASS.
- `python -m ruff check` 3 file app và 3 file test thuộc phạm vi: exit 0.

Lệnh đầy đủ, exact failure messages, JUnit XML, before/after hashes và các receipts lưu ở `backend/storage/context601/checks/` (ignored). Không chép log runtime/model hoặc corpus vào Git.
