# Context564 — Kiểm chứng atomic dependency closure

## Contract

Reviewed fact hợp lệ cần đúng canonical row và những dependency bắt buộc được metadata tham chiếu. Dòng nguồn cũng được duyệt refs riêng. Closure có hướng; vòng tham chiếu được duyệt hữu hạn; dùng lại đối tượng đã xác minh. Không lấy các consumer khác của shared note làm dependency ngược.

Canonical explicit groups cũng giữ closure bắc cầu. Sau bước thêm heading/ancestor/list/continuation, packer hoàn tất required refs của tất cả thành viên trước khi tính chi phí. Enumeration membership chỉ áp cho nhóm đã chọn, không trở thành quyền kéo mọi sibling của một referenced note.

| Kiểm chứng | Bằng chứng |
|---|---|
| Dòng nguồn chính xác, giữ đối tượng gốc | `test_fact_group_keeps_exact_source_row_and_its_own_dependencies` |
| Pack → claim projection | `test_fact_selection_pack_and_claim_projection_retains_source_proof` |
| Selection từ artifact fixture published → pack → projection, không đổi snapshot | `test_published_fact_selection_through_projection_does_not_mutate_snapshot` |
| Missing row/header/note | `test_missing_required_source_unit_stays_blocked` (3 tham số) |
| Sai binding/index/source revision/hash | `test_wrong_source_identity_is_not_replaced_by_similar_text` (4 tham số) |
| Duplicate canonical unit | `test_duplicate_canonical_unit_is_rejected` |
| Chuỗi dependency/vòng tham chiếu | `test_source_row_transitive_dependencies_and_cycles_are_closed_once`, `test_canonical_only_pack_preserves_transitive_required_context` |
| Metadata hỏng/missing target | `test_invalid_dependency_metadata_is_not_accepted`, `test_invalid_canonical_chain_remains_an_evidence_error` |
| Shared source/note, ordering và serialization | `test_shared_source_and_note_deduplicate_with_stable_order_and_serialization` |
| Không mở ngược sang row/sibling khác | `test_source_row_can_be_shared_but_note_does_not_expand_other_fact_rows`, `test_referenced_note_does_not_pull_its_unrequested_list_siblings` |
| Footnote của list member và structural ancestor | `test_numbered_group_member_keeps_its_own_footnote`, `test_structural_ancestor_keeps_its_required_note_within_budget` |
| Ngân sách K/ký tự nhỏ | `test_insufficient_budget_rejects_whole_fact_group` (2 tham số), ancestor test |
| Canonical text không có fact | `test_canonical_text_without_reviewed_facts_keeps_existing_behavior` |

Các ID trên thuộc `backend/tests/test_evidence_closure_564.py`. Dữ liệu synthetic chỉ dùng trong test; không phải nội dung thêm vào kho tri thức.

Các guard artifact, storage pair, manifest seal, source locations và stale revision tiếp tục được kiểm bởi `test_qnu_serving.py` và `test_review536_findings.py`, gồm `test_storage_pair_and_new_revision_projection_are_verified`, `test_standard_revision_rejects_missing_or_stale_projection`, `test_missing_cross_revision_or_wrong_hash_dependencies_reject_the_fact`. Không thay expectation của các tests cũ.

## Kiểm trên dữ liệu đang published

Probe read-only trên snapshot cố định hiện hành: 272 canonical blocks, 113 prose candidates. Trước hoàn tất member closure có 5 seed packs mất footnote; sau bản cuối 0. Cả 6 fact groups được chọn trong probe giữ row và closure/projection PASS, K=5 / 36000, 5 blocks/group.

`exhaustive=True` cho cùng snapshot có 67 groups, khác với 6 groups được ranking chọn. Không coi số 6 là tổng toàn tài liệu hoặc tổng DB facts.

## Budget và provenance

Chi phí của các block bổ sung được tính trước admission, cùng serialization overhead hiện có; shared block đã nhận không bị tính lại. Đây là ngân sách ký tự của packer, không phải phép đo toàn HTTP prompt hay tokenizer của Qwen. Không suy token từ số ký tự.

Fact group vượt K/character budget không được giữ một phần. `dropped` giữ `block_limit`/`character_budget`. Thiếu provenance vẫn là exception bằng chứng, không bị đổi thành budget exclusion. Guard nguyên vẹn; nguồn/hash/revision không được viết lại.

Pure-function và fixture tests chứng minh closure/projection; không thay cho provider verification hoặc chat E2E. Trạng thái những phần sau được ghi riêng trong LIVE_RAG_E2E_REPORT.
