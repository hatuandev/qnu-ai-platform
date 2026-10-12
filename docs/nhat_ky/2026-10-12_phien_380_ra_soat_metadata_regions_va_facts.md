# Phiên #380 — Rà metadata, regions, thực thể và facts so với nhánh cũ

- Ngày: 2026-10-12.
- Yêu cầu: Kiểm tra chức năng lưu tiêu đề/metadata/regions/thực thể/facts trong nhánh cũ và hiện tại, đề xuất hướng đi.
- Nhánh đối chiếu duy nhất ngoài main đang có: `codex/main-before-knowledge-publishing-v2-20261009`, commit `b2d61cb`. Hiểu đây là nhánh thứ hai user nhắc; không checkout/reset.
- Skills ingestion/RAG/clean-code: theo dõi persistence→DTO→UI→retrieval, thuật toán tổng quát và đề xuất trước; chỉ audit không sửa runtime/data.

## Bằng chứng hiện tại

Nguồn `bnd_7654b2810a0a`, revision `ks_rev_98a6b03f95fe`:

- snapshot_metadata lưu title/file_name/file_type/hash snapshot/preview cùng metadata gốc; citation_metadata lưu số văn bản/ngày/cơ quan/loại. Cơ quan persisted là Trường Đại học Quy Nhơn, số/ngày/loại null. Không suy đoán số quyết định/ngày chưa điền trong văn bản.
- page_manifest lưu14trang,76blocks,dimensions vàhas_tables ở12trang. Regions từ blocks được dựng DTO Studio; không mất khung.
- Một số text trong blocks đã dính khoảng trắng ngay trong DB: header `BỘGIÁODỤCVÀĐÀOTẠO`, title `THÔNGBÁO...`. Markdown/khungtext là hai biểu diễn khác nhau, cần alignment không lấy blocktext lỗi làm metadata canonical.
- `ocr-inspector.tsx` tab Thực thể dùng useMemo tự regex trên regions/tênfile, không lấy citation_metadata từBE. Badge Đã chuẩn hóa luônhiện không córeviewstate. Điều này có thể báo Bộ là cơquan thayvìTrường, sai type, năm chưa xácđịnh; không phải entityrecords persisted.
- Trong `source_extraction`, extracted.tables tồn tại nhưngsourceingestion chỉlấycount. Revision lưu manifestblocks vàMD, chưa bảo toàn đầyđủ structuredtable/cellspan/provenance cùng canonical_document để phục vụ factextractor.

## Facts: không trống, API đang lỗi

- Live DB có81facts thuộccol_admissions; chunkset vàindexactive củatuyensinh cùngfact_count81.
- Phânbổ73 Mãngành,4 Tổhợpxéttuyển,4 Phươngthứctuyểnsinh; chưa có cutofftheoyear/tuition/IELTS/quota tại bộfacts này. Một fact phụlục sai entity `Địa lí (7140219)` do tênmôn/nhóm được nhận thành tênngành.
- GET `/knowledge/collections/col_admissions/facts?limit=50` HTTP500. Gọi read-only facts_service tái hiện ValidationError FactItemResponse.document_id: None không phải str.
- Facts ADR012 gắnbinding_id/index_revision_id, chủđíchdocument_id=None do không dùngKnowledgeDocument legacy. DTO vẫn yêu cầustr, thiếu cácIDscope hiện hành. Không được chữa bằng IDgiả hoặc gắn lạiRepositoryfile để vừaschema.
- FE parent truyền factsQuery.data||[]/total||0 nhưngkhông truyền error; FactsTab rỗng tựchoavgconfidence100. Ảnh user đang loading không chứngminhkhôngfacts; sau500 UI vẫn cónguycơhiện0/100% sai nghĩa.
- facts_service list chỉ lọccollection, không lọc snapshotactive; sau sửaDTO phải phân biệt candidate/staging/published/paused, tránh lẫn nhiều generation/revision vào bộsốliệu chính thức.
- FactLayerRAG đã cófilter active_index_revision_ids vàscopecollection khi được truyền retrievalsnapshot. DAG gọiRAG chung, không cần extractor riêng trên mỗi câu hỏi.

## Đối chiếu nhánh cũ

- IngestionService lưutitle/metadata/page_markdowns/page_blocks/page_dimensions vàoKnowledgeDocument.doc_metadata. Studio cóthểensureblocks vàparse bổsung khiđọc; không nên phục hồi sideeffect này trong luồng mới.
- `_prepare_domain_records(parsed.canonical_document)` chạyDataQualityGate, build_domain_records/build_record_chunks vàextract_facts_from_domain_records; persist_chunks_facts ghiKnowledgeFact theo document. Approve verifiedmarkdown còn tạo lạifacts.
- TabThựcthể của nhánhcũ cũng dùnguseMemo regex frontend; không xácnhận nó đã lưu tấtcả thuộc tính hiểnthị vàoDB. Lấy trải nghiệm đốisoát cũ, không lấy cơchế suyrafrontend làmnguồnsựthật.
- Hiện tạiChunkSetService tuy docstringnói chunks+facts nhưngchỉchunkmanifest, fact_count0. VectorGenerationService mớiextractfacts mỗi lầnbuildgeneration từcanonicalpagesMarkdown rồi gắnindexrevision. Parse-once/chunk-once đãcó nhưngfact-once chưađúnghoànchỉnh.
- `extract_from_verified_markdown_pages` loạiheadercellrỗng bằngfilter, mấtvịtrícột; chỉdùng1hàngheader, table_indexluôn0, không xửlý header2024/2025 vàrowspan/subheader đầyđủ. `_ROLE_KEYWORDS` làmapping từkhóacũ; không mởrộng bằngtừđiểngõtay đểvá.

