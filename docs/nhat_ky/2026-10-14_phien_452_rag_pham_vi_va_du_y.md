# Phiên 452 Triển khai RAG đúng phạm vi và đủ ý

## Mục tiêu

Triển khai4ưu tiên người dùng đã duyệt sau báo cáo451, tiếp nối lượt bị ngắt. Dùng skill Backend/RAG/ingestion/clean-code/chatbot-evaluation; dùng skill viết tài liệu cho báo cáo theo format repository. Không reset/đổi model/config/timeout/embedding/reranker/DB/publish, không sửa DOCX, không đưa DAG trở lại chat.

## Các tệp thay đổi của phiên

- Mới: `backend/app/modules/rag/evidence_hierarchy.py`, `backend/tests/test_evidence_scope_452.py`.
- RAG: evidence_blocks, evidence_bm25, evidence_context, evidence_schemas, evidence_search, evidence_pipeline, evidence_claims, evidence_passages, evidence_validation, evidence_verification, evidence_facts, evidence_lists, evidence_model, evidence_audit, evidence_indexed_audit, evidence_historical.
- Harness451 thêm subset IDs/prefix để probe có kiểm soát; giữ artifacts451 nguyên vẹn.
- Báo cáo `docs/kiem_thu/2026-10-14_rag_pham_vi_va_du_y.md`; nhật ký/index/memory/snapshot/WORK_LOG và quy trìnhRAG được đồng bộ. Các dirty changes444/449 khác được giữ, không coi toàn bộ diffGit là thay đổi452.

## Thuật toán

Read-time lược đồ record lặp>=2fieldlabels chung; ngữ cảnh cha–con qua page-marker, dừng ởheading chưaphânloại/cấpcao. BM25context thêmrecordpath, rankmụccon theo facets vàgiữmemberraw/ưu tiênscope khi packing. Không sửa canonical/unitmanifest/hash/vector; không cần reindexcho lớpđọc.

Primarybody sai record bịchặn, verifier giữentity/education_level/attribute/year vàpublicfacetcoverage. Gắnrawheadingcùngsource; factcontexttheopagerow/header,unknown/ambiguouskhôngpositiveproof. Táchproposal sourcesđểverifyriêng, khôngtắtborrow-scopeguard. Boldscalar khôngbịbỏnhưheading; fieldtuplekhôngthànhenumunasked; rowlabelcótiềntố1từkhôngthànhgroup khi hỏithuộctính,giữcomparison/groupguard.

Historical thêmscopefilter+diagnostics, giữpartialcónhãn/deadline90/lỗiRFC7807. RepairJSON truyềnconstrainttyped; nhãnrequirement1000chars cả2DTOkhôngtruncatequote/khôngtăngretry/token.

## Kiểm tra

- Trước sửa:5regressions mới fail (hàm/fieldchưa có vàsummarypackingfail); các ca negative sau đó xác nhận lỗi record, falsecoverage vàboldscalar.
- FocusRAG160pass/21ca mới. Ruff toànBackend đạt, warningsACLtesttemp cũ; diffcheckđạt. KhôngFEchanges/Vite.
- Fullgate cuối `storage/pytest452_gate.xml`:1329pass/11fail/15skip/0errors,195,57s; tên11failtrùng449, khônglỗiRAGmới. Các lượt trước1321/1325/1327pass giữartifactriêng. Diffcheck/Ruffcuốiđạt; warningsACLtesttemp cũ.
- Liveprobe các phiênbản riêng:2lần dừng502SourceAnswerAuditrequirement; 20plan dừng6ở504; final6 dừng5ở2112historical_verification504/90s; scalar2 cuối2HTTP200/supported,2105đúngcombo/2108đúng7440122/4năm/Cửnhân,7spansDBkhớp.
- Bản scalar2 runtime/config/publicationunchanged; fingerprintd973eb60…; snapshot6180f8f51b791da886a2/21sources/1257points/parityđạt. Không full20acceptance/full82/accuracy/TM08 hoặc lịch sửliveđạt.

## Môi trường và giới hạn

Venv/default sandbox vướng quyền truy cập; kiểm thử dùng môi trường host qua quyền đãduyệt. `uv sync --extra dev` đãgỡ4extrasngoàiproject; lập tứckhôi phục nguyênversionfire0.7.1/fonttools4.66.1/pdf2docx0.5.13/termcolor3.3.0, không đổi dependencies khai báo. Một approval đọcartifact hếtthời gian đãretry1lầnthànhcông, không kếtluận thao tác unsafe.

Các kếtquảlive khônggộpcácfingerprint đểtuyênbốaccuracy. Cần chạy20ổnđịnh sau đó82; lịch sửtimeout chưaxửlýlatency hayđổimodel. Ghi nhận kỹ: citeđúngspan chưađủ đúngscope; metadata địnhdạngbôiđậm khôngđồngnghĩaheading; danh sách thuộc tính khôngđồngnghĩa toàn bộ thuộc tính đềuđược hỏi.
