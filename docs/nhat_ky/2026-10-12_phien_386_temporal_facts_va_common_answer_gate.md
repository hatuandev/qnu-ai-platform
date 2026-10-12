# Phiên #386 — Facts theo năm và quyết định trả lời chung RAG/DAG

Ngày: 12/10/2026. Trạng thái: đợt đầu triển khai Kế hoạch 14, chưa hoàn tất toàn bộ kế hoạch.

## Mục tiêu và kết quả

Ngăn lấy điểm chuẩn năm 2025 trả thành năm 2026. Ngày/năm ban hành và chủ đề thuộc nguồn, năm áp dụng/phương thức thuộc từng ô bảng/fact. Không reset DB hoặc thay pointer đang phục vụ.

Đã thêm metadata thời gian có evidence: dòng thể thức được đối chiếu lịch, ngày viện dẫn trong paragraph không cạnh tranh, ngày thiếu day/month giữ null, tên file chỉ là gợi ý. Header cây giữ ngữ cảnh cột; chỉ lan truyền trong nhóm có child schema lặp lại hoặc các cột năm rõ ràng. Ô rỗng không thành 0, identity thuần số được giữ. Chưa đọc đầy đủ mọi parser span/geometry hoặc nối bảng xuyên trang.

Facts mới lưu entity_code, attribute_code, temporal_context và qualifiers trong raw_data JSONB có sẵn. Không thêm từ điển năm/ngành/model; ánh xạ role sang mã contract dùng classifier cột hiện có. Chưa thay legacy taxonomy vốn vẫn có vocabulary cũ; không khẳng định hệ thống đã hoàn toàn zero-vocabulary.

Gate dùng facts cùng snapshot, entity/attribute/year. Hỗ trợ supported/missing/conflict và coverage nhiều năm/thuộc tính; renderer không cần model để sinh số liệu. Missing không chứng minh Trường chưa công bố. DAG bỏ consulting trước gate cho truy vấn số liệu theo năm được hỗ trợ, truyền quyết định sang output/no-answer. Prose/IELTS/kỳ thời gian/phương thức diễn đạt khác nhau chưa được bao phủ toàn bộ.

Cache đổi namespace và bỏ qua cache câu có năm; rewrite kiểm số gốc không đổi, bỏ quy tắc ngày→ngành. Không xóa Redis. UI hiển thị năm/phương thức trong Studio và tab Dữ liệu số, có bộ lọc phần facts đã tải.

## Các tệp thuộc thay đổi

- Knowledge: `services/source_artifact.py`, `table_context.py`, `temporal_metadata.py`, `source_extraction.py`, `source_ingestion_service.py`. Artifact version structured-source-v2-temporal; extraction layout-v6-temporal. Import, sửa Markdown và reparse đều lưu artifact mới. Bản stored cũ có hash hợp lệ được giữ nguyên.
- RAG: `temporal_answer.py`, `facts.py`, `schemas.py`, `service.py`. Lỗi lookup DB trả FACT_LOOKUP_UNAVAILABLE thay vì giả vờ không có dữ liệu.
- DAG: `rag_answer_node.py`, `query_rewrite_node.py`, `output_chat_node.py`, `no_answer_node.py`.
- FE: `types/knowledge.ts`, `components/knowledge/fact-context.ts`, `ocr/source-draft-facts.tsx`, `ocr/ocr-inspector.tsx`, `tabs/collection-facts-tab.tsx`.
- Tests: `test_temporal_fact_contract.py`; các test existing được chạy kiểm lại, không sửa để che lỗi.

## Kiểm chứng

Regression trước sửa: 5 fail vì chưa có temporal fields/gate. Sau sửa, các test này đạt. Suite trọng tâm cuối: 37 passed, gồm ngày thiếu/sai lịch, filename khác ngày ban hành, bảng 2023/2024 THPT/học bạ, identity IELTS, conflict, partial coverage, RAG missing không gọi model/retriever, DAG không nâng missing, rewrite không đổi năm. Có cảnh báo Qdrant không liên hệ được, không mock production adapters để che mất kết nối.

Ruff full đạt; có cảnh báo truy cập các thư mục test cũ. Biome 5 tệp mục tiêu đạt; npm run build gồm tsc đạt.

Full suite trước batch cuối: 940 passed, 12 failed, 2 skipped. 11 lỗi baseline phiên #382; lỗi mới `test_api_rag_ask_no_context` thiếu hotline đã sửa bằng No-Answer Policy hiện có và kiểm lại đạt. Không suy diễn số pass của full suite cuối chưa chạy.

Integration PostgreSQL rollback test đã đạt lúc dịch vụ còn chạy (17 tests tổng của suite ban đầu). Lần cuối test này thất bại do ConnectionRefusedError, không phải parity assertion. Read-only kiểm cả ngoài sandbox: Docker daemon pipe không tồn tại; không thấy các listener dev/DB kiểm tra. Final full/integration/browser/SSE/cold-warm E2E bị chặn bởi dịch vụ không hoạt động. Không tự mở Docker, restart worker, publish/reparse/backfill hoặc reset dữ liệu người dùng.

## Việc còn lại và bài học

Kế hoạch 14 chưa hoàn tất: migration/index truy vấn, review/editor metadata-facts có actor/time/reason, nâng legacy ở draft theo lô, parser spans/bảng nối trang/văn xuôi/kỳ thời gian, claim gate prose và mở rộng method/multiturn/cache, preview/SSE/E2E, graceful worker rollout. Các ca không có fact tương thích hiện từ chối bảo thủ; có thể thiếu đáp án dù prose chứa dữ liệu. Không trình bày đây là tăng recall hoàn chỉnh.

Giữ provenance gốc và active index; người dùng chưa cần xóa hoặc upload lại. Muốn kiểm E2E tiếp cần mở Docker/dịch vụ dev lại. Bài học: test số xuất hiện trong văn bản không chứng minh quan hệ năm; cần tuple context và evidence, đồng thời không chuyển DB down thành missing.
