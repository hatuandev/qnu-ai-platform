# Context575 — Kết quả kiểm chứng

Bản chốt đạt **59/60 = 98.33%** câu tri thức; positive **49/50**, negative **10/10**, social **4/4**. Baseline Context572 là 52/60 = 86,67%. Chấm toàn bộ 64 ID đúng thứ tự, không chọn điểm cao nhất trong các lượt phát triển.

Tám câu lỗi gốc đã chuyển FAIL → PASS: N19, M05, P03, P05, P06, P09, P15, X07. Câu PASS → FAIL so với baseline: **N18**. Không có lỗi mới trong pytest không có nghĩa benchmark không có hồi quy. N18 bị row audit yêu cầu nội dung Phụ lục II, rồi prose proposal chưa tạo được bằng chứng đầy đủ nên từ chối; nguồn chưa bị mất, nhưng câu hỏi về điều kiện NV-28 chưa được trả lời. Giữ đây là FAIL và là giới hạn còn mở, không miễn kiểm tra liên kết để tăng điểm.

## Kiểm tra mã

- Ruff 18 file: PASS, exit 0 (`checks/ruff-handoff-exit.json`).
- Kiểm tra tập trung bản chốt: 349 PASS, exit 0 (`handoff-focused-fixed`), gồm phạm vi/năm và các module RAG liên quan.
- Kiểm tra phạm vi/năm batch trước: 141 PASS, exit 0 (`year-guard-verified`), không thay thế kết quả hiện tại.
- Bộ tập trung trước lần bổ sung guard năm: 257 PASS, exit 0 (`final-all-focused`), là bằng chứng lịch sử của batch trước.
- Full hiện tại: **2905 PASS / 18 FAIL / 17 SKIP**, exit 1. **Full suite vẫn FAIL.**
- 67 case mới PASS; không thiếu ID cũ, không có thay đổi trạng thái test cũ hoặc lỗi mới. So sánh từng ID và nguyên nhân dưới đây.
- Có một batch trung gian phát sinh hai lỗi về năm. Chặn shortcut cho vai trò năm thì an toàn nhưng làm từ chối cả một số quote đúng. Bản chốt chỉ dùng claim sở hữu đúng quote/span/hash và vẫn gọi kiểm tra năm theo vai trò; năm yêu cầu khác năm nguồn, ngày ban hành giả làm năm dữ liệu hoặc temporal scope mâu thuẫn vẫn chặn. Khi không hỏi một năm cụ thể, kiểm năm giới hạn được nguồn nêu, không tự chọn năm trả lời. Probe trước sửa 4 FAIL/3 PASS, các case được đưa vào regression chính thức; không sửa assertion cũ để đạt PASS.
- Hai lần gọi nhầm đường dẫn test (`focused-third`, `year-guard-focused`) exit 4, NOT RUN; không tính vào PASS. Ruff từng phát hiện import chưa chuẩn, đã sửa và chạy lại.
- Lần đầu ghép thêm fixture năm thiếu import tạo 8 FAIL; đã sửa import và chạy lại cùng bộ 349 PASS. Giữ nguyên log lỗi thay vì ghi đè.
- Frontend/build không chạy trong Context575 vì không sửa frontend. Không gộp các diff parser/FE có từ phiên trước vào kết quả này.

## Các lượt 64 câu thực tế

| Lượt | Tri thức | ID FAIL | Usage records | Fallback records |
| --- | --- | --- | --- | --- |
| lượt đầu | 54/60 (90.0%) | P02, P06, P07, P12, P15, X09 | 139 | 0 |
| benchmark-final | 57/60 (95.0%) | P04, P06, P11 | 143 | 0 |
| benchmark-acceptance | 58/60 (96.67%) | P06, P11 | 125 | 0 |
| benchmark-complete | 55/60 (91.67%) | N18, F04, P02, P08, P16 | 130 | 0 |
| benchmark-verified | 55/60 (91.67%) | N18, F08, P05, P06, P16 | 129 | 0 |
| benchmark-handoff | 59/60 (98.33%) | N18 | 125 | 0 |

Tất cả là lượt phát triển trên cùng devset đã biết. Lượt `benchmark-release` bị gián đoạn sau 45 kết quả; P12 có intent gửi nhưng không có response chắc chắn, không gửi lại để giả hoàn tất lượt đó. Lượt này không có điểm 64 câu; cleanup đã phục hồi và xác minh. Các lượt `focused-live`/`focused-live-2` chỉ là chẩn đoán 3/1 ca, không thay thế điểm của lượt đầy đủ. Có một lần khởi chạy runner trước khi file được tạo, 0 request; giữ nguyên receipt setup lỗi.

## Luồng và phạm vi kiểm thử

Gọi thật handler chat ASGI với retrieval/embedding/reranker và LLM đang cấu hình, không mock các bước này; không khẳng định E2E qua trình duyệt hay server process đang chạy đã nạp mã mới. Mỗi request kiểm tra hash code, snapshot, cấu hình, payload vector và generation. Primary vẫn `cx/gpt-6-luna`, fallback cấu hình vẫn `qwen3.5-9b`; policy benchmark chặn Qwen giống baseline.

