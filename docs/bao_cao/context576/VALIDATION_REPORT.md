# Context576 — Kết quả kiểm chứng

Bản chốt: **59/60 = 98.33%** câu tri thức; positive 49/50, negative 10/10, social 4/4. Baseline Context575: 59/60, N18 FAIL. Chuyển FAIL → PASS: N18. Chuyển PASS → FAIL: P06. [Đối chiếu đủ 64 ID](CASE_COMPARISON.md).

**Giới hạn kết luận:** chênh lệch ròng so với Context575 là +0 câu đúng. Các PASS → FAIL là hồi quy quan sát trong phép đo; chưa có ablation/repeated controlled runs để quy toàn bộ chênh lệch cho một thay đổi cụ thể. Không lấy việc vượt85% để bỏ qua chênh lệch hoặc tuyên bố toàn RAG APPROVED.

B03 trên chính mã bản chốt: **PASS**. B03 trả nguyên văn đầy đủ phạm vi thiết bị nhómA/kế hoạch2027, yêu cầu cả thông báo lẫn quyết định, và các loại trừ. Không xác nhận hồ sơ thật đủ điều kiện; chưa có diễn giải ngắn riêng. Câu trả lời được chấm theo rubric nguồn đã chốt trước inference: trích đầy đủ quy tắc có điều kiện được chấp nhận, không bắt model tự viết một phán quyết hồ sơ. Chưa chứng minh một giao diện diễn giải ngắn “chưa đủ điều kiện”; hiện vẫn trả quote nguồn.

## Regression và Ruff

- Trước sửa: 3 FAIL / 12 PASS tái hiện thiếu attribution ở mã khác benchmark; edge tests 3 FAIL / 20 PASS; probe clause binding 1 FAIL / 2 PASS. Giữ nguyên receipts và lỗi.
- Sau batch cuối: **393 PASS**, exit0, gồm **44 test mới** và các scope/year/row/recovery/provenance liên quan.
- Ruff: **15 file PASS**, exit0.
- Full bản chốt: **2949 PASS / 18 FAIL / 17 SKIP**, exit1; toàn suite vẫn **FAIL**. Không lỗi pytest mới, không thiếu ID cũ hoặc đổi trạng thái cũ; 44 ID mới PASS. So sánh nguyên nhân đầu theo ID bên dưới.
- Batch đầu full: 2928 PASS / 18 FAIL / 17 SKIP; là bằng chứng lịch sử trước bổ sung map clause và guard audit, không thay kết quả hiện tại.
- Batch v12 full: 2945 PASS / 18 FAIL / 17 SKIP, sau đó B03 vẫn FAIL do metadata vị trí nên tiếp tục sửa projection. Không dùng full cũ để nghiệm thu code v13.
- Trong lúc mở rộng: một fixture quote quá dài chạm contract ở bước tạo catalog; đã sửa fixture thành các câu vừa contract để kiểm đúng hành vi context augmentation. Không tăng giới hạn quote nguồn. Lần binding-focused bắt được một audit phủ định bị bỏ qua (1 FAIL / 382 PASS); guard được thêm rồi chạy lại389 PASS. Không đổi assertion về đúng/sai dữ kiện cũ. Một assertion transport của test575 được cập nhật sau đó theo contract metadata mới, kèm kiểm tra provenance gốc không đổi, như báo cáo triển khai giải thích.
- Frontend/build: NOT RUN vì không đổi frontend. Không coi mock contract là model E2E.

## Gọi thật và phạm vi đo

| Lượt đầy đủ | Tri thức | ID FAIL | Usage records | Fallback |
| --- | --- | --- | --- | --- |
| benchmark64 | 57/60 (95.0%) | P02, P12, P15 | 133 | 0 |
| benchmark-handoff | 56/60 (93.33%) | F04, P02, P08, P16 | 127 | 0 |
| position64 | 59/60 (98.33%) | P06 | 128 | 0 |

`final64` bị ngắt sau37 kết quả; P04 có intent nhưng không có response chắc chắn, không gửi lại để hoàn thành lượt đó. Lượt mới `benchmark-handoff` là một thí nghiệm đầy đủ riêng, không lấy response cũ ghép vào. Full `full-binding` cũng bị ngắt và không có exit/JUnit, ghi INTERRUPTED chứ không PASS. Lượt full và64 mới được chạy lại vì lần ngắt.

Sáu diagnostic batch đầu đạt6/6, citation22/22. B03 gọi riêng sau full64 batch v12 lại FAIL (verifier dùng section vị trí làm scope), giữ nguyên kết quả trong `final-probe`; không gọi đó là PASS. Sau sửa projection v13, sáu diagnostic được chạy lại trên cùng bộ câu hỏi, trước lượt64 cuối với cùng code hash. Kết quả cuối 4/6, B03 PASS. Không đưa diagnostic vào mẫu số60, không thay FAIL của lượt đầy đủ bằng retry. Đây là devset và các biến thể từ cùng tài liệu đã dùng phát triển; nhãn Codex source-checked chưa có human signoff, không phải holdout độc lập.

