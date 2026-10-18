# Phiên 526 — Đợt 1–3: kiểm kê, lifecycle bản chuẩn và RAG

## Phạm vi và quyền

Người dùng duyệt triển khai đợt 1–3 theo batch; chưa làm đợt dọn/nạp/vector/publish.
Người dùng chọn tự tạo full backup trên UI và giữ mật khẩu. Không nhận/ghi mật khẩu,
không gọi chức năng restore; backup chưa được phiên này kiểm chứng.

Dùng skill clean-code/backend, ingestion, rag-pipeline/evaluation và frontend/admin
theo phạm vi. Không tạo agent phụ, framework, migration, LLM call mới, cấu hình model,
restart/deploy hoặc commit/push. Thay đổi cũ của người dùng được giữ.

## Bằng chứng hiện trạng và đợt 1

- Đọc PROJECT_CONTEXT, Git/diff và mã thật. Chunk service trước sửa đọc legacy
  canonical; MD/JSON mới chỉ là artifact song song. Test tái hiện standard marker
  thiếu projection trước sửa FAIL thật (`DID NOT RAISE`), không được coi là PASS.
- Chạy `.venv/Scripts/python.exe -m scripts.standard_migration_inventory --collection col_admissions --save-report`
  từ backend, exit0. PostgreSQL đọc được: 22 bindings, 33 source revisions, tất cả
  legacy, 0 queued/running job trong collection. Lưu báo cáo qua StorageDriver tại
  `snapshots/migration-inventory/74fa675fa5e0489ab1feef38a9f1e679.json` và đối soát readback.
- Báo cáo allowlist model settings, không dump prompt/credential/raw tài liệu.
  `purge_authorized=false`, `backup_verified=false`. Docker CLI hiện permission denied;
  không suy Docker đang tắt từ lỗi quyền này.

## Đợt 2–3 đã code

- `normalization/qnu_projection.py`: QNU document -> canonical nội dung + explicit
  table/row/header units; locations/field states/origins, context graph, source-table
  member index. Không infer lại header từ dòng dữ liệu, không embed derived index/raw JSON.
- `services/qnu_serving.py`: pair checksum/schema/identity/source hash/semantic parity,
  raw PDF checksum; fail-closed binding guard; chuẩn bị revision mới và input review.
  Unknown/multi-page không giả trang. Renderer escapes round-trip giữ raw không bị đổi.
- `qnu_revision.py` và artifact service: edit immutable/OCC, server identity và lý do;
  tạo lại MD/JSON/projection cùng revision, giữ raw machine provenance. Records sửa
  fields thì display body được dựng lại; thay source/locator/field source bị chặn.
- Import/reparse hỗ trợ chuẩn trước review, extraction version v15. Native correction
  cũ không được ghi đè nguồn chuẩn. File ready không tự approve; approve, chunk build
  và publication kiểm cặp tệp. Lỗi artifact không được hạ xuống legacy để index.
- Giữ seal manifest legacy khi thêm provenance; chưa tự đổi 33 revisions hiện tại.
- RAG source blocks giữ bảng chưa được facts bao phủ; phụ thuộc có hướng không kéo
  ngược tất cả rows từ shared note. Enum dedup đúng cùng row + source/year, không
  đếm canonical và fact như hai bản ghi; model context không chứa geometry/IDs kỹ thuật mới.
- UI editor theo revision, lỗi/loading/save thật, OCC/lý do, cập nhật cache và chọn
  revision trả về. Studio đối chiếu/duyệt; unknown text không đổ vào trang1 và chặn
  plain-page editor làm mất cấu trúc chuẩn. API/DB schema chỉ thêm DTO/property/JSON,
  không có migration hay thay provider/Top K.

## Kiểm chứng

Các lệnh dùng `.venv/Scripts/python.exe` từ backend; frontend từ frontend.

- Test tái hiện đầu: 1 FAIL đúng downgrade cũ.
- Lượt focused đầu: 1 FAIL pair do thứ tự key JSON khác insertion order. Sửa parity
  theo cấu trúc và thứ tự block/nội dung; checksum bytes vẫn bắt buộc.
