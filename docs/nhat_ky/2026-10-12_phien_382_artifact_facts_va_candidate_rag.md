# Phiên #382 — Artifact có cấu trúc, facts dự thảo và candidate RAG

- Ngày: 2026-10-12. Người dùng đồng ý triển khai luồng đề xuất #381.
- Skills: backend/ingestion/RAG/ModelOps/clean-code/frontend/admin design. Giữ kiến trúc source revision độc lập Repository, sử dụng JSONB và primitives sẵn có, không tạo một pipeline OCR mới.
- Không reset DB, migration, đổi policy/model/key, reparse/nạp/publish/ngừng/xóa nguồn của người dùng, không sửa qnu-sso. Integration test tạo dữ liệu tenant riêng trong transaction rồi rollback. HTTP RAG thật có thể ghi usage/cache/audit theo runtime hiện hành.

## Thay đổi đã triển khai

1. Reranker giữ `relevance_score` từ provider độc lập RRF, threshold đọc đúng trường; phản hồi rỗng/NaN/index sai không coi là thành công. Regression trước sửa: 3 tests thất bại đúng score/DTO.
2. Facts DTO cho phép document_id null, trả binding/index IDs. API scope theo actor; Dữ liệu số mặc định chỉ đọc facts của active index/source và dữ liệu Excel legacy active. UI lỗi không âm thầm báo rỗng/100%, thống kê rỗng là dấu gạch, báo giới hạn dữ liệu đã tải.
3. Artifact `structured-source-v1` trong source revision.parse_provenance: content hash, metadata, bảng Markdown/header rows/cells thô, canonical parser tables giữ source spans, draft cell facts, evidence trang/bảng/hàng/cột/row values/year, factset hash/issues/review. Không suy đoán loại ngành/đơn vị/numeric missing; không thêm từ điển vá tiếng Việt. Confidence không có được đánh dấu unavailable, lưu0 để tương thích cột DB bắt buộc nhưng UI không trình bày như điểm đo.
4. Facts được tạo trước quality/review, đối chiếu ngay Studio tab Thực thể. Thiếu header, lệch số cột, xung đột cùng entity/attribute hoặc mất bảng cần review. Sửa Markdown tạo revision + metadata/facts/hash mới, giữ geometry tệp gốc và cảnh báo stale. Duyệt revision duyệt cả facts, không tự publish.
5. DOCX/PDF giữ canonical tables từ parser; cache fingerprint tăng version và thêm cấu hình OCR DB/model/provider/timeout/update time không chứa key. Parse reuse/chunk reuse giới hạn cùng binding để không sao chép nguồn gốc giữa scope. Fresh artifact dùng lại khi đổi embedding.
6. Build vector chiếu facts đã materialize sang KnowledgeFact của index, deterministic ID theo index/draft ID; parity report pin source/factset hashes. Publish/preview so source ready, review, hashes, counts và nội dung/evidence từng fact trước remote activation. Legacy index không có manifest facts vẫn đọc/publish theo compatibility, cần build lại để nâng cấp gate.
7. Endpoint POST `/knowledge/collections/{id}/vector-generations/{generation}/preview`: actor có quyền update, scope kho, toàn bộ active sources phải có ready/active index đúng revision. Backend tự dựng candidate snapshot, không nhận snapshot tùy ý. Dense đọc staging trong snapshot cho phép nội bộ, sparse/facts/neighbors pin cùng revisions; không thay pointer, không dùng semantic cache. UI “Thử RAG” trong dialog Nạp vector dùng ModelOps mặc định, ghi rõ không phải test DAG policy của trợ lý.
8. Citation title ưu tiên tên nguồn trước section. Không coi đó là đã giải quyết toàn bộ citation relevance.

## Phạm vi tệp

- RAG: `fusion.py`, `reranker.py`, `citation_guard.py`, `service.py`, `retriever.py`, `vector_indexer.py`.
- Knowledge: `schemas.py`, `service.py`, `router.py`, `parsers/markdown_parser.py`; services `source_artifact.py` (mới), `generation_candidate.py` (mới), `parse_fingerprint.py` (mới), source_extraction/source_ingestion/chunk_set/facts/vector_generation/generation_publish.
- FE: types knowledge/studio-ocr, knowledge-api, studio-mapper, source-draft-facts/candidate-rag-preview (mới), OCR inspector/types/workspace, facts tab, detail page, vector controls.
- Tests: structured_source_contract/candidate_artifact_integration (mới); bổ sung đầy đủ fields source fixture cho source_layout_extraction/source_pause/studio_nullable_reading_order.

## Kiểm chứng

- Ruff toàn BE đạt; cảnh báo quyền đọc 3 thư mục storage cũ không phải lint error.
- Full BE cuối: **932 passed, 11 failed cũ, 2 skipped**. Các lỗi cũ vẫn gồm consulting export, cutover/GC/canary/decommissioning auth/flags, reconciliation, tools facts phụ thuộc dữ liệu và auth-session role. Không sửa test cũ cho pass giả.
- Chạy suite mặc định lần đầu gặp thêm9 lỗi quyền tmp_path và4 fixtures thiếu field mới; bổ sung fixtures và dùng basetemp mới được xác nhận, các lỗi mới không còn.
- Scoped Biome đạt; frontend build Vite + tsc đạt exit0.
- Real PostgreSQL rollback test: draft chưa serving, active facts document_idNone đọc được, paused bị loại, tenant sai bị chặn, cùng count nhưng giá trị bị sửa999 không qua gate, candidate không đổi serving pointer.
- HTTP thật: facts200/81rows; Studio200/214draftfacts từ Markdown source đã có (legacy preview read-only, không tự thay81facts đãpublish). Candidate preview trên generation hiện hành200/answered có4800. Một lượt RAG public threshold0.4 có2contexts nhưng insufficient_context; đã khắc phục mất toàn bộcontext, chưa nghiệm thu answer quality. Console lần đó lỗi encoding cp1252 khi in tiếng Việt, không phải HTTP failure.
- Chưa browser E2E vòng tạo source→review→build staging mới→preview→publish, chưa full assistant DAG/multiturn/Ragas/load/crash trên AI server. Candidate HTTP live vừa thử generation đãactive, không gọi đó là xác nhận staging GPU E2E.

## Còn lại của đề xuất #381

- Bản này là nền tảng và hai P1, không phải toàn bộ semantic extraction đã hoàn tất. Bảng HTML/OCR nhiều tầng, bảng nối xuyên trang, unit/entity semantics và đối chiếu cell→bbox cần mở rộng/test; hiện giữ parser tables và cảnh báo thiếu bảng, không bịa tọa độ.
- Metadata manual editor và fact-level approve/conflict resolution riêng chưa có; sửa qua Markdown và duyệt toàn revision. Review lưu decision/time/comment, chưa hoàn thiện actor-level audit chung.
- Legacy artifact preview được tính read-only; bản mới persist một lần. Chưa backfill/mutate artifacts đãpublish, không cần OCR lại khi build từ Markdown cũ.
- Question preview là kiểm tra thủ công, chưa có automated evaluation report/publish gate theo testset; provider/model response provenance, no-answer structured contract và citation relevance vẫn cần làm. RAG wrapper audit cũ còn thiếu model thực.

## Bàn giao

Khởi động lại dev/worker để worker nhận code mới; không reset DB. Nạp mới sẽ có artifact persist. Dữ liệu đang xuất bản giữ nguyên; muốn dùng facts mới từ Markdown cũ phải chủ động build/publish sau đối chiếu. Không coi214draft là214facts đã duyệt/đãpublish.
