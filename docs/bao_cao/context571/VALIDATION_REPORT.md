# Context571 — Kiểm chứng cấu trúc và bản đọc

## Kết quả cuối

| Kiểm tra thực chạy | Kết quả | Exit |
| --- | --- | ---: |
| Backend focused 7 files, gồm regression và API | 172 PASS, 23 subtests PASS | 0 |
| Frontend reader + semantic compatibility | 36 PASS | 0 |
| Ruff 11 file Python | PASS | 0 |
| Biome 8 file, LF theo AGENTS | PASS | 0 |
| Frontend build Vite + TypeScript | PASS | 0 |
| Bóc tách offline DOCX/PDF bằng engine thật | 1 PASS | 0 |
| Native literals/IDs/locations và AST parser hiện có | PASS | 0 |
| Full backend | **2837 PASS / 18 FAIL / 17 SKIP**, 23 subtests PASS | 1 |

Full suite vẫn FAIL. Baseline là Context570 full-final-2: 2.810 PASS / 18 FAIL / 17 SKIP. Exact ID comparison: 0 lỗi mới; 0 trạng thái cũ thay đổi; 0 ID cũ mất; 27 ID mới. Bảng dưới đối chiếu nguyên nhân đầu tiên, không chỉ tổng số lỗi.

## Môi trường và lệnh

Xác minh development DB, MinIO và Qdrant đều loopback. DB chung chỉ SET TRANSACTION READ ONLY. Test dùng đúng `qnu_test_context571_cfa468239af9` có ownership nonce, 49 bảng ORM riêng, local Storage tạm; không migration DB chung. MinIO/Qdrant/Redis/model endpoints trỏ port 1; egress guard giữ DB test và socketpair nội bộ Windows. Một row metadata defaults có kiểu được copy vào DB test để test mock cũ chạy; 0 API key/credential/provider row.

CWD root repo để điều phối; pytest CWD backend; dùng Python backend/.venv/Scripts/python.exe:

- `backend/storage/context571/checks.py setup`; `seed-defaults`; `seals --label start/end`.
- `checks.py run tests/test_document_reader_structure.py --label regression-before`: 8 FAIL / 1 PASS trước sửa, gồm hành vi PDF và module reader chưa có; không gọi toàn bộ 8 là lỗi production.
- `checks.py run tests/test_document_reader_structure.py tests/test_source_reader_api.py tests/test_qnu_docx_markdown.py tests/test_qnu_pdf_markdown.py tests/test_qnu_serving.py tests/test_qnu_standard_regressions.py tests/test_studio_revision_safety.py --label focused-handoff`.
- `checks.py run backend/storage/context571/test_offline_documents.py --label offline-handoff` (thực tế đối số là absolute path đã lưu trong receipt). Chỉ parser local/native, không full ingestion/model/live revision.
- `finish_checks.py`: Ruff có phạm vi; Biome check với `--line-ending=lf`, ghi lại receipts. Build bằng `npm run build`; test bằng `node --test src/features/knowledge/components/qnu-document-reader.test.mjs src/features/knowledge/components/semantic-review-preview.test.mjs` trong frontend.
- `verify_fidelity.py`; `node backend/storage/context571/verify_markdown.mjs`; `checks.py run --label full-final-2`; `summarize_tests.py` so JUnit theo ID.

Lượt full-final đầu bị ngắt sau khi turn gián đoạn; không có summary/exit/JUnit nên giữ INTERRUPTED, không gọi PASS hay completed FAIL. Chạy lại full-final-2 để hoàn tất gate, không bỏ lỗi từ lượt đó.

## Đối soát nguồn và parser Markdown

DOCX trước/sau đều 233 khối, 36 sections, 10 bảng và 3 raw footnotes. IDs, source_data và locations từng khối giữ; 517 raw fields/state giữ. Chỉ 3 list bodies đổi biểu diễn, không đổi toàn bộ prose của 53 item có locator nguồn. Raw tab của note còn nguyên. Parser unified/remark-parse/remark-gfm đang cài xác nhận 53 list items, độ sâu 3, 10 bảng, 3 note definitions và 3 references; code thật vẫn là code.

