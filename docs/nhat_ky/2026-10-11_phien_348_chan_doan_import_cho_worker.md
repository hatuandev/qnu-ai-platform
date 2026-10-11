# Phiên #348 — Chẩn đoán nạp nguồn đứng ở snapshot

## Yêu cầu / phạm vi

Người dùng vừa reset DB/chạy dev, nạp hai tài liệu rồi thêm nguồn bị đứng 0%. Kiểm tra read-only theo skills backend/clean-code; không sửa runtime, khởi động worker, phát lại/hủy job, reset DB hay xóa tài liệu.

## Bằng chứng

- Batch trong ảnh `imp_batch_ede277adfa6e` đã cancelled khi kiểm tra; hai item skipped ở phase snapshot.
- Batch trước đó `imp_batch_08adcf9d69bf` vẫn queued.
- 4 JobRecord knowledge_source_ingestion đều queued/dispatched, có broker IDs; Redis `arq:queue` có đúng 4 job, không có marker in-progress.
- Health key còn tồn tại nhưng nội dung từ 17:06:20, j_ongoing=0/queued=0; kiểm tra lúc 17:28:59 cho TTL còn 2242s. ARQ mặc định heartbeat interval 3600s nên không thể coi key tồn tại là worker còn sống.
- Các Python process đọc được đều khởi động khoảng 17:23:19–20. Đọc command line qua Win32_Process bị Access denied nên không khẳng định từng process là gì.
- `make.ps1 dev`, `Makefile dev` chỉ khởi động API và FE, không khởi động ARQ worker. Đây là thiếu sót vận hành phù hợp với việc queue không có consumer; không phải bằng chứng lỗi OCR/embedding vì chưa tới bước đó.

## Hướng xử lý đề xuất

Chạy worker đúng repo/config `python -m arq app.workers.arq_worker.WorkerSettings` từ backend. Worker sẽ nhận các job queued đã dispatch; không cần upload lại hay reset DB. Không tự mở worker vì sẽ xử lý đợt còn lại của người dùng; cần người dùng yêu cầu xử lý/khởi động.

Nên sửa task runner dev để quản lý API+FE+worker đồng bộ và hiển thị tình trạng chờ worker thay vì gọi tất cả queued là Đang xử lý. Không tự sửa theo câu hỏi chẩn đoán hiện tại. Không tự khôi phục đợt đã cancelled.

## Verification

DB/Redis và task runner đã đối chiếu read-only; xác minh ARQ CLI hiện có. Không chạy pytest/build vì không sửa mã ứng dụng. Chưa xác minh xử lý snapshot/OCR thật của hai file này.
