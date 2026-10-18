# NHẬT KÝ LÀM VIỆC: SỬA DỨT ĐIỂM 4 FINDING REVIEW 536 — BẢO TOÀN CẤU TRÚC VÀ Ý NGHĨA QNU RAG MARKDOWN v1.0

- **Thời gian**: 2026-10-18
- **Kỹ sư / Agent**: Qoder — Backend/RAG Engineer
- **Mục tiêu phiên (Goals)**:
  - F1: nhánh row-answer giữ nguyên cell state/raw/normalized/provenance thay vì dựng lại từ GFM.
  - F2: reviewed fact kéo đúng header/condition/note đã duyệt, đóng phụ thuộc bắc cầu, không suy theo trang.
  - F3: temporal metadata đi đúng cấp block/column/row/field, chỉ năm đã xác minh mới tham gia scope.
  - F4: citation giữ đầy đủ source_locations/source_pages của block trải nhiều trang, không bịa trang.
  - Bổ sung regression, chạy focused + Ruff, chạy full suite một lần cuối và đối chiếu exact failure IDs với baseline.

## 1. Bối cảnh và ràng buộc

- Đầu vào là phiên 536 `CHANGES REQUESTED`: 2 P1 (cell state ở row catalog; fact thiếu explicit note/header deps) và 2 P2 (temporal metadata bị bỏ; citation nối trang mất `source_pages`).
- Chỉ sửa mã ứng dụng, test và tài liệu trong phạm vi 4 finding. Không commit/push/stage/reset/dọn file tracked; không reparse, approve, reindex, publish hoặc ghi dữ liệu nghiệp vụ thật; không restart/deploy/đổi config-model-provider; không gọi model/embedding/reranker/benchmark thật.
- Không sửa assertion hoặc bỏ guard để làm test xanh; fixture dùng RAM/giao dịch cô lập.
- Giữ nguyên thay đổi đang có của phiên 537–539 (DOCX parser/evidence) và các file tài liệu đồng thời.

## 2. Thay đổi mã nguồn theo từng finding

### F1 — Cell state xuyên suốt projection → chunk → source_rows → catalog → answer

- `app/modules/knowledge/normalization/qnu_projection.py`: record row giữ `raw/state/normalized/column_id/column_index/header_path/header/field_source/field_origin/temporal/header_temporal`; metadata bảng có `columns`, `row_unit_ids`, `standard`, `cell_state_source`. GFM được đánh dấu `state_source=derived`; records giữ `declared`. Ô có state khác `present` mà còn `normalized` bị hạ về `None` và phát `CELL_NORMALIZED_UNSUPPORTED`; thiếu state phát `CELL_STATE_UNAVAILABLE` và tăng `unresolved_cell_count`, không mặc định thành present.
- `app/modules/rag/source_rows.py`: trả `row_fields`, `row_columns`, `row_table_id`, `cell_state_source`; bỏ fallback biến artifact declared thành legacy; kiểm `manifest_hash_matches` trước khi dùng vị trí row.
- `app/modules/rag/row_answer_contract.py`: `SourceCell` giữ state/normalized/field source/origin/column/header/temporal và cờ `standard`/`state_source`; declared `ambiguous|unreadable` bị chặn chọn/duyệt; validate năm theo temporal đã xác minh của từng ô; nhãn hiển thị chỉ áp cho declared state; `source_value_variants` so cặp `(state, value)` nên hai ô raw “–” khác state không bị gộp; `blank` không thành `0`, `present 0` vẫn hợp lệ, mã số có số 0 đầu được giữ nguyên.
- `app/modules/rag/row_answer.py`, `schemas.py`, `service.py`: payload/decision/citation dùng chung contract mới, không tự suy state từ marker.

### F2 — Fact giải đúng row canonical và đóng phụ thuộc header/note

