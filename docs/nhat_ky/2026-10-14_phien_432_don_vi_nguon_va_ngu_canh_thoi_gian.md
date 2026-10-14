# Phiên 432 Đơn vị nguồn và ngữ cảnh thời gian

Ngày: 2026-10-14. Mục tiêu: triển khai ba đề xuất đã được duyệt về ngữ cảnh từng đoạn, cấu trúc tìm kiếm dùng chung và kiểm thử chỉ mục riêng. Một văn bản ban hành năm 2026 có thể chứa dữ liệu năm 2022, 2023, 2024; ngày ban hành không được thay thế năm dữ liệu.

## Kết quả triển khai

Nguồn chuẩn hóa có `source-units-v1`: tiêu đề, đoạn, mục danh sách, bảng và hàng bảng, quan hệ cha con, đường dẫn tiêu đề, vị trí ký tự và trang khi có dấu trang thật. Đây là cấu trúc trên Markdown chuẩn đã bóc tách, không phải thay thế toàn bộ cây native của từng parser. Nội dung gốc giữ nguyên để đối soát; nội dung gửi embedding bổ sung tiêu đề và header bảng, giữ đủ header nhiều tầng bằng thuật toán cấu trúc sẵn có.

`TemporalScope` tách ngày ban hành, năm được nhắc, năm trong tiêu đề, năm dữ liệu và vai trò data/effective/event/unknown. Chỉ scope data đã duyệt mới lọc cứng theo năm. Năm trong tên tệp, ngày ban hành hoặc tiêu đề không tự biến thành năm dữ liệu. Câu hỏi cũng tách năm dữ liệu khỏi năm văn bản và sự kiện; khoảng năm ngắn có thể mở rộng nhưng không được tự thêm năm ngoài yêu cầu.

Đề xuất ngữ cảnh bằng mô hình là tùy chọn qua `chunk_config.unit_temporal_annotation`. Model/provider phân giải từ ModelOps DB, không có API key hoặc model gán cứng. Phiên bản này đề xuất cho đoạn văn có năm được nhắc; danh sách, bảng và đoạn không ghi năm không được tự phân loại. Quote phải khớp đúng đơn vị nguồn, năm phải có trong quote; kết quả chỉ là proposed và yêu cầu duyệt nguồn. Lỗi dịch vụ/định dạng/thời gian ghi trạng thái unavailable, giữ ngữ cảnh chưa xác nhận, không tạo năm hoặc dữ liệu giả.

Hiệu đính qua API context có `units` và `expected_unit_manifest_hash`, gắn revision, lý do, người sửa và vòng duyệt. Bảng có các header năm lặp y hệt được đánh dấu mơ hồ để đối soát; không tự đổi cột 2024 lặp thành 2025. Chưa có giao diện hiệu đính từng đơn vị mới.

Chunk set pin digest của manifest. PostgreSQL và Qdrant giữ cùng metadata đơn vị nguồn; metadata bổ sung không được ghi đè tenant/workspace/hash đã kiểm tra. Dense/FTS và BM25 dùng cùng quy tắc scope data đã duyệt; evidence kiểm digest source/index và quote gốc, bổ sung ngữ cảnh cha cùng nguồn. Fact lịch sử giữ năm của fact, không nhận năm văn bản làm scope toàn bảng.

## Tệp thay đổi

- Mới: `knowledge/normalization/retrieval_models.py`, `retrieval_units.py`, `knowledge/services/unit_annotation.py`.
- Ingestion: `schemas.py`, `source_artifact.py`, `source_context.py`, `source_ingestion_service.py`, `chunk_set_service.py`, `vector_generation_service.py`.
- Retrieval: `rag/vector_indexer.py`, `retriever.py`, `evidence_blocks.py`, `evidence_bm25.py`, `evidence_facts.py`, `evidence_schemas.py`, `evidence_model.py`, `evidence_validation.py`, `evidence_pipeline.py`, `evidence_retrieval.py`.
- Kiểm thử mới: `tests/test_knowledge_units.py`, `test_knowledge_units_integration.py`.
- Đồng bộ hướng dẫn ingestion/RAG, memory, snapshot và work log.

## Kiểm thử

Hai regression ban đầu tái hiện lỗi loại fact 2023 trong văn bản 2026 và gán năm tiêu đề cho mọi đoạn; đã sửa và kiểm tra lại. Bộ trọng tâm cuối gồm 95 ca đạt trong 5,05 giây, phủ cấu trúc, header nhiều tầng, scope đa lĩnh vực, hash/quote sai, hiệu đính, provider lỗi, quá dài, dense/lexical và truy vấn nhiều vai trò năm. Ca cuối xác nhận giữ provider quản trị chỉ định khi lấy tên model mặc định. Ruff toàn backend đạt; có cảnh báo quyền đọc các thư mục pytest cũ. Không sửa frontend nên không chạy Vite/Biome.

Hai integration thật đạt trong 13,23 giây: build chỉ mục Qdrant riêng bằng embedding đang cấu hình; so PostgreSQL/Qdrant metadata, dense/FTS/BM25, tenant isolation, giữ pointer chưa publish; mô hình đang cấu hình phân biệt năm dữ liệu 2023, năm văn bản dẫn chiếu 2020 và sự kiện 2024. Tài nguyên thử dùng tên duy nhất, DB rollback và collection Qdrant thử đã dọn, không đụng chỉ mục thật. Đây là kiểm chứng kỹ thuật, không phải chứng nhận accuracy/Ragas cho 82 câu hỏi.

Full suite sau bổ sung header: 1198 passed, 11 failed, 15 skipped trong 168,75 giây. Không có lỗi mới trong phần thay đổi; 11 lỗi trùng danh sách nền của lượt 1194 passed trước đó: hai consulting exports, sáu publishing/canary/GC/direct-upload, reconciliation, auth cookie và universal tools. Kết quả được giữ tại `backend/storage/pytest432_handoff_full.log`. Chỉnh giữ explicit provider thực hiện sau khi lượt full đã bắt đầu, được kiểm tra riêng trong bộ 95 ca cuối; không tuyên bố full suite xanh.

## Vận hành và phạm vi còn lại

Không reset DB, không đổi cấu hình trợ lý hoặc embedding, không nạp lại hay xuất bản 19 nguồn thật. Không upload văn bản tổng hợp của người dùng. Backup vẫn tạm dừng, quota nội bộ vẫn unlimited.

Nguồn cũ được dựng đơn vị đọc tương thích nhưng không tự ghi lại metadata hoặc coi năm là verified. Muốn vector có metadata mới phải build chỉ mục staging từ revision đã đối soát, thử RAG với snapshot đó rồi xuất bản theo thao tác quản trị. Khởi động lại backend/worker trước khi dùng code mới. Bật annotation là lựa chọn cấu hình API, không tự bật cho mọi kho.

Chưa triển khai khoảng hiệu lực ngày từ/đến, lịch sử chồng lấn đầy đủ, cây native cho mọi parser hoặc màn hình hiệu đính từng unit. Cần thử các câu lịch sử, so sánh năm, ngày ban hành, thiếu nguồn và paraphrase trên corpus thật trước cutover; không ép 82/82 answered khi nguồn không đủ.

## Bài học

Năm được nhắc là tín hiệu tìm kiếm, không phải bằng chứng về kỳ dữ liệu. Cấu trúc tìm kiếm và trích dẫn cần chung ID/hash nhưng khác cách trình bày: embedding có ngữ cảnh bổ sung, quote vẫn là span nguyên bản. Kiểm thử chỉ mục riêng phải kiểm cả nội dung và ranh giới phục vụ, không chỉ số lượng vector.
