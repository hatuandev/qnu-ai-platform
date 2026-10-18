# Phiên 541 — Review RAG sau khi sửa bốn finding 536

**Kết luận: CHANGES REQUESTED — còn 2 P1 và 1 P2.** Lượt này thực hiện bước 1 user giao: review mã RAG vừa vibe, đối chiếu bốn finding cũ và hợp đồng nhận dữ liệu chuẩn từ parser. Không sửa mã ứng dụng; chưa kiểm thử toàn luồng tài liệu thật hoặc nạp lại nguồn.

## Phạm vi và bằng chứng

- Đọc AGENTS, PROJECT_CONTEXT, skill clean-code/RAG, quy định kiểm chứng/memory; đối chiếu báo cáo 536/540 với diff và mã hiện tại.
- HEAD quan sát: `a9bfce95e8b907acaeb287ece4ae62ae50200809`. Review các thay đổi trong knowledge normalization, source_context/source_ingestion_service/unit_annotation, rag và test_review536_findings. Giữ parser phiên 539 và các thay đổi khác của user.
- Luồng kiểm tra: QNU document → project_document → review helper → manifest/chunks → source_rows/catalog hoặc canonical blocks/reviewed facts → context/citation. Fixture tổng hợp trong RAM; DB query được fake, model không gọi. Không thay trạng thái nguồn/binding/index thật.
- Hash 21 file review tại `.antigravity-bridge/validation/review541-code-hashes.json`; probe độc lập nằm trong bridge đã ignore, không thêm hoặc sửa test ứng dụng.

## Đối chiếu bốn finding trước

| Finding 536 | Kết quả review hiện tại |
| --- | --- |
| F1 — mất cell state ở row-answer | Luồng mới giữ raw/state/normalized/column/header/provenance và phân biệt blank/zero/not_stated/not_applicable qua catalog. Các regression hiện có đạt. Còn lỗi escape ở bước xuất giá trị, R3 bên dưới. |
| F2 — reviewed fact thiếu context_refs | Đã resolve canonical row/hash/revision và đóng phụ thuộc header/note bắc cầu, giữ liên kết có hướng; thiếu/budget không đủ thì từ chối. Regression hiện có đạt. |
| F3 — mất metadata thời gian | Đã truyền metadata và có bước review/hash lại. Chưa đạt ở ràng buộc căn cứ đúng cột và tương thích hiệu đính được duyệt: R1/R2 bên dưới. |
| F4 — mất vị trí nhiều trang | Nhánh row-answer/evidence giữ source_locations/source_pages cho fixture trải trang; locator-only không tự có trang. Regression hiện có đạt. Chưa xác minh UI thực tế. |

## R1 — P1: Cột dùng header của cột khác làm căn cứ năm được xác minh

Vị trí chính: `backend/app/modules/knowledge/normalization/qnu_projection.py:268–269`; tương tự cấp field ở 300–302. Bước duyệt: `backend/app/modules/knowledge/services/unit_annotation.py:76–81,117`.

Mỗi column được kiểm `basis_quote` trên toàn text và toàn header bảng. `_verified_scope` cũng nhận toàn header/row, không bắt buộc căn cứ thuộc column/field đang xét. Trong bảng có hai cột Chỉ tiêu / 2025 và Chỉ tiêu / 2026, đặt temporal của cột 2026 thành data_years=[2025], basis_quote="Chỉ tiêu / 2025": projection nhận proposed và review helper nâng thành **verified/data/2025** cho ô thuộc cột 2026. Căn cứ có thật nhưng thuộc dữ kiện khác, nên kiểm có chuỗi con không chứng minh vai trò.

Tác động: fact từ cột 2026 có thể được gán applicability_year=2025 và tham gia lọc scope sai; không cần mất text gốc. Probe xác minh metadata sau review, chưa gọi model để khẳng định một câu trả lời sai cụ thể.

Hướng sửa: kiểm chứng căn cứ theo identity/cấp khai báo. Cấp column chỉ nhận header path/căn cứ liên kết riêng của column; cấp field chỉ nhận raw/căn cứ liên kết của field. Kế thừa row/table cần quan hệ phạm vi rõ ràng; căn cứ ở sibling hoặc mâu thuẫn header phải ambiguous, không tự verified. Không dùng từ điển năm/từ khóa fixture.

## R2 — P1: Fact đã hiệu đính và duyệt năm bị loại khỏi nhánh evidence

Vị trí chính: `backend/app/modules/rag/evidence_facts.py:37–43,189–196`.

