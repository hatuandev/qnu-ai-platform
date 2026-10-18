# Phiên 542 — Sửa ba lỗi sau review tích hợp RAG

User cho phép sửa ba finding phiên 541. Giữ phạm vi mã normalization/review adapter/fact loader/row renderer, không sửa parser hoặc các thay đổi RAG khác. Đã sửa mã theo một batch rồi mới chạy test, theo nhịp user yêu cầu. Bốn probe độc lập đã FAIL ở phiên 541 là bằng chứng trước sửa, không cần chạy lại một lượt đỏ trước khi triển khai.

## Thay đổi và nguyên nhân

### R1 — Căn cứ năm phải thuộc đúng cột/ô

- `backend/app/modules/knowledge/normalization/qnu_projection.py`: column chỉ tìm basis trong header của chính column; field chỉ tìm trong raw/header của chính field. Không nhận chữ/năm từ sibling. Nếu năm khai báo mâu thuẫn header hiện tại, giữ khai báo, phát TEMPORAL_HEADER_CONFLICT và ambiguous. Basis sai kiểu giữ unsupported/ambiguous, không làm parser crash. Row/table chỉ được kế thừa khi có khai báo rõ ràng ở cấp đó.
- `backend/app/modules/knowledge/services/unit_annotation.py`: bước duyệt kiểm lại phạm vi theo scope_level; không lấy toàn header/row cho column/field. Không thay cơ chế annotation quyền duyệt bằng một nhãn do tài liệu tự khai. Hiệu đính year của người dùng giữ ưu tiên riêng; sửa method/unit không chặn bước xác minh scope gốc có căn cứ.

### R2 — Hiệu đính đã được duyệt dùng cùng contract tại materialization và serving

- `backend/app/modules/knowledge/services/source_context.py`: khi sửa year, lưu type/year/years/role/scope_level nhất quán; xóa năm giữ unknown/[] và không hồi sinh năm từ header. Adapter nhận cả hợp đồng year-only cũ nhưng chỉ khi temporal/context_review verified, có người sửa/lý do/thời điểm và review approved/người duyệt/thời điểm. Không giả một basis_quote trích từ nguồn cho kết luận của con người.
- Review helper đồng bộ temporal vào đúng row_fields theo table/row/column/source_unit_id, giữ raw/header/value/origin. Fact set vẫn được hash lại theo vòng đời hiện có. Không cập nhật nguồn đã xuất bản ở nền.
- `backend/app/modules/rag/evidence_facts.py`: query/materialization và loader dùng chung adapter. Fact đã duyệt năm không còn bị bỏ do thiếu role/basis_quote/years ở contract cũ; output cell cũng nhận contract chuẩn hóa. Giữ các guard identity/hash/revision/context_refs và dependency closure. Nhãn verified thiếu audit không cấp scope năm.
- `backend/app/modules/rag/row_answer_contract.py`: cell có hiệu đính được server duyệt dùng đúng scope đã sửa, kể cả xóa năm; các nhánh chọn/lọc cell không hồi sinh năm header đã bị hiệu đính. Năm raw của header vẫn được giữ nguyên để truy vết.

### R3 — Escape đúng một lần tại đầu ra Markdown

`row_answer_contract.py` thêm nhãn state trên raw rồi escape một lần tại render boundary. Escape cả backslash trước pipe; raw có ampersand, pipe, backslash, HTML hoặc newline không tạo thêm cột. `answer_decision` giữ raw nguyên gốc.

## Kiểm chứng

Cwd: `D:\DuAnPhanMem\qnu-ai-platform\backend`. Dùng Python/Ruff hiện có trong `.venv`. Không cài package hoặc đổi cấu hình. Test DB hiện có dùng giao dịch cô lập/rollback; probe mới trong RAM với DB fake, không gọi model/provider/vector.

- Thêm `backend/tests/test_review541_fixes.py`: **25 regression** cho sibling header/value, mâu thuẫn header, enclosing scope hợp lệ, basis sai kiểu, sửa/xóa năm, sửa method/unit, contract cũ, audit thiếu/bị từ chối, catalog cùng scope, round-trip ký tự và số cột.
- Lượt focused đầu: **117 passed**, exit0, 8.61s; gồm bốn probe review trước. Ruff đầu FAIL một lỗi import I001 trong evidence_facts do import mới; sửa đúng import, không auto-format file user.
- Sau self-review thêm guard mâu thuẫn header và regression, focused cuối: **158 passed**, exit0, 10.55s. Gồm 25 regression mới, 12 test phiên 540, row-answer, serving, source context/temporal, PostgreSQL standard integration, 11 regression DOCX và evidence dependency/completeness, cùng bốn probe độc lập phiên 541.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_review541_fixes.py tests/test_review536_findings.py tests/test_row_answer_contract.py tests/test_qnu_serving.py tests/test_source_context_review.py tests/test_source_context_stage2.py tests/test_temporal_fact_contract.py tests/test_qnu_standard_integration.py tests/test_docx_source_evidence.py tests/test_evidence_retrieval_regressions.py tests/test_evidence_completeness_437.py ../.antigravity-bridge/validation/test_review541_rag_edges.py --basetemp=storage/fix542-focused-final --junitxml=storage/fix542-focused-final.xml --tb=short
```

Scoped Ruff trên năm file ứng dụng sửa trong phiên và file test mới: **PASS**, exit0. Không chạy --fix hoặc format lan các file user đã sửa.

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=storage/fix542-full --junitxml=storage/fix542-full.xml
```

Full backend một lần: **FAIL — 13 failed, 2163 passed, 17 skipped, 23 subtests passed**, exit1, 214.78s. Log `backend/storage/fix542-full.log`; XML `backend/storage/fix542-full.xml`. Đối chiếu tự động exact test IDs với XML baseline phiên540 (`review536-full.xml`): **13/13 trùng, new_failures=[], missing_baseline=[], exact_match=true**, exit0; bằng chứng `backend/storage/fix542-baseline-compare.json`. Không đổi 13 lỗi nền thành PASS. Log vẫn có traceback asyncpg khi đóng connection/event loop như baseline; không sửa lan sang hạ tầng test.

Ba finding được khép trong phạm vi regression và self-review mã; bốn probe độc lập từng FAIL ở phiên541 nay đều PASS. Chưa nghiệm thu toàn luồng RAG trên tài liệu thật.

## Phạm vi và bước tiếp

Chỉ năm file ứng dụng nêu trên, một file regression và tài liệu; giữ toàn bộ diff chưa commit khác. Không commit/push/stage/reset/dọn tracked files; không nạp lại DOCX/reparse/duyệt nguồn/index/publish, không restart/deploy/config/model changes. Monitor Gemini tiếp tục paused. Không gọi CLI/model API fallback.

Chưa kiểm toàn luồng bằng DOCX thật hoặc chat/provider/UI; chưa xác nhận chất lượng retrieval trên corpus. Khi checks cuối chốt, bước tiếp theo là kiểm offline DOCX→projection→retrieval evidence/citation, rồi mới xem xét việc nạp lại bản thử chờ đối soát. Các PDF cũ và bản DOCX trong kho chưa được duyệt bởi việc sửa mã này.