- Focused 9 file: 152 pass, 3 fail do fixture PDF thiếu chuẩn nhưng mong auto-ready.
  Cập nhật contract test có chủ đích: giữ nhánh legacy text auto-ready, thêm PDF
  thiếu chuẩn chờ duyệt + không được chunk; không bỏ guard để đạt xanh.
- Chuỗi sau sửa: 79 passed (6.91s), gồm qnu_serving, SQL integration, ingestion,
  conversation_acts và enumeration/followup. SQL integration fixture nằm trong
  outer transaction rollback, storage giả trong bộ nhớ, không có model/vector calls.
  Đã kiểm edit→review→chunks→BM25 candidate/packing→quote span/page→cross-collection.
- Frontend 9 test mapper/actions/query refresh PASS; Biome scoped PASS;
  typecheck và build cuối PASS. Build đầu lỗi missing DTO property, đã bổ sung và chạy lại.
- Full suite `.venv/Scripts/python.exe -m pytest -v --tb=short -p no:cacheprovider
  --basetemp=storage/qnu526-fulltemp`: **FAIL**, exit1, **2031 passed / 11 failed /
  17 skipped / 23 subtests passed**, 220.85s. Log `backend/storage/qnu526-full.log`.
  Compare-Object với baseline phiên511: exact test IDs khớp **11/11**, không gọi
  toàn suite PASS. Sau guard round-trip/self-reference bổ sung, nhóm mới + SQL
  integration: **20 passed**, exit0, 4.12s; có trùng nhóm79/full, không cộng tổng.
- Lint toàn frontend một lần: **FAIL 61 errors**, exit1 (583 files), thêm Biome
  schema-version/deprecation info. Không autofix toàn repo; các file vừa sửa sạch.
- Kiểm kê cuối exit0: vẫn22bindings/33legacyrevisions/0job, report
  `snapshots/migration-inventory/fb1572dae82c4d738f56ec133c3ed141.json`; backup chưa verify.
- Siết cuối batch: `ambiguous`/`unreadable` cell không được whole-document approval
  vượt qua; giữ review-required và yêu cầu hiệu đính trường raw/state trước. Guard mới
  + SQL integration + structured/context contracts **32 passed**, exit0, 7.22s,
  có trùng các lượt trước. Full suite phía trên chạy trước guard cuối (chỉ standard),
  không chạy full lặp lại. Chưa có partial-table publication cho ô chưa chắc.
- So sánh hai inventory qua StorageDriver: collection/index_epoch/bindings/revisions/
  model-settings-allowlist/chunk_count/index-status-counts đều bằng nhau trước/sau.
  Đây không phải kiểm checksum toàn DB hoặc xác nhận backup đầy đủ.
- Cuối batch scoped Ruff28file/Biome8file và diff-check PASS; 44 file scope đọc
  strict UTF-8/no replacement character, chuẩn hóa LF không BOM có phạm vi.

Exact baseline failures:

```text
tests/test_consulting_dispatcher.py::test_dispatch_admissions_with_export
tests/test_consulting_dispatcher.py::test_dispatch_regulations_with_export
tests/test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint
tests/test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled
tests/test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit
tests/test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback
tests/test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies
tests/test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims
tests/test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts
```

## Giới hạn và bước sau

- Chưa full-backup verify/drill (người dùng tự làm UI), chưa purge/reparse corpus,
  embedding/index/vector publish, live inference/OCR, benchmark12/82 hoặc UI visual.
- Fixture/integration không chứng minh RAG production cải thiện chất lượng. Cần bộ
  nguồn thật đã duyệt và snapshot mới ở đợt4–7 theo kế hoạch.
- Các nguồn cũ đọc theo legacy minh thị. Standard edit giữ danh tính/tập block và
  vị trí nguồn; không phải editor cho phép tự tạo/xóa block hoặc bịa bbox.
- Chỉ mục dẫn xuất hiện có member/count theo bảng, chưa là bằng chứng unique ngành
  hay exhaustive collection. Không tự kích hoạt rule quy đổi chưa duyệt/rebind.
- Trước dọn kho cần full backup có thể đọc/khôi phục, phạm vi collection và cleanup
  MD/JSON/raw sidecars có kiểm tham chiếu; không xóa Repository hoặc docs/tai_lieu.