`source_context.apply_context_edits` tạo temporal_context của hiệu đính người dùng theo contract hiện có: type/year/status/evidence=human_correction; review_context_artifact xác minh context_review và temporal status. `query_projection` materialize applicability_year=2026. Nhưng `_verified_years` mới chỉ nhận role=data, basis_quote và years, nên trả [] cho contract hiệu đính này. Dòng 195–196 vì vậy bỏ fact dù nó đã được người dùng duyệt và có năm đúng câu hỏi. Nếu applicability_year chưa materialize, `_cell_scope` cũng hạ verified thành ambiguous do thiếu basis_quote.

Probe đi qua apply_context_edits → _apply_review_decision → query_projection → load_published_blocks/reviewed_fact_blocks trong RAM. Control xác nhận fact Chỉ tiêu / 2026 có trước hiệu đính; hiệu đính chính năm 2026, duyệt, xác nhận context_review verified và applicability_year=2026; sau đó fact biến mất, chỉ còn Điểm chuẩn / 2026. Không kết luận nguồn gốc bị xóa hoặc mọi nhánh RAG đều mất dữ liệu; lỗi nằm ở adapter fact phục vụ evidence.

Hướng sửa: thống nhất contract temporal của hiệu đính với loader/materialization. Giữ audit và quyền duyệt thật; phân biệt bằng chứng con người đã duyệt với nhãn tự khai trong file. Không bỏ guard hoặc chấp nhận mọi status=verified để vá lỗi. Cần regression cả sửa năm, xóa năm, sửa method/unit và đúng revision/hash, cùng nhánh row-answer để tránh hai cách hiểu khác nhau.

## R3 — P2: Escape hai lần làm sai giá trị và vỡ cột câu trả lời

Vị trí chính: `backend/app/modules/rag/row_answer_contract.py:384`; `_value_display` đã gọi `_display` ở 371.

`render_cells` tiếp tục gọi `_display` cho kết quả `_value_display`. Raw `A & B` thành `A &amp;amp; B`; raw `A | B` thành hai backslash trước pipe. GFM parser đọc hàng trả lời thành **4 ô thay vì 3**, nên phần giá trị bị tách thành cột ngoài schema. Đây là lỗi biểu diễn ở câu trả lời; catalog và raw nguồn vẫn đúng.

Hướng sửa: thêm nhãn state trên raw text rồi escape đúng một lần tại ranh giới Markdown; giữ nguyên raw trong answer_decision. Regression nên kiểm round-trip cả ampersand, pipe, backslash, HTML và nhiều dòng.

## Kiểm chứng thực chạy

Cwd: `D:\DuAnPhanMem\qnu-ai-platform\backend`, dùng Python/Ruff hiện có trong `.venv`; không cài gói hoặc đổi cấu hình.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_review536_findings.py tests/test_row_answer_contract.py tests/test_qnu_serving.py tests/test_evidence_retrieval_regressions.py tests/test_evidence_completeness_437.py --basetemp=storage/review541-focused --junitxml=storage/review541-focused.xml --tb=short
```

**PASS: 80 passed**, exit0, 6.61s. Gồm 12 regression của bên triển khai; không chỉ dựa vào báo cáo cũ.

Scoped Ruff trên 20 file ứng dụng đã sửa trong phạm vi và test_review536_findings.py: **PASS, All checks passed**, exit0; không chạy --fix.

```powershell
.\.venv\Scripts\python.exe -m pytest -q ../.antigravity-bridge/validation/test_review541_rag_edges.py --basetemp=storage/review541-probes-final2 --junitxml=storage/review541-probes-final2.xml --tb=short
```

**FAIL: 4 failed**, exit1, 6.14s; tương ứng R1, R2, R3 với hai biến thể ampersand/pipe. Trước đó 3 probe đầu cũng FAIL; bổ sung control trước/sau hiệu đính cho R2 rồi biến thể pipe cho R3 để xác định tác động cấu trúc. Không sửa code hoặc assertion chuẩn để làm xanh.

Full backend: **NOT RUN** ở lượt review này. Kết quả phiên 540 là lịch sử **FAIL13/2138passed/17skipped/23subtests**, không phải current PASS. Không lặp full suite khi chưa sửa mã. Không benchmark/chat/UI/provider thật, không nghiệm thu chất lượng retrieval trên corpus hoặc tích hợp DOCX thật ở bước 3.

## Bàn giao

Chỉ thêm probe/bằng chứng review và cập nhật nhật ký/index/memory/snapshot. Không sửa app/test ứng dụng, không nạp lại DOCX, reparse, duyệt nguồn, tạo index/publish hoặc thay cấu hình/model. Không commit/push/stage/reset/dọn tracked files/restart/deploy. Source DOCX thử và các PDF cũ giữ trạng thái trước; monitor Gemini giữ paused.

Ưu tiên sửa R1/R2, sau đó R3 theo một batch; chạy lại bốn probe và regression trước khi chuyển sang kiểm thử toàn luồng trên DOCX mẫu. Phần parser độc lập đã kiểm offline ở phiên 539 không thay thế nghiệm thu RAG.
