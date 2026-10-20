# Context570 — Kết quả kiểm chứng theo test ID

## Kết quả cuối

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Ruff 18 file có thay đổi (17 app + 1 test) | PASS | 0 |
| Focused, 7 test files | 155 PASS | 0 |
| Contract tương thích sau full đầu | 83 PASS | 0 |
| Regression mới chạy trên baseline-app bất biến | 20 FAIL / 5 PASS | 1 |
| Replay 9 tầng xử lý trên frozen source | 9 PASS / 0 FAIL | 0 |
| Full backend cuối | **2810 PASS / 18 FAIL / 17 SKIP** | 1 |

Tổng full vẫn **FAIL** vì còn 18 lỗi. Full Context567 là baseline lịch sử: 2.785 PASS / 18 FAIL / 17 SKIP, thêm 23 subtests PASS. Lượt hiện tại cũng có 23 subtests PASS. Đối chiếu hiện tại: 0 lỗi mới, 0 ID cũ bị mất, 0 trạng thái cũ thay đổi; 25 test ID mới PASS. Cả 18 lỗi khớp nguyên nhân đầu tiên với baseline; bảng dưới giữ từng ID và nguyên nhân. Không cộng số test từ các lượt focused có phần trùng nhau.

Regression frozen có cả các FAIL về hành vi cũ và FAIL vì module/contract mới chưa tồn tại; không gọi tất cả20FAIL là20lỗi runtime đã từng xảy ra. Bộ mới được viết sau đợt sửa theo yêu cầu batch, rồi kiểm trên bản code snapshot trước sửa; không giả đây là TDD chạy trước khi sửa.

## Lệnh và môi trường

CWD root repo để điều phối; pytest chạy ở backend. Dùng Python backend/.venv/Scripts/python.exe.

- `backend/storage/context570/checks.py setup`: xác minh DB development/MinIO/Qdrant loopback; connection DB chung READ ONLY. Tạo đúng DBtest có nonce và49ORM tables, không migration DB chung.
- `backend/storage/context570/checks.py run tests/test_context570_evidence_scope.py --label frozen-regression --baseline`: app snapshot bất biến được import trước pytest; không dùng code sửa khi chấm baseline.
- `backend/storage/context570/checks.py run tests/test_context570_evidence_scope.py tests/test_context567_rag_regressions.py tests/test_rag_prose_recovery_491.py tests/test_row_answer_contract.py tests/test_row_metric_headers.py tests/test_temporal_fact_contract.py tests/test_evidence_closure_564.py --label focused`.
- `backend/storage/context570/frozen_replay.py`: so các ID được pack, rows/caption/reference và reason; không trả lời bằng model hoặc rerank live.
- `backend/storage/context570/checks.py run --label full-final-2`: full cuối sau sửa lỗi tương thích tìm được ở full đầu; JUnit full-final-2.xml và receipt full-final-2-run.json. Full đầu26FAIL/2802PASS/17SKIP được giữ nguyên. Lượt full-final bị ngắt giữa chừng, không có exit code/JUnit hoàn tất; giữ log và receipt INTERRUPTED, không tính là PASS.
- Ruff check trên18file; git diff --check, UTF8/LF/link/hash validation lúc handoff.

DB test `qnu_test_context570_65d90c468aec`, Storage `context570-runtime-65d90c468aec`. Endpoint external test services port1, không live DB corpus/MinIO/Qdrant. Sitecustomize egress guard chỉ cho DBtest/port1 và socketpair nội bộ Windows để asyncio hoạt động; không mở port mạng tùy ý. Test có mock/fake provider chứng minh contract, không chứng minh LLM thật.

## Lỗi nền theo ID

| Test ID | Đã FAIL baseline | Nguyên nhân hiện tại | Đối chiếu cause |
|---|---|---|---|
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | Có | asyncpg.exceptions.UndefinedTableError: relation "public.alembic_version" does not exist | Khớp |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | Có | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Khớp |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | Có | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | Khớp |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | Có | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | Có | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | Có | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | Có | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | Có | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | Có | assert 403 == 400 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | Có | assert 403 == 201 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | Có | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | Có | assert 403 == 200 | Khớp |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | Có | AssertionError: assert 'legacy_payload_schema' in [] | Khớp |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | Có | assert False is True | Khớp |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | Có | AssertionError: assert 'AI.Admin' == 'admin' | Khớp |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | Có | assert False is True | Khớp |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | Có | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Khớp |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | Có | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |

Danh sách status/cause đầy đủ và IDs thêm: private `test-comparison.json`. Baseline18FAIL vẫn được giữ trung thực; không seed nguồn thật, tắt auth hoặc sửa assertion để làm chúng xanh.

## Lịch sử kiểm tra trong batch

- Ruff lần đầu4lỗi import/regex aliases; scoped fix4điểm rồi cuốiPASS, không fix toàn repo.
- Lượt mới đầu19PASS/6ERROR do egress guard chặn cả socketpair nội bộ asyncio Windows. Sửa helper test để chỉ miễn đúng thao tác socketpair trong context nội bộ; endpoint guard vẫn giữ.
- Lượt tiếp24PASS/1FAIL, positive extractive list bị tách ordinal thành assertion số riêng. Hai probe hẹp giữ cùng failure, rồi sửa sentence boundary; không đổi yêu cầu positive/negative test để làm xanh.
- Focused cuối155PASS sau sửa; baseline-app20FAIL/5PASS phản ánh code cũ; replay9PASS. Bằng chứng các lượt cũ giữ nguyên.
- Full đầu thêm7lỗi contract do catalog schema-only chứaNone/thiếublock_id; sửa helper đọc điều kiện chỉ từQuoteReference thật. Các test coverage/negative giữ nguyên. Một lỗi Context548 do DBtest chưa có systemdefaults cũng tái hiện trên appbaseline; chỉ copy1row typeddefaults vàoDBtest, khôngprovider/key/credential; nguồnModelOpsREADONLY. Lượtcontract-fixed kiểm lại riêng trướcfullcuối. Không sửa test để giấu failure.

## Bảo toàn và cleanup

Read-only row hashes của nguồn/index/model/assistant khớp Context568; không ghi dữ liệu DB chung. DB test đã xóa sau kiểm ownership nonce; trạng thái Storage: `database_and_storage_removed`. Bằng chứng ignored được giữ để đối soát; không xóa runtime cũ của Context khác đã bị policy chặn.

Không có64-case benchmark mới, inference/provider capability/holdout hoặc publication E2E ở bước2. Những phép thử đó NOT RUN; điểm51/60 hai model vẫn là lịch sử. Bộ audit condition mới còn phụ thuộc phân loại ngữ nghĩa của model và có thể tăng token/độ trễ/từ chối; chưa đo tác động này. Không báo13ca model thật đã PASS.
