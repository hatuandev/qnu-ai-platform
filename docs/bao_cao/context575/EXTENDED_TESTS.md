# Context575 — Kiểm tra mở rộng

Các fixture nội bộ dùng mã, năm và số liệu khác benchmark. Mock kiểm tra contract và số lượt phục hồi; không được coi các test này là E2E gọi model thật. Bốn biến thể thực tế bên dưới cũng lấy từ cùng tài liệu phát triển, chưa phải tập đánh giá độc lập.

| Test ID mới so với Context572 | Kết quả | Lỗi |
| --- | --- | --- |
| tests.test_source_answer_scope_575::test_extracting_part_of_list_item_retains_its_own_limit_but_not_next_item[1.] | PASS |  |
| tests.test_source_answer_scope_575::test_extracting_part_of_list_item_retains_its_own_limit_but_not_next_item[2)] | PASS |  |
| tests.test_source_answer_scope_575::test_extracting_part_of_list_item_retains_its_own_limit_but_not_next_item[a)] | PASS |  |
| tests.test_source_answer_scope_575::test_audit_catalog_checks_unselected_same_source_rule_not_just_chosen_sentence | PASS |  |
| tests.test_source_answer_scope_575::test_unrelated_owner_or_revision_cannot_invent_conditions_for_a_selected_rule | PASS |  |
| tests.test_source_answer_scope_575::test_rule_recovery_keeps_both_literal_anchor_and_full_applicable_rule | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn l\xe0 02/04/2040.-True] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn: 02/04/2040.-True] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn kh\xf4ng ph\u1ea3i 02/04/2040.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y k\u1ebft th\xfac l\xe0 02/04/2040.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn l\xe0 03/04/2040.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn l\xe0 02/04/20401.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Ng\xe0y ti\u1ebfp nh\u1eadn l\xe0 02/04/2040X.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_same_labeled_date_role_can_be_retained_without_demanding_a_duplicate_format[Kh\xf4ng \u0111\xfang r\u1eb1ng ng\xe0y ti\u1ebfp nh\u1eadn l\xe0 02/04/2040.-False] | PASS |  |
| tests.test_source_answer_scope_575::test_distinct_date_roles_are_separate_source_conditions[ v\xe0 ] | PASS |  |
| tests.test_source_answer_scope_575::test_distinct_date_roles_are_separate_source_conditions[; ] | PASS |  |
| tests.test_source_answer_scope_575::test_source_conditions_keep_decimal_and_negative_requirement | PASS |  |
| tests.test_source_answer_scope_575::test_explicit_appendix_expands_descendants_without_cross_revision_or_next_appendix | PASS |  |
| tests.test_source_answer_scope_575::test_selected_identity_schema_cannot_silently_have_non_identity_or_subset_flags[flags0] | PASS |  |
| tests.test_source_answer_scope_575::test_selected_identity_schema_cannot_silently_have_non_identity_or_subset_flags[flags1] | PASS |  |
| tests.test_source_answer_scope_575::test_rule_question_leaves_coordinate_route_before_it_can_claim_complete | PASS |  |
| tests.test_source_answer_scope_575::test_rule_recovery_is_eligible_but_conflict_and_partial_are_not | PASS |  |
| tests.test_source_answer_scope_575::test_semantic_repair_is_once_on_same_evidence_then_reverified[False] | PASS |  |
| tests.test_source_answer_scope_575::test_semantic_repair_is_once_on_same_evidence_then_reverified[True] | PASS |  |
| tests.test_source_answer_scope_575::test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows[invalid0] | PASS |  |
| tests.test_source_answer_scope_575::test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows[invalid1] | PASS |  |
| tests.test_source_answer_scope_575::test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows[invalid2] | PASS |  |
| tests.test_source_answer_scope_575::test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows[invalid3] | PASS |  |
| tests.test_source_answer_scope_575::test_identity_enumeration_never_throws_or_hides_malformed_or_duplicate_rows[invalid4] | PASS |  |
| tests.test_source_answer_scope_575::test_unlocated_heading_cannot_expand_every_unparented_block | PASS |  |
| tests.test_source_answer_scope_575::test_literal_and_own_row_description_are_returned_together_without_new_meaning[0] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_and_own_row_description_are_returned_together_without_new_meaning[Ch\u01b0a c\xf4ng b\u1ed1] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_and_own_row_description_are_returned_together_without_new_meaning[Kh\xf4ng \xe1p d\u1ee5ng] | PASS |  |
| tests.test_source_answer_scope_575::test_ordinary_source_paragraph_is_not_lost_by_clause_segmentation[S\u1ed1 l\xe0 12.75.] | PASS |  |
| tests.test_source_answer_scope_575::test_ordinary_source_paragraph_is_not_lost_by_clause_segmentation[M\xe3 phi\xean b\u1ea3n l\xe0 v2.10.] | PASS |  |
| tests.test_source_answer_scope_575::test_ordinary_source_paragraph_is_not_lost_by_clause_segmentation[Kh\xf4ng \u0111\u01b0\u1ee3c b\u1ecf b\u01b0\u1edbc \u0111\u1ed1i so\xe1t.] | PASS |  |
| tests.test_source_answer_scope_575::test_conflicting_evidence_is_not_sent_through_semantic_repair | PASS |  |
| tests.test_source_answer_scope_575::test_condition_scope_follows_reverse_order_links_without_crossing_revision | PASS |  |
| tests.test_source_answer_scope_575::test_literal_anchor_is_not_demoted_by_the_packers_section_priority_mask | PASS |  |
| tests.test_source_answer_scope_575::test_condition_completion_rejects_unknown_ids_and_non_source_text[conditions0] | PASS |  |
| tests.test_source_answer_scope_575::test_condition_completion_rejects_unknown_ids_and_non_source_text[conditions1] | PASS |  |
| tests.test_source_answer_scope_575::test_condition_completion_rejects_unknown_ids_and_non_source_text[conditions2] | PASS |  |
| tests.test_source_answer_scope_575::test_missing_source_clause_is_copied_exactly_and_never_auto_approved[True] | PASS |  |
| tests.test_source_answer_scope_575::test_missing_source_clause_is_copied_exactly_and_never_auto_approved[False] | PASS |  |
| tests.test_source_answer_scope_575::test_exact_row_identity_survives_a_positional_heading_about_a_different_group[ZR-0042] | PASS |  |
| tests.test_source_answer_scope_575::test_exact_row_identity_survives_a_positional_heading_about_a_different_group[ZR-0402] | PASS |  |
| tests.test_source_answer_scope_575::test_table_identity_is_not_fabricated_for_missing_or_inconsistent_coordinates[paragraph-\| M\xe3 \| Gi\xe1 tr\u1ecb \|\n\| --- \| --- \|-\| ZR-0042 \| 0 \|] | PASS |  |
| tests.test_source_answer_scope_575::test_table_identity_is_not_fabricated_for_missing_or_inconsistent_coordinates[table--\| ZR-0042 \| 0 \|] | PASS |  |
| tests.test_source_answer_scope_575::test_table_identity_is_not_fabricated_for_missing_or_inconsistent_coordinates[table-\| M\xe3 \| Gi\xe1 tr\u1ecb \|\n\| --- \| --- \|-\| ZR-0042 \| 0 \| th\u1eeba \|] | PASS |  |
| tests.test_source_answer_scope_575::test_table_identity_is_not_fabricated_for_missing_or_inconsistent_coordinates[table-\| M\xe3 \| Gi\xe1 tr\u1ecb \|\n\| --- \| --- \|-\| ZR-0042 \| 0 \|\n\| ZR-0402 \| 7 \|] | PASS |  |
| tests.test_source_answer_scope_575::test_explicit_note_identifier_gets_an_anchor_without_partial_code_matching | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_prose_qualifier_requires_same_source_span_and_no_foreign_public_id[False-False-True] | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_prose_qualifier_requires_same_source_span_and_no_foreign_public_id[True-False-False] | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_prose_qualifier_requires_same_source_span_and_no_foreign_public_id[False-True-False] | PASS |  |
| tests.test_source_answer_scope_575::test_missing_scoped_qualifier_is_restored_then_independently_rechecked[True] | PASS |  |
| tests.test_source_answer_scope_575::test_missing_scoped_qualifier_is_restored_then_independently_rechecked[False] | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_text_cannot_establish_a_different_requested_year[data_year] | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_text_cannot_establish_a_different_requested_year[document_year] | PASS |  |
| tests.test_source_answer_scope_575::test_verbatim_text_cannot_establish_a_different_requested_year[event_year] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[data_year-K\u1ebf ho\u1ea1ch n\u0103m 2030 ch\u1ec9 d\xe0nh cho h\u1ed3 s\u01a1 thi\u1ebft b\u1ecb.-years0-True] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[data_year-K\u1ebf ho\u1ea1ch n\u0103m 2030 ch\u1ec9 d\xe0nh cho h\u1ed3 s\u01a1 thi\u1ebft b\u1ecb.-years1-True] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[data_year-K\u1ebf ho\u1ea1ch n\u0103m 2030 ch\u1ec9 d\xe0nh cho h\u1ed3 s\u01a1 thi\u1ebft b\u1ecb.-years2-False] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[data_year-Ng\xe0y ban h\xe0nh: 02/04/2030.-years3-False] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[document_year-Ng\xe0y ban h\xe0nh: 02/04/2030.-years4-True] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[event_year-S\u1ef1 ki\u1ec7n t\u1ed5 ch\u1ee9c ng\xe0y 02/04/2030.-years5-True] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_own_claim_keeps_year_role_without_borrowing_another_claim[event_year-S\u1ef1 ki\u1ec7n t\u1ed5 ch\u1ee9c ng\xe0y 02/04/2030.-years6-False] | PASS |  |
| tests.test_source_answer_scope_575::test_literal_year_does_not_override_conflicting_verified_temporal_scope | PASS |  |

## Biến thể gọi thật

| ID | Phạm vi | Kết quả | Bằng chứng |
| --- | --- | --- | --- |
| B01 | Không áp chú thích riêng sang mã gần giống | PASS | Quote nguồn đúng scope chỉ AM-0007, loại AM-0070;2citation hợp lệ. |
| B02 | Không biến source unknown thành0 để tính tổng | PASS | Giữ ký hiệu chưa định nghĩa, không tự diễn giải;3citation hợp lệ. |
| B03 | Thiếu một điều kiện trong cặp bắt buộc đồng thời | FAIL | Từ chối chung do audit chưa xác nhận scope nhóm A/E-A; chưa trả lời rõ thiếu quyết định thì chưa đủ điều kiện. Không có kết luận cho phép sai. |
| B04 | Sai tiền đề13 chương trình khi nguồn có12 | PASS | PASS bảo vệ không bịa13 mã/dòng tổng. Reader clarify rồi từ chối chung; chưa nêu rõ số nguồn12, chưa đi tới nhánh đếm server. |
