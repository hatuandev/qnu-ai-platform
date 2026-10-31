# Phiên 763 — Review ba thay đổi RAG sau vibe

Ngày 2026-10-31. User yêu cầu review bản triển khai ba đề xuất từ phiên762. HEAD01f682ed và3file dirty: answer/context.py,answer/drafting.py,admissions-chat.ts. Chỉ review và kiểm chứng; không sửa logic, DB phục vụ, checkpoint, restart, reindex hoặc gọi model live. Giữ mọi sửa đổi của user.

## Kết luận

- Đã bỏ retry theo expected answer và tên ngành trong prompt; idempotency key nay ổn định, không tự tạo hội thoại khác khi thiếu turnID. Đây là tiến bộ so với762.
- P1 — `drafting.py:61–65`: nhánh compact áp cho mọi table có structure. Chunker lưu bảng statuskhácparsed bằng rawtext vàstructure.table_status, không córows/JSON. Nhánh mới cho prefixrỗng vàrowsrỗng, model mất toàn bộ nội dung. Probe synthetic32byte trả chỉevidence_id/kind/rows[]/page_notes[]. Cần fallbackraw khi chưa đủ parsedrows; context.evidence_size cùng lỗi.
- P1 — `drafting.py:69–79`: loại row_span,col_span,original_column_count,row_indices,source_table_citation/context nên mất quan hệ ô/header và định danh bảng khi ghép. Probeôgộp xác nhận không cònspan/tableidentity. Cần projection gọn nhưng giữ cấu trúc và proof; prompt nói sốcột/ôtrống không thay bằng chứng cùngbảng/hàng. Không tái dựng bảng chỉ nhờ thứ tự citations.
- P1 — `admissions-chat.ts:75–79,298–300`: dùng lại completedturn từcheckpoint rồi đánh first_attempt_pass=true vôđiềukiện; không kiểm config/prompt revision. Vì19kếtquả cũ tồn tại, lệnh chạy lại có thể vẫn báo19firstattempt nhưng không inference mới. elapsedMs đoGET chứkhônglatencymodel. Cần frozen evaluation run/newconversation riêng hoặc đánhreplay, không tínhfirstattempt.
- P2 — `drafting.py:12`: giữPROMPT_VERSIONv3 dùsystemprompt,payloadprojection vàevidenceorder đổi. Không thể phân biệt hợp đồng cũ/mới bằngtraceversion; cần version/hash ổn định và kiểmtest lưucheckpoint.
- Ngân sách chưa thống nhất thêm: diffchỉcompact vàtăng quota5M→10M trongE2E. Không có đổiModelOpsbudget. Không coi tăngquota là giảmusage/giải quyết output.

## Kiểm chứng

- BackendV1 Ruff scoped context.py/drafting.py: exit0PASS.
- BackendV1 fullunit `.venv/Scripts/python.exe -X utf8 -m pytest tests/unit -q --basetemp ../tmp/pytest-review-763 --tb=short`:528PASS/1FAIL,exit1. Lỗi nền đúngID `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`,invalid_identity tạiworkspaces/access.py39. Không sửa lỗi ngoài phạm vi.
- Probe synthetic trực tiếp compact_evidence_item: tái hiện mấtrawtable32bytes, bỏspan vàtableidentity. Đây là lỗi logic dù suiteunit hiện chưa córegression tương ứng.
- FrontendV1 E2ETypeScript `tsc --noEmit -p tsconfig.e2e.json`:PASS; Biomeadmissions-chat.ts:FAIL organizeImportsline9.
- Gitdiffcheck3file:exit0.
- Integration API cô lập: `scripts/run_isolated_tests.py tests/integration/test_rag_scope_context_672.py tests/integration/test_answers_api_648.py -q --tb=short`: exit1,24PASS/1FAIL/3ERROR trong213.75s. Ba setupERROR và test `test_metadata_requires_explicit_human_acknowledgement_of_its_hash` nhận422 `retrieval_metadata_invalid` (annotation trỏ đoạn không tồn tại), trước bước RAG. Chưa chạy lại HEAD để gán baseline; không kết luận toàn scope regression đạt. Harness223.88s, receipt xác nhận database test đã drop và legacy_sentinel preserved. Log `tmp/review-763-integration.txt` và runtime context636/qnu_v1_test_6215de8862ea4a85/pytest.log.
- LiveE2E/inferenceNOT_RUN; chưa thể nghiệm thu bản sửa hoặc khẳng định19freshPASS. Nhãn benchmarkdraft/humanreviewNOT_RUN giữ theo762.