## Hướng đi đề xuất, chưa triển khai

Giữ ADR012, bổ sung một artifact bóc tách có cấu trúc/phiênbản và provenance:

1. Snapshot Knowledge → parse/hybridOCR → canonicaldocument (pages/blocks/tables/cells/span/order/dimensions) + Markdown dẫnxuất. Không bắt phảicóbboxvới định dạng chưa render được; DOCXgeometry dùngpreviewPDF đãalign, không nhận làWordcoordinategốc.
2. Metadata/extractedentities persisted theo sourcerevision: tênvăn bản riêngsection, raw/normalizedvalue, page/block/cell evidence, extractorversion, reviewstate. Usermetadata gốc giữriêng, khôngghiđè KhoTàiliệu. Null làunknown, khôngtựđiềnconfidence hayngày/số.
3. Chuẩnhóabảng bằng header-tree/spanmatrix: giữcột rỗngvàrowspan/colspan, path2024→Điểmtrúngtuyển, entityđúngcộtngành, year/unit/attribute/value. Ánhxạ semantic cóschemas/modelDB hỗtrợ nếuambiguity, phảigroundvàvalidatebằngcelltext; khônggiảđịnh everytable làbảngngành.
4. Persistfactset theo sourcerevision + canonicalhash/extractorversion, độc lậpembedding. Facts cóentity/code/attribute/value/year/unit vàpage/table/row/col/block/cellrefs. Empty2026quotacell khôngsinh0; confidencephảicónguồnvàkhôngđồngnhấtvớiverified.
5. Studio đọc cùng artifact: Markdown/Thựcthể/Vùngnhậndiện/Bảngfacts, sửa/duyệt tạorevision mới. Metadata có thể chỉnh màkhôngembeddingnếu chỉdisplay; nội dung/factsđổi phảiinvalidatederivedartifactđúngdependency, không reuse dữliệucũgiảvờcònkhớp.
6. Nạpvector reuseMD/chunkset/factset; generation/indexmanifest pin đúng phiên facts. Publish đốisoát vectors+facts vàchuyểnpointer nhấtquán, giữbảnđangserving khi buildlỗi. FactsTab mặcđịnhPublished, cóDựthảo/Cầnduyệt kèmnguồn/trang/năm/unit; Excel cũngqua provenance/approval/snapshot chứkhông điđường tắtlegacy.
7. RAG dùng structuredfacts cho sốliệu, hybridchunks cho quyđịnh, metadataconstraints theoexplicitquery/year/document scope; không ép mọi truyvấn vào latestyear. Citation xácđịnhdocumenttitle/page/cell vàevidence của claim. DAG điều phối cùngRAG/FactLayer, khôngbóc tách lại khi hỏi.

### Thứ tự ưu tiên

- P0 sửa rerankerthreshold #379 để chat không loại hếtcontext.
- P1 factsDTO/errorUI/emptyconfidence/publishedscope và citationtitle đúng; không cầnOCR lại đểfixAPI.
- P1 bảo toàn canonicaltables/header-tree vàmetadata/entityartifact; fixblockspacing có thuậttoánalignment/layout, không từđiển.
- P2 factsetonce + review + indexpublishpin/migration tươngthích; re-materialize từMD+snapshot hiệncó, chỉparse/OCR khi thiếu bằngchứng structureddata. Trước mọibulkregen cầnpreview+userapproval; giữactiveindex.
- Regression: DOCX/PDFtext/scan; bảng nhiềuheader2024/2025, IELTS2bảng, cộtchỉtiêu2026rỗng, phụlụctênmôn/ngành, draft/paused/rollback, đổi2embeddingkhôngđổiđápánfacts.

## Tài liệu chính thức tham khảo

- [Docling document model](https://docling-project.github.io/docling/concepts/docling_document/): hỗtrợ representationthốngnhất/structure/layout/provenance. Đây làcơsở giữstructuredartifact, không chỉMarkdown.
- [Docling document reference](https://docling-project.github.io/docling/reference/docling_document/): tablecells/provenance/boundingboxes khi có.
- [Qdrant payload](https://qdrant.tech/documentation/concepts/payload/): lưu metadata với vectors; chỉđẩy payloadtra cứu cầnthiết, structuredartifact PostgreSQL/objectstorage, không nhồitấtcả blockjson vào từngpoint.

## Kiểm chứng và giới hạn

Gitshow/DB SELECT/HTTPGET và read-only facts_service táihiện lỗi; chưa codefix/testsuite/reparse/reindex/DBupdate/reset/qnu-sso. Không phátsinhLLMinference trongphiên. Chưa audit mọi canonicaltable ngành/nhánhkhác; chỉ dùngnhánh tồn tại cótêntrên, không đoánnhánhthứhai khác.