- `app/modules/rag/evidence_facts.py`: fact chuẩn chỉ được dựng khi resolve đúng `(index_revision_id, source_unit_id)`, đúng `binding_id`, row thuộc container bảng, parent là header bảng, `unit_manifest_hash` khớp và có refs; giữ `parent_id` để `structural_context` gắn heading. Scope năm lấy từ cell/row đã xác minh. Ref của nhiều fact trong cùng block được union; dependency đóng bắc cầu, dedupe theo source identity. Không suy note theo trang/khoảng cách.
- `app/modules/rag/evidence_dependencies.py`: nhóm dependency theo fact chuẩn dùng `(index, source_unit_id, verified_years, entity_name)`; note dùng chung chỉ gắn với row thực sự tham chiếu, không kéo mọi row cùng trang.
- `app/modules/rag/evidence_context.py`, `evidence_pipeline.py`, `evidence_blocks.py`: giữ nguyên contract legacy; budget không đủ thì loại fact thay vì giữ fact trần; context trả về gồm header/condition/note đã chọn.

### F3 — Temporal đúng cấp, có căn cứ, chỉ verified mới có hiệu lực

- `app/modules/knowledge/normalization/qnu_projection.py`: `_declared_temporal` kiểm kiểu, bỏ key không hỗ trợ, từ chối `status` tự phê duyệt, bắt buộc `basis_quote` xuất hiện trong text/header và `data_years` là tập con của căn cứ; `_aggregate_scopes` gom theo cấp `block|column|row|field`, giữ `unknown` khi thiếu căn cứ. Năm của cột không bị nâng thành năm toàn row; bảng nhiều năm giữ scope từng cột/ô.
- `app/modules/knowledge/normalization/retrieval_models.py`, `retrieval_units.py`: `TemporalScope` có kiểu rõ ràng; `legacy_manifest_digest`/`manifest_hash_matches` giữ tương thích artifact cũ; hash manifest tính lại sau khi scope đổi.
- `app/modules/knowledge/services/unit_annotation.py`: `approve_temporal_scopes` chỉ xác minh proposal khi `basis_quote` tồn tại đúng trong evidence cùng cấp; unit bị người dùng sửa không tự verified; tính lại `unit_manifest_hash` và `fact_set_hash`.
- `app/modules/knowledge/services/source_ingestion_service.py`, `source_context.py`: gọi bước duyệt temporal sau unit annotation; fact/catalog/retrieval nhận scope đã verified. Sửa so sánh năm dạng chuỗi/số để filter không chọn nhầm ô khác năm.

### F4 — Citation giữ vị trí nguồn trải trang

- `app/modules/rag/evidence_validation.py`: kiểm contract `source_locations` (list, page là số nguyên không phải bool, locator/bbox đúng kiểu); `bind_quote` gắn `source_locations` + `source_pages` đã sắp xếp/dedupe; locator-only trả `page_number=None`, không tự điền trang đầu; quote/hash/span phải khớp canonical.
- `app/modules/rag/source_rows.py`: row/unit trải trang giữ toàn bộ location và pages; fallback dùng range của block khi quote không có mapping từng trang; metadata row mang `source_locations`, `source_pages`, `row_headers`, `row_context`.
- `app/modules/rag/service.py`, `row_answer.py`, `row_answer_contract.py`, `schemas.py`: citation của evidence và row-answer đều đi qua `location_pages`/`citation_locations`; `Citation.source_locations` được giữ trong DTO; không nhận giá trị do model khai báo.
- Các chỉnh nhỏ `citation_guard.py`, `combination_enumeration.py`, `conversation_acts.py` chỉ để tương thích contract/ký tự, không đổi hành vi ngoài phạm vi.

## 3. Tệp đã sửa