PDF mẫu native từ 42 khối/0 section thành 42 khối/5 section; năm body chỉ đổi marker heading/trim biểu diễn. Mọi raw glyph/geometry và source locations giữ nguyên. Parser Markdown nhận 5 heading. Header/footer lặp, số lớn riêng, list thông thường, hai cột, mục con và chuyển trang có negative/regression fixtures.

Reader DOCX 61,760 bytes so với standard 276,238; reader PDF 6,176 bytes. Không đặt mục tiêu giảm dung lượng bằng cắt nội dung. Header/grid layout chỉ hiển thị khi khớp raw fields. Revision/source hash tương ứng giữ; đây không phải bằng chứng độ đúng cho mọi DOCX/PDF.

API ASGI dùng router thật với actor test, giữ permission dependency. Kiểm 200 cho reader/md, 403 trước tải nguồn khi thiếu quyền, 409 khi JSON checksum lệch, 404 cho revision/binding không tồn tại; không DB commit. Đây là contract integration, không phải human SSO E2E.

## Kiểm tra giao diện thật

Đã mở Source Detail local ở revision đang xuất bản, chỉ GET/read. Xem đủ ba tab và nút tải; bản dễ đọc giữ 10 bảng, Bảng 1 có 3 hàng header và 9 ô spanning thực, Bảng 2 có 4 ô spanning. Sáu link note đều có đích tồn tại; click tới note và quay lại đúng anchor. Note unknown hiển thị giới hạn, không code block. File tải thực `.readable.md` có 62,028 bytes, 3 footnote definitions, không rag:block transport metadata.

Kiểm desktop và viewport 375×812. Tab mới ban đầu tràn ngang; đã sửa grid/wrapping và đo scrollWidth=clientWidth=328. Reset viewport, đóng tab agent. Build không thay cho quan sát trực quan; chưa kiểm dark mode/đầy đủ mọi breakpoint. Source revision cũ vẫn chứa list body cũ; parser mới được xác minh riêng bằng offline source và AST, không tự cập nhật nguồn để làm giao diện xanh.

## Lỗi nền

| Test ID | Nguyên nhân hiện tại | So baseline |
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

Giữ nguyên assertion và quyền. Các failure về endpoint ngoại vi, fixture collection/migration metadata/auth vẫn FAIL; không mở kết nối thật để làm xanh.

## Lịch sử sửa và giới hạn

- Regression trước sửa: 8 FAIL / 1 PASS. Focused ban đầu 119 PASS; fixtures mở rộng phát hiện một bảng 1×1 bị engine đọc thành text và API fixture thiếu source location hợp lệ. Sửa fixture thành bảng 2×2 và locator thật, không nới app guard hoặc assertion quyền/hash.
- Biome write gặp Windows mapped-file I/O; dùng formatter stdin rồi ghi cùng file, không restart dịch vụ. Biome mặc định CRLF trái AGENTS nên scoped check dùng LF. Ruff đã sửa import và một biến thừa do task tạo; không auto-fix toàn repo.
- Fidelity probe lần đầu so glyph mới với bản cũ đã làm phẳng bullet nên FAIL; đối chiếu lại complete source item prose và raw OOXML recipe, không bỏ chữ nguồn. Receipt cũ giữ; AST vẫn đếm đúng từng item.
- 68 file RAG và 14 frozen benchmark inputs khớp byte hash trước task. Không benchmark 64 câu, không model/OCR bên ngoài, không live reparse/index/publication. Những việc đó NOT RUN.

## Bảo toàn và cleanup

Read-only row hash của 5 collections, 23 bindings, 2 source revisions, 27 index revisions, 5 assistants và 13 ModelOps config rows khớp Context568. Không đổi nguồn/index/model đang phục vụ. Không khẳng định đã re-read toàn bộ vector payload ở task này: không có vector write.

DB test đã xóa sau kiểm ownership nonce; Storage runtime riêng đã xóa sau resolve absolute path, kiểm 0 tracked file/0 reparse point. Bằng chứng ignored trong `backend/storage/context571` giữ để đối soát; không dọn runtime phiên cũ. File tải kiểm thử giữ trong Downloads để người dùng xem. Không commit/push/deploy hoặc tự restart.
