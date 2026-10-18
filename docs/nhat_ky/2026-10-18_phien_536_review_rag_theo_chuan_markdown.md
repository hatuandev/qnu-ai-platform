# Phiên 536 — Review RAG theo QNU RAG Markdown Standard v1.0

Kết luận: **CHANGES REQUESTED**. Pipeline đã dùng projection chuẩn, nhưng chưa bảo toàn đầy đủ trạng thái ô, phụ thuộc chú thích, metadata thời gian và vị trí nhiều trang tới các nhánh trả lời. Đây là review mã hiện tại và fixture tổng hợp; không phải nghiệm thu chất lượng chat/provider thật.

## Phạm vi và hiện trạng

- Đối chiếu `docs/quy_trinh/13_chuan_markdown_rag_v1.md`, PROJECT_CONTEXT, mã và Git thực tế. HEAD quan sát `1b5ab27a`; các thay đổi phiên535 đã tồn tại trong index trước lượt này, giữ nguyên. Không stage/commit/push/reset hoặc sửa mã ứng dụng.
- Luồng chính: cặp MD/JSON được xác minh → `project_document` → canonical/manifest/context graph/facts → `structure_chunks` → revision/index snapshot → hybrid hoặc evidence policy → context → quote/citation. Nhánh trả lời theo hàng còn dựng lại cells từ Markdown; nhánh evidence có cả canonical units và reviewed facts.
- Điểm đã có: loại transport metadata và derived_index khỏi chứng cứ; ghim identity/hash/manifest; hàng records/GFM giữ header, raw và vị trí; canonical context graph đóng các refs tường minh; chặn ô ambiguous/unreadable trước duyệt; chunk quá ngân sách báo lỗi thay vì cắt bỏ điều kiện. Test tích hợp PostgreSQL dùng fixture và outer rollback, storage trong RAM; không xuất bản nghiệp vụ hoặc gọi embedding/Qdrant.

## Finding

### F1 — P1: Nhánh trả lời theo hàng mất trạng thái ô chuẩn

Vị trí: `backend/app/modules/rag/row_answer_contract.py:117`–118; nguồn metadata ở `backend/app/modules/knowledge/normalization/qnu_projection.py:123`.

Projection giữ `row_fields` và lọc facts chỉ lấy state present, nhưng `source_rows`/`build_catalog` dựng lại cells bằng raw GFM và chỉ gửi id/header/value. `state`, normalized và field origins không tới catalog. Fixture có ô raw “–”, state not_applicable và chú giải tường minh được duyệt trong RAM: facts loại ô đúng; row catalog lại chỉ có raw “–”, không có state. Vì vậy nhánh trả lời theo hàng không còn hợp đồng phân biệt not_applicable/not_stated/blank/present; việc diễn giải phải suy lại từ text.

Cần truyền cell metadata theo identity hàng/cột/revision, giữ raw/state/normalized/origin qua catalog và câu trả lời. Không suy lại state từ một từ điển marker hay mặc định present. Probe xác nhận mất contract, chưa gọi model để khẳng định một câu trả lời sai cụ thể.

### F2 — P1: Reviewed fact không đóng phụ thuộc context_refs

Vị trí: `backend/app/modules/rag/evidence_facts.py:86`–92; `backend/app/modules/rag/evidence_dependencies.py:74`.

Fact raw có source_unit_id/context_unit_ids đúng. Khi gom thành EvidenceBlock reviewed_fact, loader chỉ giữ source_unit_id, không giữ context_unit_ids. `dependency_groups` chỉ xét origin canonical. Fixture row phụ thuộc note qua table context_refs: chọn canonical row có note; chọn reviewed_fact rồi `pack_context` với ngân sách đủ chỉ nhận fact, thiếu note. Bước semantic audit cũng không thể đọc điều kiện chưa được đóng vào payload.

Cần resolve deps của mọi fact về đúng canonical row/header/note cùng binding/index/source/hash, đóng toàn bộ dependency hoặc từ chối khi thiếu/quá ngân sách. Không gắn mọi note cùng trang cho fact; không dùng `fact_location` gom section theo trang làm bằng chứng scope.

### F3 — P2: Metadata thời gian có trong chuẩn bị bỏ khỏi serving units

Vị trí: `backend/app/modules/knowledge/normalization/qnu_projection.py:156`–159.

Projection chỉ tìm năm trong text/heading rồi gán proposed/unknown. Nó không đọc attributes.temporal trên block/column/field. Fixture hợp lệ có row temporal.data_years=[2026], có quote header tương ứng và column temporal: sau projection và helper duyệt RAM, row temporal.data_years vẫn []; role unknown. RAG nhận một phạm vi chưa biết dù gói chuẩn đã khai báo căn cứ, không thể dùng metadata này để lọc chính xác. Không suy ra từ đây rằng mọi câu hỏi năm đều trả sai: header text và các nhánh semantic khác vẫn có thể xác minh lại.

