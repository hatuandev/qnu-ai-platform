# Context558 — Điều chỉnh Automatic Document Ingestion

Ngày 2026-10-19. Yêu cầu sản phẩm mới ưu tiên chuẩn hóa tự động; Smart Approval chuyển sang Advanced Review. Phần mã đã làm được giữ nguyên.

## Audit trước sửa luồng ingestion

- `qnu_serving.prepare_standard_revision` hiện luôn đặt overall_status=warning và structured_review_required=true cho bản chuẩn, kể cả không có lỗi nội dung.
- `get_structured_review_state` gộp context proposal publication_blocked và mọi ô ambiguous vào một cờ requires_review. ChunkSet, queue_vector_load, generation candidate/publication và RAG row/evidence cùng dùng cờ này.
- Ingestion chỉ đặt source ready/active_source_revision khi Quality Gate passed. Đây là pointer bản nội dung hiện hành, khác active_index_revision/publication epoch. Nạp vector hiện tạo points staging, is_retrievable=false; xuất bản là hành động riêng có quyền, parity và CAS.
- Semantic proposal chưa áp dụng vốn không thay tables/graph/facts. Có thể giữ proposal và các issue trong artifact, kiểm tra nội dung nguồn độc lập; không cần giả vờ duyệt 18 issue.

## Thiết kế tối thiểu trước triển khai

Thêm policy `automatic-content-v1`, ba kết quả AUTO_READY / READY_WITH_LIMITATIONS / NEEDS_ATTENTION. Chỉ opt-in bản nạp/reparse mới qua pipeline chính; không chuyển trạng thái dữ liệu cũ bằng batch hoặc sửa DB thật.

Kết quả ghim canonical pair, source hash, revision, bảng/manifest/graph/facts và Quality Gate. Khi marker hợp lệ, cờ review nội dung lấy từ kết quả này; Semantic Review vẫn riêng và không được chứng nhận bằng marker. Thay đổi dữ liệu hoặc Quality Gate làm marker không còn hợp lệ và chặn lại.

Ký hiệu nguyên văn đọc được nhưng chưa giải nghĩa có thể dùng dạng mô tả: giữ raw + ambiguous, không fact số/không 0. Phân biệt `literal_uninterpreted` với `source_explicit`; không tuyên bố nguồn không định nghĩa chỉ vì model không tìm thấy. Unreadable, mất bảng, sai hash, lỗi toàn vẹn và cảnh báo chưa có căn cứ an toàn vẫn NEEDS_ATTENTION.

Kiểm tra máy không cấp publication. Nạp vector chỉ staging; publication vẫn phải qua quyền, collection, revision, parity, CAS và snapshot hợp lệ. Không chạy LLM, reparse nguồn thật, index thật, publish thật, commit/push/deploy.

## Regression cần tái hiện trước sửa

1. DOCX nội dung sạch vẫn bị ép chờ duyệt.
2. Pending semantic assertion không thay nguồn nhưng chặn chunk/index.
3. Raw unknown đọc được không được thành 0/fact; unreadable vẫn chặn.
4. Marker cũ không còn hợp lệ sau sửa hash/bảng/quality.
5. Index staging không tự publish; thiếu quyền/sai collection/stale revision vẫn chặn.
6. Advanced Review và snapshots v1/v2/v3 giữ contract; không tự duyệt dữ liệu thật.
