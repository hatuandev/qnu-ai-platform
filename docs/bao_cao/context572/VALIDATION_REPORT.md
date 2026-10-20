# Context572 — Kiểm chứng và giới hạn

| Kiểm tra | Kết quả thực chạy | Exit |
| --- | --- | ---: |
| Benchmark frozen64, runner | 64/64; X07 HTTP503; 52/60 tri thức đạt; xã giao4/4 | 0 runner / 0 scorer |
| Native artifact regression trước sửa | 1 FAIL, đúng block_quality_flag_invalid | 1 |
| Mở rộng projection regression trước sửa hoàn chỉnh | 1 FAIL, đúng còn issue header sau native proof | 1 |
| Backend focused-final 6 files | 109 PASS, 23 subtests PASS | 0 |
| Ruff 2 files sửa | PASS | 0 |
| Full backend cuối | **2838 PASS, 18 FAIL, 17 SKIP**, 23 subtests PASS | 1 |
| Full IDs/causes so Context571 | 0 new FAIL, 0 old status change, 0 missing, 1 new PASS | 0 |
| Native DOCX → standard → downloads → AST | PASS; raw517 fields/3 notes giữ | 0 |
| Vector API + worker thật + DB/Qdrant parity | PASS;262 staging points, old262 giữ | 0 |
| Preview6 theo nội dung | 4 PASS / 2 FAIL; HTTP/citation binding đúng | 0 runner, nội dung PARTIAL |
| D01 range canonical preview | PASS, HTTP200 và source citations đúng | 0 |

Full suite vẫn FAIL. Lượt full-final bị ngắt để hoàn thiện cùng lỗi tích hợp, không có kết luận PASS; receipt lưu exit4294967295/INTERRUPTED. Focused109 trước nhánh projection mở rộng không thay thế focused-final109 sau cùng. Không chạy lại FE lint/build vì phiên này không sửa frontend; build/FE36 của Context571 chỉ là kết quả lịch sử.

## Môi trường và lệnh

CWD root `D:/DuAnPhanMem/qnu-ai-platform`; Python `backend/.venv/Scripts/python.exe`. Các runner setup/readback xác minh development DB `127.0.0.1:5432/qnu_ai_platform`, MinIO/Qdrant loopback. Live test chỉ ghi các conversation/gap kiểm thử, revision DOCX mới và staging index được giao; không migration/production, không xóa kho. Model credentials vẫn trong ModelOps, không ghi ra báo cáo.

Pytest CWD backend, DB riêng `qnu_test_context572_83f5a04870d0`, 49 bảng ORM; Storage local runtime riêng. Service endpoints port1 và egress guard, không provider credentials. Một defaults metadata row có kiểu được copy riêng, không copy key/provider. `checks.py run` ghi exact commands, JUnit IDs, exit và causes; các lệnh chính:

- `context572/preflight.py`; `run.py`; `verify_cleanup.py`; `adjudicate.py`; `score.py`.
- `context572/checks.py setup`, `seed-defaults`, regression-before, projection-before, focused-final và `run --label full-complete`.
- Ruff scoped hai file; `compare_tests.py` đối chiếu `context571/full-final-2.xml`.
- `retry2/create_draft.py`, `validate_draft.py`, `verify_ast.mjs`, `submit_vector.py`, `audit_staging.py`, `preview.py`, `range_preview.py`.
- `final_audit.py`: 1289 file trước benchmark; chỉ đúng parser native fidelity và test đổi sau benchmark; RAG và query/gold giữ.

## Đối chiếu 18 lỗi nền

| Test ID | Nguyên nhân đầu tiên | So baseline571 |
| --- | --- | --- |
| `tests.test_configuration_seed_db::test_real_restore_roundtrip_refuses_overwrite_and_rolls_back_partial_import` | asyncpg.exceptions.UndefinedTableError: relation "public.alembic_version" does not exist | Khớp |
| `tests.test_consulting_dispatcher::test_dispatch_admissions_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Khớp |
| `tests.test_consulting_dispatcher::test_dispatch_regulations_with_export` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_regulations' | Khớp |
| `tests.test_ingestion_resilience::test_shared_capacity_bounds_twenty_simultaneous_requests` | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_ingestion_resilience::test_live_recovery_only_reclaims_expired_lease_and_preserves_completed_item` | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_ocr_modelops_safety::test_paddle_does_not_fabricate_confidence_or_shift_blank_page` | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |
| `tests.test_publishing_v2_cutover_and_gc::test_gc_api_endpoint` | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_cutover_and_gc::test_canary_policy_get_and_update_api` | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled` | assert 403 == 400 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_allowed_when_flag_enabled` | assert 403 == 201 | Khớp |
| `tests.test_publishing_v2_decommissioning_and_system_gc::test_rest_api_system_wide_gc_and_decommissioning_audit` | assert 403 == 200 | Khớp |
| `tests.test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback` | assert 403 == 200 | Khớp |
| `tests.test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies` | AssertionError: assert 'legacy_payload_schema' in [] | Khớp |
| `tests.test_tools::test_fact_layer_lookup_tool_found` | assert False is True | Khớp |
| `tests.test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims` | AssertionError: assert 'AI.Admin' == 'admin' | Khớp |
| `tests.test_universal_tools::test_fact_layer_lookup_tool` | assert False is True | Khớp |
| `tests.test_universal_tools::test_dispatch_admissions_with_dynamic_facts` | app.core.exceptions.EntityNotFoundError: Không tìm thấy bộ sưu tập 'col_admissions' | Khớp |
| `tests.test_vllm_reranker::test_vllm_embedding_generation` | ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection | Khớp |

## Bảo toàn và cleanup

Fresh readback: 5 collections, 23 bindings, mọi source/index cũ, 5 assistants/13 ModelOps rows giữ; chỉ target binding đổi editing source pointer, thêm3 draft source revisions và1 index staging. Active serving index, generation config, epoch và old point payload giữ. Source draft ready không đồng nghĩa đã xuất bản.

58 conversation threads và13 gap test đã dọn, 0 message/gap test còn; audit usage và evidence giữ. DB test đã xóa sau nonce ownership verification. Storage runtime `backend/storage/context572-runtime-83f5a04870d0` còn: automatic approval review chặn recursive deletion với lý do `blocked by policy`, không retry/bypass. Đây là phần cleanup chưa hoàn tất; không báo PASS cleanup toàn bộ. Các revision/index staging được giao giữ để người dùng xem, không coi là dữ liệu tạm phải xóa.

Không commit/push, restart/deploy, đổi model, reindex nguồn đang xuất bản hoặc publish. Không tự duyệt proposal ngữ nghĩa. [Báo cáo benchmark](BENCHMARK_REPORT.md), [nguồn/staging](INGESTION_REPORT.md).
