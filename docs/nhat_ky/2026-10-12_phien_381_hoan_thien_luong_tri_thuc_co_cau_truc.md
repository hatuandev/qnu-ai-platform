# Phiên #381 — Rà phần còn thiếu trong luồng tri thức có cấu trúc

- Ngày: 2026-10-12.
- Yêu cầu: Rà Snapshot → Bóc tách có cấu trúc → Markdown/metadata/regions/bảng/thực thể → Kiểm tra/duyệt → Chunks/Facts → Embedding → Xuất bản.
- Skills ingestion/RAG/clean-code: đọc code luồng hiện hành, tách implementation có sẵn khỏi đề xuất; không sửa runtime hoặc dữ liệu.

## Kết luận

Luồng cốt lõi đúng nhưng thiếu diễn đạt về chuẩn hóa/quality gates, facts dự thảo trước duyệt, bằng chứng nguồn, version dependencies, staging/parity/question smoke test và vận hành sau publish. Đây là đề xuất nghiệp vụ, chưa phải tính năng đã triển khai.

## Luồng đề xuất đầy đủ

1. Chọn tài liệu/phiên bản + kiểm tra quyền, scope, tồn tại, định dạng/giới hạn và chống nạp trùng đúng nội dung/cấu hình. Tạo job durable, giới hạn công suất; snapshot chỉ lấy tệp đã chọn.
2. Snapshot độc lập trong Knowledge: bytes/hash/version/metadata gốc bất biến; không ghi ngược Repository.
3. Parse/OCR theo từng trang/loại file; bảo toàn số trang, thứ tự, dimensions, blocks/tables/cells/span, parser/provider/model/version. Trang trắng có evidence, trang mất chữ phải lỗi/cần duyệt, không bỏ qua.
4. Chuẩn hóa canonical artifact + Markdown/metadata/entities/regions/table model. Gắn bằng chứng trang/block/cell cho từng giá trị; tên tài liệu khác section; missing/null khác0, confidence khác người đã duyệt.
5. Tạo facts **dự thảo** và kiểm tra chất lượng cấu trúc/semantics: multi-header/year/unit/entity, liên kết bảng xuyên trang, cell source, conflict cùng nghiệp vụ/năm/phiên bản. Chưa phục vụ chatbot.
6. Studio đối chiếu/sửa/duyệt Markdown và facts/metadata; warning/ambiguity cần duyệt, severe failure cần xử lý lại. Có thể auto-ready tài liệu sạch theo chính sách, không ép mọi trang phải duyệt thủ công. Facts nhiều rủi ro có quy tắc duyệt riêng.
7. Đóng băng revision đã sẵn sàng → tạo/reuse chunks + factset tương ứng. Chunks/factset là hai tập dẫn xuất cùng revision, không lấy arbitrary version của nhau. Đổi chunking không cần OCR; đổi embedding không cần parse/fact extraction; nội dung đổi thì invalidation theo dependency.
8. Embedding qua ModelOps → staging Qdrant theo generation/provider/model/dimension. Không đổi serving pointer trong build, không khẳng định model mới có cùng chiều là vector space tương thích.
9. Đối soát đủ sources, point IDs/hash/count/dimension, factset revision và evidence coverage. Hỏi đáp thử trên **candidate snapshot** khi được triển khai, không giả coi endpoint public đang phục vụ là test staging; test số liệu, câu không có dữ liệu, citations. Không yêu cầu sốfacts>0 cho tài liệu không có bảng/facts.
10. Xuất bản manifest/pointer pin vector+facts cùng snapshot bằng cơ chế CAS; giữ chỉ mục cũ khi build thất bại. Giao diện nhãn Published phải dựa trên pointer thật.
11. Sau publish: theo dõi retrieval/answer/no-answer, citation failures, latency/usage; ngừng nguồn/replace/delete theo scope đã có. Rollback chỉ khi manifest nguồn/facts/vector còn tương thích và retained, không hứa khôi phục vô điều kiện sau purge/GC.