Cần giữ scope có kiểu cùng basis quote và vị trí đúng cấp, kiểm chứng qua review trước verified. Bảng nhiều năm cần scope riêng từng cột/ô, không ép cả row thành một năm hoặc tin nhãn trong file là quyền duyệt.

### F4 — P2: Citation của khối nối trang mất danh sách trang

Vị trí: `backend/app/modules/rag/evidence_validation.py:114`–141; `backend/app/modules/rag/evidence_pipeline.py:88`.

Manifest/EvidenceBlock giữ source_locations hai trang [2,3]; page_number=None là đúng vì không có một trang duy nhất. `bind_quote` bỏ source_locations; `decision_response` tạo source_pages chỉ từ page_number. Probe cùng row có citation.source_pages=None thay vì [2,3], mất định vị nhiều trang dù quote/hash/span vẫn đúng.

Cần đưa source pages/locator có kiểm chứng từ server qua bound reference và Citation. Không gán trang đầu hoặc bịa bbox để lấp chỗ trống. Kiểm cả nhánh row-answer khi bổ sung.

## Kiểm chứng thực chạy

Cwd các lệnh dưới đây: `D:\DuAnPhanMem\qnu-ai-platform\backend`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_qnu_serving.py tests/test_qnu_standard_integration.py tests/test_row_answer_contract.py tests/test_evidence_retrieval_regressions.py tests/test_evidence_completeness_437.py --basetemp=storage/review536-focused --junitxml=storage/review536-focused.xml
```

**PASS: 69 passed**, exit0, 5.54s. Bao gồm fixture PostgreSQL outer rollback, không live publication/model/vector writes.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_structure_chunks_511.py tests/test_structured_source_contract.py tests/test_qnu_header_and_cell_states.py --basetemp=storage/review536-structure --junitxml=storage/review536-structure.xml
```

JUnit đã ghi **39 tests, 0 failures/errors/skipped**, 9.850s. Session terminal không còn khi resume; xác minh kết quả qua XML hoàn chỉnh, không suy exit code từ process đã mất.

```powershell
.\.venv\Scripts\python.exe -m pytest -q ../.antigravity-bridge/validation/test_review536_rag_contract.py --basetemp=storage/review536-probes --junitxml=storage/review536-probes.xml --tb=short
```

**FAIL: 4 failed**, exit1, 5.85s; bốn assertion tương ứng F1–F4. Các probe kiểm mong đợi theo chuẩn, failure là bằng chứng khoảng hở hiện tại. Fixture dùng source/review/chunk/catalog/packer/citation thật trong RAM; DB fact query fake, không gọi inference/provider, không ghi nguồn nghiệp vụ. Script review nằm trong thư mục bridge đã ignore, không thêm vào bộ test ứng dụng của lượt chỉ review.

Sau resume, làm rõ fixture F1 bằng marker “–” và chú giải not_applicable thay numeric0. Lượt pytest lặp (`--basetemp=storage/review536-probes-final --junitxml=storage/review536-probes-final.xml`) dừng sau `FF` và không tiến triển; đã INTERRUPTED, exit1 do ngắt, không có JUnit hoàn chỉnh và không tính là một suite đã xong. Chạy riêng hàm F1 bằng lệnh dưới đây tái hiện đúng AssertionError `{id: r0c2, header: 2026 / Chỉ tiêu, value: –}`, không có state; **exit1**. Import Qdrant client cảnh báo không lấy được server version; không inference hoặc vector write.

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -c "import runpy; import tests.conftest; p=runpy.run_path('../.antigravity-bridge/validation/test_review536_rag_contract.py'); p['test_record_cell_state_is_visible_to_row_answer']()"
```

Full backend/Ruff: **NOT RUN** trong lượt review không sửa app; full535 là kết quả lịch sử **FAIL13/2115passed/17skipped/23subtests**, không phải current PASS. Chưa chạy benchmark, inference hay chat UI thật; không kết luận chất lượng model/dense provider từ mock tests.

## Phạm vi bàn giao

Chỉ thêm báo cáo, snapshot và cập nhật index/memory theo workflow repo; không sửa app hoặc cấu hình. Không commit/push/stage/reset/dọn tracked files/reparse/duyệt nguồn/index/publish/restart/deploy. Năm PDF cũ chưa được duyệt; lượt review này không thay đổi trạng thái đó. Monitor Gemini tiếp tục paused. Ưu tiên sửa F1/F2 rồi F3/F4, thêm regression qua ranh giới serving → answer/citation, không chỉ kiểm validator hoặc artifact JSON.
