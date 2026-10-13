# Phiên #404 — Chẩn đoán publish 409 sau khi khởi động lại

## Mục tiêu

Kiểm tra lỗi `409 Conflict` / `Cần duyệt dữ liệu có cấu trúc` sau khi người dùng tắt và khởi động lại laptop, đồng thời xác định Redis có giữ lỗi cũ hay không.

## Bằng chứng runtime

- PostgreSQL đang ở migration head `20261012_sync_struct_review`.
- Kho `col_admissions` có 19/19 index revisions `ready`, toàn bộ parity pass; generation `vg_2fd42633fb29` vẫn `building` do chưa publish.
- Có 8 active source revisions mang `status=ready` nhưng structured artifact vẫn có `review.status=required`; tổng cộng 23 issues.
- Tám nguồn gồm: báo cáo tư vấn 2024, báo cáo tư vấn 2025, khảo sát tư vấn 2022, các ngành tuyển sinh 2025, flyer tuyển sinh 2026, hướng dẫn nhập học, NQ57 phương hướng 2025 và phương hướng tuyển sinh 2024.
- Issues gồm `VISUAL_CONTENT_REVIEW` và `TABLE_HEADER_UNRESOLVED`.
- Redis không có upload/index job chờ xử lý. Các key hiện tại chỉ là cron reconciliation đang chạy, health-check và một RAG cache; `arq:queue` có 0 job.
- PostgreSQL có 57 job completed, không có queued/running/failed job.

## Nguyên nhân

- Publish Quality Gate đọc trực tiếp structured artifact và trả `FACT_SET_REVIEW_REQUIRED` nếu artifact còn issue mà chưa có `review.status=approved`.
- Frontend chỉ bật nút publish khi `source_status === ready` và vector ready; trang chi tiết chỉ hiện khối duyệt khi revision status là `review_required`.
- Vì 8 bản ghi hiện có `source_status=ready` nhưng artifact vẫn `required`, UI báo `Đã nạp · Chờ xuất bản` và cho bấm, còn backend chặn 409. Đây là state-contract drift giữa source status và artifact review, không phải Redis cache.

## Đề xuất trước khi triển khai

1. Backend trả trường dẫn xuất `structured_review_status`/`requires_structured_review` từ artifact tại read boundary, không lấy `source.status` làm nguồn sự thật duy nhất.
2. Frontend dùng trường này để vô hiệu hóa Xuất bản, hiển thị đúng các nguồn cần duyệt và liên kết thẳng tới trang đối soát.
3. Endpoint review dựa trên artifact review invariant, sau duyệt cập nhật đồng thời artifact và source state.
4. Thêm reconciliation idempotent cho các bản ghi legacy lệch trạng thái; không tự duyệt.
5. Thêm regression API/UI cho trạng thái `ready + artifact required` để nút publish không được bật sai.

Phiên này chỉ chẩn đoán read-only; không duyệt, publish, sửa DB, xóa Redis, re-index hoặc thay đổi runtime code.