## Phần xuyên suốt, không cần biến thành nhiều nút UI

- Tenant/workspace/collection isolation cho đọc/lưu/reuse artifacts; idempotency, retries, cancel, heartbeat, giới hạn CPU/GPU, tiến độ từng file. Worker đã triển khai #376, cần tái sử dụng, không tạo worker thứ hai cho mọi giai đoạn.
- Audit actor/time/decision/extractor/model/confighash, lưu version và dependency; content hash không thay thế nguồn gốc/quyền truy cập.
- Các artifacts Knowledge độc lập Repository. Đổi metadata chỉ display có thể không cần embed; đổi metadata dùng filtering/prompt phải cập nhật payload/cache phù hợp. Sửa text/facts phải sinh revision và không tự đổi câu trả lời đang phục vụ.
- Tài liệu là dữ liệu, không là chỉ thị cho AI: quyền/scope giữ ở backend, các model extraction/generation không được dùng văn bản làm quyền thay đổi dữ liệu hoặc tool calls.

## Bằng chứng code hiện có và khoảng trống

- `source_ingestion_service`: import guard scope, checksum trước snapshot, artifact reuse scoped tenant/workspace; normalize/quality, ready/review_required/failed; chỉready mới materializechunkset. Cósnapshot độc lập.
- Artifact key parse hiện là filehash + parserprofile + EXTRACTION_VERSION; chưa chứa đầy đủ effective provider/model/options fingerprints. Đề xuất khi thay OCR setting vẫn không được tái dùng kết quả sai cấu hình chỉ vì nhãn profile không đổi.
- `documents/quality_gate.py`: chủ yếu kiểm tra text density, corrupt chars và có separator bảng; cảnh báo tables thiếuMarkdown hiện không thuộc critical_warnings. Chưa đủ kiểm định cell/year/unit/entity/provenance hoặc chấp nhậnfacts chính xác.
- `source_ingestion_service.update_revision_content`: tạo revision mới, giữ active index cũ; tables_count=0 khi đánh giáMD đã sửa, citation_metadata copy từrevision cũ; merge manifest giữ bbox cũ và `layout_text_alignment=stale`. Chưa có cơ chế hoàn chỉnh recompute metadata/facts/alignment sau hiệu đính. Bbox vẫn thuộc binary snapshot, không được fabricate bbox mới cho text người sửa.
- `chunk_set_service`: reuse theo canonicalhash+chunkconfig, query cross-revision chunk_set_key chưa join scope binding/collection. Khi mở rộng canonical artifact phải bổ sung scope/version/provenance đúng, không coi hash giống là đủ để reuse toàn metadata.
- `vector_generation_service`: facts đang tạo trongbuild theoMarkdown vàgắnindexrevision, không phải draftfacts dùngStudio trướcduyệt. Parity đã kiểmpointID/contenthash/count; không chỉđếm sốvector. Chưa có gate semantics/facts review coverage hoàn chỉnh.
- `generation_publish_service`: tất cả bindingactive phải có index phùhợp sourcerevision; remoteactivate rồi lock+epoch/membershipCAS mới swapDBpointer. Facts hiệnfiltertheoindexrevision (#380), chưa cófactsetmanifest độclậpreusepinned nhưđềxuất. Không mô tả tính năng hiệncó nhưchưacó, cũngkhôngcoi atomicpointer đãđủ đảm bảo nội dung đúng.
- Lỗi thực tế #379/#380 vẫn chưa sửa: reranker scorethreshold, factsDTO500, frontendentities suyra, facts chưađủ/year, citations/noanswer/audit. Đây là ưu tiên ngắn hạn trước refactorartifact rộng.

## Bàn giao

Chỉ đọc code và viết kết luận, không HTTPchat/LLM/DBwrite/reparse/embed/publish/reset/migration/qnu-sso. Không chạy pytest/build vì không sửa ứng dụng. Nhật ký/snapshot/memory/index đồng bộ; chưa cập nhật quy trình thực thi chính thức vì luồng mới chưa triển khai.
