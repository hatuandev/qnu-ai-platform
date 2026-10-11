# Phiên #341 — Chạy lại E2E sau sửa OCR và page provenance

## Mục tiêu và ranh giới

Chạy app thật qua trình duyệt: tạo nhóm lưu trữ, tải tệp, chọn nguồn, nạp, thử lại, lập chỉ mục và xuất bản. Đối chiếu PostgreSQL và gọi HTTP RAG thật để kiểm tra trang trích dẫn. Không reset/migrate DB, không sửa qnu-sso, không đổi khóa ModelOps, không sửa mã production, không commit. Các tài liệu là dữ liệu tổng hợp có nhãn rõ, không phải thông tin tuyển sinh chính thức và không gắn chatbot nghiệp vụ.

## Dữ liệu và môi trường

- Docker PostgreSQL, Redis, MinIO, Qdrant và Gotenberg đang chạy.
- UI `localhost:3000`; API `127.0.0.1:8001`.
- Provider hiện có trong DB: vLLM `bge-m3` 1024D / `bge-reranker-v2-m3`; PaddleOCR-VL. Không ghi khóa vào script hoặc báo cáo.
- Nhóm mới `doc_grp_428d83e08e05`: **E2E 341 - Kiểm chứng sau sửa**.
- Ba tệp: PDF native 2 trang, PDF scan 2 trang không có text layer, PDF hỏng 40 bytes. Mức phí 21.341.000 đồng/năm là số liệu giả định chỉ để kiểm thử ở trang 2.
- Kho đầu `col_4893132e0653` dùng để phát hiện tiến trình cũ; kho nghiệm thu runtime mới `col_b04b7104008f`: **E2E 341 v2 - Runtime mới**, generation `vg_2a83fc999ba4`.

## Vấn đề runtime và diễn biến

1. API/ARQ đang chạy từ trước bản sửa #340. Nạp đầu tiên còn tạo source normalizer v1; chưa dùng kết quả này để kết luận bản sửa đúng.
2. Xác minh ba JobRecord cũ ghi running nhưng broker đã completed/failed từ 13:15, không có ingestion lease và queue rỗng. Chỉ sau kiểm tra này mới khởi động lại đúng ARQ dev process. Không chỉnh trạng thái JobRecord cũ.
3. Nạp lại qua UI chạy PaddleOCR-VL thật, nhận đủ 2 trang; source v2 có manifest trang thật. Confidence bằng 0 theo sentinel unavailable, không còn giả định 0.98.
4. Bước lập chỉ mục từ API cũ vẫn tạo chunk vượt ranh giới trang. Khởi động lại đúng API dev process và tạo kho kiểm thử mới để không dùng lại chunk/index của tiến trình cũ. Không thay generation đang phục vụ dữ liệu nghiệp vụ.
5. Batch mới `imp_batch_45056e8060c7` đầu tiên: 1 thành công, 2 thất bại. Một lỗi dự kiến là PDF hỏng; một lỗi không mong đợi là `VECTOR_INDEXING_FAILED`, provider không còn khóa khả dụng khi nạp đồng thời.
6. Bấm **Thử lại 2 mục lỗi** trên UI: PDF scan thành công; PDF hỏng vẫn thất bại. Đây là phục hồi bằng retry, không phải chứng minh lỗi song song đã được sửa. Chưa xác định nguyên nhân gốc của key-pool.
7. **Lập chỉ mục → Xuất bản** qua UI: 2 nguồn được xuất bản, 6 chunks hoạt động, generation active. Hai index active đều parity_passed=true.
8. Trang thêm nguồn sau xuất bản hiện **Đã có / Đã lập chỉ mục**, vô hiệu hóa chọn lại hai tệp hợp lệ.

## Ma trận kiểm chứng thực tế

