# Phiên #403 — Kiểm tra Redis có làm lặp lỗi upload cũ hay không

## Mục tiêu

Đối chiếu code và runtime để xác định việc sửa lỗi rồi chạy lại vẫn báo lỗi có phải do Redis lưu kết quả lỗi cũ hay không.

## Kết quả kiểm tra

- Redis hiện chỉ có một khóa `rag:cache` phục vụ câu trả lời chatbot; không có `arq:queue`, `arq:job:*`, `arq:result:*` hoặc lease `qnu:job-execution:*`.
- PostgreSQL hiện có 57 job `completed`, không có job `failed`, `queued`, `running` hoặc `retrying`.
- API/UI đọc trạng thái và lỗi ingestion từ `KnowledgeImportItem`/`JobRecord` trong PostgreSQL, không đọc lại kết quả lỗi ARQ trong Redis.
- Retry batch xóa `failure_code`, `failure_detail`, tăng `retry_count`, tạo `JobRecord` mới với UUID mới rồi enqueue broker ID mới.
- Retry job chung tăng `attempt` và dùng broker ID `{job.id}:attempt:{attempt}`, nên không đụng ARQ key của lần chạy trước.
- Worker có cron reconciliation 15 giây để phát lại job durable khi Redis mất job; job terminal không được tự chạy lại.

## Các trường hợp dễ bị hiểu nhầm là Redis cache lỗi

1. Worker Python chưa restart sau khi sửa code: job mới vẫn chạy code cũ và tái hiện đúng lỗi cũ. Đây là nguyên nhân đã từng xảy ra ở phiên #390.
2. PostgreSQL còn `failure_detail` vì người dùng chưa gọi đúng thao tác retry; refresh giao diện tiếp tục hiện lỗi bền vững từ DB.
3. Structured artifact/canonical extraction được tái sử dụng theo `artifact_key`; đây là cache ở PostgreSQL/storage, không phải Redis.
4. Sau khi reset PostgreSQL nhưng không reset Redis, worker có thể nhặt ARQ job mồ côi và log `missing`. Wrapper kiểm tra DB rồi kết thúc job đó; ID mới không bị ảnh hưởng.

## Kết luận

Không có bằng chứng Redis hiện giữ lỗi upload cũ. Kiến trúc retry hiện đã tách broker ID theo job/attempt. Rủi ro thực tế cần ưu tiên kiểm tra là worker chưa nạp code mới và artifact cũ được reuse từ PostgreSQL.

Không thay đổi code, dữ liệu, Redis hoặc tiến trình trong phiên này.