| Diagnostic trên code v13 | Kết quả | Giới hạn |
| --- | --- | --- |
| N18: thuật điều kiện ghi trong bảng | PASS | Không xác nhận hồ sơ thực tế đã đạt. |
| B03: giả định thiếu quyết định gia hạn | PASS | Trích đủ quy tắc có điều kiện, chưa có câu diễn giải ngắn riêng. |
| G01: pointer có đủ để xác nhận hồ sơ được nghiệm thu? | PASS bảo vệ | Từ chối xác nhận; chưa có giải thích cụ thể. Không chứng nhận UX đầy đủ. |
| G02: áp E-A sang hồ sơ thực tập nhóm B? | FAIL | HTTP503 `ALL_PROVIDERS_UNAVAILABLE`; lỗi provider không tính là từ chối đúng. |
| G03: đủ hai điều kiện thì mọi hồ sơ/mọi nhóm đều được gia hạn? | FAIL | Từ chối chung, chưa trả lời bằng quy tắc phạm vi; không cho phép sai. |
| G04: đổi ký hiệu chưa định nghĩa thành0? | PASS | Giữ nguyên ký hiệu và unknown. |

Gọi API handler ASGI thật, retrieval/embedding/reranker/LLM thật, không dependency override hay fake adapter. Không chứng nhận browser E2E hoặc process backend đang chạy đã tự nạp mã mới. Cùng source/index/snapshot/config/vector trước và sau; primary vẫn `cx/gpt-6-luna`, fallback cấu hình `qwen3.5-9b`, policy đo chỉ cho Luna như baseline. Không fallback che lỗi; 128 usage records, fallback0, prompt tối đa11700 token. Một câu có thể gọi model nhiều lần, không quy usage records thành số câu.

Nguồn phục vụ `ks_rev_ca1e7f16d9e0` / index `idx_rev_967891af9d5d`, collection `col_admissions` epoch65; staging không xuất bản. Frozen query/gold SHA256 `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`. Citation resolve 144/144; p50 658.27ms, p95 38717.79ms. Không ablation/Hit@K/Recall@K/MRR/tải đồng thời, không so tốc độ hai model.

## Lỗi nền full suite — vẫn FAIL

| Test ID | Lỗi hiện tại | Baseline | Đối chiếu |
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

## Dọn và giới hạn

Đã xác minh DB/MinIO/Qdrant local trước test; regression dùng DB riêng có nonce, Storage riêng và endpoint dịch vụ vô hiệu. Không migration hay sửa cấu trúc DB dùng chung. Status dọn: **DB_REMOVED_STORAGE_POLICY_BLOCKED**. Live tests chỉ dọn conversation/message/gap của lượt với exact ownership; usage audit và báo cáo giữ. Bằng chứng machine-readable trong `backend/storage/context576/checks/cleanup-final.json`.

DB kiểm thử đã dọn và xác minh còn0 database đúng tên tạm. Có7 lượt cleanup live được kiểm tra: tổng219 thread và35 gap thuộc test đã dọn, không còn message/thread/gap thuộc các lượt này; dữ liệu có từ trước và usage audit giữ nguyên. Lệnh xóa đúng `backend/storage/context576-runtime-99cdf1ade8d1` bị kiểm duyệt tự động từ chối với lý do “blocked by policy”. Thư mục được giữ; không thử cách xóa khác, không tắt chính sách và không dọn runtime575 hoặc Storage cũ.

Không hạ Quality Gate, đổi model/config, reindex, xuất bản lại, restart/deploy, commit/push hoặc áp semantic proposal. Việc sửa code không tự duyệt hồ sơ hay dữ liệu nguồn. Các FAIL hiện tại: P06. Không kết luận mọi cách hỏi hoặc mọi tài liệu đều đạt; đáp án trích nguyên văn có thể dài/lặp, và provider/audit vẫn có biến thiên qua các lượt.

P06 cần được theo dõi riêng: các facet được verifier đánh dấu đủ nhưng audit toàn câu trả lời vẫn yêu cầu giữ đầy đủ điều kiện gia hạn/loại trừ và trả `complete=false`. Hệ thống giữ chặn nên chưa trả lời được câu hỏi, không tự coi các điều kiện là đã thỏa mãn. Đây là PASS → FAIL so với lượt Context575 và không được che bằng điểm tổng bằng nhau.

Các khoảng hở quan sát ở batch v12: F04 bị router trả `CONTEXT_SCOPE_UNPROVEN` nên không gọi RAG; P02 vướng audit cho quy ước năm học/năm dương lịch; P08 chưa xác nhận topic của Bảng9/chú thích; P16 bị đánh dấu thiếu điều kiện về biến đầu vào sau phục hồi. Các kết quả đó giữ nguyên là FAIL trong batch của chúng; trạng thái bản chốt đọc từ [bảng64](CASE_COMPARISON.md). Không thay nội dung gold/câu hỏi để chấm lại.
