# Phiên #349 — Worker local dev và xử lý queue thực tế

## Mục tiêu / phạm vi

Người dùng yêu cầu chạy worker để nạp tài liệu và chuẩn bị cho nhiều người dùng. Bổ sung worker vào dev runner, xử lý batch đang chờ, giữ nguyên batch đã hủy. Không reset DB, không xóa tài liệu, không sửa qnu-sso hay RAG/DAG. Áp dụng backend/clean-code skills; test regression cancellation fail trước khi sửa, đạt sau sửa.

## Thay đổi

- `scripts/start-worker.ps1`: khởi động ARQ từ backend venv, cửa sổ ẩn, stdout/stderr riêng từng lần chạy; lưu PID + start ticks để nhận diện worker và tránh mở trùng khi gọi tuần tự. Log/state được gitignore. Đây không phải service supervisor hay khóa chống hai launcher đồng thời.
- `make.ps1`, `make.bat`, `Makefile`, `make`: dev mở thêm worker; có lệnh worker độc lập; cập nhật help. PowerShell dev dừng khi ensure-ready thất bại, worker launcher lỗi sẽ ngăn tiếp tục mở API/FE.
- `backend/app/workers/arq_worker.py`: heartbeat mỗi 15 giây thay vì mặc định 3600 giây. Giữ max_jobs=10/job_timeout=300, chưa tune tải.
- `backend/app/workers/tasks.py`: `IMPORT_CANCELLED` từ service được rollback/refresh rồi đánh dấu job cancelled, không ném thành lỗi để ARQ retry batch đã hủy.
- Tests: `test_workers.py` thêm cancellation regression; `test_worker_dev_startup.py` kiểm tra hợp đồng launcher của 4 runners, log/ẩn cửa sổ và heartbeat. Các kiểm tra runner là static, không giả định đã E2E mọi shell.

## Kiểm chứng runtime

- Worker đầu chạy trong sandbox không kết nối được AI server; file PDF text thành công, scan thất bại kết nối. Kiểm tra TCP ngoài sandbox thành công. Dừng đúng worker do phiên này tạo, chạy worker với quyền truy cập mạng được phê duyệt, retry riêng item failed của batch chưa hủy.
- `imp_batch_08adcf9d69bf`: completed, succeeded=2, failed=0. Revision `ks_rev_b455a149a940` ready, 14 trang, chunk set ready 16 chunks. Revision `ks_rev_e72d84c9db88` ready, 48 trang, chunk set ready 71 chunks. Log xác nhận gọi PaddleOCR-VL `/layout-parsing` với PDF scan 18.5 MB, task retry hoàn tất khoảng 16.86 giây.
- `imp_batch_ede277adfa6e`: cancelled, hai items skipped/BATCH_CANCELLED, không resume. Job records của các lần chạy cũ giữ nguyên lịch sử lỗi; không sửa lịch sử để báo cáo đẹp.
- Sau khi queue rỗng, khởi động lại đúng worker vừa tạo để nhận code cancellation mới. PID launcher cuối 10660; gọi launcher lần nữa trả already running cùng PID. Queue 0, health 17:41:49, ongoing=0. PID runtime không phải cấu hình cố định.
- Batch không có vector_generation_id: đây là xác nhận snapshot/parse/OCR/chunk thật, **không phải xác nhận embedding/Qdrant publish hay browser E2E**.
- Full pytest có gửi một số job dùng fixture rồi rollback; worker gặp `Job record not found` với các ID test. Sau test đối chiếu lại hai batch người dùng, trạng thái không đổi.

## Verification

- PowerShell AST parse launcher và make.ps1: không lỗi. Kiểm tra launch + gọi lại: không mở trùng tuần tự.
- Ruff toàn backend: đạt (có cảnh báo access denied ở các thư mục test cũ).
- Tests worker/startup: 13 passed. Full backend: **822 passed, 13 failed, 2 skipped**, 27.03 giây. 13 failures trùng nhóm đã ghi #347: 6 API RBAC, 1 reconciliation, 1 auth actor role, 5 consulting/tools phụ thuộc facts live seed. Không sửa ngoài phạm vi để ép suite xanh.
- Không đổi FE, không chạy FE build. Không benchmark nhiều người dùng hay tải 100 file.

## Vận hành tiếp theo

Local dev có worker không thay thế production service. Docker/service cần restart/monitoring; concurrency phải giới hạn theo RAM và năng lực server OCR/embedding. max_jobs=10 là giới hạn mỗi worker, chưa chứng minh 10 PDF lớn đồng thời an toàn. Worker là process riêng không tự reload mã; sau sửa task, restart khi không có job đang xử lý. Test tích hợp nên có queue/DB riêng để không giao fixture job cho worker dev.

Đồng bộ hướng dẫn khởi động, journal index, PROJECT_CONTEXT, memory snapshot và WORK_LOG. Không commit hay dọn các thay đổi cũ của người dùng.