- Backend: `backend/app/modules/knowledge/normalization/qnu_projection.py`, `retrieval_models.py`, `retrieval_units.py`; `backend/app/modules/knowledge/services/source_context.py`, `source_ingestion_service.py`, `unit_annotation.py`; `backend/app/modules/rag/citation_guard.py`, `combination_enumeration.py`, `conversation_acts.py`, `evidence_blocks.py`, `evidence_context.py`, `evidence_dependencies.py`, `evidence_facts.py`, `evidence_pipeline.py`, `evidence_validation.py`, `row_answer.py`, `row_answer_contract.py`, `schemas.py`, `service.py`, `source_rows.py`.
- Test mới: `backend/tests/test_review536_findings.py` (12 regression).
- Tài liệu phiên: nhật ký này, `docs/nhat_ky/README.md`, `docs/WORK_LOG.md`, `docs/memory/PROJECT_CONTEXT.md`, `docs/memory/snapshots/2026-10-18_session_540.md`.

## 4. Kiểm chứng thực chạy

- Scoped Ruff trên 20 file backend thay đổi + test mới: `All checks passed!`.
- Regression mới: `.venv/Scripts/python.exe -m pytest -q tests/test_review536_findings.py` → 12 passed.
- Focused nhóm 1 (contract/serving/standard/temporal + regression mới): 94 passed in 7.35s.
- Focused nhóm 2 (evidence/facts/rag rows): 164 passed in 4.92s.
- Focused nhóm 3 (QNU DOCX/PDF/header/candidate artifact): 105 passed, 23 subtests passed in 9.77s.
- Full backend suite chạy đúng một lần cuối:
  `cd backend && .venv/Scripts/python.exe -m pytest -q --basetemp=storage/review536-fulltemp --junitxml=storage/review536-full.xml > storage/review536-full.log 2>&1`
  → exit 1; **13 failed, 2138 passed, 17 skipped, 23 subtests passed in 209.98s**. Log/JUnit: `backend/storage/review536-full.log`, `backend/storage/review536-full.xml`.
- 13 failure IDs đều trùng khít baseline phiên 535/529, không có ID mới:
  `test_consulting_dispatcher::test_dispatch_admissions_with_export`, `::test_dispatch_regulations_with_export`; `test_publishing_v2_cutover_and_gc::test_gc_api_endpoint`, `::test_canary_policy_get_and_update_api`; `test_publishing_v2_decommissioning_and_system_gc::test_direct_upload_blocked_when_flag_disabled`, `::test_direct_upload_allowed_when_flag_enabled`, `::test_rest_api_system_wide_gc_and_decommissioning_audit`; `test_publishing_v2_e2e_canary::test_api_routes_canary_and_rollback`; `test_rag_data_truth_and_lifecycle::test_reconciliation_detects_discrepancies`; `test_tools::test_fact_layer_lookup_tool_found`; `test_trust_boundary_and_hitl::test_auth_session_cookie_actor_claims`; `test_universal_tools::test_fact_layer_lookup_tool`, `::test_dispatch_admissions_with_dynamic_facts`.
- Số pass tăng +23 so với baseline 535 (2115 → 2138): 12 test review536 mới + 11 test DOCX evidence của phiên đồng thời; không có test pass cũ biến mất. Full vẫn là **FAIL** vì 13 lỗi nền, không phải PASS.

## 5. Giới hạn và bước tiếp theo

- Regression dùng fixture RAM, chưa nghiệm thu bằng chat/UI, model thật, embedding/reranker hoặc benchmark; chưa xác minh câu trả lời cuối do model sinh.
- Artifact/revision cũ chưa reparse/re-projection nên chưa có metadata cell-state/temporal/source_locations mới; muốn hưởng lợi phải chạy quy trình nạp lại và duyệt theo chuẩn, việc này chưa thực hiện.
- 13 lỗi nền thuộc publishing/consulting/tools/trust-boundary, không do batch này; không sửa ngoài phạm vi.
- Không commit/push/stage/reset, không sửa config, không gọi model hay ghi dữ liệu thật. Thay đổi DOCX của phiên 537–539 được giữ nguyên.
