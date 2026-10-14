# Phiên 431 Đề xuất cấu trúc tri thức dùng chung

## Yêu cầu

Người dùng xác nhận văn bản tổng hợp thuộc mùa2026 và hỏi khả năng tái cấu trúc khi bóc tách dựa vào ngày trang đầu, đồng thời muốn nền tảng tìm kiếm ngữ nghĩa ổn định cho nhiều chatbot. Chỉ phân tích và đề xuất; chưa được yêu cầu triển khai đợt này. Không sửa runtime/nguồn/DB hoặc nạp/xuất bản.

## Kiểm tra hiện trạng

Áp dụng skill knowledge-ingestion/RAG/clean-code: ưu tiên cấu trúc và thuật toán tổng quát, không hardcode vocabulary/mô hình, tận dụng kiến trúc có sẵn. Đọc `parsers/base.py`, DoclingOfficeParser, `chunker.py`, `services/temporal_metadata.py`, `source_context.py`, DTO ngữ cảnh, và nhánh evidence_blocks.

Đã có canonical models/blocks/table/source spans, ParsedContent.canonical_document, ChunkDraft.metadata; parserOffice đang exportDocling sangMarkdown, chưa truyền native document ở return này. Temporal extraction nhận date line trang đầu, phân biệt issued_date/issued_year/subject_years/filename_years, có evidence/status và cơ chế human edits theo revision/audit. Facts có applicability_year và qualifier projections. Tuy nhiên evidence_blocks lấy heading_years rồi gán scope_years cho mọi block của nguồn; đây là điểm không đủ tổng quát cho mixed-year prose. Đây không phải audit toàn bộ ingestion hoặc xác nhận mọiformat đều giữprovenance đầy đủ.

## Đề xuất kỹ thuật

1. Ba lớp: file/nội dung gốc bất biến; canonical document tree với headings/paragraphs/lists/tables/notes và span; đơn vị retrieval/facts có metadata. Markdown là bản trình bày, không nguồn cấu trúc duy nhất. Không nhờLLM viết lại nội dung rồi dùng như chứng cứ. Text đểembedding có thể thêm context đã xác minh nhưng quote vẫn bám originalspan.
2. Tách thời gian: ngày ban hành, thời gian hiệu lực (nếu có căn cứ), kỳ/năm dữ liệu và thời điểm sự kiện. Ngày trang đầu là candidate có provenance, không suy ra mọi dữ liệu cùngnăm. Tài liệu thiếu/ngày OCR lỗi hoặc nhiều date không đoán. DOCXpage chỉ gán khi có provenance thật; paragraph/table anchors thay page giả.
3. Coremetadata: source/revision/hash, title/issuer/documentnumber/type, hierarchy/path/span/parent, blocktype, temporal role/period/evidence/status, scope/conditions/unit và relation replaced/amended khi có chứng cứ/duyệt. Field mở rộng nghiệp vụ theo schema/cấu hình kho; không nhúngtừđiển tuyển sinh vào lõi.
4. Structural/hierarchical/token-aware chunking: không cắt điều kiện, ngoại lệ, danh sách và tupletable ởgiữa; paragraph/sentenceboundary trongparent, row+headers+identity cho bảng, parent-child expand cógiới hạn. Không đồng nhất SemanticChunkerhiệncó với chắcchắn đã dùngsemanticboundarybằngembedding.
5. Thời gian local thắng inheriteddefault chỉ khi có evidence/review đúngrole; ngày tríchdẫn văn bản khác không làngàybanhành; year thamkhảo không làyearápdụng. Userconfirmation2026 làcontextdefault cho bản tổnghợp, không xóa thôngtinlịchsử2025. Proposed/unknown không được tự nâng verified; unknown có thể retrieve+verify chứ không lọc cứng mất toànnguồn.
6. Hybrid vector+lexicalBM25/FTS/RRF+configuredAIreranker trêncùngscope/revision/metadata; filter/retrieval phải dùng cùngcontract, no-answer khi thiếuactualsupport. Metadatafilters dùngyearrole/period, khôngphải mọi con số năm. Domainassistant chỉ đổi persona/bindings/schema/models quaDB.
7. Exactduplicate bằnghash; near-duplicate bằng similaritysignature làcandidate đểđốisoát, không tựxóa source. Distinctyearrecord giữriêng. Latestpublicationdate khôngtựthaythếmọi thôngtin; supersedes relation chỉ cùngtuple/phạmvi vớiproof.
8. Triểnkhaiincremental: (a) nốimetadata ngày/năm đãcó sangproseblock/DTO, bảo toànproof; (b) unifytree/chunkcontract đếndense+lexical+facts; (c) stagingrebuildsubset, testmulti-domain/crossyear/unknown/conflict/sourcebound, CASpublish khiđượcủyquyền. Không cầnresetDB/reuploadtoànkho nhưng nội dung/metadataindexthayđổi cầnbuildrevision mới đểtránhservingcũ.

## Nguồn tham khảo chính

- Docling chunking: https://docling-project.github.io/docling/concepts/chunking/ — hierarchy/token budget/headings/captions vàtableheaders. Đây làthamkhảo phươngpháp, khôngđềxuấtthayparser hoặc tựcài dependency.
- Qdrant filters: https://qdrant.tech/documentation/search/filtering/ — payloadconditions/index phục vụlọc. Không giải quyếtsemantic temporalroles nếu ingestiongánsaimetadata.

## Kiểm chứng và giới hạn

Chỉ đọccode/docs vàtrangofficial; khôngRuff/Pytest/Vite vìkhôngruntimeedit. Chưa thực hiệnclassifier/dateextraction mới, migration, reindex hoặcbenchmark. Chưa kếtluậnaccuracy82/Ragas. Memory/index/worklog cập nhật đểtiếpquản; backup vẫnpaused/quotaunlimited.