Nguồn xuất bản `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`, collection epoch 65 giữ nguyên; staging `ks_rev_d5135c27d130` không xuất bản. Frozen queries/gold SHA-256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`. Không reindex, publish, sửa model/config, restart, commit hoặc push.

Bản chốt có 125 usage records, fallback 0; prompt tối đa 10729 token. Citation resolve 111/111. p50 687.85 ms, p95 39971.16 ms. Không quy đổi records thành số câu; một câu có thể gọi model nhiều lần. Không suy timeout là hết context.

## Lỗi nền full suite

| Test ID | Nguyên nhân hiện tại | Baseline | Đối chiếu |
| --- | --- | --- | --- |
| tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import | asyncpg.exceptions.UndefinedTableError: relation "public.alembic_version" does not exist | asyncpg.exceptions.UndefinedTableError: relation "public.alembic_version" does not exist | Trùng ID và nguyên nhân đầu |
| tests.test_consulting_dispatcher::test_dispatch_admissions_with_export | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Trùng ID và nguyên nhân đầu |
| tests.test_consulting_dispatcher::test_dispatch_regulations_with_export | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | Trùng ID và nguyên nhân đầu |
| tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Trùng ID và nguyên nhân đầu |
| tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Trùng ID và nguyên nhân đầu |
| tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint | assert 403 == 200 | assert 403 == 200 | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api | assert 403 == 200 | assert 403 == 200 | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled | assert 403 == 400 | assert 403 == 400 | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled | assert 403 == 201 | assert 403 == 201 | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit | assert 403 == 200 | assert 403 == 200 | Trùng ID và nguyên nhân đầu |
| tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback | assert 403 == 200 | assert 403 == 200 | Trùng ID và nguyên nhân đầu |
| tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies | AssertionError: assert 'legacy_payload_schema' in [] | AssertionError: assert 'legacy_payload_schema' in [] | Trùng ID và nguyên nhân đầu |
| tests.test_tools::test_fact_layer_lookup_tool_found | assert False is True | assert False is True | Trùng ID và nguyên nhân đầu |
| tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims | AssertionError: assert 'AI.Admin' == 'admin' | AssertionError: assert 'AI.Admin' == 'admin' | Trùng ID và nguyên nhân đầu |
| tests.test_universal_tools::test_fact_layer_lookup_tool | assert False is True | assert False is True | Trùng ID và nguyên nhân đầu |
| tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Trùng ID và nguyên nhân đầu |
| tests.test_vllm_reranker::test_vllm_embedding_generation | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Trùng ID và nguyên nhân đầu |

## Dọn kiểm thử và giới hạn

DB regression dùng tên riêng có nonce; Storage riêng; hạ tầng test trỏ loopback hoặc endpoint vô hiệu. DB đã được dọn một lần, rồi tạo lại đúng DB tạm được sở hữu để kiểm tra bổ sung và dọn lại sau lần full cuối. Không migration hay đổi cấu trúc DB dùng chung. Live benchmark chỉ tạo conversation/gap thuộc lượt kiểm thử và giữ usage audit. Trước/sau kiểm tra source/config/vector seals bằng nhau. Trạng thái dọn cuối: `DB_REMOVED_STORAGE_POLICY_BLOCKED`. Lệnh xóa đúng Storage runtime bị kiểm duyệt tự động từ chối với lý do “blocked by policy”; giữ nguyên thư mục, không thử cách xóa khác hoặc tắt chính sách. Chi tiết machine-readable ở `backend/storage/context575/checks/cleanup-final.json`; evidence báo cáo có chủ ý được giữ, không chứa key trong báo cáo tracked.

Các FAIL của benchmark được giữ trong [bảng 64 ID](CASE_COMPARISON.md). Bộ mở rộng gồm [case nội bộ và 4 biến thể gọi thật](EXTENDED_TESTS.md). Đây chưa phải phép đo generalization trên tài liệu độc lập; chưa chạy ablation hay đo Hit@K/Recall@K/MRR, chưa kiểm chứng tải đồng thời. Một số đáp án trích nguyên văn còn lặp đoạn. Không coi vượt 85% là mọi ca đã ổn định hoặc toàn bộ test PASS.

## Việc còn mở

- **N18: hồi quy độ trả lời so với Context572.** Row audit đòi nội dung Phụ lục II; prose proposal không khép được bằng chứng để trả lời điều kiện NV-28. Cần phân biệt câu hỏi chép điều kiện mà bảng ghi với câu hỏi xác nhận thực sự đủ điều kiện; không dùng một quote tham chiếu để mặc nhiên duyệt hồ sơ.
- **B03: biến thể mới FAIL.** Trong giả định có thông báo kiểm định nhưng thiếu quyết định gia hạn, audit tiếp tục đòi xác nhận hồ sơ thuộc nhóm A/E-A và từ chối chung. Cần phân biệt giả định của câu hỏi với fact đã xác minh, giữ các tiền đề khi trả lời có điều kiện; không suy giả định thành dữ kiện nguồn. Hệ thống chưa cho phép gia hạn sai, nhưng chưa trả lời được câu hỏi.
- **B04: chỉ PASS bảo vệ.** Không bịa chương trình thứ13; reader trả clarify rồi từ chối, chưa nói rõ nguồn chỉ có12. Lượt này chưa chứng minh nhánh kiểm đếm server được chạy, dù các kiểm tra schema/hàng vẫn được unit-test riêng.

Ba điểm này được bàn giao thành giới hạn hành vi chung, không thêm mã/từ khóa của một câu hỏi vào ứng dụng hoặc tắt audit để làm điểm xanh.