| Ca | Kết quả | Bằng chứng / giới hạn |
| --- | --- | --- |
| Upload vào Kho tài liệu không chạy OCR | Đạt | Tải cả 3 tệp bằng UI; OCRJobLog/source counts không tăng trước import |
| Native PDF + scan PDF qua Knowledge | Đạt sau retry | Source v2, manifest 2 trang; scan gọi Paddle thật trên worker mới; kho mới tái sử dụng artifact v2 |
| File hỏng không ngăn tệp hợp lệ | Đạt | PDF hỏng báo INGESTION_ERROR, không xuất bản; 2 nguồn còn lại active |
| Nạp đồng thời lần đầu | Chưa đạt | Scan lỗi provider key unavailable; retry thành công, lỗi vẫn cần xử lý |
| Publish và Qdrant parity | Đạt | UI 2 nguồn / 6 chunks; DB 2 index active, parity đạt |
| RAG Search trang 2 | Đạt | HTTP 200, 5 kết quả, rank 1 chứa đúng số liệu ở page_number=2 |
| RAG Ask và citation | Đạt qua API | HTTP 200, status answered, số liệu đúng và citation quote ở trang 2; nêu rõ đây là số liệu giả định |
| Chatbot UI/SSE/citation sheet | Chưa chạy | Không tạo hoặc gắn trợ lý nghiệp vụ trong phiên này |
| 100 tệp, embedding model thứ hai | Chưa chạy | Chỉ 3 fixtures / 1 embedding model; reranker không phải embedding thứ hai |
| Delete snapshot, rollback, provider down, CAS race | Chưa chạy | Không suy rộng từ happy path hoặc ca file hỏng |
| Ruff scripts kiểm thử | Đạt | Hai helper check/format exit 0 |
| Full pytest / FE build | Không chạy lại | Không đổi code production; #340 có 787 passed / 9 failed / 2 skipped, không xem là suite sạch |

## Điểm còn cần sửa

- Lỗi lấy khóa provider trong batch đồng thời: cần đối chiếu key lease/rate limiting và cơ chế retry/backoff, không thay credential để che lỗi.
- Candidate PDF hỏng bị nhãn **Có bản mới** dù chưa thay tệp, thay vì trạng thái thất bại/thử lại.
- Nguồn pending chỉ hiện binding ID, mất tên tệp trên danh sách; header **Nhóm nguồn 0** vẫn dùng khái niệm cũ dù đang có nguồn tài liệu.
- Có khoảng trễ cache candidate sau retry: vừa đóng modal từng hiện Chưa nạp cho nguồn đã hoàn tất; điều hướng lại lấy đúng dữ liệu. Cần invalidation đúng, không chỉ dựa F5.
- Các JobRecord cũ running trong DB nhưng broker complete cần review reconciliation riêng; chưa chỉnh trực tiếp dữ liệu.

## Tệp thay đổi và bằng chứng

- Thêm `backend/scripts/create_e2e_341_fixtures.py`: tạo fixtures UTF-8, kiểm tra scan không có text layer và render hai trang để quan sát.
- Thêm `backend/scripts/verify_e2e_341_live.py`: kiểm tra source v2, 2 active indices/parity, search và ask/citation qua HTTP thật. Đây là helper kiểm chứng read-only đối với DB; endpoint ask có thể ghi log/quota theo runtime thông thường. Không chứa khóa; login lấy cấu hình dev hiện có.
- Đồng bộ nhật ký, README nhật ký, PROJECT_CONTEXT và WORK_LOG.
- Bằng chứng runtime (không commit): `backend/storage/e2e_fixtures/341/live_verification.json`, `published_v2.jpg`, `already_indexed_v2.jpg`, worker/API logs và fixtures. Không thêm các runtime outputs vào source control.

## Kết luận

Luồng chính đạt sau restart đúng tiến trình và retry. Sửa page provenance #340 đã được kiểm chứng trên runtime mới với 6 chunks và citation trang 2. Chưa thể gọi là E2E toàn diện hoặc production-ready: batch đồng thời vẫn có lỗi provider-key availability và một số trạng thái UI chưa nhất quán. Giữ dữ liệu kiểm thử có nhãn để người dùng đối chiếu; không xóa dữ liệu hoặc reset DB. Bài học: ARQ không tự reload; phải kiểm chứng phiên bản source/chunk thực sự chạy thay vì chỉ dựa file code hoặc build pass.
